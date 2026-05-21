import sys
import os
sys.path.append(os.path.dirname(__file__))

from views.main_window_new import MainWindow
from PyQt6.QtWidgets import QApplication
from database.database import init_db

if __name__ == '__main__':
    init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())