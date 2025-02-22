import dataclasses
from typing import List, Optional, Dict

@dataclasses.dataclass
class AgentDataModel:
    name: str
    session_id: str = dataclasses.field(default_factory=str)
    user_id: str = dataclasses.field(default_factory=str)
    chat_history: List[Dict] = dataclasses.field(default_factory=list)
    initial_message: str = ""
    kwargs: Dict = dataclasses.field(default_factory=dict)
    is_interactive: bool = False
    json_chain: Optional[dict] = None
    state: str = "idle" #idle, running_chain, waiting_for_user_answer, completed
    agent_chain_step: int = 0
    memory_logs: List[str] = dataclasses.field(default_factory=list)
    final_answer: Optional[str] = None
    output_final_partials: List[str] = dataclasses.field(default_factory=list)
    start_system_prompt: str = dataclasses.field(default_factory=str)
    min_token_output_type_final: int | None = None 
    depth: int = None
    data_sources: List[str] = dataclasses.field(default_factory=list)
    delete_graph: bool = False 
