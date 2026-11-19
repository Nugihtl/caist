"""Smoke test untuk Stage 2 Desktop UI Foundation."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])  # noqa: E402

from app.main_window import MainWindow  # noqa: E402
from app.pages.dashboard_page import DashboardPage  # noqa: E402
from app.pages.evaluation_page import EvaluationPage  # noqa: E402
from app.pages.monitoring_page import MonitoringPage  # noqa: E402
from app.pages.prediction_page import PredictionPage  # noqa: E402
from app.pages.region_page import RegionPage  # noqa: E402
from app.widgets.empty_state import EmptyStateWidget  # noqa: E402
from app.widgets.header import HeaderWidget  # noqa: E402
from app.widgets.map_placeholder import MapPlaceholderWidget  # noqa: E402
from app.widgets.sidebar import SidebarWidget  # noqa: E402


def test_mainwindow_initialization():
    window = MainWindow()
    assert window is not None
    assert window.windowTitle() == "CAIST — Prediksi Probabilitas Banjir Bandung Raya"


def test_all_pages_created():
    window = MainWindow()
    assert window.page_dashboard is not None
    assert window.page_monitoring is not None
    assert window.page_prediction is not None
    assert window.page_region is not None
    assert window.page_evaluation is not None


def test_stacked_widget_has_5_pages():
    window = MainWindow()
    assert window.stack.count() == 5


def test_sidebar_navigation_changes_page():
    window = MainWindow()
    # Default: Dashboard
    assert window.stack.currentWidget() is window.page_dashboard

    # Pindah ke Monitoring
    window.sidebar.pageChanged.emit("monitoring")
    assert window.stack.currentWidget() is window.page_monitoring

    # Pindah ke Prediksi
    window.sidebar.pageChanged.emit("prediction")
    assert window.stack.currentWidget() is window.page_prediction

    # Pindah ke Data Wilayah
    window.sidebar.pageChanged.emit("region")
    assert window.stack.currentWidget() is window.page_region

    # Pindah ke Evaluasi
    window.sidebar.pageChanged.emit("evaluation")
    assert window.stack.currentWidget() is window.page_evaluation

    # Kembali ke Dashboard
    window.sidebar.pageChanged.emit("dashboard")
    assert window.stack.currentWidget() is window.page_dashboard


def test_header_updates_with_page():
    window = MainWindow()
    window.sidebar.pageChanged.emit("monitoring")
    assert "Monitoring" in window.header.title_label.text()

    window.sidebar.pageChanged.emit("prediction")
    assert "Prediksi" in window.header.title_label.text()

    window.sidebar.pageChanged.emit("dashboard")
    assert "Dashboard" in window.header.title_label.text()


def test_map_placeholder_visible():
    window = MainWindow()
    assert window.page_dashboard.map_placeholder is not None


def test_empty_state_widgets_exist():
    window = MainWindow()
    assert window.page_dashboard.monitoring_empty is not None
    assert window.page_monitoring.empty_state is not None
    assert window.page_prediction.result_empty is not None
    assert window.page_evaluation.cm_empty is not None


def test_widgets_instantiable():
    sidebar = SidebarWidget()
    assert sidebar is not None
    assert sidebar.menu.count() == 5

    header = HeaderWidget()
    assert header is not None

    map_ph = MapPlaceholderWidget()
    assert map_ph is not None

    empty = EmptyStateWidget()
    assert empty is not None
