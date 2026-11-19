"""Halaman Monitoring CAIST."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.widgets.empty_state import EmptyStateWidget
from app.widgets.section_header import SectionHeader
from app.widgets.status_badge import StatusBadge
from app.widgets.summary_card import SummaryCard


class MonitoringPage(QWidget):
    """Halaman Monitoring hidrologi.

    Menampilkan informasi curah hujan, tinggi muka air, dan debit sungai.
    Karena backend FFWS belum terintegrasi, menampilkan empty state.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        header = SectionHeader(
            title="Monitoring",
            description="Informasi curah hujan, tinggi muka air, dan debit sungai dari stasiun pemantauan",
        )
        root.addWidget(header)

        # Status koneksi
        status_row = QHBoxLayout()
        status_row.setSpacing(12)

        status_label = QLabel("Status Koneksi Data:")
        status_label.setObjectName("sectionTitle")

        self.status_badge = StatusBadge(
            text="Belum Terhubung",
            status="unavailable",
        )

        status_row.addWidget(status_label)
        status_row.addWidget(self.status_badge)
        status_row.addStretch()

        status_frame = QFrame()
        status_frame.setObjectName("groupFrame")
        status_frame.setLayout(status_row)
        root.addWidget(status_frame)

        # Kartu ringkasan monitoring
        cards = QGridLayout()
        cards.setSpacing(16)

        self.card_rain = SummaryCard(value="Belum tersedia", label="Curah Hujan")
        self.card_rain.set_icon("🌧️")

        self.card_level = SummaryCard(value="Belum tersedia", label="Tinggi Muka Air")
        self.card_level.set_icon("📏")

        self.card_flow = SummaryCard(value="Belum tersedia", label="Debit Sungai")
        self.card_flow.set_icon("🌊")

        cards.addWidget(self.card_rain, 0, 0)
        cards.addWidget(self.card_level, 0, 1)
        cards.addWidget(self.card_flow, 0, 2)

        cards_frame = QFrame()
        cards_frame.setObjectName("groupFrame")
        cards_frame.setLayout(cards)
        root.addWidget(cards_frame)

        # Daftar pengamatan terbaru
        table_section = QVBoxLayout()
        table_section.setSpacing(12)
        table_title = QLabel("Pengamatan Terbaru")
        table_title.setObjectName("sectionTitle")
        table_section.addWidget(table_title)

        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        # Model akan diatur setelah integrasi database dilakukan
        table_section.addWidget(self.table, stretch=1)

        table_frame = QFrame()
        table_frame.setObjectName("groupFrame")
        table_frame.setLayout(table_section)
        root.addWidget(table_frame, stretch=1)

        # Waktu pembaruan terakhir
        update_row = QHBoxLayout()
        update_row.setSpacing(12)

        update_label = QLabel("Waktu Pembaruan Terakhir:")
        update_label.setObjectName("sectionTitle")

        self.update_value = QLabel("Belum tersedia")
        self.update_value.setObjectName("sectionTitle")

        update_row.addWidget(update_label)
        update_row.addWidget(self.update_value)
        update_row.addStretch()

        update_frame = QFrame()
        update_frame.setObjectName("groupFrame")
        update_frame.setLayout(update_row)
        root.addWidget(update_frame)

        # Empty state di tengah area utama
        self.empty_state = EmptyStateWidget(
            title="Data monitoring belum terhubung.",
            subtitle="Stasiun pengamatan, nilai sensor, dan status peringatan"
            " akan ditampilkan setelah integrasi BBWS Citarum FFWS dilakukan.",
        )
        root.addWidget(self.empty_state, stretch=1)
