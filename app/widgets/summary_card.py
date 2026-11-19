"""Kartu ringkasan statistik reusable."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class SummaryCard(QWidget):
    """Kartu ringkasan dengan nilai besar, label, dan ikon.

    Digunakan pada dashboard untuk menampilkan ringkasan terkait
    wilayah pemantauan, stasiun aktif, risiko banjir, dan status data.
    """

    def __init__(self, value: str = "—", label: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryCard")
        self.setFixedHeight(120)
        self._build_ui()
        self.set_value(value)
        self.set_label(label)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        self.icon_label = QLabel("📊")
        self.icon_label.setObjectName("summaryCardIcon")
        self.icon_label.setFixedSize(32, 32)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(4)

        self.value_label = QLabel("—")
        self.value_label.setObjectName("summaryCardValue")

        self.label_label = QLabel("")
        self.label_label.setObjectName("summaryCardLabel")

        text_column.addWidget(self.value_label)
        text_column.addWidget(self.label_label)
        text_column.addStretch()

        layout.addWidget(self.icon_label)
        layout.addLayout(text_column)
        layout.addStretch()

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def set_label(self, label: str) -> None:
        self.label_label.setText(label)

    def set_icon(self, icon: str) -> None:
        self.icon_label.setText(icon)
