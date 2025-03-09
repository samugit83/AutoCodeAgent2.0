import json
import os
from typing import List, Dict
from .prompts import (
    SYSTEM_PROMPT_AGENT_PLANNER, 
    JSON_CHAIN_EXAMPLE, 
    DIPENDENT_AGENT_PROMPT,
    EGOT_GENERATION_PROMPT  
)  
from models.models import call_model
from .agent_session_manager import AgentSessionManager
from .agent_data_model import AgentDataModel
from .utils import sanitize_gpt_response, remove_html_body_tags
from .logging_handler import LoggingConfigurator
from .web_search import WebSearchAgent
from .egot_engine import EGoTEngine 
from .utils import apply_depth_settings 
from tools.rag.llama_index.retrieve import retrieve_documents
from params import PARAMS

class DeepSearchAgentPlanner:
    def __init__(self, chat_history: List[Dict], **kwargs):
        session_id = kwargs.get('session_id')
        if not session_id:
            raise ValueError("session_id is required")
        is_interactive = kwargs.get('is_interactive', True)

        self.data = AgentDataModel(name="DeepSearchAgentPlanner")
        self.data.memory_logs = []
        self.logger = LoggingConfigurator.configure_logger(self.data.memory_logs)
        self.enrich_log = LoggingConfigurator.enrich_log
        self.deep_search_model = PARAMS["DEEP_SEARCH_MODEL"]

        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not all([neo4j_uri, neo4j_user, neo4j_password]):
            raise EnvironmentError("Neo4j connection details are not fully set in environment variables.")
        self.egot_engine = EGoTEngine(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            logger=self.logger,
            session_id=session_id
        )

        if is_interactive:
            self.session_manager = AgentSessionManager(
                redis_host=os.getenv("REDIS_HOST", "redis"), 
                redis_port=int(os.getenv("REDIS_PORT", 6379)), 
                db=int(os.getenv("REDIS_DB", 0))
            )
            self.logger.info('🌀 Loading data from session manager: %s', f'planner-{session_id}', extra={'no_memory': True})
            self.data = self.session_manager.load_session(f'planner-{session_id}')

        self.data.kwargs.update(kwargs)
        self.data.session_id = self.data.session_id or f"planner-{self.data.kwargs.get('session_id', None)}"
        self.data.is_interactive = self.data.is_interactive or self.data.kwargs.get('is_interactive', False)
        self.data.user_id = self.data.user_id or self.data.kwargs.get('user_id', None)
        self.data.depth = self.data.depth or self.data.kwargs.get('depth', 1)
        self.data.data_sources = self.data.data_sources or self.data.kwargs.get('data_sources', ['websearch', 'rag'])
        self.data.delete_graph = self.data.delete_graph or self.data.kwargs.get('delete_graph', False)
        self.data.chat_history = chat_history
        self.data.start_system_prompt = self.data.start_system_prompt or self.data.kwargs.get(
            'start_system_prompt', SYSTEM_PROMPT_AGENT_PLANNER
        )
        self.data.initial_message = self.data.initial_message or next(
            (msg['content'] for msg in chat_history if msg.get('role') == 'user'), ''
        )
        self.data.output_final_partials = self.data.output_final_partials or [] 
        apply_depth_settings(self, self.data.depth)
        

    def reset_to_init_data_model(self):
        """
        Resets the AgentDataModel to its initial state.
        This method clears or resets fields that should return to their default values.
        """
        self.logger.info('🔁 Resetting DeepSearchAgentPlanner to initial state', extra={'no_memory': True})

        reset_fields = {
            'initial_message': '',
            'json_chain': None,
            'state': 'idle',
            'agent_chain_step': 0,
            'memory_logs': []
        }

        for field, value in reset_fields.items():
            setattr(self.data, field, value)
        if self.data.delete_graph:
            self.egot_engine.delete_graph()
            self.logger.info('🗑️ Deleted EGoT graph', extra={'no_memory': True})
        self.egot_engine.close()
        self.logger.info('✅ DeepSearchAgentPlanner has been reset to initial state', extra={'no_memory': True})

    def gen_prompt_for_subtask_agents(
        self, 
        agent_nickname: str, 
        connected_agents: List[Dict], 
        agent_llm_prompt: str,
        search_results: str
    ) -> str:
        json_chain_copy = self.data.json_chain.copy()
        connected_agents_str = ""
        connected_agent_nicknames = []
        if connected_agents:
            connected_agent_nicknames = [agent['agent_nickname'] for agent in connected_agents]
            connected_agents_str = f"These are the agents nicknames from which your input comes: {', '.join(connected_agent_nicknames)}\n"

        for agent in json_chain_copy['agents']:
            if agent['agent_nickname'] not in connected_agent_nicknames:
                agent.pop('observation', None)
        self.data.json_chain = json_chain_copy

        search_results_block = ""
        if search_results:
            search_results_block = (
                "\n**IMPORTANT:** The following detailed web search results have been "
                "retrieved to provide essential context and up-to-date information. "
                "You must carefully analyze and incorporate every relevant detail from "
                "these results into your task output to ensure accuracy and completeness:\n"
                f"{search_results}\n"
            )

        GENERATED_PROMPT = DIPENDENT_AGENT_PROMPT.substitute(
            agent_nickname=agent_nickname,
            agent_llm_prompt=agent_llm_prompt,
            connected_agents_str=connected_agents_str,
            json_chain_without_useless_info=json_chain_copy,
            initial_message=self.data.initial_message,
            user_questions=self.data.json_chain['agents'][self.data.agent_chain_step].get('user_questions', []),
            user_answers=self.data.json_chain['agents'][self.data.agent_chain_step].get('user_answers', []),
            min_token_output_type_final=self.min_token_output_type_final,
            search_results_block=search_results_block
        )
        return GENERATED_PROMPT

    def manage_user_questions(self, step: int) -> str:
        user_questions = self.data.json_chain['agents'][step].get('user_questions', []) 
        user_answers = self.data.json_chain['agents'][step].get('user_answers', []) 
        self.logger.info(
            self.enrich_log(
                f"💬 Updated User questions and answers for agent {self.data.json_chain['agents'][step]['agent_nickname']}: "
                f"Questions: {user_questions}, "
                f"Answers: {user_answers}",
                "add_orange_divider"
            ),
            extra={'no_memory': True} 
        )
        if len(user_questions) > len(user_answers):
            return user_questions[len(user_answers)]
        else:
            return None
               
    def run_agents(self, agents: List[Dict]):

        start_step = self.data.agent_chain_step
        
        for agent in agents[start_step:]:
            self.data.agent_chain_step = next(
                index for index, a in enumerate(self.data.json_chain['agents']) 
                if a['agent_nickname'] == agent['agent_nickname']
            )
            self.logger.info(
                "🏃🏃 Running agent %s, step: %d",
                agent['agent_nickname'],
                self.data.agent_chain_step, 
                extra={'no_memory': True}
            )
            if self.data.state == 'waiting_for_user_answer':
                if 'user_answers' not in self.data.json_chain['agents'][self.data.agent_chain_step]:
                    self.data.json_chain['agents'][self.data.agent_chain_step]['user_answers'] = [self.data.chat_history[-1]['content']]
                else:
                    self.data.json_chain['agents'][self.data.agent_chain_step]['user_answers'].append(self.data.chat_history[-1]['content'])
  
            if self.data.is_interactive:
                new_user_question = self.manage_user_questions(self.data.agent_chain_step)
                if new_user_question:
                    self.data.final_answer = new_user_question 
                    self.data.state = 'waiting_for_user_answer'
                    return True #temporary stop the script and give api response
                else:
                    self.data.state = 'running_chain'
            
            connected_agents = [
                a for a in self.data.json_chain['agents']
                if 'observation' in a and a['agent_nickname'] in agent.get('input_from_agents', [])
            ]

            search_results = ""
            if agent.get('external_search_query'):
                if 'websearch' in self.data.data_sources:
                    ws_agent = WebSearchAgent(
                        provider="serpapi",
                        max_search_results=self.max_search_results, 
                        max_length=self.max_scrape_length,
                        logger=self.logger,
                        enrich_log=self.enrich_log
                    )
                    ws_results = ws_agent.run_search(agent['external_search_query'])
                    search_results = json.dumps(ws_results, indent=2)
                    self.logger.info(
                        '🌐✨ Web search executed for agent %s, with query: %s, Total chars: %d',
                        agent['agent_nickname'],
                        agent['external_search_query'],
                        len(search_results),
                        extra={'no_memory': True}
                    )

                if 'rag' in self.data.data_sources:
                    rag_results = retrieve_documents(agent['external_search_query'])
                    self.logger.info(
                        '🦙✨ LlamaIndex rag search executed for agent %s, with query: %s, Total chars: %d',
                        agent['agent_nickname'],
                        agent['external_search_query'],
                        len(rag_results),
                        extra={'no_memory': True}
                    )
                    search_results += "\n" + rag_results

            agent_subtask_prompt = self.gen_prompt_for_subtask_agents(
                agent['agent_nickname'], connected_agents, agent['agent_llm_prompt'], search_results
            )
            agent_subtask_output = call_model(
                chat_history=[{"role": "user", "content": agent_subtask_prompt}],
                model=self.deep_search_model
            )

            egot_prompt = EGOT_GENERATION_PROMPT.substitute(
                agent_subtask_output=agent_subtask_output,
                json_chain=self.data.json_chain,
                egot_graph=self.egot_engine.get_graph(),
                agent_nickname=agent['agent_nickname'],
                initial_message=self.data.initial_message
            )

            egot_agent_output = call_model(
                chat_history=[{"role": "user", "content": egot_prompt}],
                model=self.deep_search_model
            )

            egot_agent_output = json.loads(sanitize_gpt_response(egot_agent_output))
            self.egot_engine.create_multiple_nodes_and_edges(egot_agent_output, agent['agent_nickname'])
            self.logger.info(
                self.enrich_log(
                    f'💡🧠 Generated EGoT step for agent {agent["agent_nickname"]}\n'
                    f'Evolution: {json.dumps(egot_agent_output, indent=4)}',
                    "add_blue_divider"
                ),
                extra={'no_memory': True}
            )
            for ag in self.data.json_chain['agents']:
                if ag['agent_nickname'] == agent['agent_nickname']:
                    ag['observation'] = agent_subtask_output
                    break
            if agent['output_type'] == 'final':
                self.data.output_final_partials.append(agent_subtask_output)
                self.logger.info( 
                    self.enrich_log(
                        f'📝 Generated final partial for agent {agent["agent_nickname"]}, Step nr {self.data.agent_chain_step}:\n\n {agent_subtask_output}',
                        'add_green_divider'
                    ),
                    extra={'no_memory': True}
                )
            self.data.agent_chain_step += 1 
        return False 

    def elab_chain(self):
        agents = self.data.json_chain['agents'] 
        
        must_block = self.run_agents(agents)
        if must_block: 
            return #temporary stop the script and give api response

        if self.data.agent_chain_step == len(agents):
            self.data.final_answer = '<html><body>' + remove_html_body_tags(''.join(self.data.output_final_partials)) + '</body></html>'
            self.data.state = 'completed'
            self.reset_to_init_data_model()
            self.logger.info(self.enrich_log('✅ DeepSearchAgentPlanner process completed ✅', 'add_green_divider'), extra={'no_memory': True})
            return

    def run_planner(self):
        if self.data.state != 'waiting_for_user_answer':
            self.logger.info(self.enrich_log('🚀 ---> Starting DeepSearchAgentPlanner', 'add_green_divider'), extra={'no_memory': True})
            self.data.state = 'running_chain'
            response = call_model(
                chat_history=[{"role": "user", "content": self.data.start_system_prompt.substitute(
                    initial_message=self.data.initial_message, 
                    json_chain_example=JSON_CHAIN_EXAMPLE,
                    min_output_type_final=self.min_output_type_final,
                    min_output_type_functional=self.min_output_type_functional
                )}], 
                model=self.deep_search_model
            )
            self.data.json_chain = json.loads(sanitize_gpt_response(response))
            if not self.data.is_interactive:
                for agent in self.data.json_chain.get('agents', []):
                    agent['user_questions'] = []
            self.logger.info(
                self.enrich_log(
                    f'🔗 Generated initial json chain:\n{json.dumps(self.data.json_chain, indent=4)}',
                    "add_blue_divider"
                ),
                extra={'no_memory': True}
            )
            self.elab_chain()
        else:
            self.logger.info('📩 Received user answer, running chain', extra={'no_memory': True})
            self.elab_chain()
        if self.data.is_interactive:
            self.session_manager.save_session(self.data)