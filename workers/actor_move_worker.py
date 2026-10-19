import copy
from collections.abc import Callable

from core.actor_searcher import ActorGroup, move_actor_groups
from core.db import DEFAULT_DB_PATH
from workers.task_runner import BackgroundTask


class ActorMoveWorker(BackgroundTask):
    def __init__(self, path: str, groups: list[ActorGroup], db_path=None):
        super().__init__()
        self.path = path
        self.groups = copy.deepcopy(groups)
        self.db_path = db_path if db_path is not None else DEFAULT_DB_PATH

    def start(
        self,
        on_progress: Callable[[int, int, str], None],
        on_log: Callable[[str], None],
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        def run() -> None:
            move_actor_groups(
                self.path,
                self.groups,
                db_path=self.db_path,
                on_message=on_log,
                on_progress=on_progress,
            )

        super().start(run, on_finished)
