# engine.py

import asyncio
from openai import OpenAI
from .browser_manager import BrowserManager  # <--- Use async version now
from .screenshot_manager import ScreenshotManager
from .command_executor import handle_model_action
from .logging_handler import LoggingConfigurator
from models.models import call_model
from .prompts import FIRST_URL_PROMPT, BROWSER_STOP_CONFIRMATION
from params import PARAMS
import redis.asyncio as aioredis

class CUAEngine:
    def __init__(self, prompt: str, session_id: str = None, socketio: any = None):
        self.user_prompt = prompt
        self.session_id = session_id
        self.socketio = socketio
        self.redis = aioredis.from_url("redis://redis:6379", decode_responses=True)
        self.execution_logs = []
        self.logger = LoggingConfigurator.configure_logger(self.execution_logs)
        self.client = OpenAI()  # OpenAI client instance
        self.model = "computer-use-preview"
        self.first_url_model = PARAMS["CUA_FIRST_URL_MODEL"]
        self.tools = [{
            "type": "computer_use_preview",
            "display_width": 1280,
            "display_height": 960,
            "environment": "browser"   
        }]
        self.screenshot_manager = ScreenshotManager()  
        self.response = None
        self.info_for_intellichain_agent = "Information from the Browser Navigation agent: "
        self.last_call_id = None


    async def run(self):
 
        async with BrowserManager(command_timeout=5000) as browser_manager:
            self.socketio.emit('reasoning_update', {
                "message": "Starting browser navigation..."
            })
            context = await browser_manager.create_context()
            page = await browser_manager.create_page(context)

            first_url_prompt = FIRST_URL_PROMPT.substitute(user_prompt=self.user_prompt)
            max_attempts = 3
            attempt = 0
            first_url = None

            while attempt < max_attempts:
                url_response = call_model(
                    chat_history=[{"role": "user", "content": first_url_prompt}],
                    model=self.first_url_model
                )
                if url_response and url_response.strip().startswith("https://"):
                    first_url = url_response.strip()
                    break
                attempt += 1
                self.logger.debug(
                    f"Invalid URL format (attempt {attempt}/{max_attempts}): {url_response}"
                )

            if not first_url:
                log_message = "CUA web browser failed to get valid URL after {max_attempts} attempts."
                self.logger.debug(log_message, extra={'no_memory': True})
                self.socketio.emit('reasoning_update', {
                    "message": log_message
                })
                self.info_for_intellichain_agent += log_message
            else:

                self.socketio.emit('reasoning_update', {
                    "message": "visiting url: " + first_url
                })

                await page.goto(first_url)
                await asyncio.sleep(5)

                self.response = self.client.responses.create(
                    model=self.model,
                    tools=self.tools,
                    input=[{"role": "user", "content": self.user_prompt}],
                    reasoning={"generate_summary": "concise"},
                    truncation="auto"
                )
                self.logger.debug("Initial response from model: %s", self.response.output, extra={'no_memory': True})

                while True:
                    self.logger.debug("Response: %s", self.response.output, extra={'no_memory': True})

                    computer_calls = [item for item in self.response.output if item.type == "computer_call"]
                    if not computer_calls:
                        messages = [item for item in self.response.output if item.type == "message"]
                        if messages:
                            message = messages[0].content[0].text
                            self.info_for_intellichain_agent += message
                            self.logger.debug(
                                "Got a message from the CUA model: %s",
                                message,
                                extra={'no_memory': True}
                            )
                            self.socketio.emit('follow_up_request', {
                                "message": message
                            })
                            self.logger.debug(
                                "Waiting for follow-up message",
                                extra={'no_memory': True}
                            )
                            timeout = 60
                            follow_up_message = await self.wait_for_follow_up(timeout)

                            if follow_up_message == "timeout":
                                new_info = "No follow-up message received fr om user, breaking the interaction loop."
                                self.info_for_intellichain_agent += new_info
                                self.logger.debug(
                                    new_info,
                                    extra={'no_memory': True}
                                )
                                break
                            stop_confirmation_prompt = BROWSER_STOP_CONFIRMATION.substitute(user_prompt=follow_up_message, assistant_request=message)
                            stop_confirmation = call_model(
                                chat_history=[{"role": "user", "content": stop_confirmation_prompt}],
                                model=self.first_url_model
                            )

                            if stop_confirmation == "stop":
                                self.logger.debug(
                                    "Received stop command from user, breaking the interaction loop",
                                    extra={'no_memory': True}
                                )
                                break  

                            self.logger.debug(
                                "Received continue command from user, continuing the interaction loop",
                                extra={'no_memory': True}
                            )
                            
                            follow_up_input = {"role": "user", "content": follow_up_message}
                            self.response = self.client.responses.create(
                                model=self.model,
                                previous_response_id=self.response.id,
                                tools=self.tools,
                                input=[follow_up_input],
                                truncation="auto"
                            )
                            self.logger.debug(
                                "After follow-up response: %s",  
                                self.response.output,
                                extra={'no_memory': True}
                            )
                            continue
                        else:
                            self.logger.debug("No messages or computer calls in response, that's weird. Let's try to continue with the loop sending a screenshot...")
                            screenshot_base64 = await self.screenshot_manager.capture(page)
                            input_payload = [{
                                "call_id": self.last_call_id,
                                "type": "computer_call_output",
                                "output": {
                                    "type": "input_image",
                                    "image_url": f"data:image/png;base64,{screenshot_base64}"
                                }
                            }]  

                            self.response = self.client.responses.create(
                                model=self.model,
                                previous_response_id=self.response.id,
                                tools=self.tools,
                                input=input_payload,
                                truncation="auto"  
                            )
                            continue

                    computer_call = computer_calls[0]
                    self.last_call_id = computer_call.call_id
                    action = computer_call.action

                    if action.type != "screenshot":
                        await handle_model_action(page, action, self.socketio)
                        await asyncio.sleep(2)

                    screenshot_base64 = await self.screenshot_manager.capture(page)

                    input_payload = [{
                        "call_id": self.last_call_id,
                        "type": "computer_call_output",
                        "output": {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{screenshot_base64}"
                        }
                    }]

                    self.response = self.client.responses.create(
                        model=self.model,
                        previous_response_id=self.response.id,
                        tools=self.tools,
                        input=input_payload,
                        truncation="auto"
                    )

        self.logger.debug("Exited BrowserManager context, about to return from run()")
        return self.info_for_intellichain_agent



    async def wait_for_follow_up(self, timeout):     
        """
        Poll Redis for a follow-up response keyed by the session_id.
        """
        redis_key = f"followup:{self.session_id}"
        start_time = asyncio.get_event_loop().time()

        while True:
            response = await self.redis.get(redis_key)
            if response:
                await self.redis.delete(redis_key)  
                return response
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                return "timeout"   

            await asyncio.sleep(1)

