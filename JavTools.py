import sys

from PyQt5.QtWidgets import QApplication, QTabWidget

from core.logging_config import setup_logging
from core.settings import load_settings
from PyQt5GUI import Ui_TabWidget
from ui.busy_guard import BusyGuard
from ui.extra_tabs import ExtraTabsMixin
from ui.helpers import pick_directory as _pick_directory
from ui.javlib_pause import JavlibPauseMixin
from ui.main_tabs import MainTabsMixin


class AppWindow(JavlibPauseMixin, ExtraTabsMixin, MainTabsMixin, QTabWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_TabWidget()
        self.ui.setupUi(self)
        self.busy = BusyGuard()
        self._pending_update_paths: list[str] = []
        self._init_extra_tab_state()
        self._load_settings_into_ui(load_settings())
        self._wire_javlib_pause_controls()
        self.setFixedSize(self.size())
        self.javClassifierTab()
        self.javQueryTab()
        self.javDBUpdaterTab()
        self.filenameFixerTab()
        self.actorSearcherTab()
        self.show()

    def pick_directory(self, start_path=""):
        return _pick_directory(self, start_path)

    def _start_worker(
        self,
        worker,
        on_finished=None,
        disable_widgets=None,
        stop_buttons=None,
    ):
        self.busy.set_worker(worker)
        if disable_widgets:
            for widget in disable_widgets:
                widget.setEnabled(False)
        if stop_buttons:
            for widget in stop_buttons:
                widget.setEnabled(True)
        worker.finished.connect(
            lambda: self._on_worker_finished(on_finished, disable_widgets, stop_buttons)
        )
        worker.start()

    def _on_worker_finished(self, callback, disable_widgets, stop_buttons=None):
        self.busy.set_worker(None)
        if disable_widgets:
            for widget in disable_widgets:
                widget.setEnabled(True)
        if stop_buttons:
            for widget in stop_buttons:
                widget.setEnabled(False)
        if callback:
            callback()


def main():
    setup_logging()
    app = QApplication(sys.argv)
    window = AppWindow()
    window.setCurrentIndex(0)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
