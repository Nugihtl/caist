"""Halaman Dashboard CAIST."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.database.ui_readers import load_ui_snapshot
from app.widgets.empty_state import EmptyStateWidget
from app.widgets.leaflet_map import LeafletMapWidget
from app.widgets.section_header import SectionHeader
from app.widgets.summary_card import SummaryCard


class DashboardPage(QWidget):
    """Halaman utama Dashboard CAIST.

    Menampilkan ringkasan monitoring dan potensi banjir Bandung Raya
    tanpa menampilkan data fiktif karena backend belum terintegrasi.
    """

    def __init__(self, parent=None, data_snapshot=None) -> None:
        super().__init__(parent)
        self.data_snapshot = data_snapshot if data_snapshot is not None else load_ui_snapshot()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # Judul halaman
        header = SectionHeader(
            title="Dashboard",
            description="Ringkasan monitoring dan potensi banjir Bandung Raya",
        )
        root.addWidget(header)

        # Kartu ringkasan
        cards = QGridLayout()
        cards.setSpacing(16)

        snapshot = self.data_snapshot
        history = snapshot.get("history", {})
        daily = snapshot.get("daily", {})
        region_count = len(snapshot.get("regions", [])) if snapshot.get("connected") else 0

        self.card_wilayah = SummaryCard(
            value=str(region_count) if snapshot.get("connected") else "-",
            label="Kecamatan Terhubung",
        )
        self.card_wilayah.set_icon("🗺️")

        self.card_station = SummaryCard(
            value=f"{history.get('district_days', 0):,}" if snapshot.get("connected") else "-",
            label="Kecamatan-Hari Banjir BNPB",
        )
        self.card_station.set_icon("📡")

        self.card_risk = SummaryCard(
            value=f"{history.get('source_rows', 0):,}" if snapshot.get("connected") else "-",
            label="Baris Sumber BNPB",
        )
        self.card_risk.set_icon("⚠️")

        self.card_update = SummaryCard(
            value=(f"{daily.get('date_start', '-')} to {daily.get('date_end', '-')}" if snapshot.get("connected") else "Tidak terhubung"),
            label="Rentang CHIRPS",
        )
        self.card_update.set_icon("🔄")

        cards.addWidget(self.card_wilayah, 0, 0)
        cards.addWidget(self.card_station, 0, 1)
        cards.addWidget(self.card_risk, 0, 2)
        cards.addWidget(self.card_update, 0, 3)

        cards_frame = QFrame()
        cards_frame.setObjectName("groupFrame")
        cards_frame.setLayout(cards)
        root.addWidget(cards_frame)

        # Baris tengah: peta (kiri) + ringkasan risiko (kanan)
        middle = QHBoxLayout()
        middle.setSpacing(20)

        # Peta Leaflet - mengambil 2/3 lebar
        map_section = QVBoxLayout()
        map_section.setSpacing(12)
        map_title = QLabel("Peta Interaktif Bandung Raya")
        map_title.setObjectName("sectionTitle")
        map_section.addWidget(map_title)

        self.map_placeholder = LeafletMapWidget()
        map_section.addWidget(self.map_placeholder, stretch=1)
        map_section.setStretch(0, 0)
        map_section.setStretch(1, 1)

        map_frame = QFrame()
        map_frame.setObjectName("groupFrame")
        map_frame.setLayout(map_section)
        middle.addWidget(map_frame, stretch=2)

        # Ringkasan risiko - mengambil 1/3 lebar
        risk_section = QVBoxLayout()
        risk_section.setSpacing(12)
        risk_title = QLabel("Ringkasan Tingkat Risiko")
        risk_title.setObjectName("sectionTitle")
        risk_section.addWidget(risk_title)

        self.risk_high = SummaryCard(value="Belum tersedia", label="Risiko Tinggi")
        self.risk_high.set_icon("🔴")

        self.risk_medium = SummaryCard(value="Belum tersedia", label="Risiko Sedang")
        self.risk_medium.set_icon("🟡")

        self.risk_low = SummaryCard(value="Belum tersedia", label="Risiko Rendah")
        self.risk_low.set_icon("🟢")

        self.risk_na = SummaryCard(value="Belum tersedia", label="Data Tidak Tersedia")
        self.risk_na.set_icon("⚪")

        risk_section.addWidget(self.risk_high)
        risk_section.addWidget(self.risk_medium)
        risk_section.addWidget(self.risk_low)
        risk_section.addWidget(self.risk_na)
        risk_section.addStretch()

        risk_frame = QFrame()
        risk_frame.setObjectName("groupFrame")
        risk_frame.setLayout(risk_section)
        middle.addWidget(risk_frame, stretch=1)

        root.addLayout(middle, stretch=1)

        # Ringkasan monitoring - empty state
        mon_section = QVBoxLayout()
        mon_section.setSpacing(12)
        mon_title = QLabel("Ringkasan Monitoring")
        mon_title.setObjectName("sectionTitle")
        mon_section.addWidget(mon_title)

        self.monitoring_empty = EmptyStateWidget(
            title="Data monitoring belum terhubung.",
            subtitle=(
                "Ringkasan curah hujan historis tersedia di kartu Dashboard. "
                "Data tinggi muka air dan debit sungai real-time belum tersedia karena integrasi BBWS Citarum FFWS belum dilakukan."
            ),
        )
        mon_section.addWidget(self.monitoring_empty)

        mon_frame = QFrame()
        mon_frame.setObjectName("groupFrame")
        mon_frame.setLayout(mon_section)
        root.addWidget(mon_frame)
