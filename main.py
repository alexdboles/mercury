from pathlib import Path
import sys

from PyQt6.QtWidgets import QApplication
from src.app import MercuryScheduler


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    app = QApplication(sys.argv)
    window = MercuryScheduler(root / "data" / "scheduler.db", root / "exports")
    window.show()
    sys.exit(app.exec())
