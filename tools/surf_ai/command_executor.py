import asyncio
from playwright.async_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

class CommandExecutor:
    def __init__(self, logger, max_retries=2, retry_backoff=2000):
        self.logger = logger
        self.max_retries = max_retries
        # Convert retry_backoff to seconds.
        self.retry_backoff = retry_backoff / 1000.0

    async def execute(self, command: str, page, task_name: str) -> bool:
        for attempt in range(self.max_retries + 1):
            try:
                # Wrap the command string in an async function.
                # Replace semicolons with newline+indentation to support multiple commands.
                command = 'await ' + command
                wrapped_command = "    " + command.replace(";", "\n    ") + "\n"
                async_code = f"async def __ex(page, self_obj):\n{wrapped_command}"
                local_vars = {}
                # Use a dedicated dict for globals (if needed, include additional context)
                exec(async_code, {'page': page, 'self_obj': self}, local_vars)
                # Now call the newly defined async function.
                await local_vars["__ex"](page, self)
                self.logger.debug(
                    f"🟢 task_name: '{task_name}', Command '{command}' executed successfully"
                )
                return True
            except PlaywrightTimeoutError as e:
                self._handle_error(e, task_name, command, "⏰ Timeout", attempt)
            except PlaywrightError as e:
                self._handle_error(e, task_name, command, "🎭 Playwright", attempt)
            except Exception as e:
                self._handle_error(e, task_name, command, "🐍 Python", attempt)
            # Wait before retrying (if not the last attempt)
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_backoff)
        return False

    def _handle_error(self, error, task_name, command, error_type, attempt=None):
        error_msg = f"{error_type} error in task '{task_name}': {command}\nError: {str(error)}"
        if attempt is not None and attempt == self.max_retries:
            error_msg += "\nMax retries reached."
        self.logger.debug(error_msg)
