"""Database-backed inventory of CAIST regional datasets."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QTableWidget, QTableWidgetItem, QWidget

from app.widgets.section_header import SectionHeader
from src.database.ui_readers import load_ui_snapshot


class RegionPage(QWidget):
    """Show source integration status and actual row/coverage details."""

    def __init__(self, parent=None, data_snapshot=None) -> None:
        super().__init__(parent)
        self.data_snapshot = data_snapshot if data_snapshot is not None else load_ui_snapshot()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)
        root.addWidget(SectionHeader(
            title="Data Wilayah",
            description="Status, jumlah baris, dan cakupan dataset dari database dan layer lokal CAIST",
        ))

        frame = QFrame()
        frame.setObjectName("groupFrame")
        layout = QVBoxLayout(frame)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Dataset", "Status", "Jumlah / Cakupan"])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 230)
        self.table.setColumnWidth(1, 145)
        layout.addWidget(self.table)
        root.addWidget(frame, stretch=1)

        entries = list(self.data_snapshot.get("datasets", []))
        if not self.data_snapshot.get("connected"):
            entries = [{"name": "Database CAIST", "status": "Belum tersedia",
                        "detail": self.data_snapshot.get("error") or "Database lokal belum tersedia."}]
        entries.append({"name": "Monitoring BBWS Citarum FFWS", "status": "Belum tersedia",
                        "detail": "Feed real-time belum diintegrasikan."})
        self.table.setRowCount(len(entries))
        for row, source in enumerate(entries):
            for column, value in enumerate((source["name"], source["status"], source["detail"])):
                item = QTableWidgetItem(str(value))
                if column == 2:
                    item.setToolTip(str(value))
                self.table.setItem(row, column, item)
        self.table.resizeRowsToContents()
