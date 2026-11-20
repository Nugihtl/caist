"""Leaflet map embedded in Qt WebEngine with a narrow data-only bridge."""

from __future__ import annotations

import json

from PySide6.QtCore import QObject, Qt, QUrl, QTimer, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from config.settings import MAP_FILE
from src.gis.map_data import load_map_payload


class _MapBridge(QObject):
    statusChanged = Signal(str)

    def __init__(self, payload: dict, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._payload = json.dumps(payload, ensure_ascii=False)

    @Slot(result=str)
    def getMapData(self) -> str:
        """Expose a fixed, prevalidated payload, not filesystem operations."""
        return self._payload

    @Slot(str)
    def reportStatus(self, status: str) -> None:
        self.statusChanged.emit(status[:500])


class _MapPage(QWebEnginePage):
    consoleError = Signal(str)

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            self.consoleError.emit(f"JavaScript peta: {message} ({source_id}:{line_number})")


class LeafletMapWidget(QWidget):
    """Desktop map view for local administrative and river GeoJSON layers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._loading_message = "Memuat peta lokal..."
        self._map_reported = False
        self.status_label = QLabel(self._loading_message)
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status_label)

        self.view = QWebEngineView(self)
        self.map_page = _MapPage(self.view)
        self.view.setPage(self.map_page)
        self.map_page.consoleError.connect(self._on_map_status)
        self.view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        self.view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        self.channel = QWebChannel(self.map_page)
        self.bridge = _MapBridge(load_map_payload(), self.channel)
        self.bridge.statusChanged.connect(self._on_map_status)
        self.view.loadFinished.connect(self._on_load_finished)
        self.channel.registerObject("caistBridge", self.bridge)
        self.map_page.setWebChannel(self.channel)
        layout.addWidget(self.view, stretch=1)

        if MAP_FILE.is_file():
            self.view.setUrl(QUrl.fromLocalFile(str(MAP_FILE.resolve())))
            QTimer.singleShot(15000, self._report_if_still_loading)
        else:
            self.status_label.setText(f"Halaman peta tidak ditemukan: {MAP_FILE}")

    def _on_map_status(self, message: str) -> None:
        self._map_reported = True
        self.status_label.setText(message)

    def _on_load_finished(self, succeeded: bool) -> None:
        if not succeeded:
            self._on_map_status("Halaman peta gagal dimuat. Periksa file HTML dan resource lokal.")

    def _report_if_still_loading(self) -> None:
        if not self._map_reported and self.status_label.text() == self._loading_message:
            self.status_label.setText(
                "Peta belum memberi status dari JavaScript. Periksa QWebChannel dan console WebEngine."
            )
