"""
ErrorHandler — centralised exception logging and user-facing error reporting.

Keeps page code clean: instead of sprinkling try/except + logger.exception
everywhere, call ``safe_call`` or ``log_exception``.

Usage
-----
    from qt_app.services.error_handler import eh

    # Wrap a risky call
    result = eh.safe_call("schedule autosave", self._do_save)

    # Explicit log + user toast
    try:
        ...
    except Exception as exc:
        eh.log_exception("edit_block", exc)
        eh.show_error_toast("Could not update block.")

Logs to: logs/qt_errors.log
"""
from __future__ import annotations

import logging
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# ── File logger ───────────────────────────────────────────────────────────────
_logs_dir = Path(__file__).parent.parent.parent / "logs"
_logs_dir.mkdir(exist_ok=True)

_file_handler = logging.FileHandler(_logs_dir / "qt_errors.log", encoding="utf-8")
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s")
)

_err_logger = logging.getLogger("benchflow.errors")
if not _err_logger.handlers:
    _err_logger.addHandler(_file_handler)
    _err_logger.setLevel(logging.ERROR)


# ── ErrorHandler ──────────────────────────────────────────────────────────────

class _ErrorHandler:
    """Singleton-style error reporting helper.

    Never raises — all methods are safe to call from signal handlers.
    """

    def log_exception(self, context: str, exc: Exception) -> None:
        """Write *exc* + traceback to the error log."""
        tb = traceback.format_exc()
        _err_logger.error(f"[{context}] {type(exc).__name__}: {exc}\n{tb}")

    def show_error_toast(self, message: str) -> None:
        """Show a non-blocking error toast.  Silently does nothing if the
        toast system is not yet initialized."""
        try:
            from qt_app.components.toast import ToastManager  # late import
            ToastManager.show_error(message)
        except Exception:
            pass   # toast not ready yet

    def show_warning_toast(self, message: str) -> None:
        try:
            from qt_app.components.toast import ToastManager
            ToastManager.show_warning(message)
        except Exception:
            pass

    def safe_call(self, context: str, func: Callable[..., Any],
                  *args: Any, **kwargs: Any) -> Any:
        """Call *func* with *args*/*kwargs*; log + optionally toast on exception.

        Returns the function's return value, or ``None`` on error.
        """
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            self.log_exception(context, exc)
            return None

    def backup_corrupt_file(self, path: Path) -> Path | None:
        """Copy *path* to ``<path>.corrupt_TIMESTAMP.json`` and return the
        backup path, or ``None`` if the copy fails."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_suffix(f".corrupt_{ts}.json")
        try:
            shutil.copy2(path, backup)
            _err_logger.warning(f"Corrupt file backed up: {backup}")
            return backup
        except Exception as exc:
            _err_logger.error(f"Could not backup {path}: {exc}")
            return None


# ── Module-level singleton ────────────────────────────────────────────────────

eh = _ErrorHandler()
