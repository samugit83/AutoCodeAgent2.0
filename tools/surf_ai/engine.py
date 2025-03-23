import asyncio
import json
from models.models import call_model
from .browser_manager import BrowserManager
from .command_executor import CommandExecutor
from .element_highlighter import ElementHighlighter
from .screenshot_manager import ScreenshotManager
from .json_handler import JsonResponseHandler
from .logging_handler import LoggingConfigurator
from .prompt import GEN_JSON_TASK_PROMPT, GEN_JSON_TASK_LOOP_PROMPT, FINAL_ANSWER_PROMPT
from params import PARAMS

class SurfAiEngine:
    def __init__(self):  
        self.execution_logs = [] 
        self.logger = LoggingConfigurator.configure_logger(self.execution_logs)
        self.json_task_model = PARAMS["SURF_AI_JSON_TASK_MODEL"]
        self.command_executor = CommandExecutor(self.logger)
        self.highlighter = ElementHighlighter(self.logger)
        self.screenshot_manager = ScreenshotManager(truncation_length=400000)
        self.max_retries = 2      
        self.retry_backoff = 2000   
        self.final_answer = None    

    async def go_surf(self, prompt: str):  
        try:
            await self._initialize_task(prompt)
            async with BrowserManager(command_timeout=5000) as browser_manager:
                context = await browser_manager.create_context() 
                page = await browser_manager.create_page(context)
                await self._process_tasks(prompt, page)
                self.logger.debug("🟢 Final answer From SurfAI Engine: %s", self.final_answer, extra={'no_memory': True})
            return self.final_answer
        except Exception as e:
            self.logger.exception(f"Critical error: {str(e)}")    
            raise

    async def _call_model_with_retry(self, chat_history, model, **kwargs):      
        """
        Helper method that wraps the call_model function in a retry loop.
        It retries if the response is None, if it doesn't have the expected attribute,
        or if the JSON cannot be parsed. 
        """
        attempts = 0 
        while attempts <= self.max_retries:      
            try:
                response = call_model(
                    chat_history=chat_history,
                    model=model,
                    **kwargs,
                    output_format="json_object"
                )
                if response is None:
                    raise ValueError("Received None as response from call_model")
                sanitized = JsonResponseHandler.sanitize_response(response)
                json.loads(sanitized)
                return response
            except (AttributeError, ValueError, json.JSONDecodeError) as e: 
                attempts += 1
                self.logger.warning( 
                    "Received invalid response from call_model (attempt %d/%d) due to error: %s. Retrying in %dms...",
                    attempts, self.max_retries, e, self.retry_backoff,
                    extra={'no_memory': True}
                )
                if attempts > self.max_retries: 
                    self.logger.error("Max retries exceeded for call_model.", extra={'no_memory': True})
                    raise
                await asyncio.sleep(self.retry_backoff / 1000.0)

    async def _initialize_task(self, prompt: str):
        json_task_prompt = GEN_JSON_TASK_PROMPT.substitute(user_message=prompt)
        response = await self._call_model_with_retry(
            chat_history=[{"role": "user", "content": json_task_prompt}],
            model=self.json_task_model
        )
        self.json_task = json.loads(JsonResponseHandler.sanitize_response(response))
        self.logger.debug( 
            "🔵 Initial JSON response: %s", 
            json.dumps(self.json_task, indent=4), 
            extra={'no_memory': True}   
        )

    async def _process_tasks(self, prompt: str, page):
        while True:
            task = self.json_task['tasks'][-1] 
            await self._execute_task_commands(task, page)
            await self._update_task_state(prompt, page, task)
              
            if self.json_task.get('is_last_task'):
                final_answer_prompt = FINAL_ANSWER_PROMPT.substitute( 
                    json_task=json.dumps(self.json_task, indent=4),
                    user_message=prompt
                )
                response = call_model(
                    chat_history=[{"role": "user", "content": final_answer_prompt}],
                    model=self.json_task_model,
                    output_format="text"
                )
                self.logger.debug("Final task completed")
                self.final_answer = response  
                break 
 
    async def _execute_task_commands(self, task, page):    
        if task.get('data_extraction') and (task.get('commands') == 'data_extraction' or task.get('commands') is None):
            return
        if task.get('commands') is None:  
            return 
        commands = [cmd.strip() for cmd in task['commands'].split(';') if cmd.strip()]
        for command in commands:  
            # Assuming command_executor.execute is updated to support async
            result = await self.command_executor.execute(command, page, task['task_name'])
            if result:
                break     
 
    async def _update_task_state(self, prompt: str, page, task): 
        await self.highlighter.remove_highlight(page)   
        pages = page.context.pages 
        if len(pages) > 1:
            page = pages[-1]    
            await asyncio.sleep(3)
            self.logger.debug("🟡 Multiple pages detected; switching to the last opened page.")
        await self.highlighter.apply_highlight(page) 
        await asyncio.sleep(1)
        await self.screenshot_manager.capture(page, task['task_name'])
        
        loop_prompt = GEN_JSON_TASK_LOOP_PROMPT.substitute( 
            json_task=json.dumps(self.json_task, indent=4), 
            execution_logs=self.execution_logs,
            scraped_page=self.screenshot_manager.scraped_page,
            user_message=prompt
        ) 
        
        response = await self._call_model_with_retry(
            chat_history=[{"role": "user", "content": loop_prompt}],
            model=self.json_task_model,
            image_base64=self.screenshot_manager.screenshot_base64,
            image_extension="png"
        ) 
        
        self.json_task = JsonResponseHandler.update_task_structure(
            self.json_task,
            json.loads(JsonResponseHandler.sanitize_response(response)) 
        )

        self.logger.debug(
            "🔵 Whole JSON tasks %s", 
            json.dumps(self.json_task, indent=4), 
            extra={'no_memory': True}
        )
