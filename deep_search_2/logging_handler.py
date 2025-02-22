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

class MemoryFilter(logging.Filter):
    def filter(self, record):
        return not getattr(record, 'no_memory', False)

class ConsoleFilter(logging.Filter):
    def filter(self, record):
        return not getattr(record, 'no_print', False)

class LoggingConfigurator:
    @staticmethod
    def configure_logger(execution_logs: List[str]) -> logging.Logger:
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)

        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("neo4j").setLevel(logging.ERROR)
        logging.getLogger("httpx").setLevel(logging.WARNING)

        logger.handlers = []
        logger.propagate = False 

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        memory_handler = MemoryLogHandler(execution_logs)
        memory_handler.setLevel(logging.DEBUG)
        memory_handler.addFilter(MemoryFilter())
        memory_handler.setFormatter(formatter)
        logger.addHandler(memory_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.addFilter(ConsoleFilter())
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    @staticmethod
    def enrich_log(message: str, enrichment_key: str) -> str:
        if enrichment_key == "add_green_divider":
            divider = "\n\033[32m" + "-" * 150 + "\033[0m\n"
            return f"\n{divider}\n{message}\n{divider}\n"
        elif enrichment_key == "add_red_divider":
            divider = "\n\033[31m" + "-" * 150 + "\033[0m\n"
            return f"\n{divider}\n{message}\n{divider}\n"
        elif enrichment_key == "add_blue_divider":
            divider = "\n\033[34m" + "-" * 150 + "\033[0m\n"
            return f"\n{divider}\n{message}\n{divider}\n"
        elif enrichment_key == "add_orange_divider":
            divider = "\n\033[33m" + "-" * 150 + "\033[0m\n"
            return f"\n{divider}\n{message}\n{divider}\n"
        else:
            return message
