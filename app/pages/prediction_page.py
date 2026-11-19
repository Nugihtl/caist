"""Halaman Prediksi CAIST."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.widgets.empty_state import EmptyStateWidget
from app.widgets.section_header import SectionHeader
from app.widgets.status_badge import StatusBadge


class PredictionPage(QWidget):
    """Halaman Prediksi banjir.

    Tempat untuk memilih wilayah dan menjalankan prediksi.
    Tombol prediksi dinonaktifkan karena model belum tersedia.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        header = SectionHeader(
            title="Prediksi",
            description="Pilih wilayah kecamatan dan jalankan prediksi probabilitas kejadian banjir",
        )
        root.addWidget(header)

        # Status model
        status_row = QHBoxLayout()
        status_row.setSpacing(12)

        status_label = QLabel("Status Model:")
        status_label.setObjectName("sectionTitle")

        self.status_badge = StatusBadge(
            text="Model prediksi belum tersedia",
            status="unavailable",
        )

        status_row.addWidget(status_label)
        status_row.addWidget(self.status_badge)
        status_row.addStretch()

        status_frame = QFrame()
        status_frame.setObjectName("groupFrame")
        status_frame.setLayout(status_row)
        root.addWidget(status_frame)

        # Form input prediksi
        form_section = QVBoxLayout()
        form_section.setSpacing(16)

        form_title = QLabel("Parameter Prediksi")
        form_title.setObjectName("sectionTitle")
        form_section.addWidget(form_title)

        form_grid = QGridLayout()
        form_grid.setSpacing(16)

        # Pemilihan wilayah
        wilayah_label = QLabel("Wilayah Kecamatan:")
        wilayah_label.setObjectName("sectionTitle")

        self.wilayah_combo = QComboBox()
        self.wilayah_combo.addItems(
            [
                "Kota Bandung",
                "Kabupaten Bandung",
                "Kabupaten Bandung Barat",
                "Kota Cimahi",
            ]
        )
        self.wilayah_combo.setMinimumWidth(260)

        # Tanggal prediksi
        tanggal_label = QLabel("Tanggal Prediksi:")
        tanggal_label.setObjectName("sectionTitle")

        self.tanggal_edit = QDateEdit()
        self.tanggal_edit.setMinimumWidth(260)
        from PySide6.QtCore import QDate

        self.tanggal_edit.setDate(QDate.currentDate())

        # Tombol jalankan prediksi
        self.btn_predict = QPushButton("Jalankan Prediksi")
        self.btn_predict.setObjectName("primaryButton")
        self.btn_predict.setEnabled(False)
        self.btn_predict.setMinimumWidth(200)

        form_grid.addWidget(wilayah_label, 0, 0)
        form_grid.addWidget(self.wilayah_combo, 0, 1)
        form_grid.addWidget(tanggal_label, 1, 0)
        form_grid.addWidget(self.tanggal_edit, 1, 1)
        form_grid.addWidget(self.btn_predict, 2, 0, 1, 2)

        form_frame = QFrame()
        form_frame.setObjectName("groupFrame")
        form_frame.setLayout(form_grid)
        form_section.addWidget(form_frame)

        root.addLayout(form_section)

        # Hasil prediksi
        result_section = QVBoxLayout()
        result_section.setSpacing(12)

        result_title = QLabel("Hasil Prediksi")
        result_title.setObjectName("sectionTitle")
        result_section.addWidget(result_title)

        self.result_empty = EmptyStateWidget(
            title="Model prediksi belum tersedia.",
            subtitle="Hasil probabilitas dan tingkat potensi banjir akan ditampilkan"
            " setelah model machine learning dilatih dan dievaluasi.",
        )
        result_section.addWidget(self.result_empty)

        result_frame = QFrame()
        result_frame.setObjectName("groupFrame")
        result_frame.setLayout(result_section)
        root.addWidget(result_frame, stretch=1)

        # Faktor pengaruh
        factor_section = QVBoxLayout()
        factor_section.setSpacing(12)

        factor_title = QLabel("Faktor yang Mempengaruhi Prediksi")
        factor_title.setObjectName("sectionTitle")
        factor_section.addWidget(factor_title)

        self.factor_empty = EmptyStateWidget(
            title="Belum tersedia.",
            subtitle="Faktor geografis dan curah hujan yang memengaruhi prediksi"
            " akan ditampilkan setelah integrasi data spasial dilakukan.",
        )
        factor_section.addWidget(self.factor_empty)

        factor_frame = QFrame()
        factor_frame.setObjectName("groupFrame")
        factor_frame.setLayout(factor_section)
        root.addWidget(factor_frame)
