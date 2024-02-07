import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QComboBox, QDateEdit, QStyledItemDelegate, QSizePolicy, QHeaderView, QMessageBox
from PyQt6.QtCore import Qt, QDate

class DateDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDate(QDate.currentDate().addDays(-QDate.currentDate().dayOfWeek() + 1))
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.ItemDataRole.DisplayRole)
        date = QDate.fromString(value, "yyyy-MM-dd")
        editor.setDate(date)

    def setModelData(self, editor, model, index):
        date = editor.date().addDays(-editor.date().dayOfWeek() + 1)
        model.setData(index, date.toString("yyyy-MM-dd"), Qt.ItemDataRole.DisplayRole)

class InteractiveTable(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(2)  # Reduced to 2 columns
        self.table.setHorizontalHeaderLabels(["Week of", "Exp"])
        self.table.setRowCount(1)

        self.table.setItemDelegateForColumn(0, DateDelegate())  # Set delegate for date column

        self.exp_dropdown = QComboBox()
        self.exp_dropdown.addItems([""] + ["Option 1", "Option 2", "Option 3"])  # Add empty string as default
        self.table.setCellWidget(0, 1, self.exp_dropdown)

        self.layout.addWidget(self.table)

        # Horizontal layout for buttons
        button_layout = QHBoxLayout()

        self.pushButton_plus = QPushButton("+")
        self.pushButton_plus.setStyleSheet("background-color: pink;")
        self.pushButton_plus.clicked.connect(self.addRow)
        button_layout.addWidget(self.pushButton_plus)

        self.done_button = QPushButton("Done")
        self.done_button.setStyleSheet("background-color: lightblue;")
        self.done_button.clicked.connect(self.collectData)
        button_layout.addWidget(self.done_button)

        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)
        self.setWindowTitle("Interactive Table")
        self.show()

        # Set default width for the table
        self.table.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.table.setFixedWidth(400)  # Adjust the width as needed

        # Allow the second column to expand
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Disable the "Done" button initially
        self.done_button.setEnabled(False)

        # Connect signals for table events
        self.table.itemChanged.connect(self.checkFirstDate)
        self.table.model().rowsRemoved.connect(self.checkRowsRemoved)

    def addRow(self):
        row_count = self.table.rowCount()
        self.table.setRowCount(row_count + 1)
        
        exp_dropdown = QComboBox()
        exp_dropdown.addItems([""] + ["Option 1", "Option 2", "Option 3"])  # Add empty string as default
        self.table.setCellWidget(row_count, 1, exp_dropdown)

        # Set the date of the new row to be the same as the date of the previous row
        if row_count > 0:
            previous_date_item = self.table.item(row_count - 1, 0)
            if previous_date_item:
                previous_date = QDate.fromString(previous_date_item.text(), "yyyy-MM-dd")
                self.table.setItem(row_count, 0, QTableWidgetItem(previous_date.toString("yyyy-MM-dd")))
            else:
                # If previous date is not available, set the current date
                self.table.setItem(row_count, 0, QTableWidgetItem(QDate.currentDate().toString("yyyy-MM-dd")))
        else:
            self.table.setItem(row_count, 0, QTableWidgetItem(QDate.currentDate().toString("yyyy-MM-dd")))

        # Enable the "Done" button if the first row has a date
        if row_count == 0:
            self.done_button.setEnabled(True)

    def collectData(self):
        dates = set()
        options = set()
        error_message = ""

        for row in range(self.table.rowCount()):
            date_item = self.table.item(row, 0)
            option_item = self.table.cellWidget(row, 1)

            if date_item and option_item:
                date = date_item.text()
                option = option_item.currentText()

                if date in dates:
                    error_message += f"Date {date} is duplicated.\n"
                else:
                    dates.add(date)

                if option == "":
                    error_message += "An option must be selected.\n"
                elif option in options:
                    error_message += f"Option {option} is duplicated.\n"
                else:
                    options.add(option)

        if error_message:
            QMessageBox.critical(self, "Error", error_message)
        else:
            data = {row + 1: self.table.item(row, 0).text() for row in range(self.table.rowCount())}
            print(data)
            self.table.setEnabled(False)
            self.done_button.setText("Edit")

            # Connect edit functionality to the button
            self.done_button.clicked.disconnect()
            self.done_button.clicked.connect(self.editTable)

    def editTable(self):
        self.table.setEnabled(True)
        self.done_button.setText("Done")

        # Connect data collection functionality back to the button
        self.done_button.clicked.disconnect()
        self.done_button.clicked.connect(self.collectData)

    def checkFirstDate(self, item):
        if item.row() == 0 and item.column() == 0:
            self.done_button.setEnabled(bool(item.text()))

    def checkRowsRemoved(self):
        # Disable the "Done" button if all rows are removed
        if self.table.rowCount() == 0:
            self.done_button.setEnabled(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            # Delete the selected row when the Delete key is pressed
            selected_row = self.table.currentRow()
            if selected_row >= 0:
                self.table.removeRow(selected_row)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = InteractiveTable()
    sys.exit(app.exec())
