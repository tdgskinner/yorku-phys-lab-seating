import sys , os, io, re
import requests
import appdirs
import pandas as pd
import logging
from packaging import version

from qtpy import QtWidgets, QtCore
from qtpy import uic
from qtpy.QtCore import QAbstractTableModel, QVariant, QModelIndex, QSettings, QThread, Signal, QObject, Qt, QMarginsF, QSize, QUrl
from qtpy.QtWidgets import QDialog, QApplication, QFileDialog, QWidget, QProgressBar, QProgressDialog, QStyle
from qtpy.QtWidgets import  QLabel, QVBoxLayout, QComboBox, QSplashScreen, QListWidgetItem, QMessageBox
from qtpy.QtWidgets import QGraphicsView, QGraphicsScene
from qtpy.QtWidgets import QTableWidgetItem, QDateEdit, QStyledItemDelegate, QSizePolicy, QHeaderView
from qtpy.QtGui import QIcon, QPixmap, QFont, QPainter, QPageSize, QPageLayout, QShortcut, QKeySequence, QDesktopServices
from qtpy.QtPrintSupport import QPrinter, QPrintPreviewDialog
from qtpy.QtCore import QTimer, QDateTime, QDate

import scripts.SeatingManager as seating
import scripts.GPcManager2 as gpc
from scripts.remote_copy import Remote_GPC_manager, Remote_LPC_manager
from scripts.remote_reboot2 import Remote_PC_Reboot
import json
from collections import OrderedDict

# Get the user-specific directory for your application in AppData\Local
user_data_dir = appdirs.user_data_dir(appname='userData', appauthor='YUlabManager')

# Create directories if they don't exist
os.makedirs(user_data_dir, exist_ok=True)

