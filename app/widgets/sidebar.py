"""Sidebar navigasi utama aplikasi CAIST."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.settings import APP_NAME, APP_VERSION


class SidebarWidget(QWidget):
    """Sidebar kiri dengan branding dan lima menu navigasi utama.

    Memancarkan sinyal pageChanged(str) saat item menu diklik.
    """

    pageChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)

        self._menu_items: list[tuple[str, str, str]] = [
            ("dashboard", "Dashboard", "🏠"),
            ("monitoring", "Monitoring", "🌧️"),
            ("prediction", "Prediksi", "🔮"),
            ("region", "Data Wilayah", "🗺️"),
            ("evaluation", "Evaluasi Model", "📊"),
        ]

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Branding
        brand = QFrame()
        brand.setObjectName("sidebarBrand")
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(20, 16, 20, 16)
        brand_layout.setSpacing(4)

        brand_label = QLabel(APP_NAME)
        brand_label.setObjectName("sidebarBrandLabel")
        brand_sub = QLabel(f"v{APP_VERSION}")
        brand_sub.setObjectName("sidebarBrandSub")

        brand_layout.addWidget(brand_label)
        brand_layout.addWidget(brand_sub)
        layout.addWidget(brand)

        # Menu
        self.menu = QListWidget()
        self.menu.setObjectName("sidebarMenu")
        self.menu.setCurrentRow(0)
        self.menu.currentRowChanged.connect(self._on_row_changed)

        for key, label, icon_text in self._menu_items:
            item = QListWidgetItem(f"{icon_text}  {label}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.menu.addItem(item)

        layout.addWidget(self.menu)
        layout.addStretch()

        self._update_active_state(0)

    def _on_row_changed(self, row: int) -> None:
        self._update_active_state(row)
        item = self.menu.item(row)
        if item is not None:
            key = item.data(Qt.ItemDataRole.UserRole)
            self.pageChanged.emit(key)

    def _update_active_state(self, row: int) -> None:
        for index in range(self.menu.count()):
            item = self.menu.item(index)
            if item is not None:
                item.setSelected(index == row)

    def set_active_page(self, page_key: str) -> None:
        """Set menu item aktif berdasarkan kunci halaman."""
        for index in range(self.menu.count()):
            item = self.menu.item(index)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == page_key:
                self.menu.setCurrentRow(index)
                break
