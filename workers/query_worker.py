from collections.abc import Callable

from core.query import run_query
from workers.task_runner import BackgroundTask


class JavQuery(BackgroundTask):
    def __init__(self, search_keywords, search_type):
        super().__init__()
        self.search_keywords = search_keywords
        self.search_type = search_type

    def start(
        self,
        on_result: Callable[[str], None],
        on_count: Callable[[int], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        def run() -> None:
            count, lines = run_query(self.search_keywords, self.search_type)
            if count and on_count is not None:
                on_count(count)
            for line in lines:
                on_result(line)

        super().start(run, on_finished)
