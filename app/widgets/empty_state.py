"""Empty state reusable untuk halaman yang belum memiliki data."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class EmptyStateWidget(QWidget):
    """Kosong state yang menjelaskan alasan data belum tersedia."""

    def __init__(
        self,
        title: str = "Belum ada data",
        subtitle: str = "Data akan tersedia setelah integrasi backend dilakukan.",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("emptyState")
        self._build_ui()
        self.set_title(title)
        self.set_subtitle(subtitle)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)
        layout.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )

        self.title_label = QLabel("")
        self.title_label.setObjectName("emptyStateTitle")

        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("emptyStateSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        self.subtitle_label.setText(subtitle)
