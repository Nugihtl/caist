"""Halaman Data Wilayah CAIST.

Menampilkan daftar sumber data geografis Bandung Raya dengan status
ketersediaan masing-masing dataset.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.widgets.section_header import SectionHeader
from app.widgets.status_badge import StatusBadge


class RegionPage(QWidget):
    """Halaman Data Wilayah untuk mengelola dan melihat ketersediaan data geografis."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        header = SectionHeader(
            title="Data Wilayah",
            description="Ketersediaan dan status integrasi sumber data geografis Bandung Raya",
        )
        root.addWidget(header)

        # Tabel sumber data
        table_section = QVBoxLayout()
        table_section.setSpacing(12)
        table_title = QLabel("Daftar Sumber Data")
        table_title.setObjectName("sectionTitle")
        table_section.addWidget(table_title)

        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table_section.addWidget(self.table, stretch=1)

        table_frame = QFrame()
        table_frame.setObjectName("groupFrame")
        table_frame.setLayout(table_section)
        root.addWidget(table_frame, stretch=1)

        # Detail setiap sumber data
        detail_section = QVBoxLayout()
        detail_section.setSpacing(12)
        detail_title = QLabel("Detail Sumber Data")
        detail_title.setObjectName("sectionTitle")
        detail_section.addWidget(detail_title)

        sources = [
            {
                "nama": "Curah hujan CHIRPS",
                "deskripsi": "Data curah hujan harian dari satelit CHIRPS untuk wilayah Bandung Raya.",
                "tipe": "Curah hujan",
                "sumber": "CHIRPS",
                "status": "Belum diintegrasikan",
                "status_level": "pending",
            },
            {
                "nama": "Riwayat banjir BNPB",
                "deskripsi": "Data historis kejadian banjir dari BNPB untuk pelatihan model.",
                "tipe": "Riwayat kejadian",
                "sumber": "BNPB",
                "status": "Belum diintegrasikan",
                "status_level": "pending",
            },
            {
                "nama": "Batas administrasi",
                "deskripsi": "Batas administratif kecamatan di Kota Bandung, Kabupaten Bandung, Kabupaten Bandung Barat, dan Kota Cimahi.",
                "tipe": "Batas administrasi",
                "sumber": "Pemerintah / Badan data spasial",
                "status": "Belum diintegrasikan",
                "status_level": "pending",
            },
            {
                "nama": "Elevasi dan kemiringan SRTM",
                "deskripsi": "Data elevasi dan kemiringan tanah dari NASA SRTM untuk analisis kerentanan banjir.",
                "tipe": "Elevasi dan kemiringan",
                "sumber": "NASA SRTM",
                "status": "Belum diintegrasikan",
                "status_level": "pending",
            },
            {
                "nama": "Tutupan lahan ESA WorldCover",
                "deskripsi": "Data tutupan lahan global dari ESA WorldCover untuk analisis land use.",
                "tipe": "Tutupan lahan",
                "sumber": "ESA WorldCover",
                "status": "Belum diintegrasikan",
                "status_level": "pending",
            },
            {
                "nama": "Jaringan sungai OpenStreetMap",
                "deskripsi": "Jaringan sungai dan saluran air dari OpenStreetMap untuk pemetaan risiko banjir.",
                "tipe": "Jaringan sungai",
                "sumber": "OpenStreetMap",
                "status": "Belum diintegrasikan",
                "status_level": "pending",
            },
            {
                "nama": "Data monitoring BBWS Citarum FFWS",
                "deskripsi": "Data monitoring tinggi muka air, curah hujan, dan debit sungai dari BBWS Citarum FFWS (akses otomatis belum dipastikan).",
                "tipe": "Monitoring real-time",
                "sumber": "BBWS Citarum FFWS",
                "status": "Belum tersedia",
                "status_level": "unavailable",
            },
        ]

        for source in sources:
            row = self._create_source_row(source)
            detail_section.addWidget(row)

        detail_frame = QFrame()
        detail_frame.setObjectName("groupFrame")
        detail_frame.setLayout(detail_section)
        root.addWidget(detail_frame)

    def _create_source_row(self, source: dict) -> QFrame:
        frame = QFrame()
        frame.setObjectName("groupFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(2)

        name = QLabel(source["nama"])
        name.setObjectName("sectionTitle")

        desc = QLabel(source["deskripsi"])
        desc.setObjectName("sectionDescription")
        desc.setWordWrap(True)

        meta = QLabel(f"{source['tipe']}  •  Sumber: {source['sumber']}")
        meta.setObjectName("sectionDescription")

        info.addWidget(name)
        info.addWidget(desc)
        info.addWidget(meta)

        badge = StatusBadge(text=source["status"], status=source["status_level"])

        layout.addLayout(info, stretch=1)
        layout.addWidget(badge)

        return frame
