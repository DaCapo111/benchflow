"""
Perf — lightweight performance instrumentation for BenchFlow Qt UI.

Only logs operations that exceed a configurable threshold (default 50 ms)
to keep the log quiet under normal conditions.

Usage
-----
    from qt_app.services.perf import perf

    # Context manager form (recommended)
    with perf.measure("render_step_cards"):
        self._render_cards()

    # Manual form
    perf.start("schedule_recalc")
    exp.recalculate_times()
    perf.end("schedule_recalc")

Logs to: logs/qt_perf.log
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# ── File logger ───────────────────────────────────────────────────────────────
_logs_dir = Path(__file__).parent.parent.parent / "logs"
_logs_dir.mkdir(exist_ok=True)

_file_handler = logging.FileHandler(_logs_dir / "qt_perf.log", encoding="utf-8")
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s")
)
_perf_logger = logging.getLogger("benchflow.perf")
if not _perf_logger.handlers:
    _perf_logger.addHandler(_file_handler)
    _perf_logger.setLevel(logging.DEBUG)


# ── Perf ──────────────────────────────────────────────────────────────────────

class _Perf:
    """Performance measurement helper.

    Thread-safe for reads; concurrent measure() calls with the same label
    from different call sites will interleave but each is independent.
    """

    DEFAULT_THRESHOLD_MS: float = 50.0

    def __init__(self) -> None:
        self._starts: dict[str, float] = {}

    # ── Context-manager API ───────────────────────────────────────────────────

    @contextmanager
    def measure(self, label: str,
                threshold_ms: float = DEFAULT_THRESHOLD_MS) -> Iterator[None]:
        """Measure the block's wall-clock time.

        Logs a WARNING to qt_perf.log only when elapsed > *threshold_ms*.
        """
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            if elapsed_ms > threshold_ms:
                _perf_logger.warning(f"SLOW [{label}] {elapsed_ms:.1f} ms")
            else:
                _perf_logger.debug(f"[{label}] {elapsed_ms:.1f} ms")

    # ── Manual start/end API ──────────────────────────────────────────────────

    def start(self, label: str) -> None:
        """Record start time for *label*."""
        self._starts[label] = time.perf_counter()

    def end(self, label: str,
            threshold_ms: float = DEFAULT_THRESHOLD_MS) -> float:
        """Compute elapsed since ``start(label)`` and log if slow.

        Returns elapsed milliseconds (0.0 if ``start`` was never called).
        """
        t0 = self._starts.pop(label, None)
        if t0 is None:
            return 0.0
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if elapsed_ms > threshold_ms:
            _perf_logger.warning(f"SLOW [{label}] {elapsed_ms:.1f} ms")
        else:
            _perf_logger.debug(f"[{label}] {elapsed_ms:.1f} ms")
        return elapsed_ms


# ── Module-level singleton ────────────────────────────────────────────────────

perf = _Perf()
