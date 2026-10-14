from PySide6.QtCore import QObject, Signal


class IndicatorRefreshWorker(QObject):
    """Runs IndicatorUseCases.refresh() off the GUI thread.

    Move an instance onto a QThread and connect the thread's started signal to
    run(); the worker emits finished(result_dict) on success or failed(message)
    on an unexpected error, then done() so the caller can tear down the thread.
    """

    finished = Signal(dict)
    failed = Signal(str)
    done = Signal()

    def __init__(self, indicator_use_cases, keys=None):
        super().__init__()
        self._use_cases = indicator_use_cases
        self._keys = keys

    def run(self):
        try:
            # Network only — persisting to SQLite happens on the main thread
            # (the connection is bound to the thread that created it).
            result = self._use_cases.fetch_remote(self._keys)
            self.finished.emit(result)
        except Exception as exc:  # defensive: keep the UI responsive on any error
            self.failed.emit(str(exc))
        finally:
            self.done.emit()
