import json
from typing import List, Dict
from .tool_generator import generate_tools
from .logging_handler import LoggingConfigurator
from .agent_plan_generator import PlanGenerator
from .agent_plan_evaluator import PlanEvaluator
from .agent_subtask_executor import SubtaskExecutor
from .utils import transform_final_answer
from params import PARAMS

class CodeAgent:
    def __init__(self, chat_history: List[Dict], tools: List[str], session_id: str, use_default_tools: bool = True, socketio: any = None): 
        """
        Initializes the CodeAgent with conversation history and a list of tool names. 
        Additional default tools are appended automatically.
        """
        self.chat_history = chat_history
        self.session_id = session_id
        self.socketio = socketio
        self.tools = generate_tools(tools, use_default_tools)
        self.execution_logs = []  # This list will collect logs (excluding those with 'no_memory' extra).
        self.logger = LoggingConfigurator.configure_logger(self.execution_logs)
        self.enrich_log = LoggingConfigurator.enrich_log
        self.models = {  
            "TOOL_HELPER_MODEL": PARAMS["TOOL_HELPER_MODEL"], 
            "TOOL_HELPER_MODEL_WEB_SEARCH": PARAMS["TOOL_HELPER_MODEL_WEB_SEARCH"],
            "JSON_PLAN_MODEL": PARAMS["JSON_PLAN_MODEL"],
            "EVALUATION_MODEL": PARAMS["EVALUATION_MODEL"],
            "SIMPLE_RAG_EMBEDDING_MODEL": PARAMS["SIMPLE_RAG_EMBEDDING_MODEL"]
        }
        # Instantiate helper components.
        self.plan_generator = PlanGenerator(self.chat_history, self.tools, self.models["JSON_PLAN_MODEL"])
        self.plan_evaluator = PlanEvaluator(self.models["EVALUATION_MODEL"])
        self.json_plan = None
        self.subtask_executor = SubtaskExecutor(self) 
        self.user_qa = None
       
    def run_agent(self):
        """
        Orchestrates the agent's execution: generating a plan, executing subtasks,
        and evaluating the output iteratively.
        """  
 
        try:  
            self.logger.info(
                self.enrich_log(f"🚀 Starting agent with request: {json.dumps(self.chat_history, indent=4)}", "add_green_divider"),
                extra={'no_memory': True}
            )
            self.json_plan, agent_prompt = self.plan_generator.generate_plan()
            self.logger.info(
                self.enrich_log(f"💡 JSON plan: {json.dumps(self.json_plan, indent=4)}", "add_green_divider"),
                extra={'no_memory': True}
            )

            max_iterations = PARAMS["MAX_ITERATIONS_AFTER_EVALUATION"]
            iteration = 0

            while iteration <= max_iterations:
                iteration += 1
                self.logger.info(f"Iteration nr. {iteration}", extra={'no_memory': True})
                self.subtask_executor.execute_subtasks()

                evaluation_output = self.plan_evaluator.evaluate(
                    agent_prompt, self.json_plan, iteration, max_iterations, self.execution_logs
                )

                if iteration < max_iterations + 1:
                    if evaluation_output.get("satisfactory", False):
                        final = evaluation_output.get("final_answer", "")
                        # Transform audio snippet if necessary.
                        final = transform_final_answer(final)
                        self.logger.info(
                            self.enrich_log(f"✅ Evaluation satisfactory. Final answer: {final}", "add_green_divider"),  
                            extra={'no_memory': True}
                        )
                        return final  
                    else:
                        if not evaluation_output.get("max_iterations_reached", False):
                            self.logger.info(
                                self.enrich_log("🔄 Evaluation not satisfactory. Updating JSON plan.", "add_red_divider"),
                                extra={'no_memory': True}
                            )
                            self.json_plan = evaluation_output.get("new_json_plan", {})
                            self.logger.info(f"New JSON plan: {json.dumps(self.json_plan, indent=4)}")
                        elif evaluation_output.get("max_iterations_reached", False):
                            self.logger.warning("Max iterations reached without satisfactory evaluation.")
                            final = evaluation_output.get("final_answer", "")
                            final = transform_final_answer(final)
                            return final
                else:
                    self.logger.warning("🔴 Max iterations reached without satisfactory evaluation.", extra={'no_memory': True})
                    final = evaluation_output.get("final_answer", "")
                    final = transform_final_answer(final)
                    return final 
                    
        except Exception as e: 
            self.logger.error("Error running agent:", exc_info=True)  
