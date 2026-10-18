from PyQt5.QtCore import QThread, pyqtSignal

from core.query import run_query


class JavQuery(QThread):
    result = pyqtSignal(str)
    result2 = pyqtSignal(int)

    def __init__(self, search_keywords, search_type):
        super().__init__()
        self.search_keywords = search_keywords
        self.search_type = search_type

    def run(self):
        count, lines = run_query(self.search_keywords, self.search_type)
        if count:
            self.result2.emit(count)
        for line in lines:
            self.result.emit(line)
