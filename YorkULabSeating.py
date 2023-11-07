import sys , os
import pandas as pd
import logging
import glob
from PyQt6 import QtWidgets, QtCore
from PyQt6 import uic
from PyQt6.QtCore import QAbstractTableModel, QVariant, QModelIndex, QSettings, QThread, pyqtSignal, QObject, Qt, QMarginsF, QSize, QUrl
from PyQt6.QtWidgets import QDialog, QApplication, QFileDialog, QWidget, QProgressBar
from PyQt6.QtWidgets import  QLabel, QVBoxLayout, QComboBox
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QPageSize, QPageLayout, QShortcut, QKeySequence, QDesktopServices
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QListWidget, QListWidgetItem, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QFileDialog, QTextEdit

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene

import scripts.SeatingManager as seating
import scripts.GPcManager as gpc
from scripts.remote_copy import MyRemoteCopyFile, Remote_LPC_manager
from scripts.remote_reboot import Remote_PC_Reboot

appVersion = '6.6'
#--------------------------------------------------------------------------------
class OutputWrapper(QObject):
    outputWritten = QtCore.pyqtSignal(object, object)

    def __init__(self, parent, stdout=True):
        super().__init__(parent)
        if stdout:
            self._stream = sys.stdout
            sys.stdout = self
        else:
            self._stream = sys.stderr
            sys.stderr = self
        self._stdout = stdout

    def write(self, text):
        self._stream.write(text)
        self.outputWritten.emit(text, self._stdout)

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def __del__(self):
        try:
            if self._stdout:
                sys.stdout = self._stream
            else:
                sys.stderr = self._stream
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

        self.ui = uic.loadUi('YorkULabSeating_att.ui',self)
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
        icon = QIcon('printer-icon-48.png')
        self.pushButton_print_att.setIcon(icon)
        self.pushButton_print_att.clicked.connect(self.print_prev_dlg)
        shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        shortcut.activated.connect(self.pushButton_print_att.click)
        self.pushButton_print_att.setToolTip("Click me (Ctrl+M)")
        
        self.retrieveDataset()
    
    def retrieveDataset(self):
        self.df = seating.concat_stud_lists(self.stud_list)
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
        self.df["Attn"] = "         "
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

        self.ui = uic.loadUi('YorkULabSeating_lpc.ui',self)
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
                self.pbar_copy.setFormat("Copy files ...")
                self.lpc_thread[1] = lpcCopyFileThread(self.lpc_list, self.selected_files, destination_path, self.LocalCopyMode, parent=None)
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
            delete_files = textEdit_delete_input.splitlines()

            if delete_files:
                destination_path = self.lineEdit_destination_input.text()
                self.pushButton_delete.setEnabled(False)
                self.pbar_delete.show()
                self.pbar_delete.setFormat("Delete files ...")
                self.lpc_thread[2] = lpcDeleteFileThread(self.lpc_list, delete_files, destination_path, self.LocalCopyMode, parent=None)
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
            QMessageBox.information(None, 'Delete Successful', ' All files are deleted from target Laptop(s) successfully')   
        else:
            res = [key for key, value in self.lpc_thread[1].status.values() if not value]
            error_message = f' Failed to delete the identified files from: {", ".join(res)}'
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

