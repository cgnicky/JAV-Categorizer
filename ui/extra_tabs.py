from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QTableWidgetItem, QTreeWidgetItem

from core.actor_searcher import ActorGroup, count_move_tasks, scan_first_level_mp4
from core.db import DEFAULT_DB_PATH
from core.filename_fixer import RenameItem, apply_renames, scan_directory


class ExtraTabsMixin:
    """Filename fixer and actor searcher tab wiring."""

    def _init_extra_tab_state(self):
        self._rename_items: list[RenameItem] = []
        self._actor_groups: list[ActorGroup] = []
        self._actor_header_sync = False
        self._actor_move_progress: QProgressDialog | None = None

    def filenameFixerTab(self):
        self.ui.fixerBrowseBtn.clicked.connect(self.fixerBrowse)
        self.ui.fixerScanBtn.clicked.connect(self.fixerScan)
        self.ui.fixerSelectAllBtn.clicked.connect(self.fixerSelectAll)
        self.ui.fixerClearSelectionBtn.clicked.connect(self.fixerClearSelection)
        self.ui.fixerRenameBtn.clicked.connect(self.fixerRename)

    def fixerBrowse(self):
        path = self.pick_directory(self.ui.fixerPathEdit.text())
        if path:
            self.ui.fixerPathEdit.setText(path)
            self._persist_path("fixer_path", path)

    def fixerScan(self):
        path = self.ui.fixerPathEdit.text().strip()
        if not path:
            QMessageBox.information(self, "Error!", "Please select a directory.")
            return
        self._rename_items = scan_directory(path)
        self._populate_fixer_table()
        self.ui.fixerLog.append(f"Found {len(self._rename_items)} file(s) to fix.")

    def _populate_fixer_table(self):
        table = self.ui.fixerTable
        table.setRowCount(len(self._rename_items))
        for row, item in enumerate(self._rename_items):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked if item.checked else Qt.Unchecked)
            table.setItem(row, 0, check_item)
            table.setItem(row, 1, QTableWidgetItem(item.src_name))
            table.setItem(row, 2, QTableWidgetItem(item.dest_name))

    def _sync_fixer_checks_from_table(self):
        for row, item in enumerate(self._rename_items):
            check_item = self.ui.fixerTable.item(row, 0)
            item.checked = check_item.checkState() == Qt.Checked

    def fixerSelectAll(self):
        for row in range(self.ui.fixerTable.rowCount()):
            self.ui.fixerTable.item(row, 0).setCheckState(Qt.Checked)
        for rename_item in self._rename_items:
            rename_item.checked = True

    def fixerClearSelection(self):
        for row in range(self.ui.fixerTable.rowCount()):
            self.ui.fixerTable.item(row, 0).setCheckState(Qt.Unchecked)
        for rename_item in self._rename_items:
            rename_item.checked = False

    def fixerRename(self):
        path = self.ui.fixerPathEdit.text().strip()
        if not path or not self._rename_items:
            QMessageBox.information(self, "Error!", "Scan a directory with invalid names first.")
            return
        self._sync_fixer_checks_from_table()
        for msg in apply_renames(path, self._rename_items):
            self.ui.fixerLog.append(msg)
        self.fixerScan()

    def actorSearcherTab(self):
        self.ui.actorBrowseBtn.clicked.connect(self.actorBrowse)
        self.ui.actorScanBtn.clicked.connect(self.actorScan)
        self.ui.actorStopBtn.clicked.connect(self.actorScanStop)
        self.ui.actorStopBtn.setEnabled(False)
        self.ui.actorMoveBtn.clicked.connect(self.actorMove)
        self.ui.actorHeaderCheck.setTristate(True)
        self.ui.actorHeaderCheck.setEnabled(False)
        self.ui.actorHeaderCheck.stateChanged.connect(self._on_actor_header_check_changed)
        self.ui.actorTree.itemChanged.connect(self._on_actor_tree_item_changed)

    def actorBrowse(self):
        path = self.pick_directory(self.ui.actorPathEdit.text())
        if path:
            self.ui.actorPathEdit.setText(path)
            self._persist_path("actor_path", path)

    def actorScan(self):
        if self.busy.warn_if_busy(self):
            return
        path = self.ui.actorPathEdit.text().strip()
        if not path:
            QMessageBox.information(self, "Error!", "Please select a directory.")
            return
        self.ui.actorLog.clear()
        self.ui.actorTree.clear()
        from workers.actor_search_worker import ActorSearchWorker

        worker = ActorSearchWorker(
            path,
            lookup_delay_seconds=self.javlib_search_pause_seconds(),
        )
        worker.result.connect(self.ui.actorLog.append)
        worker.groups_ready.connect(self._on_actor_groups_ready)
        worker.finished.connect(self._actor_scan_done)
        self.busy.set_worker(worker)
        self.ui.actorScanBtn.setEnabled(False)
        self.ui.actorMoveBtn.setEnabled(False)
        self.ui.actorHeaderCheck.setEnabled(False)
        self.ui.actorStopBtn.setEnabled(True)
        worker.start()

    def actorScanStop(self):
        self.busy.request_stop()

    def _on_actor_groups_ready(self, groups):
        self._actor_groups = groups
        self._populate_actor_tree()

    def _populate_actor_tree(self):
        tree = self.ui.actorTree
        self._actor_header_sync = True
        tree.blockSignals(True)
        tree.clear()
        for group in self._actor_groups:
            top = QTreeWidgetItem([group.actor, str(len(group.files))])
            top.setFlags(top.flags() | Qt.ItemIsUserCheckable)
            top.setCheckState(0, Qt.Checked if group.checked else Qt.Unchecked)
            for filename in group.files:
                child = QTreeWidgetItem([filename, ""])
                child.setFlags(child.flags() & ~Qt.ItemIsUserCheckable)
                top.addChild(child)
            tree.addTopLevelItem(top)
        tree.expandAll()
        tree.header().setStretchLastSection(False)
        tree.setColumnWidth(0, max(280, tree.columnWidth(0)))
        tree.setColumnWidth(1, 60)
        tree.blockSignals(False)
        self._actor_header_sync = False
        has_groups = tree.topLevelItemCount() > 0
        self.ui.actorHeaderCheck.setEnabled(has_groups)
        self._refresh_actor_header_check()

    def _sync_actor_checks_from_tree(self):
        for index, group in enumerate(self._actor_groups):
            top = self.ui.actorTree.topLevelItem(index)
            if top is not None:
                group.checked = top.checkState(0) == Qt.Checked

    def _set_all_actor_checks(self, checked: bool) -> None:
        if not self._actor_groups:
            return
        state = Qt.Checked if checked else Qt.Unchecked
        self._actor_header_sync = True
        self.ui.actorTree.blockSignals(True)
        try:
            for index in range(self.ui.actorTree.topLevelItemCount()):
                self.ui.actorTree.topLevelItem(index).setCheckState(0, state)
            for group in self._actor_groups:
                group.checked = checked
        finally:
            self.ui.actorTree.blockSignals(False)
            self._actor_header_sync = False
        self._refresh_actor_header_check()

    def _refresh_actor_header_check(self) -> None:
        if not self._actor_groups:
            self._actor_header_sync = True
            self.ui.actorHeaderCheck.setCheckState(Qt.Unchecked)
            self._actor_header_sync = False
            return
        self._sync_actor_checks_from_tree()
        checked = sum(1 for group in self._actor_groups if group.checked)
        total = len(self._actor_groups)
        self._actor_header_sync = True
        if checked == 0:
            self.ui.actorHeaderCheck.setCheckState(Qt.Unchecked)
        elif checked == total:
            self.ui.actorHeaderCheck.setCheckState(Qt.Checked)
        else:
            self.ui.actorHeaderCheck.setCheckState(Qt.PartiallyChecked)
        self._actor_header_sync = False

    def _on_actor_header_check_changed(self, state: int) -> None:
        if self._actor_header_sync:
            return
        if state == Qt.PartiallyChecked:
            self._set_all_actor_checks(True)
            return
        self._set_all_actor_checks(state == Qt.Checked)

    def _on_actor_tree_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._actor_header_sync or column != 0:
            return
        index = self.ui.actorTree.indexOfTopLevelItem(item)
        if index < 0 or index >= len(self._actor_groups):
            return
        self._actor_groups[index].checked = item.checkState(0) == Qt.Checked
        self._refresh_actor_header_check()

    def actorMove(self):
        if self.busy.warn_if_busy(self):
            return
        path = self.ui.actorPathEdit.text().strip()
        if not path or not self._actor_groups:
            QMessageBox.information(self, "Error!", "Scan a directory first.")
            return
        self._sync_actor_checks_from_tree()
        groups_snapshot = [
            ActorGroup(group.actor, list(group.files), group.checked) for group in self._actor_groups
        ]
        total = count_move_tasks(groups_snapshot)
        if total == 0:
            QMessageBox.information(self, "Move", "No files selected to move.")
            return

        from workers.actor_move_worker import ActorMoveWorker

        self._actor_move_progress = QProgressDialog("Moving files...", None, 0, total, self)
        self._actor_move_progress.setWindowTitle("Moving files")
        self._actor_move_progress.setWindowModality(Qt.WindowModal)
        self._actor_move_progress.setMinimumDuration(0)
        self._actor_move_progress.setAutoClose(True)
        self._actor_move_progress.setAutoReset(True)
        self._actor_move_progress.setValue(0)

        worker = ActorMoveWorker(path, groups_snapshot, db_path=DEFAULT_DB_PATH)
        worker.progress.connect(self._on_actor_move_progress)
        worker.log_line.connect(self.ui.actorLog.append)
        self._start_worker(
            worker,
            on_finished=self._after_actor_move,
            disable_widgets=[self.ui.actorMoveBtn, self.ui.actorScanBtn],
        )
        self._actor_move_progress.show()

    def _on_actor_move_progress(self, current: int, total: int, filename: str) -> None:
        if self._actor_move_progress is None:
            return
        self._actor_move_progress.setMaximum(total)
        self._actor_move_progress.setValue(current)
        self._actor_move_progress.setLabelText(f"Moving ({current}/{total}): {filename}")

    def _after_actor_move(self) -> None:
        if self._actor_move_progress is not None:
            self._actor_move_progress.close()
            self._actor_move_progress = None
        path = self.ui.actorPathEdit.text().strip()
        remaining = set(scan_first_level_mp4(path))
        self._actor_groups = [
            ActorGroup(
                group.actor,
                [name for name in group.files if name in remaining],
                group.checked,
            )
            for group in self._actor_groups
            if any(name in remaining for name in group.files)
        ]
        self._populate_actor_tree()

    def _actor_scan_done(self):
        self.busy.set_worker(None)
        self.ui.actorScanBtn.setEnabled(True)
        self.ui.actorMoveBtn.setEnabled(True)
        self.ui.actorStopBtn.setEnabled(False)
