"""Placeholder peta interaktif (untuk integrasi Leaflet/WebEngine di tahap berikutnya)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class MapPlaceholderWidget(QWidget):
    """Area placeholder peta yang akan diganti dengan widget Leaflet.

    Tidak menampilkan peta palsu atau batas wilayah yang diarang.
    """

    def __init__(
        self,
        title: str = "Peta Interaktif Bandung Raya",
        subtitle: str = "Integrasi batas kecamatan dan visualisasi probabilitas banjir akan tersedia pada tahap GIS Map Integration.",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("mapPlaceholder")
        self._build_ui()
        self.set_title(title)
        self.set_subtitle(subtitle)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)
        layout.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )

        self.title_label = QLabel("")
        self.title_label.setObjectName("mapPlaceholderTitle")

        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("mapPlaceholderSubtitle")
        self.subtitle_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        self.subtitle_label.setText(subtitle)