#================================================================================
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Default settings will be set if no stored settings found from previous session
        self.default_settings = {
            'year':'2023', 
            'semester':'Winter',
            'code':'xxxx',
            'laptop_list': [],
            'exp_id':1,
            'exp':'dummy_exp',
            'n_max_group':6,
            'n_benches':4,
            'pkl_name':'dummy.pkl',
            'pkl_path': 'dummy_pkl_path.pkl'
        }
        self.getSettingValues()
        
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi('YorkULabSeating.ui',self)

        stdout = OutputWrapper(self, True)
        stdout.outputWritten.connect(self.handleOutput)
        stderr = OutputWrapper(self, False)
        stderr.outputWritten.connect(self.handleOutput)
        
        # Retrieving settings from previous session 
        self.semester   = self.setting_Course.value('semester')
        self.year       = self.setting_Course.value('year')
        self.code       = self.setting_Course.value('code')
        self.course_dir  = self.setting_Course.value('course_dir')
        self.pc_dir  = self.setting_Course.value('pc_dir')
        #self.pc_txt_path = self.setting_Course.value('pc_txt_path')
        self.laptop_list = self.setting_Course.value('laptop_list')
        self.exp_id = self.setting_Course.value('exp_id')
        self.exp = self.setting_Course.value('exp')
        self.room = self.setting_Course.value('room')
        self.n_max_group    = self.setting_Course.value('n_max_group')
        self.n_benches  = self.setting_Course.value('n_benches')

        # Default settings is set if no stored settings found from previous session
        if not self.semester: self.semester = self.default_settings['semester']
        if not self.year: self.year = self.default_settings['year']
        if not self.code: self.code = self.default_settings['code']
        if not self.laptop_list: self.laptop_list = self.default_settings['laptop_list']
        if not self.exp_id: self.exp_id = self.default_settings['exp_id']
        if not self.exp: self.exp = self.default_settings['exp']
        if not self.n_max_group: self.n_max_group = self.default_settings['n_max_group']
        if not self.n_benches: self.n_benches = self.default_settings['n_benches']
        
        self.lineEdit_year.setText(self.year) 
        self.comboBox_semester.setCurrentText(self.semester)
        self.lineEdit_code.setText(self.code)
        
        if self.pc_dir and os.path.isdir(self.pc_dir):
            self.lineEdit_pc_dir.setText(self.pc_dir)
            self.pc_csv_path = self.extract_pc_csv_path(self.pc_dir)

            if self.pc_csv_path:
                self.room_list = self.extract_rooms(self.pc_dir, self.pc_csv_path)

        if self.course_dir and os.path.isdir(self.course_dir):
            self.lineEdit_course_dir.setText(self.course_dir)
            self.exp_csv_path, self.stud_csv_path_list, self.time_csv_path = self.extract_course_csv_paths(self.course_dir)
        
            if self.time_csv_path:
                self.session_list = self.extract_sessions(self.time_csv_path)
            if self.exp_csv_path:
                self.exp_list = self.extract_exp(self.exp_csv_path)
            
        self.lineEdit_ngroups.setText(str(self.n_max_group))
        self.lineEdit_nbenches.setText(str(self.n_benches))
        self.comboBox_exp_id.setCurrentText(self.exp)
        if self.room:
            self.comboBox_room.setCurrentText(self.room)
        self.course_label.setText(f'PHYS {self.code}')
        self.course_label.setFont(QFont('Arial', 15, weight=700))
        

        self.gpc_list = []
        self.gpc_map ={}
        if self.pc_dir and os.path.exists(self.pc_dir):
            self.lineEdit_pc_dir.setText(self.pc_dir)
            self.set_pc_txt_path()
        
        self.session_id = None
        self.pkl_path = None
        self.thread={}
        self.LocalCopyMode = False
        self.isCopyFileRunning = False
        self.is_gpc_reboot_running = False
        self.is_laptop_reboot_running = False
        
        self.lineEdit_TAname.setEnabled(False)
        self.overwite_ta_name = False
        self.ta_name = None
        self.layout_out = None
        self.pushButton_labLayout.setEnabled(False)
        self.pushButton_att.setEnabled(False)

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
        
        #--signal and slots
        self.pushButton_save_settings.clicked.connect(self.save_button_click)
        self.pushButton_grouping.clicked.connect(self.generate_groups)
        self.pushButton_htmlgen.clicked.connect(self.generate_html)
        self.comboBox_exp_id.activated.connect(self.set_exp_id)
        self.comboBox_session.activated.connect(self.set_session_id)
        self.comboBox_room.activated.connect(self.set_pc_txt_path)

        self.pushButton_copyfiles.clicked.connect(self.start_copyfiles_worker)
        self.pushButton_rebootPCs.clicked.connect(self.start_gpc_reboot_worker)
        self.pushButton_rebootLaptops.clicked.connect(self.start_laptop_reboot_worker)
        self.pushButton_lpc_remote_files.clicked.connect(self.open_lpc_file_manager)
        self.pushButton_lpc_remote_files.setToolTip("Copy/Delete files to/from laptops")
        if not self.room:
            self.pushButton_lpc_remote_files.setEnabled(False)


        self.pushButton_course_dir_browse.clicked.connect(self.browse_course_dir)
        self.pushButton_pc_browse.clicked.connect(self.browse_pc_dir)
        self.checkBox_debugMode.toggled.connect(self.set_debug_mode)
        self.checkBox_localCopy.toggled.connect(self.set_copy_mode)
        self.checkBox_TAname_overwrite.toggled.connect(self.set_ta_name_mode)
        self.pushButton_labLayout.clicked.connect(self.show_lab_layout)
        self.pushButton_att.clicked.connect(self.show_attendance)
        self.pushButton_Watt.clicked.connect(self.show_weekly_att)
    
    def show_weekly_att(self):
        pdf_file_path = seating.create_weekly_att(self.stud_csv_path_list, self.session_list, self.code, self.exp_id)
        
        # Check if the file exists
        if pdf_file_path and os.path.isfile(pdf_file_path):
            # Open the PDF file with the default PDF viewer
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_file_path))
        else:
            # Handle the case where the file doesn't exist
            logging.error("PDF file not found: ", pdf_file_path)

    def show_attendance(self):
        self.att = AttWindow(self.stud_csv_path_list, self.session, self.session_id, self.code, self.exp_id)
        self.att.setWindowTitle('Print attendance list')
        self.att.show()

    def show_lab_layout(self):
        # Populating layout image:
        if self.course_dir:
            self.lab_layout_out_file = seating.print_on_layout(self.gpc_map, self.room, self.room_list, self.exp_id, self.pkl_path)
            logging.debug(f'self.lab_layout_out_file: {self.lab_layout_out_file}')
            
            if os.path.isfile(self.lab_layout_out_file):
                self.lablayout = LabLayoutWindow_new(self.lab_layout_out_file)
                self.lablayout.showMaximized()
            else:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("Cannot generate lab_layout_grp.jpg.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
        else:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("Course main directory not found. Please select the mian directory from the setting tab first.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
        
    def browse_course_dir(self):
        '''
        open dialog box to browse for source dir and return the pathes for exp, stud(s) and time csv files.
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
                self.exp_list = self.extract_exp(self.exp_csv_path)
                
    
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
        open dialog box to browse for source dir and return the pathes for exp, stud(s) and time csv files.
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
            self.comboBox_session.setCurrentIndex(-1)
        
        return session_list

    def extract_exp(self, exp_csv_path):
        exp_list = seating.get_exp_list(exp_csv_path)
        self.comboBox_exp_id.clear()

        if exp_list:
            list_helper = list(exp_list.keys())
            
            self.comboBox_exp_id.addItems(list_helper)
            logging.debug(f'---exps loaded:{list_helper}')
            self.comboBox_exp_id.setCurrentIndex(-1)
        
        return exp_list

    def set_debug_mode(self):
        debug_mode = self.checkBox_debugMode.isChecked()
        if debug_mode:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
    
    def set_copy_mode(self):
        self.LocalCopyMode = self.checkBox_localCopy.isChecked()
    
    def set_ta_name_mode(self):
        self.overwite_ta_name = self.checkBox_TAname_overwrite.isChecked()
        if self.overwite_ta_name:
            self.lineEdit_TAname.setEnabled(True)
        else:
            self.lineEdit_TAname.setEnabled(False)

    def getSettingValues(self):
        '''
        # Load the last user setting from previous session
        '''
        self.setting_Course = QSettings('YorkLabSeating', 'Course')
        self.setting_Network = QSettings('YorkLabSeating', 'Network')
    
    def save_button_click(self):
        '''
        # Save the user setting values with pressing in SAVE button
        '''
        self.year       = self.lineEdit_year.text() 
        self.semester   = self.comboBox_semester.currentText()
        self.code       = self.lineEdit_code.text() 
        self.n_max_group    = int(self.lineEdit_ngroups.text())
        self.n_benches    = int(self.lineEdit_nbenches.text())
        self.course_label.setText(f'PHYS {self.code}')
        
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Inof.")
        dlg.setText("Settings saved")
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Information)
        dlg.exec()
    
    def set_pklfile_name(self):
        pklfile_name_list = ['SeatingDB', self.semester, self.year, self.code, self.session_id.replace(" ", "")]
        pklfile_name = '_'.join(pklfile_name_list)+'.pkl'
        logging.debug(f'pklfile_name:{pklfile_name}')
        return pklfile_name

    def set_exp_id(self):
        self.exp = self.comboBox_exp_id.currentText()
        if self.exp:
            self.exp_id = self.exp_list[self.exp]
            logging.info(f' Selected exp_id:{self.exp_id}')

    def set_session_id(self):
        self.session = self.comboBox_session.currentText()
        self.pushButton_att.setEnabled(True)
        
        if self.session:
            self.session_id = self.session_list[self.session]
            logging.info(f' Selected session_id:{self.session_id}')
    
    def set_pc_txt_path(self):
        self.room = self.comboBox_room.currentText()
        
        if self.room:
            self.pc_txt_path = self.room_list[self.room][0]
            logging.info(f' Selected room:{self.room}')
            logging.debug(f'--pc_txt_path:{self.pc_txt_path}')
            self.gpc_list, self.laptop_list, self.gpc_map =gpc.extract_pc_list(self.pc_txt_path)
            self.pushButton_lpc_remote_files.setEnabled(True)

    def generate_groups(self):
        if not self.session_id:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("Please select a <b>session</b> before generating groups.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return 
        else:
            logging.debug(f'selected session_id:{self.session_id}.')
            if not self.stud_csv_path_list:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText(f"Please select a student list from the settings tab and save, before generating groups.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
            else: 
                n_stud = seating.get_number_of_students(self.stud_csv_path_list, self.session_id)
                logging.debug(f' There are {n_stud} students enrolled in this session.')
        
        if n_stud > self.n_benches * self.n_max_group:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"There are <b>no enough seats for {n_stud} students in {self.n_max_group} groups</b>. Either increase the number of groups or the number of seats per group and try again.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
        else:
            if not self.exp_csv_path:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText(f"Please make sure exp_* (experiments list) exists in the main course directory.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
            else:
                self.pkl_file_name   = self.set_pklfile_name()
                self.pkl_path, self.n_group = seating.make_groups(self.exp_csv_path, self.stud_csv_path_list, self.time_csv_path, self.session_id, n_stud, self.n_benches, self.code, self.pkl_file_name )
                if self.pkl_path:
                    dlg = QtWidgets.QMessageBox(self)
                    dlg.setWindowTitle("Info.")
                    dlg.setText(f"<b>{n_stud} enrolled students</b> in this session are assigned into <b>{self.n_group} groups</b>. Number of groups can be adjusted from the settings tab if needed.")
                    dlg.setIcon(QtWidgets.QMessageBox.Icon.Information)
                    dlg.exec()
                    self.pushButton_grouping.setEnabled(False)
                    self.comboBox_session.setEnabled(False)
                    self.pushButton_labLayout.setEnabled(True)
                else:
                    dlg = QtWidgets.QMessageBox(self)
                    dlg.setWindowTitle("Error")
                    dlg.setText("Experiment list and/or Student list are(is) empty. If not, check the csv headers.")
                    dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                    dlg.exec()
            
    def generate_html(self):
        if self.pkl_path:
            if os.path.exists(self.pkl_path):
                logging.debug(f'self.pkl_path: {self.pkl_path}')
                
                if self.overwite_ta_name:
                    self.ta_name = self.lineEdit_TAname.text()
                else: self.ta_name = None
                
                seating.html_generator(self.pkl_path, self.code, self.n_max_group, self.n_benches, appVersion, self.ta_name)
        else:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"pkl file not found. Run Grouping first to generate it.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()

    def start_copyfiles_worker(self):
        if self.gpc_list and self.course_dir:
            self.copy_pbar.show()
            self.copy_pbar.setFormat("Copy files ...")

            self.thread[1] = CopyFileThread(self.exp_id, self.gpc_list, self.gpc_map, self.course_dir, self.code, localCopy = self.LocalCopyMode, parent=None)
            self.thread[1].finished.connect(self.on_copyFinished)
            self.thread[1].start()
            self.pushButton_copyfiles.setEnabled(False)
            self.comboBox_exp_id.setEnabled(False)
            self.pushButton_htmlgen.setEnabled(False)
            self.pushButton_rebootPCs.setEnabled(False)
            self.isCopyFileRunning = True
            self.thread[1].progress.connect(self.copy_setProgress)
                        
        elif not self.gpc_list and self.course_dir:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"No Group PC name found in Group PC list. Check the input txt file")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return
        elif not self.course_dir:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"Select the main course directory from setting tab.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return
    
    def copy_setProgress(self, copy_progress):
        self.copy_pbar.setValue(copy_progress)

    def on_copyFinished(self):
        self.copy_pbar.setFormat("Copy completed")
        self.pushButton_copyfiles.setEnabled(True)
        self.comboBox_exp_id.setEnabled(True)
        self.pushButton_htmlgen.setEnabled(True)
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
                self.gpc_reboot_pbar.setFormat("Rebooting Group PCs ...")
                self.thread[2] = Reboot_PC_Thread(self.gpc_list, parent=None)
                self.thread[2].finished.connect(self.on_gpc_rebootFinished)
                self.thread[2].start()
                
                self.pushButton_rebootPCs.setEnabled(False)
                self.is_gpc_reboot_running = True
                self.thread[2].progress.connect(self.gpc_reboot_setProgress)
            else:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText(f"No Group PC name found in Group PC list. Check the input txt file")
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
                self.pc_reboot_pbar.setFormat("Rebooting Laptops ...")
                self.thread[3] = Reboot_PC_Thread(self.laptop_list, parent=None)
                self.thread[3].finished.connect(self.on_laptop_rebootFinished)
                self.thread[3].start()
                
                self.pushButton_rebootLaptops.setEnabled(False)
                self.is_laptop_reboot_running = True
                self.thread[3].progress.connect(self.pc_reboot_setProgress)
            else:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText(f"No Laptop found in laptop list. Check the input txt file")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
    
    def open_lpc_file_manager(self):
        self.lpc_remote = lpc_file_manager(self.laptop_list, self.LocalCopyMode)
        self.lpc_remote.setWindowTitle('Laptops Remote File Manager')
        self.lpc_remote.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.lpc_remote.show()
    

    def pc_reboot_setProgress(self, pc_progress):
        self.pc_reboot_pbar.setValue(pc_progress)

    def on_laptop_rebootFinished(self):
        self.pushButton_rebootLaptops.setEnabled(True)
        self.is_laptop_reboot_running = False
        self.pc_reboot_pbar.setFormat("LAptops rebooted")

    #----------------------------------
    def handleOutput(self, text, stdout):
        color = self.statusbox.textColor()
        self.statusbox.setTextColor(color)
        self.statusbox.setOpenExternalLinks(True)
        self.statusbox.append(text)
        self.statusbox.setTextColor(color)

    def closeEvent(self, event):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Warning")
        dlg.setText("Are you sure you want to close the program?")
        dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        button = dlg.exec()

        if button == QtWidgets.QMessageBox.StandardButton.Yes:
            #--- store the current setting in the system before closing the app
            self.setting_Course.setValue('year', self.lineEdit_year.text() )
            self.setting_Course.setValue('semester', self.comboBox_semester.currentText())
            self.setting_Course.setValue('code', self.lineEdit_code.text() )
            self.setting_Course.setValue('course_dir', self.course_dir )
            self.setting_Course.setValue('pc_dir', self.pc_dir )
            #self.setting_Course.setValue('pc_txt_path', self.pc_txt_path)
            self.setting_Course.setValue('exp_id', int(self.exp_id))
            self.setting_Course.setValue('exp', self.comboBox_exp_id.currentText())
            self.setting_Course.setValue('room', self.comboBox_room.currentText())
            self.setting_Course.setValue('n_max_group', int(self.lineEdit_ngroups.text()) )
            self.setting_Course.setValue('n_benches', int(self.lineEdit_nbenches.text()))
            try:
                event.accept()
                logging.debug('The application exited Normaly.')
            except Exception as e:
                logging.error(f'The application exited with error: {e}')
            
        else:
            event.ignore()

#--------------------------------------------------------------------------------
class CopyFileThread(QThread):
    progress = pyqtSignal(int)
    
    def __init__(self, exp_id, gpc_list, gpc_map, course_dir, code, localCopy, parent=None ):
        super(CopyFileThread, self).__init__(parent)
        self.status = {}
        self.exp_id=exp_id
        self.gpc_list = gpc_list
        self.gpc_map = gpc_map
        self.course_dir = course_dir
        self.code = code
        self.localCopy = localCopy
        self.is_running = True
        self.copy_service = MyRemoteCopyFile(self.localCopy)
        
    def run(self):
        logging.info(f' Copying html files of Exp {self.exp_id} to Group PCs. Please wait ...')
        
        self.progress.emit(0)

        if self.localCopy:
            gpc = 'LOCAL PC'
            group_id = 0
            self.status[gpc] = self.copy_service.run_copyfile(self.exp_id, gpc, group_id ,self.course_dir, self.code)
        else:
            for i, gpc in enumerate(self.gpc_list):
                group_id = int(self.gpc_map[gpc][3])
                self.status[gpc] = self.copy_service.run_copyfile(self.exp_id, gpc, group_id ,self.course_dir, self.code)
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
    progress = pyqtSignal(int)

    def __init__(self, lpc_list, selected_files, destination_path, localCopy, parent=None ):
        super(lpcCopyFileThread, self).__init__(parent)
        self.status = {}
        self.lpc_list = lpc_list
        self.selected_files = selected_files
        self.destination_path = destination_path
        self.localCopy = localCopy
        self.is_running = True
        self.lpc_copy_service = Remote_LPC_manager(self.localCopy)
        
    def run(self):
        logging.info(f' Copying selected file(s) to the laptops. Please wait ...')
        
        self.progress.emit(0)

        if self.localCopy:
            lpc = 'LOCAL PC'
            self.status[lpc] = self.lpc_copy_service.run_copyfile(lpc, self.selected_files, self.destination_path)
        else:
            for i, lpc in enumerate(self.lpc_list):
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
class lpcDeleteFileThread(QThread):
    progress = pyqtSignal(int)

    def __init__(self, lpc_list, delete_files, destination_path, localCopy, parent=None ):
        super(lpcDeleteFileThread, self).__init__(parent)
        self.status = {}
        self.lpc_list = lpc_list
        self.delete_files = delete_files
        self.destination_path = destination_path
        self.localCopy = localCopy
        self.is_running = True
        self.lpc_delete_service = Remote_LPC_manager(self.localCopy)
        
    def run(self):
        logging.info(f' Deleting identified file(s) from the laptops. Please wait ...')
        
        self.progress.emit(0)

        for i, lpc in enumerate(self.lpc_list):
            self.status[lpc] = self.lpc_delete_service.run_deletefile(lpc, self.delete_files, self.destination_path)
            self.progress.emit(int(100*(i+1)/len(self.lpc_list)))
            
        if all(self.status.values()):
            logging.info(' Files are deleted from target Laptop(s) successfully')
        else:
            res = [key for key, value in self.status.items() if not value]
            logging.error(f' Failed to delete the identified files from: {res}')

    def stop(self):
        self.is_running = False
        self.terminate()
#--------------------------------------------------------------------------------
class Reboot_PC_Thread(QThread):
    progress = pyqtSignal(int)

    def __init__(self, pc_list, parent=None ):
        super(Reboot_PC_Thread, self).__init__(parent)
        self.status = {}
        self.pc_list = pc_list
        self.is_running = True
        self.reboot_service = Remote_PC_Reboot()
        
        
    def run(self):
        logging.info(f' Rebooting PCs. Please wait ...')
        self.progress.emit(0)

        #status = self.reboot_service.reboot_Pcs(self.pc_list)
        for i, pc in enumerate(self.pc_list):
            self.status[pc] = self.reboot_service.reboot_Pcs(pc)
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
    print('Welcome to YorkU PHYS Lab Seat Assigner')
    logging.getLogger().setLevel(logging.INFO)
    app = QApplication(sys.argv)
    app_icon = QIcon("YorkU_icon.jpg")
    app.setWindowIcon(app_icon)
    mainWindow = MainWindow()
    mainWindow.show()

    sys.exit(app.exec())