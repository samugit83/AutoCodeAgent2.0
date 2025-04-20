import numpy as np
import redis
import json
import re # Import re for parsing
from reinforcement_learning.qlearn_agent import QLearningAgent
from params import PARAMS
from .prompts import EXTRACT_QUERY_FEATS_PROMPT, SUGGEST_ACTION_PROMPT, RAG_ANSWER_PROMPT
from models.models import call_model
from code_agent.utils import sanitize_gpt_response

# Helper function to extract categories from prompt template
def _extract_categories_from_prompt(prompt_template, feature_name):
    """Extracts list items for a given feature from the prompt template."""
    match = re.search(rf"- {feature_name}:.*?\[(.*?)\]", prompt_template.template, re.DOTALL)
    if match:
        # Extract the content within the brackets and split into items
        categories_str = match.group(1).strip()
        # Split by comma, strip quotes and whitespace
        categories = [cat.strip().strip("'\"") for cat in categories_str.split(',')]
        return categories
    return []


class RlMetaRag:
    def __init__(self,
        model=PARAMS.get("RL_META_RAG_MODEL"),
        data_file=PARAMS.get("RAG_Q_DATA_FILE"),
        n_recent=PARAMS.get("RL_N_RECENT"),
        error_threshold=PARAMS.get("RL_ERROR_THRESHOLD"),
        alpha=PARAMS.get("RL_ALPHA"),
        gamma=PARAMS.get("RL_GAMMA"),
        epsilon=PARAMS.get("RL_EPSILON"),
        socketio=None,
        request_human_evaluation=PARAMS.get("RL_REQUEST_HUMAN_EVALUATION")):
        """
        Initializes the RL Meta RAG system with a Q-Learning agent for RAG technique selection.
        
        Args:
            data_file: File for persisting Q-learning data.
            n_recent: Number of recent episodes to compute average error.
            error_threshold: Threshold to decide whether to use Q-learning or LLM suggestion.
            alpha: Learning rate for Q-learning.
            gamma: Discount factor.
            epsilon: Exploration rate for epsilon-greedy.
            socketio: Socket.IO instance for real-time frontend communication.
        """

        question_type_categories = _extract_categories_from_prompt(EXTRACT_QUERY_FEATS_PROMPT, 'question_type')
        domain_categories = _extract_categories_from_prompt(EXTRACT_QUERY_FEATS_PROMPT, 'domain')

        # Create maps for the agent (index -> list of categories)
        # The agent will create index maps from these lists internally
        category_maps = {
            0: question_type_categories, # Index 0 corresponds to question_type
            1: domain_categories      # Index 1 corresponds to domain
        }

        # Calculate state_dim based on one-hot encoding dimensions + other features
        # Features: question_type (cat), domain (cat), has_entities (bool), 6 numericals
        num_bool_features = 1 # has_entities
        num_numerical_features = 6 # complexity, ambiguity, query_length, specificity, formality, urgency
        state_dim = len(question_type_categories) + len(domain_categories) + num_bool_features + num_numerical_features

        self.agent = QLearningAgent(
            data_file=data_file,
            n_recent=n_recent,
            alpha=alpha,
            gamma=gamma,
            epsilon=epsilon,
            mode='neural',
            state_dim=state_dim, # Use calculated state_dim
            n_actions=3, # Assuming 3 RAG techniques still
            category_maps=category_maps # Pass the dynamic maps
        )
        self.rag_techniques = {
            0: self._llama_index,
            1: self._hyde_rag,
            2: self._adaptive_rag,
            # Additional RAG techniques can be added here
        }
        self.n_recent = n_recent
        self.error_threshold = error_threshold
        self.epsilon = epsilon
        self.socketio = socketio
        self.model = model
        self.request_human_evaluation = request_human_evaluation

    def _extract_query_features(self, query):
        """
        Extracts features from the query using the LLM.
        """
        prompt = EXTRACT_QUERY_FEATS_PROMPT.substitute(query=query)
        features_str = call_model(
            chat_history=[{"role": "user", "content": prompt}],
            model=self.model
        )
        features_str = sanitize_gpt_response(features_str)
        try:
            # Expecting a list: [question_type, domain, has_entities, complexity, ambiguity, query_length, specificity, formality, urgency]
            features = json.loads(features_str)

            # Basic validation
            if not isinstance(features, list) or len(features) != 9:
                 raise ValueError(f"Expected 9 features in a list, got: {features}")

            # Convert boolean-like strings/values if necessary (LLM might return strings)
            if isinstance(features[2], str):
                 features[2] = features[2].lower() == 'true'
            elif not isinstance(features[2], bool):
                 features[2] = bool(features[2]) # Attempt conversion

            # Convert numerical features to float/int
            features[3] = float(features[3]) # complexity
            features[4] = float(features[4]) # ambiguity
            features[5] = int(features[5])   # query_length
            features[6] = float(features[6]) # specificity
            features[7] = float(features[7]) # formality
            features[8] = float(features[8]) # urgency

        except (json.JSONDecodeError, ValueError, TypeError, IndexError) as e:
            self.socketio.emit('reasoning_update', {
                "message": f"Error parsing features from LLM response: {e}. Response: '{features_str}'. Using default features."
            })
            # Provide default features matching the expected structure but indicating failure
            # Use the first category from maps, False for boolean, 0 for numericals
            q_cats = self.agent.category_maps.get(0, ['unknown'])
            d_cats = self.agent.category_maps.get(1, ['unknown'])
            num_numerical = 6
            features = [q_cats[0], d_cats[0], False] + [0.0] * num_numerical
            # Adjust query length specifically if needed
            features[5] = len(query.split()) # A reasonable default for query_length

        self.socketio.emit('reasoning_update', {
            "message": f"Extracted query features: {features}"
        })

        # Return the list of features directly (agent's preprocess expects this structure)
        return features # Should be a list: [cat1_val, cat2_val, bool_val, num1, num2, ...]
      

    def select_rag_technique(self, query):
        """
        Selects the most appropriate RAG technique for the given query.
        
        Args:
            query (str): The user query.
        
        Returns:
            int: The selected RAG technique ID.
        """
        self.socketio.emit('reasoning_update', {
            "message": "Selecting RAG technique..."
        })
        # Pass the raw query features list as the state
        state_features = self._extract_query_features(query)
        # Convert to tuple if QLearningAgent expects hashable state (simple mode)
        # For neural mode, the list is fine as it goes to _preprocess_state
        state = tuple(state_features) if self.agent.mode == 'simple' else state_features
        action = self.choose_action(query, state)
        return action

    def choose_action(self, query, state):
        """
        Chooses an action for the current state.
        - If there are at least n_recent errors, compute the average error.
        - If the average error is below error_threshold, use epsilon-greedy based on Q-values.
        - Otherwise (or if there is insufficient data), use an LLM suggestion.
        
        Returns:
            int: The chosen action (RAG technique ID).
        """

        error_list = self.agent.error_list
        
        if len(error_list) >= self.n_recent:
            recent_avg_error = np.mean(error_list[-self.n_recent:])
            self.socketio.emit('reasoning_update', {
                "message": f"Average error over the last {self.n_recent} episodes: {recent_avg_error:.3f}"
            })
            use_llm = recent_avg_error >= self.error_threshold
            if use_llm:
                self.socketio.emit('reasoning_update', {
                    "message": f"Using LLM suggestion because average error is too high. Error threshold: {self.error_threshold}"
                })
            else:
                self.socketio.emit('reasoning_update', {
                    "message": f"Using Q-learning because average error is below threshold. Error threshold: {self.error_threshold}"
                })
        else:
            self.socketio.emit('reasoning_update', {
                "message": "Not enough data yet to evaluate predictive quality. Using LLM suggestion."
            })
            use_llm = True
        
        if use_llm:
            return self.llm_suggest_action(query)
        else:
            q_values = self.agent.get_q_values(state)
            self.socketio.emit('reasoning_update', {
                "message": f"Q-values: {q_values}"
            })
            if np.random.uniform(0, 1) < self.epsilon:
                action = np.random.randint(0, len(self.rag_techniques))
                self.socketio.emit('reasoning_update', {
                    "message": f"Using random action because epsilon is too high. Epsilon: {self.epsilon}"
                })
            else:
                action = int(np.argmax(q_values))
                self.socketio.emit('reasoning_update', {
                    "message": f"Using Q-learning because epsilon is too low. Epsilon: {self.epsilon}"
                })
            return action


    def retrieve(self, query, session_id=None):
        """
        Retrieves documents using the selected RAG technique. If a session_id is provided,
        evaluation data (state, action, query) is stored in Redis for later Q-value updates.
        Also, if a Socket.IO instance was provided, emits a 'request_evaluation' event with the result.
        
        Args:
            query (str): The user query.
            session_id (str, optional): A unique session identifier.
        
        Returns:
            str: Retrieved documents as a string.
        """
        # Get state features first for potential storage
        state_features = self._extract_query_features(query)
        state = tuple(state_features) if self.agent.mode == 'simple' else state_features

        technique_id = self.choose_action(query, state) # Use pre-calculated state

        if technique_id in self.rag_techniques:
            result = self.rag_techniques[technique_id](query)
        else:
            self.socketio.emit('reasoning_update', {
                "message": f"Warning: Selected technique ID {technique_id} not found. Defaulting to technique 0."
            })
            technique_id = 0 # Reset ID for storage/evaluation consistency if needed
            result = self.rag_techniques[0](query)
        
        self.socketio.emit('reasoning_update', {
            "message": f"Generating answer with RAG context..."
        })

        rag_answer_prompt = RAG_ANSWER_PROMPT.substitute(query=query, context=result)
        rag_answer = call_model(
            chat_history=[{"role": "user", "content": rag_answer_prompt}],
            model=self.model
        )
        rag_answer = sanitize_gpt_response(rag_answer)
        
        if session_id and self.request_human_evaluation:
            redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)
            # Store the original feature list before tuple conversion if needed
            data_to_store = {
                "state": state_features,
                "action": technique_id,
                "query": query
            }
            redis_key = f"rl_update:{session_id}"

            try:
                redis_client.set(redis_key, json.dumps(data_to_store))
                self.socketio.emit('reasoning_update', {
                    "message": f"Stored evaluation data in Redis under key: {redis_key}"
                })
            except TypeError as e:
                 self.socketio.emit('reasoning_update', {
                    "message": f"Error storing evaluation data to Redis: {e}. Data: {data_to_store}"
                })


            if self.socketio:
                self.socketio.emit('reasoning_update', {
                    "message": f"Emitting request_evaluation event with session_id: {session_id}"
                })
                self.socketio.emit('request_evaluation', {"session_id": session_id, "assistant": rag_answer})

        return rag_answer

    def _llama_index(self, query):
        """Basic LlamaIndex RAG implementation."""
        from tools.rag.llama_index.retrieve import retrieve_documents
        text_list = retrieve_documents(query)
        return "\n".join(text_list) if isinstance(text_list, list) else str(text_list)

    def _hyde_rag(self, query):
        """Hypothetical Document Embedding RAG implementation."""
        from tools.rag.hyde_rag.retrieve import retrieve_hyde_documents
        return retrieve_hyde_documents(query)

    def _adaptive_rag(self, query):
        """Adaptive RAG implementation."""
        from tools.rag.adaptive_rag.retrieve import AdaptiveRAG
        return AdaptiveRAG().answer(query)

    def llm_suggest_action(self, query):
        """
        Uses the LLM with SUGGEST_ACTION_PROMPT to suggest a RAG technique,
        based solely on the query.
        
        Args:
            query (str): The original query string.
        
        Returns:
            int: The suggested RAG technique ID.
        """
        prompt = SUGGEST_ACTION_PROMPT.substitute(query=query)
        response_str = call_model(
            chat_history=[{"role": "user", "content": prompt}],
            model=self.model
        )
        response_str = sanitize_gpt_response(response_str)
        self.socketio.emit('reasoning_update', {
            "message": f"LLM suggested action: {response_str}. Executing selected RAG technique..."
        })
        try:
            suggested_action = int(response_str.strip())
        except Exception as e:
            self.socketio.emit('reasoning_update', {
                "message": f"Error parsing suggested action: {e}. Defaulting to action 0."
            })
            suggested_action = 0

        return suggested_action



