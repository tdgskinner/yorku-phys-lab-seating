import sys , os
from PyQt6 import QtWidgets, QtCore
from PyQt6 import uic
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QDialog, QApplication, QFileDialog
from PyQt6.QtGui import QIcon

import logging
import scripts.SeatingManager as seating
import scripts.GPcManager as gpc

from scripts.remote_copy import MyRemoteCopyFile


class OutputWrapper(QtCore.QObject):
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

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Default settings will be set if no stored settings found from previous session
        self.default_settings = {
            'year':'2022', 
            'semester':'Fall',
            'code':'xxxx',
            'coursename':'PHYS',
            'session_list': [],
            'gpc_list': [],
            #'ta_name':'Best TA',
            'exp_id':1,
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
        self.session_list = self.setting_Course.value('session_list')
        self.exp_csv_path  = self.setting_Course.value('exp_csv_path')
        self.src_dir  = self.setting_Course.value('src_dir')
        self.stud_csv_path_list = self.setting_Course.value('stud_csv_path_list')
        self.time_csv_path = self.setting_Course.value('time_csv_path')
        self.gpc_txt_path = self.setting_Course.value('gpc_txt_path')
        self.gpc_list = self.setting_Course.value('gpc_list')
        self.exp_id = self.setting_Course.value('exp_id')
        self.n_max_group    = self.setting_Course.value('n_max_group')
        self.n_benches  = self.setting_Course.value('n_benches')

        # Default settings is set if no stored settings found from previous session
        if not self.semester: self.semester = self.default_settings['semester']
        if not self.year: self.year = self.default_settings['year']
        if not self.code: self.code = self.default_settings['code']
        if not self.session_list: self.session_list = self.default_settings['session_list']
        if not self.gpc_list: self.gpc_list = self.default_settings['gpc_list']
        if not self.exp_id: self.exp_id = self.default_settings['exp_id']
        if not self.n_max_group: self.n_max_group = self.default_settings['n_max_group']
        if not self.n_benches: self.n_benches = self.default_settings['n_benches']
        
        self.lineEdit_year.setText(self.year) 
        self.comboBox_semester.setCurrentText(self.semester)
        self.lineEdit_code.setText(self.code)
        if self.session_list:
            list_helper = sorted(list(self.session_list.keys()))
            self.comboBox_session.addItems(list_helper)
            self.comboBox_session.setCurrentIndex(-1)
            
        self.lineEdit_ngroups.setText(str(self.n_max_group))
        self.lineEdit_nbenches.setText(str(self.n_benches))
        self.spinBox_exp_id.setValue(self.exp_id)
        self.lineEdit_exp_csv.setText(self.exp_csv_path)
        if self.stud_csv_path_list:
            self.lineEdit_stud_csv.setText(','.join(str(s) for s in self.stud_csv_path_list ))
            
        self.lineEdit_time_csv.setText(self.time_csv_path)
        self.lineEdit_gpc_txt.setText(self.gpc_txt_path)

        self.session_id = None
        self.pkl_path = None
        self.thread={}
        self.LocalCopyMode = False
        self.isCopyFileRunning = False
        
        self.lineEdit_TAname.setEnabled(False)
        self.overwite_ta_name = False
        self.ta_name = None

        #--signal and slots
        self.pushButton_save_settings.clicked.connect(self.save_button_click)
        self.pushButton_grouping.clicked.connect(self.generate_groups)
        self.pushButton_htmlgen.clicked.connect(self.check_pkl)
        self.spinBox_exp_id.valueChanged.connect(self.set_exp_id)
        self.pushButton_copyfiles.clicked.connect(self.start_copyfiles_worker)
        self.comboBox_session.activated.connect(self.set_session_id)
        self.pushButton_rebootPCs.clicked.connect(self.Reboot_Pcs)
        self.pushButton_exp_brows.clicked.connect(lambda: self.browsefile('exp'))
        self.pushButton_stud_brows.clicked.connect(self.browsefiles)
        self.pushButton_time_brows.clicked.connect(lambda: self.browsefile('time'))
        self.pushButton_gpc_brows.clicked.connect(lambda: self.browsefile('gpc'))
        self.checkBox_debugMode.toggled.connect(self.set_debug_mode)
        self.checkBox_localCopy.toggled.connect(self.set_copy_mode)
        self.checkBox_TAname_overwrite.toggled.connect(self.set_ta_name_mode)
    
    def browsefile(self, category):
        logging.debug(f'self.src_dir: {self.src_dir}')
        if self.src_dir:
            fname=QFileDialog.getOpenFileName(self, 'Open file', directory=self.src_dir, filter='Input file (*.csv *.txt)')
        else:
            fname=QFileDialog.getOpenFileName(self, 'Open file', directory='data', filter='Input file (*.csv *.txt)')
        
        if category == 'time':
            self.lineEdit_time_csv.setText(fname[0])
            self.time_csv_path = fname[0]
            if fname[0]:
                self.extract_sessions(self.time_csv_path)
        elif category == 'exp':
            self.lineEdit_exp_csv.setText(fname[0])
            self.exp_csv_path = fname[0]
            self.src_dir = os.path.dirname(self.exp_csv_path)
        elif category == 'gpc':
            self.lineEdit_gpc_txt.setText(fname[0])
            self.gpc_txt_path = fname[0]
            logging.debug(f'--gpc_txt_path:{self.gpc_txt_path}')
            if fname[0]:
                self.gpc_list =gpc.extract_gpc_list(self.gpc_txt_path)
        
    def browsefiles(self):
        if self.src_dir:
            fnames=QFileDialog.getOpenFileNames(self, 'Open file', directory=self.src_dir, filter='Input files (*.csv *.txt)')
        else:
            fnames=QFileDialog.getOpenFileNames(self, 'Open file', directory='data', filter='Input files (*.csv *.txt)')
        
        self.lineEdit_stud_csv.setText(','.join(str(s) for s in fnames[0] ))
        self.stud_csv_path_list = fnames[0]
    
    def extract_sessions(self, time_csv_path):
        self.session_list = seating.get_session_list(time_csv_path)
        logging.debug(f'sessions in this course:{self.session_list.keys()}')
        self.comboBox_session.clear()
        if self.session_list:
            list_helper = sorted(list(self.session_list.keys()))
            self.comboBox_session.addItems(list_helper)
            self.comboBox_session.setCurrentIndex(-1)

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
        self.exp_id     = self.spinBox_exp_id.value()
        
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
        self.exp_id = self.spinBox_exp_id.value()

    def set_session_id(self):
        self.session   = self.comboBox_session.currentText()
        if self.session:
            self.session_id = self.session_list[self.session][0]
            logging.debug(f'---set_session_id:{self.session_id}')


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
                logging.debug(f' There are {n_stud} students enroled in this session.')
        
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
                dlg.setText(f"Please select experiments list from the settings tab and save, before generating groups.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return
            else:
                self.pkl_file_name   = self.set_pklfile_name()
                self.pkl_path, n_group = seating.make_groups(self.exp_csv_path, self.stud_csv_path_list, self.time_csv_path, self.session_id, n_stud, self.n_benches, self.code, self.pkl_file_name )
                if self.pkl_path:
                    dlg = QtWidgets.QMessageBox(self)
                    dlg.setWindowTitle("Info.")
                    dlg.setText(f"<b>{n_stud} enroled students</b> in this session are assigned into <b>{n_group} groups</b>. Number of groups can be adjusted from the settings tab if needed.")
                    dlg.setIcon(QtWidgets.QMessageBox.Icon.Information)
                    dlg.exec()
                else:
                    dlg = QtWidgets.QMessageBox(self)
                    dlg.setWindowTitle("Error")
                    dlg.setText("Experiment list and/or Student list are(is) empty. If not, check the csv headers.")
                    dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                    dlg.exec()
            
    def check_pkl(self):
        if self.pkl_path:
            if os.path.exists(self.pkl_path):
                logging.debug(f'self.pkl_path: {self.pkl_path}')
                
                if self.overwite_ta_name:
                    self.ta_name = self.lineEdit_TAname.text()
                else: self.ta_name = None
                
                seating.html_generator(self.pkl_path, self.code, self.ta_name)
        else:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"pkl file does not exit. Run Grouping first to generate it.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()

    def start_copyfiles_worker(self):
        if self.gpc_list and self.src_dir:
            self.thread[1] = CopyFileThread(self.exp_id, self.gpc_list, self.src_dir, self.code, localCopy = self.LocalCopyMode, parent=None)
            self.thread[1].finished.connect(self.on_copyFinished)
            self.thread[1].start()
            self.pushButton_copyfiles.setEnabled(False)
            self.spinBox_exp_id.setEnabled(False)
            self.pushButton_grouping.setEnabled(False)
            self.pushButton_htmlgen.setEnabled(False)
            self.pushButton_rebootPCs.setEnabled(False)
            self.isCopyFileRunning = True
        elif not self.gpc_list and self.src_dir:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"No Group PC name found in Group PC list. Check the input txt file")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return
        elif not self.src_dir:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"Exp source dir not found. Reload the exp csv file from setting tab.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
            return
    
    def on_copyFinished(self):
        self.pushButton_copyfiles.setEnabled(True)
        self.spinBox_exp_id.setEnabled(True)
        self.pushButton_grouping.setEnabled(True)
        self.pushButton_htmlgen.setEnabled(True)
        self.pushButton_rebootPCs.setEnabled(True)
        self.isCopyFileRunning = False
    
    def Reboot_Pcs(self):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Warning")
        dlg.setText("Are you sure you want to Reboot all Group Computers?")
        dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        button = dlg.exec()
        if button == QtWidgets.QMessageBox.StandardButton.Yes:
            if self.gpc_list:
                gpc.reboot_Pcs(self.gpc_list)
            else:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText(f"No Group PC name found in Group PC list. Check the input txt file")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()
                return 

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
            self.setting_Course.setValue('session_list', self.session_list)
            self.setting_Course.setValue('exp_csv_path', self.lineEdit_exp_csv.text())
            self.setting_Course.setValue('src_dir', self.src_dir)
            self.setting_Course.setValue('stud_csv_path_list', self.stud_csv_path_list)
            self.setting_Course.setValue('time_csv_path', self.lineEdit_time_csv.text())
            self.setting_Course.setValue('gpc_txt_path', self.lineEdit_gpc_txt.text())
            self.setting_Course.setValue('gpc_list', self.gpc_list)
            self.setting_Course.setValue('exp_id', int(self.spinBox_exp_id.value())  )
            self.setting_Course.setValue('n_max_group', int(self.lineEdit_ngroups.text()) )
            self.setting_Course.setValue('n_benches', int(self.lineEdit_nbenches.text()))
            try:
                event.accept()
                logging.debug('The application exited properly.')
            except Exception as e:
                logging.error(f'The application exited improperly: {e}')
            
        else:
            event.ignore()
#--------------------------------------------------------------------------------

class CopyFileThread(QtCore.QThread):
    def __init__(self, exp_id, gpc_list, src_dir, code, localCopy, parent=None ):
        super(CopyFileThread, self).__init__(parent)
        
        self.exp_id=exp_id
        self.gpc_list = gpc_list
        self.src_dir = src_dir
        self.code = code
        self.localCopy = localCopy
        self.is_running = True
        self.copy_service = MyRemoteCopyFile(self.localCopy)
        
        
    def run(self):
        logging.info(f' Copying html files of Exp {self.exp_id} to Group PCs. Please wait ...')
        status = self.copy_service.run_copyfile(self.exp_id, self.gpc_list, self.src_dir, self.code)
        
        if all(status.values()):
            logging.info(' html files are copied to target PC(s) successfully')
        else:
            res = [key for key, value in status.items() if not value]
            logging.error(f' Failed to copy html files to: {res}')

    def stop(self):
        self.is_running = False
        self.terminate()

#-------------------------------------------------
if __name__ == '__main__':
    #logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().setLevel(logging.INFO)
    
    app = QtWidgets.QApplication(sys.argv)
    app_icon = QIcon("YorkU_icon.jpg")
    app.setWindowIcon(app_icon)
    mainWindow = MainWindow()
    mainWindow.show()

    print('Welcome to YorkU PHYS Lab Seating Monitor')
    sys.exit(app.exec())