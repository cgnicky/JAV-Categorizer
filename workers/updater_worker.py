from collections.abc import Callable

from core.updater import run_update
from workers.task_runner import BackgroundTask


class JavDatabaseUpdater(BackgroundTask):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def start(
        self,
        on_message: Callable[[str], None],
        on_progress: Callable[[int], None] | None = None,
        on_max: Callable[[int], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        def run() -> None:
            run_update(
                self.path,
                on_message=on_message,
                on_progress=on_progress or (lambda _i: None),
                on_max=on_max or (lambda _i: None),
            )

        super().start(run, on_finished)
