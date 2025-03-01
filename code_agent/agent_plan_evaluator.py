import json
from .prompts import EVALUATION_AGENT_PROMPT
from models.models import call_model
from .utils import sanitize_gpt_response
import logging

logger = logging.getLogger(__name__)

class PlanEvaluator:
    def __init__(self, evaluation_model):
        """
        :param evaluation_model: The model identifier used for evaluation.
        """
        self.evaluation_model = evaluation_model

    def evaluate(self, agent_prompt, json_plan, iteration, max_iterations, logs):
        """
        Evaluates the current plan and execution logs.

        :param agent_prompt: The original agent prompt.
        :param json_plan: The current JSON plan.
        :param iteration: The current iteration count.
        :param max_iterations: Maximum allowed iterations.
        :param logs: Execution logs to include in the evaluation.
        :return: A dictionary with evaluation results.
        """
        evaluation_prompt = EVALUATION_AGENT_PROMPT.substitute(
            original_prompt=agent_prompt,
            original_json_plan=json.dumps(json_plan, indent=4),
            max_iterations=max_iterations,
            iteration=iteration,
            logs=logs
        )

        evaluation_output_str = call_model(
            chat_history=[{"role": "user", "content": evaluation_prompt}],
            model=self.evaluation_model
        )
        evaluation_output_str = sanitize_gpt_response(evaluation_output_str)
        evaluation_output = json.loads(evaluation_output_str)
        return evaluation_output
