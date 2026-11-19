"""Header atau top navigation bar aplikasi CAIST."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class HeaderWidget(QWidget):
    """Header bagian atas dengan judul halaman, deskripsi, dan status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("header")
        self.setFixedHeight(64)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(0)

        # Kolom kiri: judul dan deskripsi
        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(2)

        self.title_label = QLabel("Dashboard")
        self.title_label.setObjectName("headerTitle")

        self.subtitle_label = QLabel("Ringkasan monitoring dan potensi banjir Bandung Raya")
        self.subtitle_label.setObjectName("headerSubtitle")

        text_column.addWidget(self.title_label)
        text_column.addWidget(self.subtitle_label)
        layout.addLayout(text_column)
        layout.addStretch()

        # Kolom kanan: status aplikasi
        self.status_label = QLabel("Memeriksa koneksi database...")
        self.status_label.setObjectName("headerStatus")
        layout.addWidget(self.status_label)

    def set_page_info(self, title: str, description: str) -> None:
        """Perbarui judul dan deskripsi halaman aktif."""
        self.title_label.setText(title)
        self.subtitle_label.setText(description)

    def set_status(self, status: str) -> None:
        """Perbarui teks status di kanan header."""
        self.status_label.setText(status)
