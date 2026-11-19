"""Halaman Evaluasi Model CAIST.

Menampilkan metrik evaluasi model machine learning setelah model
dilatih dan dievaluasi. Saat ini menampilkan empty state.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.widgets.empty_state import EmptyStateWidget
from app.widgets.section_header import SectionHeader
from app.widgets.status_badge import StatusBadge
from app.widgets.summary_card import SummaryCard


class EvaluationPage(QWidget):
    """Halaman Evaluasi Model machine learning.

    Menampilkan accuracy, precision, recall, F1-score, ROC-AUC,
    confusion matrix, dan perbandingan model.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        header = SectionHeader(
            title="Evaluasi Model",
            description="Hasil evaluasi model prediksi probabilitas banjir",
        )
        root.addWidget(header)

        # Status model
        status_row = QHBoxLayout()
        status_row.setSpacing(12)

        status_label = QLabel("Status Model:")
        status_label.setObjectName("sectionTitle")

        self.status_badge = StatusBadge(
            text="Belum ada model yang dilatih",
            status="unavailable",
        )

        status_row.addWidget(status_label)
        status_row.addWidget(self.status_badge)
        status_row.addStretch()

        status_frame = QFrame()
        status_frame.setObjectName("groupFrame")
        status_frame.setLayout(status_row)
        root.addWidget(status_frame)

        # Kartu metrik evaluasi
        metrics_section = QVBoxLayout()
        metrics_section.setSpacing(12)
        metrics_title = QLabel("Metrik Evaluasi")
        metrics_title.setObjectName("sectionTitle")
        metrics_section.addWidget(metrics_title)

        cards = QGridLayout()
        cards.setSpacing(16)

        self.card_accuracy = SummaryCard(value="—", label="Accuracy")
        self.card_precision = SummaryCard(value="—", label="Precision")
        self.card_recall = SummaryCard(value="—", label="Recall")
        self.card_f1 = SummaryCard(value="—", label="F1-Score")
        self.card_roc = SummaryCard(value="—", label="ROC-AUC")

        cards.addWidget(self.card_accuracy, 0, 0)
        cards.addWidget(self.card_precision, 0, 1)
        cards.addWidget(self.card_recall, 0, 2)
        cards.addWidget(self.card_f1, 0, 3)
        cards.addWidget(self.card_roc, 0, 4)

        cards_frame = QFrame()
        cards_frame.setObjectName("groupFrame")
        cards_frame.setLayout(cards)
        metrics_section.addWidget(cards_frame)

        root.addLayout(metrics_section)

        # Confusion matrix
        cm_section = QVBoxLayout()
        cm_section.setSpacing(12)
        cm_title = QLabel("Confusion Matrix")
        cm_title.setObjectName("sectionTitle")
        cm_section.addWidget(cm_title)

        self.cm_empty = EmptyStateWidget(
            title="Belum ada model yang dilatih dan dievaluasi.",
            subtitle="Confusion matrix, calibration assessment, dan perbandingan model"
            " akan ditampilkan setelah pelatihan model dilakukan.",
        )
        cm_section.addWidget(self.cm_empty)

        cm_frame = QFrame()
        cm_frame.setObjectName("groupFrame")
        cm_frame.setLayout(cm_section)
        root.addWidget(cm_frame, stretch=1)
