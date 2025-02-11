import json
import os
from typing import List, Dict
from .default_tools import generate_default_tools
from .logging_handler import LoggingConfigurator
from .agent_plan_generator import PlanGenerator
from .agent_plan_evaluator import PlanEvaluator
from .agent_subtask_executor import SubtaskExecutor

class CodeAgent:
    def __init__(self, chat_history: List[Dict], tools: List[str]): 
        """
        Initializes the CodeAgent with conversation history and a list of tool names. 
        Additional default tools are appended automatically.
        """
        self.chat_history = chat_history
        self.tools = tools + generate_default_tools()
        self.execution_logs = []  # This list will collect logs (excluding those with 'no_memory' extra).
        self.logger = LoggingConfigurator.configure_logger(self.execution_logs)
        self.enrich_log = LoggingConfigurator.enrich_log
        self.models = {
            "TOOL_HELPER_MODEL": os.getenv("TOOL_HELPER_MODEL"), 
            "JSON_PLAN_MODEL": os.getenv("JSON_PLAN_MODEL"),
            "EVALUATION_MODEL": os.getenv("EVALUATION_MODEL"),
            "SIMPLE_RAG_EMBEDDING_MODEL": os.getenv("SIMPLE_RAG_EMBEDDING_MODEL")
        }
        # Instantiate helper components.
        self.plan_generator = PlanGenerator(self.chat_history, self.tools, self.models["JSON_PLAN_MODEL"])
        self.plan_evaluator = PlanEvaluator(self.models["EVALUATION_MODEL"])
        self.json_plan = None
        self.subtask_executor = SubtaskExecutor(self)
       

    def run_agent(self):
        """
        Orchestrates the agent's execution: generating a plan, executing subtasks,
        and evaluating the output iteratively.
        """ 
        try:
            self.logger.info(
                self.enrich_log(f"🚀🚀🚀 Starting agent with user request: {json.dumps(self.chat_history, indent=4)}\n\n✨ Generating initial JSON plan...", "add_green_divider"),
                extra={'no_memory': True}
            )

            # Generate initial JSON plan and agent prompt.
            self.json_plan, agent_prompt = self.plan_generator.generate_plan()

            self.logger.info(
                self.enrich_log(f"💡💡💡 Code agent json plan: {json.dumps(self.json_plan, indent=4)}", "add_green_divider"),
                extra={'no_memory': True} 
            )

            max_iterations = 2
            iteration = 0

            while iteration <= max_iterations + 1:
                iteration += 1
                self.logger.info(
                    f"● ● ● JSON plan execution iteration nr. {iteration} ● ● ● \n\n",
                    extra={'no_memory': True}
                ) 
                
                # Execute each subtask in the JSON plan.
                self.subtask_executor.execute_subtasks()

                # Evaluate the results of the current iteration.
                evaluation_output = self.plan_evaluator.evaluate(
                    agent_prompt, self.json_plan, iteration, max_iterations, self.execution_logs
                )

                if iteration < max_iterations + 1:
                    if evaluation_output.get("satisfactory", False):
                        self.logger.info(
                            self.enrich_log(f"✅ Evaluation is satisfactory, returning final answer: {evaluation_output.get('final_answer', '')}", "add_green_divider"),
                            extra={'no_memory': True}
                        )
                        return evaluation_output.get("final_answer", "")  
                    else: 
                        if (not evaluation_output.get("satisfactory", False) and  
                            not evaluation_output.get("max_iterations_reached", False)):
                            self.logger.info(
                                self.enrich_log(f"🔄 Evaluation is not satisfactory, updating JSON plan.", "add_red_divider"),
                                extra={'no_memory': True}
                            ) 
                            self.json_plan = evaluation_output.get("new_json_plan", {})
                            self.logger.info(f"Evaluation is not satisfactory. {evaluation_output.get('thoughts', '')}. Now updating JSON plan...\n\n 💡💡💡 New JSON plan: {self.json_plan}")
                        elif evaluation_output.get("max_iterations_reached", False):
                            self.logger.warning("Max iterations reached without satisfactory evaluation.")
                            return evaluation_output.get("final_answer", "")
                else:
                    self.logger.warning("🔴 Max iterations reached without satisfactory evaluation.", extra={'no_memory': True})
                    return evaluation_output.get("final_answer", "")
                    
        except Exception as e:
            self.logger.error("Error running agent:", exc_info=True) 
