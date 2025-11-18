import logging
import traceback
from typing import Any, Dict, Optional


class CustomLogger:
    """
    Django-aligned structured logger.

    - Uses Django LOGGING dictConfig
    - No handlers or formatters defined here
    - Adds structured context safely
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def debug(self, message: str, **context: Any) -> None:
        self.logger.debug(message, extra=self._extra(context))

    def info(self, message: str, **context: Any) -> None:
        self.logger.info(message, extra=self._extra(context))

    def warning(self, message: str, **context: Any) -> None:
        self.logger.warning(message, extra=self._extra(context))

    def error(
        self,
        message: str,
        *,
        exc: Optional[BaseException] = None,
        **context: Any,
    ) -> None:
        if exc:
            context["exception"] = self._format_exception(exc)
        self.logger.error(message, extra=self._extra(context))

    def critical(
        self,
        message: str,
        *,
        exc: Optional[BaseException] = None,
        **context: Any,
    ) -> None:
        if exc:
            context["exception"] = self._format_exception(exc)
        self.logger.critical(message, extra=self._extra(context))

    # --------------------------------------------------
    # Internals
    # --------------------------------------------------

    def _extra(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject structured context into LogRecord.
        """
        return {
            "context": context,
        }

    def _format_exception(self, exc: BaseException) -> Dict[str, Any]:
        return {
            "type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
