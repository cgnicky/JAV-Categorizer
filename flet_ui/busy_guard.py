class BusyGuard:
    def __init__(self):
        self.worker = None

    def is_busy(self) -> bool:
        if self.worker is None:
            return False
        if hasattr(self.worker, "is_running"):
            return self.worker.is_running()
        return False

    def set_worker(self, worker) -> None:
        self.worker = worker

    def warn_if_busy(self) -> bool:
        return self.is_busy()

    def request_stop(self) -> None:
        worker = self.worker
        if worker is not None and hasattr(worker, "request_stop"):
            if hasattr(worker, "is_running") and worker.is_running():
                worker.request_stop()
