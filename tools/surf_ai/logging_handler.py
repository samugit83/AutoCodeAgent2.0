import logging
from typing import List

class MemoryLogHandler(logging.Handler):
    def __init__(self, execution_logs: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execution_logs = execution_logs

    def emit(self, record):
        if getattr(record, 'no_memory', False):
            return
        log_entry = self.format(record)
        self.execution_logs.append(log_entry)

class LoggingConfigurator:
    @staticmethod
    def configure_logger(execution_logs: List[str]) -> logging.Logger:
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        
        memory_handler = MemoryLogHandler(execution_logs) 
        memory_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        memory_handler.setFormatter(formatter)
        
        logger.addHandler(memory_handler)
        return logger