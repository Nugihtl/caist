"""Jendela utama aplikasi CAIST dengan navigasi QStackedWidget.

Menyatukan sidebar, header, dan lima halaman utama dalam satu
antarmuka desktop yang modular dan konsisten.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config.settings import WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH
from app.widgets.empty_state import EmptyStateWidget
from app.widgets.header import HeaderWidget
from app.widgets.sidebar import SidebarWidget

from app.pages.dashboard_page import DashboardPage
from app.pages.evaluation_page import EvaluationPage
from app.pages.monitoring_page import MonitoringPage
from app.pages.prediction_page import PredictionPage
from app.pages.region_page import RegionPage
from src.database.ui_readers import load_ui_snapshot


class MainWindow(QMainWindow):
    """Jendela utama aplikasi CAIST.

    Struktur:
    - Sidebar kiri (navigasi utama, selalu terlihat)
    - Header atas (judul, deskripsi, status)
    - Area konten (QStackedWidget dengan 5 halaman)
    - Status bar bawah (status aplikasi)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(1024, 700)

        self.data_snapshot = load_ui_snapshot()
        self._build_ui()
        self._apply_stylesheet()
        if self.data_snapshot.get("connected"):
            self.header.set_status(f"SQLite terhubung | {len(self.data_snapshot['regions'])} kecamatan | versi {self.data_snapshot['data_version']}")
            self.statusBar().showMessage(f"Data lokal terhubung: {len(self.data_snapshot['regions'])} kecamatan | SQLite {self.data_snapshot['data_version']}")
        else:
            self.header.set_status("Database lokal tidak terhubung")
            self.statusBar().showMessage(f"Database lokal tidak terhubung: {self.data_snapshot.get('error') or 'data belum tersedia'}")
        self._connect_signals()

        # Tampilkan halaman Dashboard secara default
        self.stack.setCurrentWidget(self.page_dashboard)
        self.header.set_page_info(
            "Dashboard",
            "Ringkasan monitoring dan potensi banjir Bandung Raya",
        )
        self.sidebar.set_active_page("dashboard")

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralPanel")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = SidebarWidget()
        root.addWidget(self.sidebar)

        # Konten kanan (header + stacked widget)
        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(0)

        # Header
        self.header = HeaderWidget()
        right_column.addWidget(self.header)

        # Stacked widget halaman
        self.stack = QStackedWidget()

        self.page_dashboard = DashboardPage(data_snapshot=self.data_snapshot)
        self.page_monitoring = MonitoringPage()
        self.page_prediction = PredictionPage(data_snapshot=self.data_snapshot)
        self.page_region = RegionPage(data_snapshot=self.data_snapshot)
        self.page_evaluation = EvaluationPage()

        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_monitoring)
        self.stack.addWidget(self.page_prediction)
        self.stack.addWidget(self.page_region)
        self.stack.addWidget(self.page_evaluation)

        right_column.addWidget(self.stack, stretch=1)
        root.addLayout(right_column, stretch=1)

        # Status bar
        self.statusBar().setObjectName("statusBar")

    def _apply_stylesheet(self) -> None:
        """Muat QSS tema dari app/styles/theme.qss."""
        from pathlib import Path

        qss_path = Path(__file__).resolve().parents[1] / "styles" / "theme.qss"
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _connect_signals(self) -> None:
        self.sidebar.pageChanged.connect(self._on_page_changed)

    def _on_page_changed(self, page_key: str) -> None:
        """Handler navigasi sidebar: pindah halaman dan perbarui header."""
        page_map = {
            "dashboard": (self.page_dashboard, "Dashboard", "Ringkasan monitoring dan potensi banjir Bandung Raya"),
            "monitoring": (self.page_monitoring, "Monitoring", "Informasi curah hujan, tinggi muka air, dan debit sungai dari stasiun pemantauan"),
            "prediction": (self.page_prediction, "Prediksi", "Pilih wilayah kecamatan dan jalankan prediksi probabilitas kejadian banjir"),
            "region": (self.page_region, "Data Wilayah", "Ketersediaan dan status integrasi sumber data geografis Bandung Raya"),
            "evaluation": (self.page_evaluation, "Evaluasi Model", "Hasil evaluasi model prediksi probabilitas banjir"),
        }

        if page_key in page_map:
            page, title, description = page_map[page_key]
            self.stack.setCurrentWidget(page)
            self.header.set_page_info(title, description)
            self.sidebar.set_active_page(page_key)
