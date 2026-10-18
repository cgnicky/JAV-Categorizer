from PyQt5.QtWidgets import QMessageBox

from core.settings import AppSettings, save_settings
from workers.classifier_worker import JavClassifier
from workers.query_worker import JavQuery
from workers.updater_worker import JavDatabaseUpdater


class MainTabsMixin:
    """Classifier, media query, and database updater tabs."""

    def _load_settings_into_ui(self, settings: AppSettings) -> None:
        self._settings = settings
        if settings.classifier_path:
            self.ui.srcEdit.setText(settings.classifier_path)
        if settings.fixer_path:
            self.ui.fixerPathEdit.setText(settings.fixer_path)
        if settings.actor_path:
            self.ui.actorPathEdit.setText(settings.actor_path)

    def _persist_path(self, field: str, value: str) -> None:
        setattr(self._settings, field, value)
        save_settings(self._settings)

    def javClassifierTab(self):
        default = self._settings.classifier_path or ""
        if default:
            self.ui.srcEdit.setText(default)
        self.ui.execBtn.clicked.connect(self.javClassifierMain)
        self.ui.classifierStopBtn.clicked.connect(self.classifierStop)
        self.ui.classifierStopBtn.setEnabled(False)
        self.ui.clearBtn.clicked.connect(self.clearOutput)
        self.ui.browseBtn.clicked.connect(self.selectFolder)

    def javClassifierMain(self):
        if self.busy.warn_if_busy(self):
            return
        path = self.ui.srcEdit.text()
        self._persist_path("classifier_path", path)
        worker = JavClassifier(
            path,
            lookup_delay_seconds=self.javlib_search_pause_seconds(),
        )
        worker.result.connect(self.msgLogging)
        self._start_worker(
            worker,
            self.classifier_done,
            [self.ui.execBtn],
            stop_buttons=[self.ui.classifierStopBtn],
        )

    def classifierStop(self):
        self.busy.request_stop()

    def classifier_done(self):
        QMessageBox.information(self, "Message", "Process Completed!")

    def selectFolder(self):
        path = self.pick_directory(self.ui.srcEdit.text() or "")
        if path:
            self.ui.srcEdit.setText(path)
            self._persist_path("classifier_path", path)

    def msgLogging(self, content):
        self.ui.msgBox.append(content)

    def clearOutput(self):
        self.ui.msgBox.clear()

    def javQueryTab(self):
        self.ui.searchKeywordsTextBox.setText("Enter Your Search Keywords Here!!")
        self.ui.queryBtn.clicked.connect(self.javQueryMain)
        self.ui.queryResultClearBtn.clicked.connect(self.clearQueryResult)
        self.ui.searchKeywordsTextBox.clicked.connect(self.ui.searchKeywordsTextBox.clear)

    def javQueryMain(self):
        if self.busy.warn_if_busy(self):
            return
        search_type = self.set_search_type()
        if not search_type:
            return
        self.ui.queryResultTextBox.clear()
        worker = JavQuery(self.ui.searchKeywordsTextBox.text(), search_type)
        worker.result.connect(self.msgLoggingJavQuery)
        worker.result2.connect(self.updateRecordsCount)
        self._start_worker(worker, disable_widgets=[self.ui.queryBtn])

    def msgLoggingJavQuery(self, content):
        self.ui.queryResultTextBox.append(content)

    def updateRecordsCount(self, record_count):
        self.ui.recordCountNumber.setText(str(record_count))

    def clearQueryResult(self):
        self.ui.queryResultTextBox.clear()

    def set_search_type(self):
        if self.ui.actorRadioBtn.isChecked():
            return "actor"
        if self.ui.titleRadioBtn.isChecked():
            return "label"
        QMessageBox.information(self, "Error!", "No Type Selected!")
        return None

    def javDBUpdaterTab(self):
        default_str = self._settings.updater_dir_placeholder
        self.ui.dirTextBox.setText(default_str)
        self.ui.dirBrowseBtn.clicked.connect(
            lambda: self.selectFolderJavUpdater(self.ui.dirTextBox.text(), default_str)
        )
        self.ui.addDirBtn.clicked.connect(
            lambda: self.addPathToList(self.ui.dirTextBox.text(), default_str)
        )
        self.ui.clearDirListBtn.clicked.connect(self.clearDirList)
        self.ui.updateBtn.clicked.connect(self.javDBUpdaterMain)
        self.ui.dirTextBox.clicked.connect(self.ui.dirTextBox.clear)
        self.ui.dirList.itemDoubleClicked.connect(self.removeItemOnSelection)

    def javDBUpdaterMain(self):
        if self.busy.warn_if_busy(self):
            return
        dir_list = [str(self.ui.dirList.item(i).text()) for i in range(self.ui.dirList.count())]
        if not dir_list:
            QMessageBox.information(self, "Error!", "Empty Directory List!")
            return
        self._pending_update_paths = dir_list
        self.ui.updateBtn.setEnabled(False)
        self.startNextUpdaterJob()

    def startNextUpdaterJob(self):
        if not self._pending_update_paths:
            self.ui.statusContent.setText("Idle")
            self.ui.updateBtn.setEnabled(True)
            return

        path = self._pending_update_paths.pop(0)
        self.ui.updateProgressBar.reset()
        worker = JavDatabaseUpdater(path)
        worker.result.connect(self.showStatusText)
        worker.pBarMaxValue.connect(self.setProgressMaximum)
        worker.progressResult.connect(self.updateProgress)
        worker.finished.connect(self.startNextUpdaterJob)
        self.busy.set_worker(worker)
        worker.start()

    def selectFolderJavUpdater(self, textbox_path, default_str):
        start = textbox_path if textbox_path not in {default_str, ""} else ""
        path = self.pick_directory(start)
        if path:
            self.ui.dirTextBox.setText(path)

    def addPathToList(self, dir_path, default_str):
        cleaned = dir_path.strip()
        if cleaned and cleaned != default_str:
            existing = {self.ui.dirList.item(i).text() for i in range(self.ui.dirList.count())}
            if cleaned not in existing:
                self.ui.dirList.addItem(cleaned)
        else:
            QMessageBox.information(self, "Error!", "Invalid Directory!")

    def clearDirList(self):
        self.ui.dirList.clear()

    def showStatusText(self, content):
        self.ui.statusContent.setText(content)

    def updateProgress(self, complete):
        self.ui.updateProgressBar.setValue(complete)

    def setProgressMaximum(self, max_value):
        self.ui.updateProgressBar.setMaximum(max_value)

    def removeItemOnSelection(self, item):
        row = self.ui.dirList.row(item)
        if row >= 0:
            self.ui.dirList.takeItem(row)
