from PyQt5.QtCore import QThread, pyqtSignal

from core.actor_searcher import scan_and_group


class ActorSearchWorker(QThread):
    result = pyqtSignal(str)
    groups_ready = pyqtSignal(list)

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

    def run(self):
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
            on_message=self.result.emit,
            lookup_delay_seconds=self.lookup_delay_seconds,
            lookup_factory=lookup_factory,
            should_stop=lambda: self._stop_requested,
        )
        self.groups_ready.emit(groups)
