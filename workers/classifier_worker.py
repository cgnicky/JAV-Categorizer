from PyQt5.QtCore import QThread, pyqtSignal

from core.classifier import ClassifierService


class JavClassifier(QThread):
    result = pyqtSignal(str)

    def __init__(self, path, lookup_delay_seconds: float = 0.0):
        super().__init__()
        self.path = path
        self.lookup_delay_seconds = lookup_delay_seconds
        self._stop_requested = False
        self._service: ClassifierService | None = None

    def request_stop(self):
        self._stop_requested = True
        if self._service is not None and self._service.lookup is not None:
            self._service.lookup.request_stop()

    def run(self):
        self._service = ClassifierService(
            self.path,
            self.result.emit,
            should_stop=lambda: self._stop_requested,
            lookup_delay_seconds=self.lookup_delay_seconds,
        )
        self._service.run()
        self._service = None
