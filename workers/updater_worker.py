from PyQt5.QtCore import QThread, pyqtSignal

from core.updater import run_update


class JavDatabaseUpdater(QThread):
    result = pyqtSignal(str)
    progressResult = pyqtSignal(int)
    pBarMaxValue = pyqtSignal(int)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        for message in run_update(
            self.path,
            on_message=self.result.emit,
            on_progress=self.progressResult.emit,
            on_max=self.pBarMaxValue.emit,
        ):
            self.result.emit(message)
