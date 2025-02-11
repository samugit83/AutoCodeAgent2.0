import json
from .prompts import CODE_SYSTEM_PROMPT
from models.models import call_model
from .utils import sanitize_gpt_response

class PlanGenerator:
    def __init__(self, chat_history, tools, json_plan_model):
        """
        :param chat_history: List of dictionaries representing the conversation history.
        :param tools: List of tool names available.
        :param json_plan_model: The model identifier to generate the JSON plan.
        """
        self.chat_history = chat_history
        self.tools = tools
        self.json_plan_model = json_plan_model

    def generate_plan(self):
        """
        Generates a JSON plan for the agent by substituting conversation history and tools into the prompt.
        
        :return: A tuple (json_plan, agent_prompt)
        """
        agent_prompt = CODE_SYSTEM_PROMPT.substitute(
            conversation_history=self.chat_history,
            tools=self.tools 
        )
        agent_output_str = call_model(
            chat_history=[{"role": "user", "content": agent_prompt}],
            model=self.json_plan_model,
            output_format="json_object"
        )
        agent_output_str = sanitize_gpt_response(agent_output_str)
        json_plan = json.loads(agent_output_str)
        return json_plan, agent_prompt
