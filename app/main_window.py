"""Jendela utama aplikasi CAIST (placeholder Stage 1)."""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget

from config.settings import WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        central = QWidget()
        layout = QVBoxLayout(central)
        label = QLabel("CAIST — Prediksi Probabilitas Banjir Bandung Raya\n\nStage 1: Inisialisasi proyek selesai.")
        layout.addWidget(label)
        self.setCentralWidget(central)
