
import redis
import pickle
import threading
import logging
import traceback
from .agent_data_model import AgentDataModel


class AgentSessionManager:
    def __init__(self, redis_host='redis', redis_port=6379, db=0):
        self.redis = redis.StrictRedis(host=redis_host, port=redis_port, db=db)
        self.lock = threading.Lock()
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    def get_session_key(self, session_id):
        return f"session:{session_id}"

    def load_session(self, session_id):
        """
        Load (unpickle) the user's DataModel from Redis.
        If not found, create a new DataModel.
        """
        with self.lock:
            try:
                serialized_data = self.redis.get(self.get_session_key(session_id))
                if serialized_data:
                    self.logger.info(f"Loading existing session for session_id: {session_id}")
                    data_model = pickle.loads(serialized_data)

                else:
                    self.logger.info(f"No existing session found. Creating new session for session_id: {session_id}")
                    # Create a new DataModel
                    data_model = AgentDataModel(
                        name="AgentSInteractive",
                        session_id=session_id
                    )
                return data_model
            except Exception as e:
                self.logger.error("Error loading session:")
                self.logger.error(traceback.format_exc())
                raise e

    def save_session(self, data_model: AgentDataModel):
        """
        Serialize (pickle) the DataModel and store it in Redis.
        """
        with self.lock:
            try:
                serialized_data = pickle.dumps(data_model)
                self.redis.set(self.get_session_key(data_model.session_id), serialized_data)
                self.logger.info(f"Session saved for session_id: {data_model.session_id}")
            except Exception as e:
                self.logger.error("Error saving session:")
                self.logger.error(traceback.format_exc())
                raise e  