#--------------------------------------------------------------------------------
def resource_path(relative_path):
    """
    Get the absolute path to a resource file.

    This function takes a relative path to a resource file and returns the absolute path to that file.
    It works for both development and PyInstaller builds.

    Parameters:
    relative_path (str): The relative path to the resource file.

    Returns:
    str: The absolute path to the resource file.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS2
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
#--------------------------------------------------------------------------------
class OutputWrapper(QObject):
    """
    A class that wraps the standard output or error stream and emits a signal whenever text is written to it.
    """

    outputWritten = QtCore.Signal(object, object)

    def __init__(self, parent, stdout=True):
        super().__init__(parent)
        self._stdout = stdout

        if stdout:
            self._stream = sys.stdout
        else:
            self._stream = sys.stderr
        
        if self._stream is None:
            # If sys.stdout or sys.stderr is None, create a new StringIO instance
            self._stream = io.StringIO()
        
        # Save the original stream
        self._original_stream = self._stream
        
        # Redirect the stream
        if stdout:
            sys.stdout = self
        else:
            sys.stderr = self
        

    def write(self, text):
        """
        Writes the specified text to the stream and emits the outputWritten signal.

        Args:
            text (str): The text to be written to the stream.
        """
        self._original_stream.write(text)
        self.outputWritten.emit(text, self._stdout)

    def flush(self):
        """
        Flushes the stream.
        """
        self._original_stream.flush()

    def __getattr__(self, name):
        return getattr(self._original_stream, name)

    def __del__(self):
        try:
            if self._stdout:
                sys.stdout = self._original_stream
            else:
                sys.stderr = self._original_stream
        except AttributeError:
            pass
#--------------------------------------------------------------------------------
class LabLayoutWindow_new(QWidget):
    def __init__(self, layout_out, main_window_size=QSize(800, 600)):
        super().__init__()

        # Set the size of the LabLayoutWindow to match the main window size
        self.resize(main_window_size)

        # Create a QGraphicsView to display the image
        self.view = QGraphicsView(self)
        self.view.setRenderHints(QPainter.RenderHint.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        # Create a QGraphicsScene and add the pixmap to it
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)

        # Create a QVBoxLayout to organize the contents
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)

        # Set the layout for the QWidget
        self.setLayout(layout)

        # Load the image and set it to the view
        self.loadImage(layout_out)

    def loadImage(self, layout_out):
        # Load the image file
        self.pixmap = QPixmap(layout_out)

        # Add the pixmap to the scene
        self.scene.clear()
        self.scene.addPixmap(self.pixmap)

        # Resize the image to fit the view with aspect ratio preservation
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        # Resize the image to fit the view when the window is resized
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
#--------------------------------------------------------------------------------
class LabLayoutWindow(QWidget):
    """
    This "window" is a QWidget. If it has no parent, it
    will appear as a free-floating window as we want.
    """
    def __init__(self, layout_out):
        super().__init__()
        
        pixmap = QPixmap(layout_out)
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Lab Layout")
        flags = dialog.windowFlags()
        flags |= QtCore.Qt.WindowType.WindowMaximizeButtonHint
        dialog.setWindowFlags(flags)

        layout = QVBoxLayout()
            
        label = QLabel(dialog)
        label.setPixmap(pixmap)
        label.resize(pixmap.width(), pixmap.height())

        layout.addWidget(label)
        self.setLayout(layout)
#--------------------------------------------------------------------------------
class PandasModel(QAbstractTableModel):
    def __init__(self, df=pd.DataFrame(), parent=None):
        super().__init__(parent)
        self._df = df

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
             return QVariant()
        if orientation == Qt.Orientation.Horizontal:
            try:
                return self._df.columns.tolist()[section]
            except IndexError:
                return QVariant()
        elif orientation == Qt.Orientation.Vertical:
            try:
                return self._df.index.tolist()[section]
            except IndexError:
                return QVariant()
    
    def rowCount(self, parent=QModelIndex()):
        return self._df.shape[0]

    def columnCount(self, parent=QModelIndex()):
        return self._df.shape[1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return QVariant()
        if not index.isValid():
            return QVariant()
        return QVariant(str(self._df.iloc[index.row(), index.column()]))
#--------------------------------------------------------
class AttWindow(QWidget):
    """
    This "window" is a QWidget. If it has no parent, it
    will appear as a free-floating window as we want.
    """
    def __init__(self, stud_list, session, session_id, code, exp_id):
        super().__init__()

        self.ui = uic.loadUi(resource_path(os.path.join('assets', 'YorkULabSeating_att.ui')),self)
        self.stud_list = stud_list
        self.session = session
        self.session_id = session_id
        self.exp_id = exp_id
        self.code = code
        self.tableView_att.setSortingEnabled(True)
        self.tableView_att.horizontalHeader().setSectionsMovable(True)
        myFont=QFont()
        myFont.setBold(True)

        self.label_exp_id.setText(str(self.exp_id))
        self.label_code.setText(f'PHYS {self.code} - {self.session}')
        self.label_exp_id.setFont(myFont)
        self.label_code.setFont(myFont)
        self.label_4.setFont(myFont)
        self.label_5.setFont(myFont)
        self.label_6.setFont(myFont)
        icon = QIcon(resource_path(os.path.join('assets','printer-icon.png')))
        self.pushButton_print_att.setIcon(icon)
        self.pushButton_print_att.clicked.connect(self.print_prev_dlg)
        shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        shortcut.activated.connect(self.pushButton_print_att.click)
        self.pushButton_print_att.setToolTip("Click me (Ctrl+M)")
        
        self.retrieveDataset()
    
    def retrieveDataset(self):
        self.df, _ = seating.concat_stud_lists(self.stud_list)
        self.df = self.df.reset_index(drop=True)
        n_col = len(list(self.df.columns))
        if n_col == 9 or n_col ==10:
            self.df.columns = seating.get_studList_header(n_col)
    	
        self.df = self.df.dropna()
        self.df = self.df.loc[self.df['session_id'].str.strip()!='LAB 99']
        self.df = self.df.loc[self.df['session_id'].str.strip()==self.session_id]
        
        self.df = self.df.rename(columns={'first_name': 'First Name'})
        self.df = self.df.rename(columns={'surname': 'Last Name'})
        self.df = self.df[["First Name", "Last Name"]]
        self.df["Attn."] = "         "
        idx = range(1,len(self.df)+1)
        self.df.insert(0, '', idx)
		
        font_plainText = QFont()
        font_plainText.setPointSize(8)
        self.plainTextEdit_att.setFont(font_plainText)

        if self.code == '1801':
            if self.exp_id ==2:
                self.df["LA1\n(2 marks)"] = ""
                self.df["LA2\n(4 marks)"] = ""
                self.df["LA3\n(4 marks)"] = ""
                self.df["Bonus\n(1 marks)"] = ""
                self.df["Total\n(10 marks)"] = ""
                self.plainTextEdit_att.setPlainText('LA1 - Used DMM to measure the output voltage of a potentiometer\nLA2 - Wrote LabVIEW for data acquisition of the output voltage from potentiometer\nLA3 - Wrote LabVIEW program for control of DC motor\nBonus - Able to add additional control to stop motor with the "STOP" button')
            elif self.exp_id ==3:
                self.df["LA1\n(5 marks)"] = ""
                self.df["LA2\n(5 marks)"] = ""
                self.df["Bonus\n(2 marks)"] = ""
                self.df["Total\n(10 marks)"] = ""
                self.plainTextEdit_att.setPlainText('LA1 - Wheatstone bridge circuit operates correctly\nLA2 - Digital Thermometer operates correctly\nBonus - Fan switches on when temperature is too high')
            elif self.exp_id ==5:
                self.df["LA1\n(2 marks)"] = ""
                self.df["LA2\n(3 marks)"] = ""
                self.df["InLab\nTotal"] = ""
                self.plainTextEdit_att.setPlainText('LA1 - Circuit works as expected with magnet\nLA2 - Digital Speedometer works properly')
            elif self.exp_id ==9:
                self.df["LA2\n(3 marks)"] = ""
                self.plainTextEdit_att.setPlainText('LA2 - Successfully able to decipher number sent using Oscilloscope')
		
        self.df.fillna('')
        
        self.model = PandasModel(self.df)
        font_table = QFont()
        font_table.setPointSize(8)
        self.tableView_att.setFont(font_table)
        self.tableView_att.setModel(self.model)

        for i in range(len(self.df)):
            self.tableView_att.setRowHeight(i, 2)
        
        self.tableView_att.setColumnWidth(0,3)
        self.tableView_att.setColumnWidth(3,40)
        self.tableView_att.verticalHeader().hide()

        for i in range(4, len(self.df.columns)):
            self.tableView_att.setColumnWidth(i,60)
    
    
    def print_prev_dlg(self):
        printer = QPrinter(QPrinter.PrinterMode.PrinterResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))

        #To fix: setPageMargins is doing nothing!
        printer.setPageMargins(QMarginsF(1,1,1,1), units=QPageLayout.Unit.Millimeter)
        
        prev_dlg = QPrintPreviewDialog(printer, self)
        combobox = prev_dlg.findChild(QComboBox)
        index = combobox.findText("100%")
        combobox.setCurrentIndex(index)

        prev_dlg.paintRequested.connect(self.print_prev_att)
        prev_dlg.exec() 

    def print_prev_att(self, printer):
        painter = QPainter(printer)
        # calculate the scaling factor to fit the widget to the page
        xscale = printer.pageRect(QPrinter.Unit.Point).width() / self.width()
        yscale = printer.pageRect(QPrinter.Unit.Point).height() / self.height()
        scale = 8*min(xscale, yscale)

        # set the transformation matrix of the painter
        painter.translate((printer.paperRect(QPrinter.Unit.Point).x()) + (printer.pageRect(QPrinter.Unit.Point).width()/2), (printer.paperRect(QPrinter.Unit.Point).y()) + (printer.pageRect(QPrinter.Unit.Point).height()/2))
        painter.scale(scale, scale)

        # draw the widget onto the printer
        self.render(painter)

        # cleanup
        painter.end()
        logging.debug('Printing completed')

#--------------------------------------------------------------------------------
class lpc_file_manager(QDialog):
    def __init__(self, laptop_list, LocalCopyMode):
        super().__init__()

        self.ui = uic.loadUi(resource_path(os.path.join('assets', 'YorkULabSeating_lpc.ui')),self)
        self.lpc_list = laptop_list
        self.LocalCopyMode = LocalCopyMode
        self.selected_files = []
        self.lpc_thread={}

        self.pushButton_browse.clicked.connect(self.browse_files)
        self.pushButton_copy.clicked.connect(self.start_lpc_copy_worker)
        self.lineEdit_destination_input.setReadOnly(False)
        self.pushButton_delete.clicked.connect(self.start_lpc_delete_worker)

        self.pbar_copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pbar_delete.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pbar_copy.hide()
        self.pbar_delete.hide()
    
    def start_lpc_copy_worker(self):
        if self.lpc_list:
            if self.selected_files:
                destination_path = self.lineEdit_destination_input.text()
                self.pushButton_copy.setEnabled(False)
                self.pbar_copy.show()
                #self.pbar_copy.setFormat("Copy files ...")
                self.lpc_thread[1] = lpcCopyFileThread(self.lpc_list, self.selected_files, destination_path, self.LocalCopyMode, self.pbar_copy, parent=None)
                self.lpc_thread[1].finished.connect(self.on_copyFinished)
                self.lpc_thread[1].start()
                self.lpc_thread[1].progress.connect(self.copy_setProgress)
            else:
                QMessageBox.warning(self, "No Files Selected", "No files were selected to copy.")
        else:
            QMessageBox.warning(self, "No Laptop found", "No laptop was found in the PC list of the selected room.")
    
    def start_lpc_delete_worker(self):
        if self.lpc_list:
            textEdit_delete_input = self.textEdit_delete_input.toPlainText()
            to_delete = textEdit_delete_input.splitlines()

            if to_delete:
                destination_path = self.lineEdit_destination_input.text()
                self.pushButton_delete.setEnabled(False)
                self.pbar_delete.show()
                self.lpc_thread[2] = lpcDeleteThread(self.lpc_list, to_delete, destination_path, self.LocalCopyMode, self.pbar_delete, parent=None)
                self.lpc_thread[2].finished.connect(self.on_deleteFinished)
                self.lpc_thread[2].start()
                self.lpc_thread[2].progress.connect(self.delete_setProgress)
            else:
                QMessageBox.warning(self, "No Files to Delete", "No file names/ pattern were entered to delete.")
        else:
            QMessageBox.warning(self, "No Laptop found", "No laptop was found in the PC list of the selected room.")

    
    def copy_setProgress(self, copy_progress):
        self.pbar_copy.setValue(copy_progress)

    def on_copyFinished(self):
        self.pbar_copy.setFormat("Copy completed")
        self.pushButton_copy.setEnabled(True)

        if all(self.lpc_thread[1].status.values()):
            QMessageBox.information(None,'Copy Successful',' All selected files are copied to target Laptop(s) successfully')   
        else:
            res = [key for key, value in self.lpc_thread[1].status.items() if not value]
            if res:
                error_message = f'Failed to copy the selected files to: {", ".join(res)}'
            else:
                error_message = "Failed to copy the selected files to All laptops!."
            
            QMessageBox.warning(None, "Copy Failed", error_message)
    
    def delete_setProgress(self, delete_progress):
        self.pbar_delete.setValue(delete_progress)

    def on_deleteFinished(self):
        self.pbar_delete.setFormat("Delete completed")
        self.pushButton_delete.setEnabled(True)

        if all(self.lpc_thread[2].status.values()):
            QMessageBox.information(None, 'Delete Successful', ' All files/dir are deleted from target Laptop(s) successfully')   
        else:
            res = [key for key, value in self.lpc_thread[1].status.values() if not value]
            error_message = f' Failed to delete the identified files/ dir from: {", ".join(res)}'
            QMessageBox.warning(None, "Delete Failed", error_message)

    def browse_files(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        selected_files, _ = dialog.getOpenFileNames(self, "Select Files", "", "")

        if selected_files:
            self.selected_files.extend(selected_files)
            self.update_selected_files_list()

    def update_selected_files_list(self):
        self.listWidget_selected_files_list.clear()
        for file_path in self.selected_files:
            file_name = os.path.basename(file_path)
            item = QListWidgetItem(file_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.listWidget_selected_files_list.addItem(item)
    
    def removeSelectedFile(self, item):
        if item:
            file_name = item.text()
            self.selected_files = [f for f in self.selected_files if not f.endswith(file_name)]
            self.update_selected_files_list()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_item = self.listWidget_selected_files_list.currentItem()
            self.removeSelectedFile(selected_item)
    
    def closeEvent(self, event):
        running_cp_process = False
        running_del_process = False 
        
        if self.lpc_thread.get(1, None):
            if self.lpc_thread[1].isRunning():
                running_cp_process = True
        if self.lpc_thread.get(2, None):
            if self.lpc_thread[2].isRunning():
                running_del_process = True

        if running_cp_process or running_del_process:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Warning")
            dlg.setText("Are you sure you want to close lpc manager?")
            dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel)
            dlg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Question)
            button = dlg.exec()

            if button == QtWidgets.QMessageBox.StandardButton.Yes:
                if running_cp_process:
                    self.lpc_thread[1].terminate()
                if running_del_process:
                    self.lpc_thread[2].terminate()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
#--------------------------------------------------------------------------------
class lab_scheduler_manager(QDialog):
    def __init__(self, exp_list, time_csv_path, room, code, location_list):
        super().__init__()
        self.ui = uic.loadUi(resource_path(os.path.join('assets', 'YorkULabSeating_lab_scheduler.ui')),self)
        self.exp_list = exp_list
        self.time_csv_path = time_csv_path
        self.room = room
        self.code = code
        self.location_list = location_list
        
        # Function is out of scope - Leya, 26/09/25
        # self.update_current_lab_config_ui()
        
        # Sets course label at the top of the window
        self.course_label.setText(f"PHYS {code}")
        
        self.pushButton_plus.clicked.connect(self.addRow)
        self.pushButton_done.clicked.connect(self.collectData)
        self.pushButton_create_csv.clicked.connect(self.generate_schedule_csv)

        self.tableWidget_scheduler.setColumnCount(3)  # Reduced to 2 columns
        self.tableWidget_scheduler.setHorizontalHeaderLabels(["Week of", "Exp", "Room"])
        self.tableWidget_scheduler.setRowCount(1)
        self.tableWidget_scheduler.setItemDelegateForColumn(0, DateDelegate())  # Set delegate for date column
        self.exp_dropdown = QComboBox()
        self.exp_dropdown.addItems(list(self.exp_list.keys())) 
        self.tableWidget_scheduler.setCellWidget(0, 1, self.exp_dropdown)
        self.tableWidget_scheduler.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.exp_dropdown.setCurrentIndex(0)
        self.room_dropdown = QComboBox()
        self.room_dropdown.addItems(list(self.location_list))
        self.tableWidget_scheduler.setCellWidget(0, 2, self.room_dropdown)
        self.tableWidget_scheduler.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Disable the "Done" button initially
        self.pushButton_done.setEnabled(False)
        self.pushButton_create_csv.setEnabled(False)

        # Connect signals for table events
        self.tableWidget_scheduler.itemChanged.connect(self.checkFirstDate)
        self.tableWidget_scheduler.model().rowsRemoved.connect(self.checkRowsRemoved)

    def addRow(self):
        self.exp_dropdown = QComboBox()
        self.exp_dropdown.addItems(list(self.exp_list.keys())) 
        self.room_dropdown = QComboBox()
        self.room_dropdown.addItems(list(self.location_list))
        row_count = self.tableWidget_scheduler.rowCount()
        self.tableWidget_scheduler.setRowCount(row_count + 1)
        self.tableWidget_scheduler.setCellWidget(row_count, 1, self.exp_dropdown)
        self.tableWidget_scheduler.setCellWidget(row_count, 2, self.room_dropdown)

        # Set the date of the new row to be a week after the date of the previous row
        if row_count > 0:
            previous_date_item = self.tableWidget_scheduler.item(row_count - 1, 0)
            if previous_date_item:
                next_date = QDate.fromString(previous_date_item.text(), "yyyy-MM-dd")
                next_date = next_date.addDays(7)
                self.tableWidget_scheduler.setItem(row_count, 0, QTableWidgetItem(next_date.toString("yyyy-MM-dd")))
            else:
                # If previous date is not available, set the current date
                self.tableWidget_scheduler.setItem(row_count, 0, QTableWidgetItem(QDate.currentDate().toString("yyyy-MM-dd")))
        else:
            self.tableWidget_scheduler.setItem(row_count, 0, QTableWidgetItem(QDate.currentDate().toString("yyyy-MM-dd")))
            
        # Set the experiment and room of the new row to be the next experiment and room in the list
        if row_count > 0:
            index = self.tableWidget_scheduler.cellWidget(row_count - 1, 1).currentIndex()
            index += 1
            self.exp_dropdown.setCurrentIndex(index)
            self.room_dropdown.setCurrentIndex(index)

        # Enable the "Done" button if the first row has a date
        if row_count == 0:
            self.pushButton_done.setEnabled(True)
    
    def collectData(self):
        dates = set()
        options = set()
        error_message = ""

        for row in range(self.tableWidget_scheduler.rowCount()):
            date_item = self.tableWidget_scheduler.item(row, 0)
            option_item = self.tableWidget_scheduler.cellWidget(row, 1)

            if date_item and option_item:
                date = date_item.text()
                option = option_item.currentText()

                if date in dates:
                    error_message += f"Date {date} is duplicated.\n"
                else:
                    dates.add(date)

                if option == "":
                    error_message += "A Exp. must be selected.\n"
                elif option in options:
                    error_message += f"Exp. {option} is duplicated.\n"
                else:
                    options.add(option)

        if error_message:
            QMessageBox.critical(self, "Error", error_message)
        else:
            self.schedule_data_dict = {row + 1: self.tableWidget_scheduler.item(row, 0).text() for row in range(self.tableWidget_scheduler.rowCount())}
            logging.debug(f'self.schedule_data_dict: {self.schedule_data_dict}')
            
            self.tableWidget_scheduler.setEnabled(False)
            self.pushButton_done.setText("Edit")

            # Connect edit functionality to the button
            self.pushButton_done.clicked.disconnect()
            self.pushButton_done.clicked.connect(self.editTable)
            self.pushButton_create_csv.setEnabled(True)
            return self.schedule_data_dict
    
    def editTable(self):
        self.tableWidget_scheduler.setEnabled(True)
        self.pushButton_create_csv.setEnabled(False)
        self.pushButton_done.setText("Done")

        # Connect data collection functionality back to the button
        self.pushButton_done.clicked.disconnect()
        self.pushButton_done.clicked.connect(self.collectData)

    def checkFirstDate(self, item):
        if item.row() == 0 and item.column() == 0:
            self.pushButton_done.setEnabled(bool(item.text()))

    def checkRowsRemoved(self):
        # Disable the "Done" button if all rows are removed
        if self.tableWidget_scheduler.rowCount() == 0:
            self.pushButton_done.setEnabled(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            # Delete the selected row when the Delete key is pressed
            selected_row = self.tableWidget_scheduler.currentRow()
            if selected_row >= 0:
                self.tableWidget_scheduler.removeRow(selected_row)
    
    def closeEvent(self, event):
        pass

    def generate_schedule_csv(self):
        schedule = seating.generate_schedule(self.schedule_data_dict, self.time_csv_path, self.exp_list, self.code, self.location_list)
            
        # Prompt the user to save the file
        fileName, _ = QFileDialog.getSaveFileName(None, "Save Schedule", "", "CSV Files (*.csv)")
        
        if fileName:
            if not fileName.endswith('.csv'):
                fileName += '.csv'
            # Save DataFrame to CSV
            schedule.to_csv(fileName, index=False)
            if schedule.shape[0] == 0:
                logging.debug('Empty schedule written. Check that time csv has no empty fields.')
            print(f"Lab Schedule saved to {fileName}")

#================================================================================
class att_editor_manager(QDialog):
    column_details_updated = Signal(dict) # Define a signal to emit updated column details
    customizedAttChanged = Signal(bool)  # Signal to notify customizedAtt change

    def __init__(self, code, exp_list, customized_att, column_details=None):
        super().__init__()
        self.ui = uic.loadUi(resource_path(os.path.join('assets', 'YorkULabSeating_att_editor.ui')), self)
        self.setWindowTitle("Attendance Sheet Editor")
        self.setGeometry(100, 100, 500, 500)
        self.code = code
        self.exp_list = exp_list
        self.comboBox_exp.addItems(['Extended (Default)'])
        self.comboBox_exp.addItems(list(self.exp_list.keys()))
        self.comboBox_exp.setCurrentIndex(0)
        self.course_label.setText(f'PHYS {self.code} Extended Attendance Sheet')
        self.customized_att = customized_att
        self.comboBox_exp.setEnabled(self.customized_att)
        self.checkBox_customize.setChecked(self.customized_att)

        self.setupTable()
        
        self.pushButton_save.setEnabled(False)

        #--signal and slots
        self.pushButton_add.clicked.connect(self.addRow)
        self.pushButton_done.clicked.connect(self.collectData)
        self.pushButton_save.clicked.connect(self.generate_att_json)
        self.comboBox_exp.activated.connect(self.loadColumnDetails)
        self.pushButton_load.clicked.connect(self.load_att_json)
        self.checkBox_customize.toggled.connect(self.set_customized_mode)

        # Initialize flag
        self.is_initializing = True

        # Load existing details or set default rows
        self.experiments_data = column_details if column_details else {}

        if self.experiments_data:
            self.loadColumnDetails()
        else:
            self.setDefaultRows()
        
        # Initialization complete
        self.is_initializing = False         

    def set_customized_mode(self):
        self.customized_att = self.checkBox_customize.isChecked()
        self.customizedAttChanged.emit(self.customized_att) # Emit signal when customized_att changes

        if self.customized_att:
            self.comboBox_exp.setEnabled(True)
        else:
            self.comboBox_exp.setCurrentIndex(0)
            self.comboBox_exp.setEnabled(False)
            self.loadColumnDetails()

    def setupTable(self):
        self.tableWidget_attEditor.setColumnCount(2)
        self.tableWidget_attEditor.setHorizontalHeaderLabels(["Column Title", "Column Width [cm]"])
        self.setDefaultRows()
        self.adjustColumnWidths()

    def adjustColumnWidths(self):
        header = self.tableWidget_attEditor.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

    def setDefaultRows(self):
        """Set the default rows for the table."""
        self.tableWidget_attEditor.setRowCount(3)  # Start with 3 rows
        self.setRowValues(0, "First Name", "3.5")
        self.setRowValues(1, "Last Name", "3.5")
        self.setRowValues(2, "Attendance", "4")
    
    def loadColumnDetails(self):
        self.pushButton_save.setEnabled(False)

        """Load and fill the table with data from column_details."""
        selected_experiment = self.comboBox_exp.currentText()
        column_details, footer = self.experiments_data.get(selected_experiment, [[], ''])

        if column_details:
            # Clear the existing table
            self.tableWidget_attEditor.clearContents()
            self.tableWidget_attEditor.setRowCount(0)

            # Sort the column details by index
            column_details.sort(key=lambda x: x["index"])

            for column_data in column_details:
                title = column_data["title"]
                width = column_data["width"]
                index = column_data["index"]

                # Add row if necessary
                if index >= self.tableWidget_attEditor.rowCount():
                    self.addRow()

                # Set values for the existing row
                self.setRowValues(index, title, width)

            self.textEdit_footer.setPlainText(footer)
        else:
            self.setDefaultRows()
            self.textEdit_footer.setPlainText('')


    def loadColumnDetails2(self):
        self.pushButton_save.setEnabled(False)

        """Load and fill the table with data from column_details."""
        selected_experiment = self.comboBox_exp.currentText()
        column_details, footer = self.experiments_data.get(selected_experiment, [OrderedDict(), ''])

        if column_details:
            # Clear the existing table
            self.tableWidget_attEditor.clearContents()
            self.tableWidget_attEditor.setRowCount(0)

            for title, width in column_details.items():
                self.addRow()
                last_row = self.tableWidget_attEditor.rowCount() - 1
                self.setRowValues(last_row, title, width)
            self.textEdit_footer.setPlainText(footer)
        else:
            self.setDefaultRows()
            self.textEdit_footer.setPlainText('')

    def setRowValues(self, row, title, width):
        """Helper method to set the values of a row."""
        title_item = QTableWidgetItem(title)
        width_item = QTableWidgetItem(str(width))

        # Ensure the row exists
        if row >= self.tableWidget_attEditor.rowCount():
            self.addRow()

        self.tableWidget_attEditor.setItem(row, 0, title_item)
        self.tableWidget_attEditor.setItem(row, 1, width_item)
    
    def addRow(self):
        row_count = self.tableWidget_attEditor.rowCount()
        self.tableWidget_attEditor.setRowCount(row_count + 1)

        # Initialize the new row with empty items
        self.tableWidget_attEditor.setItem(row_count, 0, QTableWidgetItem())
        self.tableWidget_attEditor.setItem(row_count, 1, QTableWidgetItem())
    
    def generate_att_json(self): 
        # Prompt the user to save the file
        fileName, _ = QFileDialog.getSaveFileName(None, "Save Attendance Sheet Design", "", "JSON Files (*.json)")
        
        if fileName:
            if not fileName.endswith('.json'):
                fileName += '.json'
            
            # Writing JSON data
            with open(fileName, 'w') as json_file:
                json.dump(self.experiments_data, json_file, indent=4)  # Use `indent` for pretty-printing

            self.accept()  # Close dialog if data collection is successful

    def load_att_json(self):
        # Open a file dialog to select the JSON file
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Attendance Sheet JSON", "", "JSON Files (*.json)")
        if fileName:
            try:
                # Read the JSON file
                with open(fileName, 'r') as file:
                    data = json.load(file, object_pairs_hook=OrderedDict)
    
                # Check if the data is a dictionary
                if not isinstance(data, dict):
                    QMessageBox.warning(self, "Invalid File", "The selected file does not contain valid configuration data.")
                    return
    
                # Update the internal dictionary with the loaded data
                self.experiments_data = data
    
                # Automatically load details for the first experiment, if available
                if self.experiments_data:
                    first_experiment = next(iter(self.experiments_data))
                    self.comboBox_exp.setCurrentText(first_experiment)
                    self.loadColumnDetails()
    
            except Exception as e:
                QMessageBox.critical(self, "Loading Error", f"An error occurred while loading the file: {str(e)}")

    def collectData(self):
        if not self.validityCheck():
            return  # If data is invalid, halt operation.

        # Get the current experiment title from the comboBox
        experiment_title = self.comboBox_exp.currentText()

        # Create a new list to store this experiment's column details
        column_details = []

        # Collect the column titles, widths, and indices from the table
        for index in range(self.tableWidget_attEditor.rowCount()):
            title_item = self.tableWidget_attEditor.item(index, 0)
            width_item = self.tableWidget_attEditor.item(index, 1)
            if title_item and width_item:
                title = title_item.text().strip()
                width_text = width_item.text().strip()
                try:
                    width = float(width_text)
                except ValueError:
                    continue  # Skip if invalid
                column_details.append({"title": title, "width": width, "index": index})

        # Store the collected details in the experiments_data under the selected experiment
        self.experiments_data[experiment_title] = [column_details, self.textEdit_footer.toPlainText()]

        # Emit the updated data
        self.column_details_updated.emit(self.experiments_data)
        logging.debug(f"Updated details for {experiment_title}: {column_details}")
        self.pushButton_save.setEnabled(True)


    # def collectData2(self):
    #     if not self.validityCheck():
    #         return  # If data is invalid, halt operation.

    #     # Get the current experiment title from the comboBox
    #     experiment_title = self.comboBox_exp.currentText()

    #     # Create a new dictionary to store this experiment's column details
    #     column_details = {}

    #     # Collect the column titles and widths from the table
    #     for row in range(self.tableWidget_attEditor.rowCount()):
    #         title_item = self.tableWidget_attEditor.item(row, 0)
    #         width_item = self.tableWidget_attEditor.item(row, 1)
    #         if title_item and width_item:
    #             title = title_item.text().strip()
    #             width_text = width_item.text().strip()
    #             try:
    #                 width = float(width_text)
    #             except ValueError:
    #                 continue  # Skip if invalid
    #             column_details[title] = width

    #     # Store the collected details in the experiments_data under the selected experiment
    #     self.experiments_data[experiment_title] = [column_details, self.textEdit_footer.toPlainText()]

    #     # Emit the updated data
    #     self.column_details_updated.emit(self.experiments_data)
    #     logging.debug(f"Updated details for {experiment_title}: {column_details}")
    #     self.pushButton_save.setEnabled(True)

    def validityCheck(self):
        if self.is_initializing:
            return True  # Skip checks during initialization.

        seen_titles = set()
        for row in range(self.tableWidget_attEditor.rowCount()):
            title_item = self.tableWidget_attEditor.item(row, 0)
            width_item = self.tableWidget_attEditor.item(row, 1)

            if not title_item or not title_item.text().strip():
                QMessageBox.warning(self, "Invalid Entry", "Please fill in all titles.")
                return False

            title_text = title_item.text().strip()
            if title_text in seen_titles:
                QMessageBox.warning(self, "Duplicate Title Detected", "Each title must be unique.")
                return False
            seen_titles.add(title_text)

            if not width_item or not width_item.text().strip():
                QMessageBox.warning(self, "Invalid Entry", "Please fill in all widths.")
                return False
            try:
                width = float(width_item.text().strip())
                if width <= 0:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "Invalid Entry", "Enter a positive number for width.")
                return False

        return True  # Data is valid
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            # Delete the selected row when the Delete key is pressed
            selected_row = self.tableWidget_attEditor.currentRow()
            if selected_row >= 0:
                self.tableWidget_attEditor.removeRow(selected_row)

#================================================================================
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
        
#================================================================================
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, appVersion, appDate):
        super().__init__()
        
        self.appVersion = appVersion
        self.appDate = appDate
        
        self.room_setting_dict ={} # is a nested dictionary, holds room settings dictionary
        self.pkl_path = None
        self.laptop_list = []
        self.extended_attlist_mode = False
        self.blankAtt_mode = False
        self.small_screen_mode = False
        self.customized_att = False

        self.gpc_list = []
        self.gpc_map ={}

        self.LoadSettingValues()
        QtWidgets.QMainWindow.__init__(self)
        
        self.ui = uic.loadUi(resource_path(os.path.join('assets','YorkULabSeating_new.ui')),self)
        YUlogo_s = QPixmap(resource_path(os.path.join('assets','yorklogo.png')))
        YUlogo_l = QPixmap(resource_path(os.path.join('assets','YorkU_logo_L.png')))
        self.label_logo_s.setPixmap(YUlogo_s.scaled(180,180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.label_logo_L.setPixmap(YUlogo_l.scaled(450,450, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


        self.label_appVersion.setText(f'v{self.appVersion} , {self.appDate}')
        
        self.update_time()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(60*1000) # Update every minute
        
        stdout = OutputWrapper(self, True)
        stdout.outputWritten.connect(self.handleOutput)
        stderr = OutputWrapper(self, False)
        stderr.outputWritten.connect(self.handleOutput)
        
        # -- Retrieving settings from previous session (from Windows registry)
        
        # reading bundled room settings
        self.room = self.setting_Course.value('room')
        self.pc_dir  = self.setting_Course.value('pc_dir')
        
        self.course_dir = self.setting_Course.value('course_dir')
        self.exp = self.setting_Course.value('exp')

        if self.pc_dir and os.path.isdir(self.pc_dir):
            self.lineEdit_pc_dir.setText(self.pc_dir)
            self.pc_csv_path = self.extract_pc_csv_path(self.pc_dir)

            if self.pc_csv_path:
                self.room_list = self.extract_rooms(self.pc_dir, self.pc_csv_path)
                
                if self.room:
                    if self.room in self.room_list.keys():
                        self.load_room_settings(self.room)
                        self.set_pc_txt_path()

        self.tabWidget.setCurrentIndex(0)

       
        '''
        
        if self.pc_dir and os.path.exists(self.pc_dir):
            self.lineEdit_pc_dir.setText(self.pc_dir)
            if self.room:
                if self.room in self.room_list.keys():
                    self.set_pc_txt_path()
        '''
        self.session_id = None
        self.thread={}
        self.LocalCopyMode = False
        self.isCopyFileRunning = False
        self.is_gpc_reboot_running = False
        self.is_laptop_reboot_running = False
        self.can_copy_htmlfiles = False
        
        self.lineEdit_TAname.setEnabled(False)
        self.overwite_ta_name = False
        self.ta_name = None
        self.layout_out = None
        self.pushButton_labLayout.setEnabled(False)
        #self.pushButton_att.setEnabled(False)
        self.pushButton_copyfiles.setEnabled(False)

        if self.comboBox_exp_id.currentText() == '':
            self.pushButton_Watt.setEnabled(False)
        
        #if self.comboBox_session.currentText() != '' and self.comboBox_exp_id.currentText() != '':
        #    self.pushButton_att.setEnabled(True)
        
        self.checkBox_extended_att.setChecked(self.extended_attlist_mode)
        self.checkBox_blankAtt.setChecked(self.blankAtt_mode)
        self.checkBox_small_scr.setChecked(self.small_screen_mode)

        #-- progress bars ---
        self.copy_pbar = QProgressBar()
        self.copy_pbar.setTextVisible(True)
        
        self.gpc_reboot_pbar = QProgressBar()
        self.gpc_reboot_pbar.setTextVisible(True)
        
        self.pc_reboot_pbar = QProgressBar()
        self.pc_reboot_pbar.setTextVisible(True)
        
        self.copy_pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gpc_reboot_pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pc_reboot_pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.statusBar().addPermanentWidget(self.copy_pbar,1)
        self.statusBar().addPermanentWidget(self.gpc_reboot_pbar,1)
        self.statusBar().addPermanentWidget(self.pc_reboot_pbar,1)
        
        self.copy_pbar.hide()
        self.gpc_reboot_pbar.hide()
        self.pc_reboot_pbar.hide()
        
        #-- setting pushbutton icons
        icon_save = self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_DialogSaveButton'))
        icon_reboot = self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_BrowserReload'))
        icon_brows = self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_DirOpenIcon'))
        icon_file = self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_FileIcon'))
        icon_lab_scheduler = self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_FileDialogListView'))
        icon_weekly_att = self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_FileDialogDetailedView'))
        # icon_session_att = self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_FileDialogContentsView'))
        
        self.pushButton_save_settings.setIcon(icon_save)
        self.pushButton_course_dir_browse.setIcon(icon_brows)
        self.pushButton_pc_browse.setIcon(icon_brows)
        self.pushButton_rebootPCs.setIcon(icon_reboot)
        self.pushButton_rebootLaptops.setIcon(icon_reboot)
        self.pushButton_lpc_remote_files.setIcon(icon_file)
        self.pushButton_attEdit.setIcon(icon_weekly_att)
        self.pushButton_labScheduler.setIcon(icon_lab_scheduler)
        self.pushButton_Watt.setIcon(icon_weekly_att)
        #self.pushButton_att.setIcon(icon_session_att)

        #--signal and slots
        #self.pushButton_update_check.clicked.connect(self.check_for_update)
        self.pushButton_update_check.clicked.connect(self.check_for_update_2)
        self.pushButton_save_settings.clicked.connect(self.save_button_click)
        self.pushButton_grouping_htmlgen.clicked.connect(self.generate_groups_html_combined)
        self.comboBox_exp_id.activated.connect(self.set_exp_id)
        #self.comboBox_exp_id.currentIndexChanged.connect(self.check_comboboxes)
        self.comboBox_session.activated.connect(self.set_session_id)
        #self.comboBox_session.currentIndexChanged.connect(self.check_comboboxes)
        self.comboBox_room.activated.connect(self.room_selector)

        self.pushButton_copyfiles.clicked.connect(self.start_copyfiles_worker)
        self.pushButton_rebootPCs.clicked.connect(self.start_gpc_reboot_worker)
        self.pushButton_rebootLaptops.clicked.connect(self.start_laptop_reboot_worker)
        self.pushButton_lpc_remote_files.clicked.connect(self.open_lpc_file_manager)
        self.pushButton_lpc_remote_files.setToolTip("Copy/Delete files to/from laptops")

        self.pushButton_attEdit.clicked.connect(self.open_att_editor)
        self.pushButton_labScheduler.clicked.connect(self.open_lab_scheduler)
        self.pushButton_labScheduler.setToolTip("Creates lab schedule csv file, to import in outlook calendar")

        if not self.room:
            self.pushButton_lpc_remote_files.setEnabled(False)
        
        if not self.course_dir:
            self.pushButton_attEdit.setEnabled(False)
            self.pushButton_labScheduler.setEnabled(False)

        if not self.exp:
            self.pushButton_Watt.setEnabled(False)

        self.pushButton_course_dir_browse.clicked.connect(self.browse_course_dir)
        self.pushButton_pc_browse.clicked.connect(self.browse_pc_dir)
        self.checkBox_debugMode.toggled.connect(self.set_debug_mode)
        self.checkBox_localCopy.toggled.connect(self.set_copy_mode)
        self.checkBox_extended_att.toggled.connect(self.set_attlist_mode)
        self.checkBox_blankAtt.toggled.connect(self.set_blankAtt_mode)
        self.checkBox_small_scr.toggled.connect(self.set_screen_mode)
        self.checkBox_TAname_overwrite.toggled.connect(self.set_ta_name_mode)
        self.pushButton_labLayout.clicked.connect(self.show_lab_layout)
        #self.pushButton_att.clicked.connect(self.show_attendance)
        self.pushButton_Watt.clicked.connect(self.generate_weekly_att)
    #--------------------------------------------------------------------------------   
    def update_time(self):
        now = QDateTime.currentDateTime()
        formatted_time = now.toString("<b>ddd h:mm AP, MMM d, yyyy</b>")
        self.label_time.setText(formatted_time)
        self.label_time.setStyleSheet("color: blue; font-size: 12pt;")
    #--------------------------------------------------------------------------------
    def set_default_room_settings(self):
        room_setting = {}
        
        # Default year/semester set according to today's date
        room_setting['year'] = str(QDate.currentDate().year())
        
        match QDate.currentDate().month():
            case 1 | 2 | 3 | 4:
                room_setting['semester'] = 'Winter'
            case 5 | 6 | 7 | 8:
                room_setting['semester'] = 'Summer'
            case _:
                room_setting['semester'] = 'Fall'
        
        room_setting['code'] = 'xxxx'
        room_setting['course_dir'] = None
        room_setting['exp_id'] = 1
        room_setting['exp'] = None
        room_setting['n_max_group'] = 6
        room_setting['n_benches'] = 4
        room_setting['extended_attlist_mode'] = False
        room_setting['blankAtt_mode'] = False
        room_setting['small_screen_mode'] = False
        room_setting['att_column'] = {}
        room_setting['customized_att'] = False
        
        return room_setting
    
    def set_course_code_textbox(self, stud_csv_path):
        # Uses stud csv filename to get course code 
        filename_extract = os.path.basename(stud_csv_path)
        course_code_extract = filename_extract[-9:-5]
        if course_code_extract.isdigit():
            self.code = course_code_extract
            self.lineEdit_code.setText(self.code)
    
    def load_room_settings(self, room):
        # Load the room setting dictionary
        self.room_setting_dict = self.setting_Course.value('room_setting_dict')
        logging.debug(f'room_setting_dict: {self.room_setting_dict}')

        if self.room_setting_dict is None:
            logging.debug('No room setting dictionary found. Creating new dictionary with default settings.')
            self.room_setting_dict = {}
            room_setting = self.set_default_room_settings()
            self.room_setting_dict[room] = room_setting

        else:
            room_setting = self.room_setting_dict.get(room, {})
            if room_setting is None:
                logging.info('No setting found for the selected room. Set default settings.')
                room_setting = self.set_default_room_settings()
            
        self.year = room_setting.get('year')
        self.semester = room_setting.get('semester')
        self.code = room_setting.get('code', 'xxxx')
        self.course_dir = room_setting.get('course_dir', None)
        logging.debug(f'course_dir: {self.course_dir}')
        self.exp_id = room_setting.get('exp_id', 1)
        self.exp = room_setting.get('exp', None)
        self.n_max_group = room_setting.get('n_max_group', 6)
        self.n_benches = room_setting.get('n_benches', 4)
        
        self.extended_attlist_mode = room_setting.get('extended_attlist_mode', False)
        self.blankAtt_mode = room_setting.get('blankAtt_mode', False)
        self.att_column = room_setting.get('att_column', {})

        self.small_screen_mode = room_setting.get('small_screen_mode', False)
        self.customized_att = room_setting.get('customized_att', False)

        # load the setting into the GUI, selected year and semester changes if not matching current date
        today_settings = self.set_default_room_settings()
        if self.room_setting_dict.get('year') != QDate.currentDate().year() or self.room_setting_dict.get('semester') != today_settings.get('semester'):
            self.lineEdit_year.setText(str(QDate.currentDate().year()))
            
            match QDate.currentDate().month():
                case 1 | 2 | 3 | 4:
                    index = self.comboBox_semester.findText('Winter', Qt.MatchExactly)
                    self.comboBox_semester.setCurrentIndex(index)
                case 5 | 6 | 7 | 8:
                    index = self.comboBox_semester.findText('Summer', Qt.MatchExactly)
                    self.comboBox_semester.setCurrentIndex(index)
                case _:
                    index = self.comboBox_semester.findText('Fall', Qt.MatchExactly)
                    self.comboBox_semester.setCurrentIndex(index)
            
        else:
            self.lineEdit_year.setText(self.year)
            index = self.comboBox_semester.findText(self.semester, Qt.MatchExactly)
            self.comboBox_semester.setCurrentIndex(index)
            
        self.lineEdit_code.setText(self.code)

        self.checkBox_extended_att.setChecked(self.extended_attlist_mode)
        self.checkBox_blankAtt.setChecked(self.blankAtt_mode)
        self.checkBox_small_scr.setChecked(self.small_screen_mode)

        if not self.exp:
            self.comboBox_exp_id.clear()
            self.pushButton_Watt.setEnabled(False)
        else:
            self.pushButton_Watt.setEnabled(True)

        self.css_file = 'style_large.css' if not self.small_screen_mode else 'style_small.css'
        self.css_file_all = 'style_all.css'

        if self.course_dir and os.path.isdir(self.course_dir):
            self.lineEdit_course_dir.setText(self.course_dir)
            self.exp_csv_path, self.stud_csv_path_list, self.time_csv_path = self.extract_course_csv_paths(self.course_dir)
            
            # If course code is set to default value, pulls it from csv onto GUI
            if self.code == 'xxxx':
                self.set_course_code_textbox(self.stud_csv_path_list[0])
            
            if self.time_csv_path:
                self.session_list = self.extract_sessions(self.time_csv_path)
                # Load current lab config dictionary
                lab_config = self.setting_Course.value('current_lab_config')
                if lab_config:
                    prev_session = lab_config.get('session')
                    # Set current index of session combobox as the next session in the list
                    #Does not currently work as intended: Needs to also update session_id appropriately
                    #eg ['LAB 01_1','T'] for LAB01 on Tuesday from the first course section
                    index = self.comboBox_session.findText(prev_session, Qt.MatchExactly)
                    index += 1
                    self.comboBox_session.setCurrentIndex(index)
                else:
                    #Initialise to a default lab config
                    default_lab_config = {'room':'Room', 'code':'XXXX', 'exp':'Exp', 'session':'Session'}
                    self.setting_Course.setValue('current_lab_config', default_lab_config)
                    
            if self.exp_csv_path:
                self.exp_list, self.location_list = self.extract_exp(self.exp_csv_path)
                
                    
        else:
            self.lineEdit_course_dir.clear()
            self.pushButton_attEdit.setEnabled(False)
            self.pushButton_labScheduler.setEnabled(False)
            
        self.lineEdit_ngroups.setText(str(self.n_max_group))
        self.lineEdit_nbenches.setText(str(self.n_benches))
        self.comboBox_exp_id.setCurrentText(self.exp)

        if self.room:
            self.comboBox_room.setCurrentText(self.room)
        self.update_current_lab_config_ui()

    #--------------------------------------------------------------------------------        
    #def check_comboboxes(self):
    #    if self.comboBox_exp_id.currentText() != '' and self.comboBox_session.currentText() != '':
    #        self.pushButton_att.setEnabled(True)
    
    def generate_weekly_att(self):
        pdf_file_path = seating.create_weekly_att(user_data_dir, self.stud_csv_path_list, self.session_list, self.code, self.exp_id, self.exp, self.extended_attlist_mode, self.blankAtt_mode, self.att_column, self.customized_att, self.n_max_group*self.n_benches)
        
        # Check if the file exists
        if pdf_file_path and os.path.isfile(pdf_file_path):
            # Open the PDF file with the default PDF viewer
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_file_path))
        else:
            # Handle the case where the file doesn't exist
            logging.error("PDF file not found: %s", pdf_file_path)

    def show_attendance(self):
        self.att = AttWindow(self.stud_csv_path_list, self.session, self.session_id[0], self.code, self.exp_id)
        self.att.setWindowTitle('Print attendance list')
        self.att.show()

    def show_lab_layout(self):
        # Populating layout image:
        if self.course_dir:
            self.lab_layout_out_file = seating.print_on_layout(user_data_dir, self.gpc_map, self.room, self.room_list, self.exp_id, self.pkl_path)
            logging.debug(f'self.lab_layout_out_file: {self.lab_layout_out_file}')
            
            if os.path.isfile(self.lab_layout_out_file):
                self.lablayout = LabLayoutWindow_new(self.lab_layout_out_file)
                self.lablayout.showMaximized()
            else:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("Cannot generate lab_layout file!")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
        else:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("Course main directory not found. Please select the main directory from the setting tab first.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
        
    def browse_course_dir(self):
        '''
        open dialog box to browse for source dir and return the paths for exp, stud(s) and time csv files.
        '''
        self.course_dir = QFileDialog.getExistingDirectory(self, "Select the main course directory", directory=self.course_dir)
        
        
        if self.course_dir:
            self.lineEdit_course_dir.setText(self.course_dir)
            self.exp_csv_path, self.stud_csv_path_list, self.time_csv_path = self.extract_course_csv_paths(self.course_dir)
            self.session_list = []
            self.exp_list = []
            self.comboBox_session.clear()
            self.comboBox_exp_id.clear()

            if not self.exp_csv_path:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("No exp_*.csv found in the course directory.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
            if not self.stud_csv_path_list:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("No stud_*.csv found in the course directory.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
            if not self.time_csv_path:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("No time_*.csv found in the course directory.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
            else:
                self.session_list = self.extract_sessions(self.time_csv_path)
                self.exp_list, self.location_list = self.extract_exp(self.exp_csv_path)

                self.pushButton_attEdit.setEnabled(True)
                self.pushButton_labScheduler.setEnabled(True)
            
            # Updates course code on GUI automatically 
            self.set_course_code_textbox(self.stud_csv_path_list[0])
                
    
    def extract_course_csv_paths(self, course_dir):
        exp_csv_path, time_csv_path = None, None
        stud_csv_path_list = []
        for filename in os.listdir(course_dir):
            if filename.endswith(".csv"):
                if 'time' in filename:
                    time_csv_path= os.path.join(course_dir, filename)
                    
                elif 'exp' in filename:
                    exp_csv_path= os.path.join(course_dir, filename)
                #there might be multiple stud csv files
                elif 'stud' in filename:
                    stud_csv_path_list.append(os.path.join(course_dir, filename))
        return exp_csv_path, stud_csv_path_list, time_csv_path
    
    def extract_pc_csv_path(self, pc_dir):
        pc_csv_path= None
        for filename in os.listdir(pc_dir):
            if filename.endswith(".csv"):
                if 'pc' in filename:
                    pc_csv_path= os.path.join(pc_dir, filename)
                    
        return pc_csv_path
                  
    def browse_pc_dir(self):
        '''
        open dialog box to browse for source dir and return the paths for exp, stud(s) and time csv files.
        '''  
        self.pc_dir = QFileDialog.getExistingDirectory(self, "Select the pc lists directory", directory=self.pc_dir)  
        
        if self.pc_dir:
            self.lineEdit_pc_dir.setText(self.pc_dir)
            self.pc_csv_path = self.extract_pc_csv_path(self.pc_dir)
            self.room_list = []
            self.comboBox_room.clear()

            if not self.pc_csv_path:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("No pc_*.csv found in this directory.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
            else:
                logging.debug(f'--pc_csv_path:{self.pc_csv_path}')
                self.room_list = self.extract_rooms(self.pc_dir, self.pc_csv_path)
        
    def sort_helper(self, item):
            day_sort = {'Mon':1,'Tue':2,'Wed':3,'Thu':4,'Fri':5}
            time = item.split(",")[1].strip()
            time = int(time.split(":")[0])
            return (day_sort[item[:3]], time)

    def extract_rooms(self, pc_dir, pc_csv_path):
        room_list = seating.get_room_list(pc_dir ,pc_csv_path)
        self.comboBox_room.clear()
        if room_list:
            self.comboBox_room.addItems(room_list.keys())
            logging.debug(f'---rooms loaded:{room_list.keys()}')
            self.comboBox_room.setCurrentIndex(-1)
        
        return room_list
    
    def extract_sessions(self, time_csv_path):
        session_list = seating.get_session_list(time_csv_path)
        self.comboBox_session.clear()

        if session_list:
            list_helper = sorted(list(session_list.keys()), key=self.sort_helper)
            
            self.comboBox_session.addItems(list_helper)
            logging.debug(f'---sessions loaded:{list_helper}')
        
        return session_list

    def extract_exp(self, exp_csv_path):
        exp_list, location_list = seating.get_exp_list(exp_csv_path)
        self.comboBox_exp_id.clear()

        if exp_list:
            list_helper = list(exp_list.keys())
            
            self.comboBox_exp_id.addItems(list_helper)
            logging.debug(f'---exps loaded:{list_helper}')
            self.comboBox_exp_id.setCurrentIndex(-1)
        
        return exp_list, location_list

    def set_debug_mode(self):
        debug_mode = self.checkBox_debugMode.isChecked()
        if debug_mode:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
    
    def set_copy_mode(self):
        self.LocalCopyMode = self.checkBox_localCopy.isChecked()
    
    def set_attlist_mode(self):
        self.extended_attlist_mode = self.checkBox_extended_att.isChecked()
    
    def set_blankAtt_mode(self):
        self.blankAtt_mode = self.checkBox_blankAtt.isChecked()
    
    def set_screen_mode(self):
        self.small_screen_mode = self.checkBox_small_scr.isChecked()
        self.css_file = 'style_large.css' if not self.small_screen_mode else 'style_small.css'
        logging.debug(f'--self.css_file:{self.css_file}')
    
    def set_ta_name_mode(self):
        self.overwite_ta_name = self.checkBox_TAname_overwrite.isChecked()
        if self.overwite_ta_name:
            self.lineEdit_TAname.setEnabled(True)
        else:
            self.lineEdit_TAname.setEnabled(False)

    def LoadSettingValues(self):
        r'''
        # Load the last user setting from previous session (stored in Windows registry)
        CurrentUser\Software\YorkLabSeating\Course
        '''
        self.setting_Course = QSettings('YorkLabSeating', 'Course')
    
    def save_button_click(self):
        '''
        # Save the user setting values with pressing in SAVE button
        '''
        self.year       = self.lineEdit_year.text() 
        self.semester   = self.comboBox_semester.currentText()
        self.code       = self.lineEdit_code.text() 
        self.n_max_group    = int(self.lineEdit_ngroups.text())
        self.n_benches    = int(self.lineEdit_nbenches.text())
        
        self.save_settings()
        self.update_current_lab_config_ui()

        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Inof.")
        dlg.setText("Settings saved")
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Information)
        dlg.exec()
    
    def set_pklfile_name(self):
        pklfile_name_list = ['SeatingDB', self.semester, self.year, self.code, self.session_id[0].replace(" ", "")]
        pklfile_name = '_'.join(pklfile_name_list)+'.pkl'
        logging.debug(f'pklfile_name:{pklfile_name}')
        return pklfile_name

    def set_exp_id(self):
        self.exp = self.comboBox_exp_id.currentText()
        if self.exp:
            self.exp_id = self.exp_list[self.exp]
            logging.info(f' Selected exp_id:{self.exp_id}')
            self.pushButton_Watt.setEnabled(True)
            if self.can_copy_htmlfiles:
                self.pushButton_copyfiles.setEnabled(True)
        else:
            self.pushButton_Watt.setEnabled(False)

    def set_session_id(self):
        self.session = self.comboBox_session.currentText()
        
        if self.session:
            self.session_id = self.session_list[self.session]
            logging.info(f' Selected session_id:{self.session_id}')
            logging.debug(f' self.session:{self.session}')
    
    def set_pc_txt_path(self):
        logging.debug(f'---self.room:{self.room}')
        self.pc_txt_path = self.room_list.get(self.room,[None])[0]
        logging.info(f' Selected room:{self.room}')
        logging.debug(f'--pc_txt_path:{self.pc_txt_path}')
        if self.pc_txt_path:
            if os.path.isfile(self.pc_txt_path):
                self.gpc_list, self.laptop_list, self.gpc_map =gpc.extract_pc_list(self.pc_txt_path)
        
        self.pushButton_lpc_remote_files.setEnabled(True)
        self.location_label.setText(f'{self.room}')
    
    def room_selector(self):
        self.session_id = None
        self.session_list = []
        self.exp_list = []
        self.comboBox_session.clear()
        self.comboBox_exp_id.clear()
        
        self.room = self.comboBox_room.currentText()
        
        if self.room:
            self.set_pc_txt_path()
            self.load_room_settings(self.room)
    
            
    def show_lab_configs(self):
        """
        Reads and displays the lab_config.txt contents from the first Group PC (GR1)
        of every lab room in the selected PC lists directory.
        - Leya (7/11/25)
        
        Returns:
            None
        """
    
        # Ensure PC lists directory has been selected
        if not hasattr(self, 'pc_dir') or not self.pc_dir:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("No PC lists directory selected. Please select one first.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return
    
        # Get CSV path for pc_room_map.csv
        self.pc_csv_path = self.extract_pc_csv_path(self.pc_dir)
        if not self.pc_csv_path or not os.path.exists(self.pc_csv_path):
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("No valid pc_*.csv found in this directory.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return
    
        # Step 1: Call get_room_list() to get the gpc txt file paths for each room stored in a dict
        rooms = seating.get_room_list(self.pc_dir, self.pc_csv_path)
        if not rooms:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("No room data found in the PC lists directory.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return
        
        # Step 2: Iterate over all room keys, get the file path to the GPCs txt file and store it in a new list
        gpc_paths_filepath = []
        for room in rooms:
            gpc_paths_filepath.append(rooms[room][0])
            
        # Step 3: With txt file paths for all rooms available in this new list, iterate over them, extract pc paths and other unnecessary vals to to local vars
        config_strings = []
        for room_path in gpc_paths_filepath:
            room_gpc_list, room_laptop_list, room_gpc_map = gpc.extract_pc_list(room_path)
            
            # Step 4: Take only the GPC 1 name from the GPC list, then read lab_config.txt from it
            gpc_1_name = room_gpc_list[0]
            remote = Remote_GPC_manager()
            lab_config_text = remote.read_lab_config(gpc_1_name)
            config_strings.append(lab_config_text)
        
        # Show all lab config text obtained by clicking on a button in the ui - TO BE IMPLEMENTED
            
            

    def generate_groups(self):
        """
        Generates lab groups pkl file only if session, student list is selected, and there are enough groups for all students.

        Returns:
            bool
            Returns True if groups successfully made, otherwise returns False.
            
        """
        if self.session_id is None:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("Please select a <b>session</b> before generating groups.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return False
        else:
            logging.debug(f'selected session_id:{self.session_id}.')
            if not self.stud_csv_path_list:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("Please select a student list from the settings tab and save, before generating groups.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return False
            else: 
                n_stud = seating.get_number_of_students(self.stud_csv_path_list, self.session_id[0])
                logging.debug(f' There are {n_stud} students enrolled in this session.')
        
        if n_stud == 0:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("No student found in the selected session.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return False

        if n_stud > self.n_benches * self.n_max_group:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"There are <b>not enough seats for {n_stud} students in {self.n_max_group} groups</b>. Either increase the number of groups or the number of seats per group and try again.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return False
        else:
            if not self.exp_csv_path:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("Make sure exp_* (experiments list) exists in the main course directory.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return False
            else:
                self.pkl_file_name   = self.set_pklfile_name()
                self.pkl_path, self.n_group = seating.make_groups(user_data_dir, self.exp_csv_path, self.stud_csv_path_list, self.time_csv_path, self.session_id, n_stud, self.n_benches, self.code, self.pkl_file_name )
                if self.pkl_path:
                    # Removed unnecessary pop-up and replaced with console log, pop-ups are reserved for errors - Leya, 06/10/25
                    logging.info(f" <b>{n_stud} enrolled students</b> in this session are assigned into <b>{self.n_group} groups</b>.")
                    self.pushButton_labLayout.setEnabled(True)
                    return True
                else:
                    dlg = QtWidgets.QMessageBox(self)
                    dlg.setWindowTitle("Error")
                    dlg.setText("Experiment list and/or Student list appear to be empty. If this is not the case, check the csv headers.")
                    dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                    dlg.exec()
                    return False
            
    def generate_html(self):
        """
        If a pkl file already exists, generates html files for groups

        Returns 
            None.

        """
        if self.pkl_path:
            if os.path.exists(self.pkl_path):
                logging.debug(f'self.pkl_path: {self.pkl_path}')
                
                if self.overwite_ta_name:
                    self.ta_name = self.lineEdit_TAname.text()
                else: self.ta_name = None
                
                self.lab_layout_out_file = seating.print_on_layout(user_data_dir, self.gpc_map, self.room, self.room_list, self.exp_id, self.pkl_path)
                html_dir = seating.html_generator(user_data_dir, self.pkl_path, self.code, self.n_max_group, self.n_benches, self.appVersion, self.css_file, self.css_file_all, self.ta_name)
                if html_dir:
                    self.can_copy_htmlfiles = True
                    if self.comboBox_exp_id.currentText() != '':
                        self.pushButton_copyfiles.setEnabled(True)

            else:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("pkl file not found. Run Grouping first to generate it.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
        else:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("pkl file not found. Run Grouping first to generate it.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                
    def generate_groups_html_combined(self):
        """
        Calls generate_html() only if generate_groups() returns True.

        Returns:
            None.
            
        - Leya, 07/07/25   
        """
        if self.generate_groups():
            self.generate_html()
           

    def start_copyfiles_worker(self):
        if self.gpc_list and self.course_dir:
            self.copy_pbar.show()
            self.copy_pbar.setFormat("Copy files ...")
            self.save_current_lab_config_txt()

            self.thread[1] = CopyFileThread(self.exp_id, self.gpc_list, self.gpc_map, self.course_dir, self.code, localCopy = self.LocalCopyMode, lab_config_txt=self.current_lab_config_txt, parent=None)
            self.thread[1].finished.connect(self.on_copyFinished)
            self.thread[1].start()
            self.pushButton_copyfiles.setEnabled(False)
            self.comboBox_exp_id.setEnabled(False)
            self.pushButton_grouping_htmlgen.setEnabled(False)
            self.pushButton_rebootPCs.setEnabled(False)
            self.isCopyFileRunning = True
            self.thread[1].progress.connect(self.copy_setProgress)
        
        elif not self.gpc_list and self.course_dir:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("No Group PC name found in Group PC list. Check the input txt file")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return
        elif not self.course_dir:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("Select the main course directory from setting tab.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return
    
    def copy_setProgress(self, copy_progress):
        self.copy_pbar.setValue(copy_progress)

    def on_copyFinished(self):
        self.copy_pbar.setFormat("Copy completed")
        self.save_current_lab_config()
        self.update_current_lab_config_ui()
        self.pushButton_copyfiles.setEnabled(True)
        self.comboBox_exp_id.setEnabled(True)
        self.pushButton_grouping_htmlgen.setEnabled(True)
        self.pushButton_rebootPCs.setEnabled(True)
        self.isCopyFileRunning = False
    
    #----------------- Reboot thread
    def start_gpc_reboot_worker(self):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Warning")
        dlg.setText("Are you sure you want to Reboot all Group Computers?")
        dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        button = dlg.exec()
        if button == QtWidgets.QMessageBox.StandardButton.Yes:
            if self.gpc_list:
                self.gpc_reboot_pbar.show()
                #self.gpc_reboot_pbar.setFormat("Rebooting Group PCs ...")
                self.thread[2] = Reboot_PC_Thread(self.gpc_list, self.gpc_reboot_pbar, self.n_max_group, _type='gpc', parent=None)
                self.thread[2].finished.connect(self.on_gpc_rebootFinished)
                self.thread[2].start()
                
                self.pushButton_rebootPCs.setEnabled(False)
                self.is_gpc_reboot_running = True
                self.thread[2].progress.connect(self.gpc_reboot_setProgress)
            else:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("No Group PC name found in Group PC list. Check the input txt file")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
    def gpc_reboot_setProgress(self, gpc_progress):
        self.gpc_reboot_pbar.setValue(gpc_progress)

    def on_gpc_rebootFinished(self):
        self.pushButton_rebootPCs.setEnabled(True)
        self.is_gpc_reboot_running = False
        self.gpc_reboot_pbar.setFormat("Group PCs rebooted")
    
    def start_laptop_reboot_worker(self):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Warning")
        dlg.setText("<b>WARNING!</b>  Are you sure you want to Reboot all Laptops? Students may lose their unsaved work!")
        dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        button = dlg.exec()
        if button == QtWidgets.QMessageBox.StandardButton.Yes:
            if self.laptop_list:
                self.pc_reboot_pbar.show()
                #self.pc_reboot_pbar.setFormat(f"Rebooting Laptop {}")
                self.thread[3] = Reboot_PC_Thread(self.laptop_list, self.pc_reboot_pbar, self.n_max_group, _type='lpc', parent=None)
                self.thread[3].finished.connect(self.on_laptop_rebootFinished)
                self.thread[3].start()
                
                self.pushButton_rebootLaptops.setEnabled(False)
                self.is_laptop_reboot_running = True
                self.thread[3].progress.connect(self.pc_reboot_setProgress)
            else:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("No Laptop found in laptop list. Check the input txt file")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
    
    def open_lpc_file_manager(self):
        self.lpc_remote = lpc_file_manager(self.laptop_list, self.LocalCopyMode)
        self.lpc_remote.setWindowTitle('Laptops Remote File/Dir Manager')
        self.lpc_remote.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.lpc_remote.show()
    
    def open_lab_scheduler(self):
        if self.location_list:
            self.lab_scheduler = lab_scheduler_manager(self.exp_list, self.time_csv_path, self.room, self.code, self.location_list)
            self.lab_scheduler.setWindowTitle('Lab Scheduler')
            self.lab_scheduler.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.lab_scheduler.show()
        else:
            QMessageBox.critical(self, "Error", "Cannot generate Lab schedule. No 'location' is listed in exp_*.csv file.")
            return None

    def open_att_editor(self):
        self.att_editor = att_editor_manager(self.code, self.exp_list , self.customized_att, self.att_column)
        self.att_editor.column_details_updated.connect(self.updateColumnDetails)  # Connect the signal
        self.att_editor.customizedAttChanged.connect(self.updateCustomizedAtt)  # Connect signal to slot
        self.att_editor.setWindowTitle('Attendence Sheet Editor')
        self.att_editor.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.att_editor.show()
    
    def updateColumnDetails(self, updated_details):
        self.att_column = updated_details
    
    def updateCustomizedAtt(self, new_value):
        self.customized_att = new_value
        
    def update_current_lab_config_ui(self):
        """
        Updates the main tab UI with the current lab configuration by pulling saved data from QSettings

        Returns: None

        """
        lab_config = self.setting_Course.value('current_lab_config')
        if lab_config:
            code = lab_config.get('code')
            self.course_label.setText(f'PHYS {code}')
            # self.course_label.setFont(QFont('Arial', 12, weight=700))
            room = lab_config.get('room')
            self.location_label.setText(f'{room}')
            # self.location_label.setFont(QFont('Arial', 12, weight=700))
            session = lab_config.get('session')
            self.session_label.setText(f'{session}')
            # self.session_label.setFont(QFont('Arial', 12, weight=700))
            exp_id = lab_config.get('exp')[0]
            self.exp_label.setText(f'Exp {exp_id}')
            # self.exp_label.setFont(QFont('Arial', 12, weight=700))

    def pc_reboot_setProgress(self, pc_progress):
        self.pc_reboot_pbar.setValue(pc_progress)

    def on_laptop_rebootFinished(self):
        self.pushButton_rebootLaptops.setEnabled(True)
        self.is_laptop_reboot_running = False
        self.pc_reboot_pbar.setFormat("Laptops rebooted")
        res = [key for key, value in self.thread[3].status.items() if not value]
        if res:
            error_message = f'Failed to send reboot command to: {", ".join(res)}'
        else:
            error_message = "Failed to send reboot command to All laptops!."
            
        QMessageBox.warning(None, "Laptops Reboot Failed", error_message)

    #----------------------------------
    def handleOutput(self, text, stdout):
        color = self.statusbox.textColor()
        self.statusbox.setTextColor(color)
        self.statusbox.setOpenExternalLinks(True)
        self.statusbox.append(text)
        self.statusbox.setTextColor(color)
    
    #--------------------------------------------------------------------------------
    def save_settings(self):
        """
        Save the current settings to the system.

        This method saves the current settings to the system using the QSettings object.

        Returns:
            None
        """
        #--- store the current setting in the system before closing the app
        #self.setting_Course.setValue('year', self.lineEdit_year.text() )
        #self.setting_Course.setValue('semester', self.comboBox_semester.currentText())
        #self.setting_Course.setValue('code', self.lineEdit_code.text() )
        self.setting_Course.setValue('course_dir', self.course_dir )
        self.setting_Course.setValue('pc_dir', self.pc_dir )
        #self.setting_Course.setValue('exp_id', int(self.exp_id))
        self.setting_Course.setValue('exp', self.comboBox_exp_id.currentText())
        self.setting_Course.setValue('room', self.comboBox_room.currentText())
        #self.setting_Course.setValue('n_max_group', int(self.lineEdit_ngroups.text()) )
        #self.setting_Course.setValue('n_benches', int(self.lineEdit_nbenches.text()))
        #self.setting_Course.setValue('extended_attlist_mode', self.checkBox_extended_att.isChecked())
        #self.setting_Course.setValue('small_screen_mode', self.checkBox_small_scr.isChecked())
        #self.setting_Course.setValue('customized_att', self.customized_att)

        # wrap the room setting in a dictionary: key = room name, value = {pc_list, laptop_list, gpc_map}
        room_setting = {}
        room_setting['year'] = self.lineEdit_year.text()
        room_setting['semester'] = self.comboBox_semester.currentText()
        room_setting['code'] = self.lineEdit_code.text()
        room_setting['course_dir'] = self.course_dir
        room_setting['exp_id'] = int(self.exp_id)
        room_setting['exp'] = self.comboBox_exp_id.currentText()
        room_setting['n_max_group'] = int(self.lineEdit_ngroups.text())
        room_setting['n_benches'] = int(self.lineEdit_nbenches.text())
        room_setting['extended_attlist_mode'] = self.checkBox_extended_att.isChecked()
        room_setting['blankAtt_mode'] = self.checkBox_blankAtt.isChecked()
        room_setting['att_column'] = self.att_column
        room_setting['small_screen_mode'] = self.checkBox_small_scr.isChecked()
        room_setting['customized_att'] = self.customized_att
        logging.debug(f'customized_att: {self.customized_att}')
            
        self.room_setting_dict[self.comboBox_room.currentText()] = room_setting
        self.setting_Course.setValue('room_setting_dict', self.room_setting_dict)
        
    def save_current_lab_config(self):
        """
        Saves the current lab configuration to the system using QSettings.

        Returns: None

        """
        # After copying files to pcs, save the current configuration of the lab pcs
        lab_config = {}
        lab_config['room'] = self.comboBox_room.currentText()
        lab_config['code'] = self.lineEdit_code.text()
        lab_config['exp'] = self.comboBox_exp_id.currentText()
        lab_config['session'] = self.comboBox_session.currentText()
        self.setting_Course.setValue('current_lab_config', lab_config)
        
    def save_current_lab_config_txt(self):
        """
        Creates a string of the current lab configuration. Will be used to
        check all rooms' current lab configuration.
        
        - Leya 24/10/25
        
        Returns: None.

        """
        self.current_lab_config_txt = self.comboBox_room.currentText() + " - PHYS" + self.lineEdit_code.text() + " Session: " + self.comboBox_session.currentText() + " Exp " + self.comboBox_exp_id.currentText()
        

    #--------------------------------------------------------------------------------    
    def closeEvent(self, event):
        """
        Event handler for the close event of the application window.
        Asks the user for confirmation before closing the program.
        Stores the current settings in the system before closing.

        Args:
            event (QCloseEvent): The close event object.

        Returns:
            None
        """
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Warning")
        dlg.setText("Are you sure you want to close the program?")
        dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        button = dlg.exec()

        if button == QtWidgets.QMessageBox.StandardButton.Yes:
            
            self.save_settings()

            try:
                event.accept()
                logging.debug('The application exited normally.')
            except Exception as e:
                logging.error(f'The application exited with error: {e}')
            
        else:
            event.ignore()
    #--------------------------------------------------------------------------------
    
    def check_for_update(self):
        """
        Check for updates and download the latest version if available.

        This method fetches update information from a GitHub Pages URL and compares the latest version with the installed version.
        If a newer version is available, it prompts the user to download it to a selected location.

        Raises:
            Exception: If there is an error fetching update information or checking for updates.

        Returns:
            None
        """
        # GitHub Pages URL where your update_info.json is hosted
        update_info_url = "https://m-kareem.github.io/yorku-phys-lab-seating/assets/update_info.json"

        try:
            # Fetch update information from the GitHub Pages URL
            response = requests.get(update_info_url)
            update_info = response.json()

            # Extract version information from the JSON response
            latest_version = update_info.get('version')
            logging.debug(f'latest_version: {latest_version}')

            # Compare latest version with your installed version
            if version.parse(latest_version) > version.parse(self.appVersion):
                # Alert the user about the update
                reply = QMessageBox.question(
                    None,
                    "Update Available",
                    f"A new version ({latest_version}) is available. Do you want to download it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # Get the default Windows download folder
                    default_download_folder = os.path.join(os.path.expanduser("~"), "Downloads")

                    # Prompt user to select download location starting from the default download folder
                    file_dialog = QFileDialog()
                    file_dialog.setFileMode(QFileDialog.FileMode.Directory)
                    save_path = file_dialog.getExistingDirectory(None, "Select Download Location", default_download_folder)

                    if save_path:
                        # Download the file to the selected location
                        download_url = update_info.get('download_url')
                        if download_url:
                            response = requests.get(download_url)
                            file_name = download_url.split('/')[-1]
                            file_path = f"{save_path}/{file_name}"
                            with open(file_path, 'wb') as file:
                                file.write(response.content)
                            QMessageBox.information(
                                None, "Download Complete", f"File downloaded to: {file_path}"
                            )
            else:
                QMessageBox.information(None, "No Update", "YU LabManager is up to date.")

        except Exception as e:
            print(f"Error fetching update information: {e}")
            QMessageBox.critical(None, "Error", "Failed to check for updates.")



    def check_for_update_2(self):
        """
        Check for updates and download the latest version if available, with a progress bar.

        This method fetches update information from a GitHub Pages URL and compares the latest version with the installed version.
        If a newer version is available, it prompts the user to download it to a selected location while showing a download progress bar.

        Raises:
            Exception: If there is an error fetching update information or checking for updates.

        Returns:
            None
        """
        update_info_url = "https://m-kareem.github.io/yorku-phys-lab-seating/assets/update_info.json"

        try:
            response = requests.get(update_info_url)
            update_info = response.json()

            latest_version = update_info.get('version')
            logging.debug(f'latest_version: {latest_version}')

            if version.parse(latest_version) > version.parse(self.appVersion):
                reply = QMessageBox.question(
                    None,
                    "Update Available",
                    f"A new version ({latest_version}) is available. Do you want to download it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    default_download_folder = os.path.join(os.path.expanduser("~"), "Downloads")

                    file_dialog = QFileDialog()
                    file_dialog.setFileMode(QFileDialog.FileMode.Directory)
                    save_path = file_dialog.getExistingDirectory(None, "Select Download Location", default_download_folder)

                    if save_path:
                        download_url = update_info.get('download_url')
                        if download_url:
                            # Download with progress bar
                            with requests.get(download_url, stream=True) as r:
                                r.raise_for_status()
                                total_length = int(r.headers.get('content-length', 0))
                                chunk_size = 4096
                                num_bars = total_length // chunk_size

                                progress_dialog = QProgressDialog("Downloading in progress ...", "Cancel", 0, num_bars, None)
                                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                                progress_dialog.setWindowTitle("Downloading")
                                progress_dialog.setValue(0)

                                file_name = download_url.split('/')[-1]
                                file_path = f"{save_path}/{file_name}"

                                with open(file_path, 'wb') as f:
                                    for num, chunk in enumerate(r.iter_content(chunk_size=chunk_size)):
                                        if progress_dialog.wasCanceled():
                                            break
                                        f.write(chunk)
                                        progress_dialog.setValue(num)

                                if not progress_dialog.wasCanceled():
                                    QMessageBox.information(None, "Download Completed", f"File downloaded to: {file_path}")
                                else:
                                    os.remove(file_path)  # Remove partial file if canceled
            else:
                QMessageBox.information(None, "No Update", "Your application is up to date.")

        except Exception as e:
            print(f"Error fetching update information: {e}")
            QMessageBox.critical(None, "Error", "Failed to check for updates.")

#--------------------------------------------------------------------------------
class CopyFileThread(QThread):
    progress = Signal(int)
    
    def __init__(self, exp_id, gpc_list, gpc_map, course_dir, code, localCopy, lab_config_txt=None, parent=None ):
        super(CopyFileThread, self).__init__(parent)
        self.status = {}
        self.exp_id=exp_id
        self.gpc_list = gpc_list
        self.gpc_map = gpc_map
        self.course_dir = course_dir
        self.code = code
        self.localCopy = localCopy
        self.lab_config_txt = lab_config_txt
        self.is_running = True
        self.copy_service = Remote_GPC_manager(self.localCopy)
        
    def run(self):
        """
        Used in:
            class MainWindow
                start_copyfiles_worker()

        Returns
        -------
        None.

        """
        logging.info(f' Copying html files of Exp {self.exp_id} to Group PCs. Please wait ...')
        
        self.progress.emit(0)

        if self.localCopy:
            gpc = 'LOCAL PC'
            group_id = 0
            self.status[gpc] = self.copy_service.run_copyfile(user_data_dir,self.exp_id, gpc, group_id ,self.course_dir, self.code, self.lab_config_txt)
        else:
            for i, gpc in enumerate(self.gpc_list):
                group_id = int(self.gpc_map[gpc][3])
                self.status[gpc] = self.copy_service.run_copyfile(user_data_dir,self.exp_id, gpc, group_id ,self.course_dir, self.code, self.lab_config_txt)
                self.progress.emit(int(100*(i+1)/len(self.gpc_list)))
            
        if all(self.status.values()):
            logging.info(' html files are copied to target PC(s) successfully')
        else:
            res = [key for key, value in self.status.items() if not value]
            logging.error(f' Failed to copy html files to: {res}')

    def stop(self):
        self.is_running = False
        self.terminate()

#--------------------------------------------------------------------------------
class lpcCopyFileThread(QThread):
    """
    A thread class for copying files to laptops.

    Args:
        lpc_list (list): A list of laptops to copy files to.
        selected_files (list): A list of files to be copied.
        destination_path (str): The destination path on the laptops.
        localCopy (bool): Flag indicating whether to copy files to the local PC.
        parent (QObject): The parent object of the thread.

    Attributes:
        progress (Signal): A signal emitted to indicate the progress of the file copying.
        status (dict): A dictionary to store the status of each file copy operation.
        lpc_list (list): A list of laptops to copy files to.
        selected_files (list): A list of files to be copied.
        destination_path (str): The destination path on the laptops.
        localCopy (bool): Flag indicating whether to copy files to the local PC.
        is_running (bool): Flag indicating whether the thread is running.
        lpc_copy_service (Remote_LPC_manager): An instance of the Remote_LPC_manager class for file copying.

    Methods:
        run(): The main method of the thread that performs the file copying.
        stop(): Stops the execution of the thread.
    """

    progress = Signal(int)

    def __init__(self, lpc_list, selected_files, destination_path, localCopy, progress_bar, parent=None ):
        super(lpcCopyFileThread, self).__init__(parent)
        self.status = {}
        self.lpc_list = lpc_list
        self.selected_files = selected_files
        self.destination_path = destination_path
        self.localCopy = localCopy
        self.pbar = progress_bar
        self.is_running = True
        self.lpc_copy_service = Remote_LPC_manager(self.localCopy)
        
    def run(self):
        logging.info(' Copying selected file(s) to the laptops. Please wait ...')
        
        self.progress.emit(0)

        if self.localCopy:
            lpc = 'LOCAL PC'
            self.status[lpc] = self.lpc_copy_service.run_copyfile(lpc, self.selected_files, self.destination_path)
        else:
            for i, lpc in enumerate(self.lpc_list):
                self.pbar.setFormat(f"Copy files to {lpc.split('.')[0]} ")
                self.status[lpc] = self.lpc_copy_service.run_copyfile(lpc, self.selected_files, self.destination_path)
                self.progress.emit(int(100*(i+1)/len(self.lpc_list)))
                
            
        if all(self.status.values()):
            logging.info(' All selected files are copied to target Laptop(s) successfully')   
        else:
            res = [key for key, value in self.status.items() if not value]
            logging.error(f' Failed to copy the selected files to: {res}')

    def stop(self):
        self.is_running = False
        self.terminate()

#--------------------------------------------------------------------------------
class lpcDeleteThread(QThread):
    progress = Signal(int)

    def __init__(self, lpc_list, to_delete, destination_path, localCopy, progress_bar, parent=None ):
        super(lpcDeleteThread, self).__init__(parent)
        self.status = {}
        self.lpc_list = lpc_list
        self.to_delete = to_delete
        self.destination_path = destination_path
        self.localCopy = localCopy
        self.pbar = progress_bar
        self.is_running = True
        self.lpc_delete_service = Remote_LPC_manager(self.localCopy)
        
    def run(self):
        logging.info(' Deleting identified file(s) from the laptops. Please wait ...')
        
        self.progress.emit(0)
        
        for i, lpc in enumerate(self.lpc_list):
            self.pbar.setFormat(f"Delete files/dir from {lpc.split('.')[0]} ")
            self.status[lpc] = self.lpc_delete_service.run_delete(lpc, self.to_delete, self.destination_path)
            self.progress.emit(int(100*(i+1)/len(self.lpc_list)))
        if all(self.status.values()):
            logging.info(' Files/Dir are deleted from target Laptop(s) successfully')
        else:
            res = [key for key, value in self.status.items() if not value]
            logging.error(f' Failed to delete the identified files/dir from: {res}')

    def stop(self):
        self.is_running = False
        self.terminate()


#--------------------------------------------------------------------------------
class Reboot_PC_Thread(QThread):
    progress = Signal(int)

    def __init__(self, pc_list, progress_bar, n_max_pc, _type, parent=None ):
        super(Reboot_PC_Thread, self).__init__(parent)
        self.status = {}
        self.pc_list = pc_list
        self.is_running = True
        self.pbar = progress_bar
        self.n_max_pc= n_max_pc
        self._type = _type
        self.reboot_service = Remote_PC_Reboot()
        
        
    def run(self):
        logging.info(' Rebooting PCs. Please wait ...')
        self.progress.emit(0)

        for i, pc in enumerate(self.pc_list):
            if self._type=='gpc':
                if i< self.n_max_pc: # this is to avoid rebooting PCs other than the group PCs assigned to the course
                    self.pbar.setFormat(f"Rebooting -- {pc.split('.')[0]}")
                    self.status[pc] = self.reboot_service.reboot_Pc(pc)
                    self.progress.emit(int(100*(i+1)/self.n_max_pc))
            else:
                self.pbar.setFormat(f"Rebooting -- {pc.split('.')[0]}")
                self.status[pc] = self.reboot_service.reboot_Pc(pc)
                self.progress.emit(int(100*(i+1)/len(self.pc_list)))
        
        if all(self.status.values()):
            logging.info(' All PCs rebooted successfully')
        else:
            res = [key for key, value in self.status.items() if not value]
            logging.error(f' Failed to send reboot command to: {res}')

    def stop(self):
        self.is_running = False
        self.terminate()


#-------------------------------------------------
if __name__ == '__main__':
    
    def show_main_window(app):
        with open(resource_path(os.path.join('assets', 'update_info.json'))) as json_file:
            data = json.load(json_file)
            appVersion = data["version"]
            appDate = data["date"]
        
        mainWindow = MainWindow(appVersion,appDate)
        mainWindow.setWindowTitle(f'YU LabManager - v{appVersion}')
        mainWindow.show()
        splash.finish(mainWindow)
        logging.getLogger().setLevel(logging.INFO)
    
    app = QApplication(sys.argv)
    app_icon = QIcon(resource_path("YorkU_icon.ico"))
    app.setWindowIcon(app_icon)

    # Create and show the splash screen
    splash_pix = QPixmap(resource_path(os.path.join('assets', 'startup.png')))
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())

    # Add a label to the splash screen
    splash_label = QLabel("", splash)
    splash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    splash_label.setStyleSheet("QLabel { color : white; }")

    # Layout for the splash screen
    layout = QVBoxLayout(splash)
    layout.addWidget(splash_label)
    splash.setLayout(layout)

    splash.show()
    
    # Process events to make sure the splash screen is displayed
    QApplication.processEvents()

    # Use QTimer to delay the appearance of the main window after 1 seconds
    QtCore.QTimer.singleShot(1000, lambda: show_main_window(app))
    
    sys.exit(app.exec())