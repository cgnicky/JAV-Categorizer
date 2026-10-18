from PyQt5.QtWidgets import QFileDialog


def pick_directory(parent, start_path: str = "") -> str:
    path = QFileDialog.getExistingDirectory(
        parent,
        "Select a Folder",
        start_path or "",
        QFileDialog.ShowDirsOnly,
    )
    return path or ""
