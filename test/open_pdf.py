import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

class PDFViewerApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)

        self.main_window = PDFViewerWindow()
        self.main_window.show()

class PDFViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PDF Viewer")
        self.setGeometry(100, 100, 400, 200)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        open_pdf_button = QPushButton("Open PDF")
        open_pdf_button.clicked.connect(self.open_pdf)
        layout.addWidget(open_pdf_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setCentralWidget(central_widget)

    def open_pdf(self):
        # Replace 'path_to_your_pdf.pdf' with the actual path to your PDF file
        pdf_file_path = 'attendance_sheets.pdf'

        # Use QDesktopServices to open the PDF file with the default PDF viewer
        QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_file_path))

if __name__ == "__main__":
    app = PDFViewerApp(sys.argv)
    sys.exit(app.exec())
