"""Paket halaman aplikasi CAIST."""

from .dashboard_page import DashboardPage
from .evaluation_page import EvaluationPage
from .monitoring_page import MonitoringPage
from .prediction_page import PredictionPage
from .region_page import RegionPage

__all__ = [
    "DashboardPage",
    "MonitoringPage",
    "PredictionPage",
    "RegionPage",
    "EvaluationPage",
]
