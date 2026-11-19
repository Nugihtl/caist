"""Header bagian halaman (section title + deskripsi)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class SectionHeader(QWidget):
    """Judul dan deskripsi bagian halaman."""

    def __init__(
        self,
        title: str = "",
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sectionHeader")
        self._build_ui()
        self.set_title(title)
        self.set_description(description)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.title_label = QLabel("")
        self.title_label.setObjectName("sectionTitle")

        self.description_label = QLabel("")
        self.description_label.setObjectName("sectionDescription")

        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_description(self, description: str) -> None:
        self.description_label.setText(description)
