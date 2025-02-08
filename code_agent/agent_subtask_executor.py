
import json

class SubtaskExecutor:
    def __init__(self, logger, enrich_log, execution_logs):
        """
        :param logger: Logger instance to use for logging within subtask execution.
        """
        self.logger = logger
        self.enrich_log = enrich_log
        self.execution_logs = execution_logs

    def execute_subtasks(self, json_plan):
        """
        Executes each subtask provided in the JSON plan.

        :param json_plan: A dictionary containing a list of subtasks.
        :return: A dictionary with the results of the executed subtasks.
        """
        results = {}
        subtasks = json_plan.get("subtasks", [])
        
        for index, subtask in enumerate(subtasks):
            code_string = subtask["code"]

            temp_namespace = {"logger": self.logger} 
            self.logger.info(
                self.enrich_log(f"⌛ Executing subtask nr.{index + 1} of {len(subtasks)}: {subtask['subtask_name']}", "add_orange_divider"),
                extra={'no_memory': True}
            )
            exec(code_string, temp_namespace)  

            subtask_name = subtask["subtask_name"] 
            input_tool_name = subtask.get("input_from_subtask", "")

            if subtask_name in temp_namespace:
                tool_func = temp_namespace[subtask_name] 
                if index > 0:
                    previous_result = results.get(input_tool_name, {})
                    result = tool_func(previous_result)  
                else:
                    result = tool_func() 
                results[subtask_name] = result

                results_str = json.dumps(results, indent=4)
                if len(results_str) > 500:
                    results_str = results_str[:500] + "... [truncated]"

                self.logger.info(
                    self.enrich_log(f""""📌 Subtask nr.{index + 1} executed: {subtask_name}.  
                                    \n\n🧠 Updated memory logs:\n {self.execution_logs}
                                    \n\n📤 Task output:\n {results_str}""", "add_green_divider"),
                    extra={'no_memory': True} 
                )

        return results 
