from PyQt5.QtWidgets import QDoubleSpinBox

from core.settings import save_settings

JAVLIB_PAUSE_MAX_SECONDS = 120.0


def configure_javlib_pause_spin(spin: QDoubleSpinBox, seconds: float) -> None:
    spin.setRange(0.0, JAVLIB_PAUSE_MAX_SECONDS)
    spin.setSingleStep(0.5)
    spin.setDecimals(1)
    spin.setSuffix(" s")
    spin.setValue(float(seconds))


class JavlibPauseMixin:
    """Shared JavLib web pause (seconds) on Classifier and Actor Searcher tabs."""

    def _wire_javlib_pause_controls(self) -> None:
        spins = (self.ui.classifierJavlibPauseSpin, self.ui.actorJavlibPauseSpin)
        for spin in spins:
            configure_javlib_pause_spin(spin, self._settings.javlib_search_pause_seconds)
            spin.valueChanged.connect(self._on_javlib_pause_changed)

    def _on_javlib_pause_changed(self, value: float) -> None:
        self._settings.javlib_search_pause_seconds = float(value)
        save_settings(self._settings)
        for spin in (self.ui.classifierJavlibPauseSpin, self.ui.actorJavlibPauseSpin):
            if abs(spin.value() - value) > 1e-9:
                spin.blockSignals(True)
                spin.setValue(value)
                spin.blockSignals(False)

    def javlib_search_pause_seconds(self) -> float:
        return float(self.ui.classifierJavlibPauseSpin.value())
