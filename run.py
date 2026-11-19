"""Titik masuk aplikasi CAIST."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(prog="CAIST")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifikasi inisialisasi aplikasi tanpa menampilkan jendela.",
    )
    args = parser.parse_args()

    if args.check:
        app = QApplication(sys.argv)
        MainWindow()
        return 0

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
