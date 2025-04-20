import os
import pickle
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
import logging 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class QLearningAgent:
    def __init__(
        self,
        data_file="q_data.pkl",
        n_recent=50,
        alpha=0.8,
        gamma=0.95,
        epsilon=0.1,
        mode='neural',
        state_dim=None,
        n_actions=10,
        model_file="reinforcement_learning/q_model.h5",
        category_maps=None 
    ):
        """
        Initializes the agent:
          - data_file: file for persisting non-model data (episodes, error list)
          - n_recent: number of recent episodes to compute the average error
          - alpha: learning rate (used for both modes, though DQN often uses optimizer's rate)
          - gamma: discount factor
          - epsilon: exploration rate for epsilon-greedy
          - mode: 'simple' for Q-table, 'neural' for DQN
          - state_dim: required dimension of the state input for neural mode
          - n_actions: number of possible actions (output dimension for neural mode)
          - model_file: file for persisting the neural network model
          - category_maps: Dict mapping feature index to list/dict of categories for one-hot encoding
        """
        self.data_file = data_file
        self.n_recent = n_recent
        self.alpha = alpha # Learning rate for simple mode / used in TD error calculation
        self.gamma = gamma
        self.epsilon = epsilon
        self.mode = mode
        self.n_actions = n_actions
        self.model_file = model_file # File for saving/loading the NN model
        self.category_maps = category_maps if category_maps is not None else {} # +++ Store category maps

        if self.mode == 'simple':
            self.q_table = {}
            logging.info("Initialized QLearningAgent in 'simple' mode.")
        elif self.mode == 'neural':
            if state_dim is None:
                raise ValueError("state_dim must be provided for 'neural' mode.")
            self.state_dim = state_dim
            self.model = self._build_model()
            self.optimizer = Adam(learning_rate=self.alpha) 
            logging.info(f"Initialized QLearningAgent in 'neural' mode with state_dim={state_dim}.")
        else:
            raise ValueError(f"Invalid mode: {self.mode}. Choose 'simple' or 'neural'.")


        self.episodes = 0
        self.error_list = []
        self.load_data()


    def _build_model(self):
        """Builds the neural network model for DQN."""
    
        model = Sequential([
            Dense(24, input_dim=self.state_dim, activation='relu'),
            Dense(24, activation='relu'),
            Dense(self.n_actions, activation='linear') # Linear activation for Q-values
        ])
        
        # Build internal value-to-index maps for faster lookup during preprocessing
        self._build_category_index_maps()

        logging.info("Built neural network model.")
        # model.summary() # Optional: print model summary
        return model

    def load_data(self):
        """
        Loads persistent data.
        - For 'simple' mode: loads Q-table, episode count, error list from pickle.
        - For 'neural' mode: loads NN model weights and episode/error data from pickle.
        """
        # Load common data (episodes, error_list)
        common_data_loaded = False
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "rb") as f:
                    data = pickle.load(f)
                self.episodes = data.get("episodes", 0)
                self.error_list = data.get("error_list", [])
                logging.info(f"Loaded common data (episodes, error_list) from {self.data_file}.")
                common_data_loaded = True
            except (EOFError, pickle.UnpicklingError) as e:
                 logging.warning(f"Could not load common data from {self.data_file}: {e}. Starting fresh.")
                 self.episodes = 0
                 self.error_list = []

        # Load mode-specific data
        if self.mode == 'simple':
            if common_data_loaded: # Only load q_table if common data was loaded
                 self.q_table = data.get("q_table", {})
                 logging.info("Loaded Q-table for 'simple' mode.")
            else:
                 self.q_table = {}
                 logging.warning("Initializing empty Q-table for 'simple' mode as data file was missing/corrupt.")
        elif self.mode == 'neural':
            if os.path.exists(self.model_file):
                try:
                    # Load the entire model (architecture + weights + optimizer state)
                    self.model = load_model(self.model_file)
                    # Re-assign the optimizer if needed, or ensure it's loaded correctly
                    if hasattr(self.model, 'optimizer'):
                         self.optimizer = self.model.optimizer
                         logging.info(f"Optimizer state loaded from {self.model_file}")
                    else:
                         # If optimizer state wasn't saved with model, re-initialize
                         self.optimizer = Adam(learning_rate=self.alpha) # Use the agent's alpha
                         logging.warning(f"Optimizer state not found in {self.model_file}, re-initializing.")

                    logging.info(f"Loaded neural network model from {self.model_file}.")
                    # Verify input shape compatibility if possible (optional)
                    expected_input_shape = (None, self.state_dim)
                    if self.model.input_shape != expected_input_shape:
                        logging.warning(f"Loaded model input shape {self.model.input_shape} differs from expected {expected_input_shape}. Ensure compatibility.")

                except Exception as e: 
                    logging.error(f"Error loading model from {self.model_file}: {e}. Building a new model.")
                    # Fallback to building a new model if loading fails
                    self.model = self._build_model()
            else:
                 logging.warning(f"Model file {self.model_file} not found. Using newly built model.")
                 if not hasattr(self, 'model') or self.model is None:
                      self.model = self._build_model()

        if not common_data_loaded and not os.path.exists(self.data_file):
             logging.info(f"Data file {self.data_file} not found. Starting fresh.")


    def save_data(self):
        """
        Saves persistent data.
        - For 'simple' mode: saves Q-table, episode count, error list to pickle.
        - For 'neural' mode: saves NN model weights and episode/error data to pickle.
        """
        # Save common data
        common_data = {
            "episodes": self.episodes,
            "error_list": self.error_list
        }

        # Add mode-specific data to save
        if self.mode == 'simple':
            common_data["q_table"] = self.q_table # Add q_table for simple mode
            logging.info("Preparing to save Q-table and common data.")
        elif self.mode == 'neural':
            # Save the neural network model
            try:
                self.model.save(self.model_file) # Saves architecture, weights, optimizer state
                logging.info(f"Neural network model saved to {self.model_file}.")
            except Exception as e:
                 logging.error(f"Error saving model to {self.model_file}: {e}")
            logging.info("Preparing to save common data for neural mode.")

        # Save the data (common + simple mode specific) to the pickle file
        try:
            with open(self.data_file, "wb") as f:
                pickle.dump(common_data, f)
            logging.info(f"Data saved to {self.data_file}.")
        except IOError as e:
            logging.error(f"Could not save data to {self.data_file}: {e}")

    def _build_category_index_maps(self):
        """Creates internal value-to-index mappings from the provided category lists."""
        self._category_to_index = {}
        for feature_index, categories in self.category_maps.items():
            if isinstance(categories, list):
                self._category_to_index[feature_index] = {category: i for i, category in enumerate(categories)}
                logging.debug(f"Built index map for categorical feature {feature_index}: {self._category_to_index[feature_index]}")
            elif isinstance(categories, dict):
                # Assume it's already a category -> index map
                self._category_to_index[feature_index] = categories
                logging.debug(f"Using provided index map for categorical feature {feature_index}.")
            else:
                logging.warning(f"Invalid category map format for feature {feature_index}. Expected list or dict.")

    def _preprocess_state(self, state):
        """
        Converts state tuple (potentially mixed types) to a NumPy array
        suitable for the NN, using one-hot encoding for categorical strings
        and float conversion for booleans.
        """
  
        processed_parts = []
        try:
            # Ensure state is a list or tuple
            if not isinstance(state, (list, tuple)):
                raise TypeError(f"Expected state to be a list or tuple, got {type(state)}")

            # --- Process Categorical Features Dynamically ---
            categorical_indices = sorted(self._category_to_index.keys()) # Process in order

            if 0 in categorical_indices: # Assuming first categorical feature is at index 0
                cat1_value = state[0]
                cat1_index_map = self._category_to_index.get(0, {})
                num_cat1 = len(cat1_index_map)
                one_hot1 = np.zeros(num_cat1, dtype=np.float32)
                if isinstance(cat1_value, str):
                    if cat1_value in cat1_index_map:
                        one_hot1[cat1_index_map[cat1_value]] = 1.0
                    else:
                        logging.warning(f"Unknown category '{cat1_value}' for feature 0. Using zero vector.")
                else:
                    raise ValueError(f"Expected string for state element 0, got {type(cat1_value)}")
                processed_parts.append(one_hot1)
            else:
                logging.warning("No category map found for feature index 0.")

            if 1 in categorical_indices: # Assuming second categorical feature is at index 1
                cat2_value = state[1]
                cat2_index_map = self._category_to_index.get(1, {})
                num_cat2 = len(cat2_index_map)
                one_hot2 = np.zeros(num_cat2, dtype=np.float32)
                if isinstance(cat2_value, str):
                    if cat2_value in cat2_index_map:
                        one_hot2[cat2_index_map[cat2_value]] = 1.0
                    else:
                        logging.warning(f"Unknown category '{cat2_value}' for feature 1. Using zero vector.")
                else:
                    raise ValueError(f"Expected string for state element 1, got {type(cat2_value)}")
                processed_parts.append(one_hot2)
            else:
                logging.warning("No category map found for feature index 1.")
            # --- End Categorical Processing ---

            # --- Process Remaining Features ---
            # Assuming boolean is at index 2 and numerical start from index 3
            current_index = 2 # Start processing from the element after the last categorical feature handled

            # Process boolean feature (assuming it's at index `current_index`)
            if len(state) <= current_index:
                raise IndexError(f"State has insufficient length ({len(state)}) to access boolean feature at index {current_index}")
            bool_value = state[current_index]
            if isinstance(bool_value, bool):
                processed_parts.append(np.array([1.0 if bool_value else 0.0], dtype=np.float32))
            else:
                raise ValueError(f"Expected boolean for state element {current_index}, got {type(bool_value)}")
            current_index += 1

            # Process remaining numerical features
            if len(state) > current_index:
                numerical_part = np.array(state[current_index:], dtype=np.float32)
                processed_parts.append(numerical_part)
            elif len(processed_parts) == 0:
                # Handle case where state only had categorical/boolean and no numericals
                logging.warning(f"No numerical features found in state starting from index {current_index}. State: {state}")
            # --- End Remaining Feature Processing ---

            # Concatenate all parts into a single vector
            if not processed_parts:
                logging.error(f"Could not process any parts of the state: {state}")
                return np.zeros((1, self.state_dim), dtype=np.float32) # Fallback

            final_state_vector = np.concatenate(processed_parts)

            # Reshape and verify dimension
            final_state_vector = final_state_vector.reshape(1, -1) # Reshape to (1, num_features)
            actual_dim = final_state_vector.shape[1]

            if actual_dim != self.state_dim:
                 # Important: The calculated dimension must match the one used to build the model
                 logging.error(f"Processed state dimension ({actual_dim}) does not match model input dimension ({self.state_dim}). Update state_dim during agent initialization or fix preprocessing/category maps.")
                 # raise ValueError("State dimension mismatch.") # Option: raise error immediately
                 # Fallback or allow mismatch? Returning zeros might hide the issue.
                 # Let's return the mismatched vector for now, but the error highlights the root cause.
                 pass # Logged the error, proceed cautiously.

            return final_state_vector

        except (IndexError, TypeError, ValueError) as e:
            logging.error(f"Error processing state {state}: {e}")
            return np.zeros((1, self.state_dim), dtype=np.float32) # Fallback
        

    def get_q_values(self, state):
        """
        Returns the array of Q-values for the specified state.
        - For 'simple' mode: uses the Q-table (dictionary).
        - For 'neural' mode: uses the NN model to predict Q-values.
        Initializes if state not seen ('simple') or predicts ('neural').
        The state representation depends on the mode.
        """
        if self.mode == 'simple':
            # State is expected to be a hashable type, e.g., a tuple
            if not isinstance(state, tuple):
                 logging.warning(f"State {state} is not a tuple in simple mode. Converting.")
                 try:
                      state = tuple(state) # Attempt conversion
                 except TypeError:
                      logging.error(f"Cannot convert state {state} to tuple. Returning zeros.")
                      return np.zeros(self.n_actions) # Fallback

            if state not in self.q_table:
                # Initialize Q-values for a new state in simple mode
                self.q_table[state] = np.zeros(self.n_actions)
                logging.debug(f"Initialized Q-values for new state (simple): {state}")
            return self.q_table[state]

        elif self.mode == 'neural':
            # State should be suitable for preprocessing (e.g., tuple or list of numbers)
            processed_state = self._preprocess_state(state)
            if processed_state is None: # Handle potential preprocessing errors
                 logging.error(f"Could not preprocess state {state} for neural network. Returning zeros.")
                 return np.zeros(self.n_actions)

            def predict_q(model, input_data):
                 return model(input_data, training=False) 

            q_values = predict_q(self.model, processed_state)

            return q_values.numpy().flatten() 


    @tf.function # Decorate for potential graph execution speedup
    def _train_step(self, states, actions, targets):
         """Performs one gradient descent step for the DQN."""
         with tf.GradientTape() as tape:
             # Predict Q-values for the given states
             q_values = self.model(states, training=True) # Forward pass

             # Gather the Q-values corresponding to the actions taken
             # Create indices for tf.gather_nd: [[0, action0], [1, action1], ...]
             action_indices = tf.stack([tf.range(tf.shape(actions)[0]), actions], axis=1)
             action_q_values = tf.gather_nd(q_values, action_indices)

             # Calculate loss (e.g., Mean Squared Error or Huber loss)
             loss = tf.keras.losses.MSE(targets, action_q_values)
             # loss = tf.keras.losses.Huber()(targets, action_q_values) # Alternative: Huber loss

         # Compute gradients and apply updates
         gradients = tape.gradient(loss, self.model.trainable_variables)
         self.optimizer.apply_gradients(zip(gradients, self.model.trainable_variables))
         return loss
    

    def update_q_value(self, state, action, reward, next_state=None, use_next_state=True):
        """
        Updates the Q-value or trains the DQN model for the transition.
        - For 'simple' mode: uses the Q-learning update rule on the Q-table.
        - For 'neural' mode: performs a training step on the NN model.
        Returns the new Q-value (simple) or loss (neural) and the TD error.
        """
        logging.debug(f"Updating Q-value for state: {state}, action: {action}, reward: {reward}, next_state: {next_state}, use_next_state: {use_next_state}, mode: {self.mode}")

        if self.mode == 'simple':
            current_q = self.get_q_values(state)[action]
            if use_next_state and (next_state is not None):
                next_q_values = self.get_q_values(next_state)
                max_next_q = np.max(next_q_values)
                td_target = reward + self.gamma * max_next_q
            else: # Terminal state or next state not used
                td_target = reward

            td_error = abs(td_target - current_q)
            new_q = current_q + self.alpha * (td_target - current_q)

            # Ensure state is hashable (tuple) before updating dict
            if not isinstance(state, tuple):
                 try:
                     state = tuple(state)
                 except TypeError:
                      logging.error(f"Cannot convert state {state} to tuple for Q-table update. Skipping.")
                      return np.nan, np.nan # Indicate failure

            self.q_table[state][action] = new_q
            result_metric = new_q # Return the updated Q-value for simple mode

        elif self.mode == 'neural':
            # Preprocess states
            processed_state = self._preprocess_state(state)
            if processed_state is None:
                 return np.nan, np.nan # Failed preprocessing

            # Predict Q-values for the current state to calculate TD error later
            current_q_values_tensor = self.model(processed_state, training=False)
            current_q = current_q_values_tensor.numpy().flatten()[action] # Q(s, a)

            if use_next_state and (next_state is not None):
                processed_next_state = self._preprocess_state(next_state)
                if processed_next_state is None:
                     # Handle case where next state is invalid? Assume terminal?
                     logging.warning(f"Could not preprocess next_state {next_state}. Treating as terminal.")
                     max_next_q = 0.0 # Treat as terminal state
                else:
                    # Predict Q-values for the next state
                    next_q_values_tensor = self.model(processed_next_state, training=False)
                    max_next_q = np.max(next_q_values_tensor.numpy()) # max Q(s', a')
                td_target = reward + self.gamma * max_next_q
            else: # Terminal state or next state not used
                td_target = reward

            td_error = abs(td_target - current_q)

            # Perform a training step
            # Convert inputs to tensors for the training step
            state_tensor = tf.convert_to_tensor(processed_state, dtype=tf.float32)
            action_tensor = tf.convert_to_tensor([action], dtype=tf.int32) # Action needs to be tensor/array
            target_tensor = tf.convert_to_tensor([td_target], dtype=tf.float32) # Target Q-value

            # Use the dedicated train step function
            loss = self._train_step(state_tensor, action_tensor, target_tensor)
            result_metric = loss.numpy() # Return the loss for neural mode

        self.episodes += 1 # Increment episode/step counter (consider if this should be per update or per episode end)
        logging.debug(f"Step/Episode count: {self.episodes}")
        self.error_list.append(td_error)
        # Limit the error list size
        max_error_list_size = max(100, self.n_recent) # Keep at least n_recent items
        if len(self.error_list) > max_error_list_size:
            self.error_list = self.error_list[-max_error_list_size:]

        # Consider saving data less frequently for performance (e.g., every N steps or episode end)
        self.save_data()

        return result_metric, td_error

    # ... (keep choose_action, get_average_error, etc., they should work with get_q_values) ...

    def choose_action(self, state):
        """
        Chooses an action based on the current state using epsilon-greedy strategy.
        Works for both 'simple' and 'neural' modes via get_q_values.
        """
        if np.random.rand() < self.epsilon:
            # Exploration: choose a random action
            action = np.random.randint(self.n_actions)
            logging.debug(f"Choosing action (Explore): {action}")
        else:
            # Exploitation: choose the best action based on Q-values
            q_values = self.get_q_values(state)
            action = np.argmax(q_values)
            logging.debug(f"Choosing action (Exploit): {action} from Q-values: {q_values}")
        return action

    def get_average_error(self): 
        """Computes the average error over the last n_recent steps/episodes."""
        if not self.error_list:
            return 0.0
        # Calculate average over the last n_recent errors, or fewer if list is shorter
        recent_errors = self.error_list[-self.n_recent:]
        return np.mean(recent_errors) if recent_errors else 0.0

