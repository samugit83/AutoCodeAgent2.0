from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

class CommandExecutor:
    def __init__(self, logger, max_retries=2, retry_backoff=2000):
        self.logger = logger
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def execute(self, command: str, page, task_name: str) -> bool:
        for attempt in range(self.max_retries + 1):
            try:
                exec(command, {'page': page, 'self': self})    
                self.logger.debug(f"🟢 task_name: '{task_name}', Command '{command}' executed successfully") 
                return True
            except PlaywrightTimeoutError as e:
                self._handle_error(e, task_name, command, "⏰ Timeout", attempt)  
            except PlaywrightError as e:
                self._handle_error(e, task_name, command, "🎭 Playwright")
            except Exception as e:
                self._handle_error(e, task_name, command, "🐍 Python")
            return False

    def _handle_error(self, error, task_name, command, error_type, attempt=None):
        error_msg = f"{error_type} error in task '{task_name}': {command}\nError: {str(error)}"
        if attempt and attempt == self.max_retries:
            error_msg += "\nMax retries reached."
        self.logger.debug(error_msg) 