import os
import sys
import shutil
import glob
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QListWidget, QListWidgetItem, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QFileDialog, QTextEdit
from PyQt6.QtCore import Qt

class FileCopierApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("File Copier")
        self.setGeometry(100, 100, 400, 400)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()

        self.browse_button = QPushButton("Browse Files")
        self.browse_button.clicked.connect(self.browse_files)
        self.layout.addWidget(self.browse_button)

        self.send_button = QPushButton("Send to Laptops")
        self.send_button.clicked.connect(self.send_files)
        self.layout.addWidget(self.send_button)

        client_name = 'SC-L-PH-BC3-ta1'
        self.client_path = r'\\' + client_name
        self.destination_label = QLabel("Destination Directory in Client PC:")
        self.destination_input = QLineEdit('/phys/')
        self.destination_input.setReadOnly(False)
        self.layout.addWidget(self.destination_label)
        self.layout.addWidget(self.destination_input)

        self.selected_files_list = QListWidget(self)
        self.layout.addWidget(self.selected_files_list)

        # Add QTextEdit for file names and patterns to be deleted
        self.delete_label = QLabel("File Names/Patterns (e.g. *.pdf) to Delete | one entry per line:")
        self.delete_input = QTextEdit()
        self.layout.addWidget(self.delete_label)
        self.layout.addWidget(self.delete_input)

        # Add button for file deletion
        self.delete_button = QPushButton("Delete Files")
        self.delete_button.clicked.connect(self.delete_files)
        self.layout.addWidget(self.delete_button)

        self.central_widget.setLayout(self.layout)

        self.selected_files = []

    def browse_files(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        selected_files, _ = dialog.getOpenFileNames(self, "Select Files", "", "")

        if selected_files:
            self.selected_files.extend(selected_files)
            self.update_selected_files_list()
        else:
            QMessageBox.warning(self, "No Files Selected", "No files were selected to send.")

    def update_selected_files_list(self):
        self.selected_files_list.clear()
        for file_path in self.selected_files:
            file_name = os.path.basename(file_path)
            item = QListWidgetItem(file_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.addRemoveButton(item)
            self.selected_files_list.addItem(item)

    def send_files(self):
        if not self.selected_files:
            QMessageBox.warning(self, "No Files to Send", "No files to send. Please select files first.")
            return

        destination_path = os.path.join(self.client_path, self.destination_input.text())

        if not destination_path:
            QMessageBox.warning(self, "No Destination Directory", "Please enter a destination directory.")
            return

        for source_path in self.selected_files:
            source_name = os.path.basename(source_path)
            destination = os.path.join(destination_path, source_name)

            if not os.path.exists(destination_path):
                os.makedirs(destination_path)

            try:
                shutil.copy(source_path, destination)
                print(f"Successfully copied file: {source_path} to {destination}")
            except Exception as e:
                print(f"Failed to copy file: {source_path} - {e}")

        QMessageBox.information(self, "Task Completed", "All selected files have been copied.")

    def addRemoveButton(self, item):
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(lambda: self.removeSelectedFile(item))

        layout = QHBoxLayout()
        layout.addWidget(QLabel(item.text()))
        layout.addWidget(remove_button)

        custom_widget = QWidget()
        custom_widget.setLayout(layout)

        self.selected_files_list.setItemWidget(item, custom_widget)

    def removeSelectedFile(self, item):
        if item:
            file_name = item.text()
            self.selected_files = [f for f in self.selected_files if not f.endswith(file_name)]
            self.update_selected_files_list()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_item = self.selected_files_list.currentItem()
            self.removeSelectedFile(selected_item)

    def delete_files(self):
        client_name = 'SC-L-PH-BC3-ta1'
        client_path = r'\\' + client_name

        delete_input = self.delete_input.toPlainText()
        delete_files = delete_input.splitlines()

        for file in delete_files:
            file = file.strip()
            file_to_delete = os.path.join(client_path, self.destination_input.text().strip(), file)
            
            if '*' in file:
                matching_files = glob.glob(file_to_delete)
                for matching_file in matching_files:
                    try:
                        os.remove(matching_file)
                        print(f"Successfully deleted file: {matching_file}")
                    except Exception as e:
                        print(f"Failed to delete file: {matching_file} - {e}")
            else:
                try:
                    os.remove(file_to_delete)
                    print(f"Successfully deleted file: {file_to_delete}")
                except Exception as e:
                    print(f"Failed to delete file: {file_to_delete} - {e}")

        QMessageBox.information(self, "Deletion Completed", "All selected files have been deleted.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileCopierApp()
    window.show()
    sys.exit(app.exec())
