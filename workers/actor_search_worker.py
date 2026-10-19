from collections.abc import Callable

from core.actor_searcher import scan_and_group
from workers.task_runner import StoppableBackgroundTask


class ActorSearchWorker(StoppableBackgroundTask):
    def __init__(self, path: str, lookup_delay_seconds: float = 0.0):
        super().__init__()
        self.path = path
        self.lookup_delay_seconds = lookup_delay_seconds
        self._stop_requested = False
        self._lookup = None

    def request_stop(self) -> None:
        self._stop_requested = True
        if self._lookup is not None:
            self._lookup.request_stop()

    def start(
        self,
        on_log: Callable[[str], None],
        on_groups_ready: Callable[[list], None],
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        self._stop_requested = False

        def run() -> None:
            def lookup_factory(on_message):
                from core.actor_lookup import ActorLookup
                from core.db import DEFAULT_DB_PATH

                self._lookup = ActorLookup(
                    on_message,
                    db_path=DEFAULT_DB_PATH,
                    web_delay_seconds=self.lookup_delay_seconds,
                    should_stop=lambda: self._stop_requested,
                )
                return self._lookup

            groups = scan_and_group(
                self.path,
                on_message=on_log,
                lookup_delay_seconds=self.lookup_delay_seconds,
                lookup_factory=lookup_factory,
                should_stop=lambda: self._stop_requested,
            )
            on_groups_ready(groups)

        super().start(run, on_finished)
