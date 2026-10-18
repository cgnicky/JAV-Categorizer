from PyQt5.QtWidgets import QMessageBox


class BusyGuard:
    def __init__(self):
        self.worker = None

    def is_busy(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def set_worker(self, worker) -> None:
        self.worker = worker

    def warn_if_busy(self, parent) -> bool:
        if self.is_busy():
            QMessageBox.information(parent, "Busy", "Another task is still running.")
            return True
        return False

    def request_stop(self) -> None:
        worker = self.worker
        if worker is not None and worker.isRunning() and hasattr(worker, "request_stop"):
            worker.request_stop()
