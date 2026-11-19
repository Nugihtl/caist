"""Badge status reusable untuk menampilkan kondisi data."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel


class StatusBadge(QLabel):
    """Badge kecil dengan warna berdasarkan status.

    Status yang dikenali:
    - available: hijau
    - unavailable: merah
    - pending: oranye
    - default: abu-abu
    """

    def __init__(self, text: str = "", status: str = "default", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("statusBadge")
        self.setProperty("status", status)
        self.set_text(text, status)

    def set_text(self, text: str, status: str = "default") -> None:
        super().setText(text)
        self.setProperty("status", status)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
