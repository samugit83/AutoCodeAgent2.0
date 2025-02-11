import json
import traceback
import inspect
from .function_validator import FunctionValidator
from models.models import call_model
from .utils import sanitize_gpt_response
from .prompts import REGENERATE_SUBTASK_PROMPT, CODE_SYSTEM_PROMPT

class SubtaskExecutor:
    def __init__(self, agent):
        """
        :param agent: An instance of CodeAgent that holds shared state.
        """
        self.agent = agent
        self.subtask_regeneration_records = []
        self.validator_max_regeneration_attempts = 3  # For validation errors
        self.execution_max_regeneration_attempts = 3  # For execution errors
        self.allowed_lib_names = [
            lib_name for tool in self.agent.tools for lib_name in tool["lib_names"]
        ]

    def execute_subtasks(self):
        """
        Iterates over the subtasks in the JSON plan, validates each subtask’s code,
        attempts to execute it (with regeneration on error), and then calls the subtask function.

        :return: A dictionary with the results of the executed subtasks.
        """
        results = {}
        subtasks = self.agent.json_plan.get("subtasks", [])

        for index, subtask in enumerate(subtasks):
            # --- Step 1: Validate subtask code ---
            output_validator, subtask = self._validate_subtask_code(subtask, index, results)
            code_string = output_validator["code_string"]

            # --- Step 2: Execute the subtask code (with retries) ---
            temp_namespace, code_string = self._execute_subtask_code(subtask, code_string, index)

            # --- Step 3: Run the subtask function from the namespace ---
            subtask_name = subtask["subtask_name"]
            input_tool_name = subtask.get("input_from_subtask", "")
            if subtask_name in temp_namespace:
                tool_func = temp_namespace[subtask_name]
                sig = inspect.signature(tool_func)
                if index > 0:
                    previous_result = results.get(input_tool_name, {})
                    result = tool_func(previous_result)
                else:
                    if "previous_output" in sig.parameters:
                        result = tool_func({})
                    else:
                        result = tool_func()
                results[subtask_name] = result

                results_str = json.dumps(results, indent=4) 
                if index == len(subtasks) - 1:
                    self.agent.logger.info(f"✅ Last subtask '{subtask_name}' executed successfully. this is the final result: {results_str}")
                if len(results_str) > 500:
                    results_str = results_str[:500] + "... [truncated]"

                self.agent.logger.info(
                    self.agent.enrich_log(
                        f"📌 Subtask nr.{index + 1} executed: {subtask_name}.\n\n"
                        f"🧠 Updated memory logs:\n{self.agent.execution_logs}\n\n"
                        f"📤 Task output:\n{results_str}",
                        "add_green_divider"
                    ),
                    extra={'no_memory': True}
                )
            else:
                error_msg = f"Subtask '{subtask_name}' not found in the execution namespace."
                self.agent.logger.error(
                    self.agent.enrich_log(error_msg, "add_red_divider"),
                    extra={'no_memory': True}
                )
                raise Exception(error_msg)

        return results

    def _update_subtask_in_plan(self, subtask_name, new_subtask):
        """
        Updates the JSON plan with the regenerated subtask.

        :param subtask_name: Name of the subtask to update.
        :param new_subtask: The regenerated subtask (a dict) that will replace the old one.
        """
        for i, existing_subtask in enumerate(self.agent.json_plan["subtasks"]):
            if existing_subtask["subtask_name"] == subtask_name:
                self.agent.json_plan["subtasks"][i] = new_subtask
                return

    def _validate_subtask_code(self, subtask, index, results):
        """
        Validates the subtask’s code and regenerates it if errors are found.
        Updates the JSON plan and returns the validation result along with the (possibly updated) subtask.

        :param subtask: The current subtask (a dict) to validate.
        :param index: The index of the current subtask.
        :param results: Dictionary of previously computed subtask results.
        :return: A tuple of (output_validator, subtask). The output_validator contains the validated code string.
        :raises Exception: If the subtask still contains errors after the maximum regeneration attempts.
        """
        attempts = 0
        output_validator = FunctionValidator(
            subtask["subtask_name"],
            self.allowed_lib_names,
            index,
            len(self.agent.json_plan.get("subtasks", []))
        ).validate(subtask["code"])

        if not output_validator["errors_for_regeneration"]:
            self.agent.logger.info(
                self.agent.enrich_log(
                    f"🟢 Subtask '{subtask['subtask_name']}' function code is valid.\n"
                    f"No errors found during validation.",
                    "add_green_divider"
                ),
                extra={'no_memory': True}
            )

        while output_validator["errors_for_regeneration"] and attempts < self.validator_max_regeneration_attempts:
            self.agent.logger.info(
                self.agent.enrich_log(
                    f"🔄 Regenerating subtask: {subtask['subtask_name']} "
                    f"(attempt {attempts + 1}/{self.validator_max_regeneration_attempts}).\n"
                    f"Errors found during validation:\n{output_validator['errors_for_regeneration']}",
                    "add_red_divider"
                ),
                extra={'no_memory': True}
            )

            regen_subtask = self.regenerate_subtask(output_validator["errors_for_regeneration"], subtask)
            # Update the JSON plan and the local subtask with the regenerated version.
            self._update_subtask_in_plan(subtask["subtask_name"], regen_subtask) 
            subtask = regen_subtask

            previous_result = results.get(subtask.get("input_from_subtask", ""), {}) if index > 0 else {}
            output_validator = FunctionValidator(
                subtask["subtask_name"],
                self.allowed_lib_names,
                index,
                len(self.agent.json_plan.get("subtasks", [])),
                previous_result
            ).validate(subtask["code"])

            if not output_validator["errors_for_regeneration"]:
                self.agent.logger.info(
                    self.agent.enrich_log(
                        f"🟢 Subtask '{subtask['subtask_name']}' function code is valid after "
                        f"regeneration attempt {attempts + 1}.\n"
                        f"No errors found during validation.",
                        "add_green_divider"
                    ),
                    extra={'no_memory': True}
                )
            attempts += 1

        if output_validator["errors_for_regeneration"]:
            error_msg = (
                f"❌❌❌ Subtask '{subtask['subtask_name']}' still has errors after {attempts} "
                f"regeneration attempts:\n{output_validator['errors_for_regeneration']}"
            )
            self.agent.logger.error(
                self.agent.enrich_log(error_msg, "add_red_divider"),
                extra={'no_memory': True}
            )
            raise Exception(error_msg)

        return output_validator, subtask

    def _execute_subtask_code(self, subtask, code_string, index):
        """
        Executes the code string within a dedicated namespace and attempts regeneration if an error occurs.

        :param subtask: The current subtask (a dict).
        :param code_string: The Python code (as a string) to execute.
        :param index: The index of the current subtask.
        :return: A tuple (temp_namespace, code_string) where temp_namespace is the dictionary in which the code was executed.
        :raises Exception: If execution fails after the maximum regeneration attempts.
        """
        attempts = 0
        temp_namespace = {"logger": self.agent.logger}

        self.agent.logger.info(
            self.agent.enrich_log(
                f"⌛ Executing subtask nr.{index + 1} of {len(self.agent.json_plan.get('subtasks', []))}: {subtask['subtask_name']}",
                "add_orange_divider"
            ),
            extra={'no_memory': True}
        )

        while attempts < self.execution_max_regeneration_attempts:
            try:
                exec(code_string, temp_namespace)
                return temp_namespace, code_string
            except Exception:
                error_message = traceback.format_exc()
                self.agent.logger.error(
                    self.agent.enrich_log(
                        f"❌ Error during execution of subtask '{subtask['subtask_name']}' "
                        f"(attempt {attempts + 1}/{self.execution_max_regeneration_attempts}):\n{error_message}",
                        "add_red_divider"
                    ),
                    extra={'no_memory': True}
                )
                regen_subtask = self.regenerate_subtask(error_message, subtask)
                self._update_subtask_in_plan(subtask["subtask_name"], regen_subtask)
                # In this case we assume that the regenerated subtask has an updated "code" field.
                code_string = regen_subtask["code"]
                attempts += 1

        error_msg = (
            f"❌❌❌ Subtask '{subtask['subtask_name']}' still fails after "
            f"{attempts} execution regeneration attempts."
        )
        self.agent.logger.error(
            self.agent.enrich_log(error_msg, "add_red_divider"),
            extra={'no_memory': True}
        )
        raise Exception(error_msg)

    def regenerate_subtask(self, subtask_errors, subtask):
        """
        Uses the LLM to regenerate the subtask based on the errors encountered.
        Also records the regeneration attempt.

        :param subtask_errors: The error message or validation errors that triggered regeneration.
        :param subtask: The original subtask (a dict) that needs to be regenerated.
        :return: The regenerated subtask (a dict) as provided by the LLM.
        """
        regen_prompt = REGENERATE_SUBTASK_PROMPT.substitute(
            agent_initial_prompt=CODE_SYSTEM_PROMPT,
            conversation_history=self.agent.chat_history,
            json_plan=self.agent.json_plan,
            tools=self.agent.tools,
            subtask_name=subtask["subtask_name"],
            subtask_errors=subtask_errors
        )
        llm_output_str = call_model(
            chat_history=[{"role": "user", "content": regen_prompt}],
            model=self.agent.models["JSON_PLAN_MODEL"],
            output_format="json_object"
        )

        llm_output_str = sanitize_gpt_response(llm_output_str)
        llm_output_json = json.loads(llm_output_str)
        self.agent.logger.info(
            self.agent.enrich_log(
                f"🤖 LLM output for subtask regeneration: {llm_output_str}",
                "add_green_divider"
            ),
            extra={'no_memory': True}
        )

        corrected_subtask = llm_output_json["corrected_subtask"]

        # Record the regeneration attempt.
        self.subtask_regeneration_records.append({
            "original_subtask": subtask,
            "errors": subtask_errors,
            "reasoning": llm_output_json["reasoning"],
            "corrected_subtask": corrected_subtask
        })

        return corrected_subtask
