from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QTreeWidgetItem

from core.actor_searcher import ActorGroup, move_actor_groups
from core.filename_fixer import RenameItem, apply_renames, scan_directory


class ExtraTabsMixin:
    """Filename fixer and actor searcher tab wiring."""

    def _init_extra_tab_state(self):
        self._rename_items: list[RenameItem] = []
        self._actor_groups: list[ActorGroup] = []

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
        self.ui.actorSelectAllBtn.clicked.connect(self.actorSelectAll)
        self.ui.actorClearSelectionBtn.clicked.connect(self.actorClearSelection)
        self.ui.actorMoveBtn.clicked.connect(self.actorMove)

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
        self.ui.actorStopBtn.setEnabled(True)
        worker.start()

    def actorScanStop(self):
        self.busy.request_stop()

    def _on_actor_groups_ready(self, groups):
        self._actor_groups = groups
        self._populate_actor_tree()

    def _populate_actor_tree(self):
        tree = self.ui.actorTree
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

    def _sync_actor_checks_from_tree(self):
        for index, group in enumerate(self._actor_groups):
            top = self.ui.actorTree.topLevelItem(index)
            if top is not None:
                group.checked = top.checkState(0) == Qt.Checked

    def actorSelectAll(self):
        for index in range(self.ui.actorTree.topLevelItemCount()):
            self.ui.actorTree.topLevelItem(index).setCheckState(0, Qt.Checked)
        for group in self._actor_groups:
            group.checked = True

    def actorClearSelection(self):
        for index in range(self.ui.actorTree.topLevelItemCount()):
            self.ui.actorTree.topLevelItem(index).setCheckState(0, Qt.Unchecked)
        for group in self._actor_groups:
            group.checked = False

    def actorMove(self):
        path = self.ui.actorPathEdit.text().strip()
        if not path or not self._actor_groups:
            QMessageBox.information(self, "Error!", "Scan a directory first.")
            return
        self._sync_actor_checks_from_tree()
        for msg in move_actor_groups(path, self._actor_groups):
            self.ui.actorLog.append(msg)
        self.actorScan()

    def _actor_scan_done(self):
        self.busy.set_worker(None)
        self.ui.actorScanBtn.setEnabled(True)
        self.ui.actorMoveBtn.setEnabled(True)
        self.ui.actorStopBtn.setEnabled(False)
