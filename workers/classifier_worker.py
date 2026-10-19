from collections.abc import Callable

from core.classifier import ClassifierService
from workers.task_runner import StoppableBackgroundTask


class JavClassifier(StoppableBackgroundTask):
    def __init__(self, path, lookup_delay_seconds: float = 0.0):
        super().__init__()
        self.path = path
        self.lookup_delay_seconds = lookup_delay_seconds
        self._stop_requested = False
        self._service: ClassifierService | None = None
        self.on_result: Callable[[str], None] | None = None
        self.on_finished: Callable[[], None] | None = None

    def request_stop(self) -> None:
        self._stop_requested = True
        if self._service is not None and self._service.lookup is not None:
            self._service.lookup.request_stop()

    def _run(self) -> None:
        emit = self.on_result or (lambda _s: None)
        self._service = ClassifierService(
            self.path,
            emit,
            should_stop=lambda: self._stop_requested,
            lookup_delay_seconds=self.lookup_delay_seconds,
        )
        self._service.run()
        self._service = None

    def start(self, on_result: Callable[[str], None], on_finished: Callable[[], None] | None = None) -> None:
        self.on_result = on_result
        self.on_finished = on_finished
        self._stop_requested = False
        super().start(self._run, on_finished)
