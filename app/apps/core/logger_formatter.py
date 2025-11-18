# apps/core/logger_formatter.py
import logging


class SafeContextFormatter(logging.Formatter):
    """
    Formatter that ensures every LogRecord has 'context' key.
    Avoids KeyError for Django internal logs.
    """

    def format(self, record):
        if not hasattr(record, "context"):
            record.context = {}
        return super().format(record)
