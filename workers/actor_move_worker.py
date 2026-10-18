import copy

from PyQt5.QtCore import QThread, pyqtSignal

from core.actor_searcher import ActorGroup, move_actor_groups
from core.db import DEFAULT_DB_PATH


class ActorMoveWorker(QThread):
    progress = pyqtSignal(int, int, str)
    log_line = pyqtSignal(str)

    def __init__(self, path: str, groups: list[ActorGroup], db_path=None):
        super().__init__()
        self.path = path
        self.groups = copy.deepcopy(groups)
        self.db_path = db_path if db_path is not None else DEFAULT_DB_PATH

    def run(self):
        def on_progress(current: int, total: int, filename: str) -> None:
            self.progress.emit(current, total, filename)

        def on_message(text: str) -> None:
            self.log_line.emit(text)

        move_actor_groups(
            self.path,
            self.groups,
            db_path=self.db_path,
            on_message=on_message,
            on_progress=on_progress,
        )
