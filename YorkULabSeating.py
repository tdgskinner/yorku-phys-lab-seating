import sys , os
from PyQt6 import QtWidgets, QtCore
from PyQt6 import uic
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QDialog, QApplication, QFileDialog

import logging
import scripts.SeatingManager as seating
from scripts.webserver import MyWebServer


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
            'code':'2213',
            'coursename':'PHYS',
            'session':'',
            'session_list': [],
            'ta_name':'Mohammad Kareem',
            'hostname':'127.0.0.1',
            'portnumber':'5000',
            'data_dir':'data',
            #'exp_csv_path':'exp_autogen_list.csv',
            #'stud_csv_path':'student_autogen_list.csv',
            'exp_id':1,
            'n_group':6,
            'n_benches':4,
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
        self.coursename = self.setting_Course.value('coursename')
        self.session    = self.setting_Course.value('session')
        self.session_list = self.setting_Course.value('session_list')
        self.TA_name    = self.setting_Course.value('ta_name')
        self.hostname   = self.setting_Network.value('hostname')
        self.portnumber = self.setting_Network.value('portnumber')
        self.data_dir   = self.setting_Course.value('data_dir')
        self.exp_csv_path  = self.setting_Course.value('exp_csv_path')
        self.stud_csv_path = self.setting_Course.value('stud_csv_path')
        self.time_csv_path = self.setting_Course.value('time_csv_path')
        self.exp_id = self.setting_Course.value('exp_id')
        self.n_group    = self.setting_Course.value('n_group')
        self.n_benches  = self.setting_Course.value('n_benches')       

        # Default settings is set if no stored settings found from previous session
        if not self.semester: self.semester = self.default_settings['semester']
        if not self.year: self.year = self.default_settings['year']
        if not self.code: self.code = self.default_settings['code']
        if not self.coursename: self.coursename = self.default_settings['coursename']
        #if not self.session: self.session = self.default_settings['session']
        #if not self.session_list: self.session_list = self.default_settings['session_list']
        if not self.TA_name: self.TA_name = self.default_settings['ta_name']
        if not self.hostname: self.hostname = self.default_settings['hostname']
        if not self.portnumber: self.portnumber = self.default_settings['portnumber']
        if not self.data_dir: self.data_dir = self.default_settings['data_dir']
        #if not self.exp_csv_path: self.exp_csv_path = self.default_settings['exp_csv_path']
        #if not self.stud_csv_path: self.stud_csv_path = self.default_settings['stud_csv_path']
        if not self.exp_id: self.exp_id = self.default_settings['exp_id']
        if not self.n_group: self.n_group = self.default_settings['n_group']
        if not self.n_benches: self.n_benches = self.default_settings['n_benches']
        
        #self.lineEdit_ta.setText(self.TA_name)
        self.lineEdit_year.setText(self.year) 
        self.comboBox_semester.setCurrentText(self.semester)
        self.lineEdit_code.setText(self.code) 
        #self.lineEdit_coursename.setText(self.coursename) 
        if self.session_list:
            self.comboBox_session.addItems(self.session_list)
            self.comboBox_session.setCurrentText(self.session)
        self.lineEdit_ngroups.setText(str(self.n_group))
        self.lineEdit_nbenches.setText(str(self.n_benches))
        self.lineEdit_host.setText(self.hostname)
        self.lineEdit_port.setText(self.portnumber)
        #self.lineEdit_data_dir.setText(self.data_dir)
        self.spinBox_exp_id.setValue(self.exp_id)
        self.lineEdit_exp_csv.setText(self.exp_csv_path)
        self.lineEdit_stud_csv.setText(self.stud_csv_path)
        self.lineEdit_time_csv.setText(self.time_csv_path)

        #self.exp_csv_path = os.path.join('scripts', self.data_dir, self.exp_csv_path )
        #self.stud_csv_path = os.path.join('scripts', self.data_dir, self.stud_csv_path )

        #self.lineEdit_pkl.setEnabled(False)
        self.pkl_file_name   = self.set_pklfile_name()

        self.thread={}
        self.isWebServerRunning = False

        #--signal and slots
        self.pushButton_save_settings.clicked.connect(self.save_button_click)
        self.pushButton_grouping.clicked.connect(self.generate_groups)
        self.pushButton_htmlgen.clicked.connect(self.check_pkl)
        self.spinBox_exp_id.valueChanged.connect(self.set_spin_value)
        self.pushButton_copyfiles.clicked.connect(self.start_webserver_worker)
        self.pushButton_restartPCs.clicked.connect(self.stop_webserver_worker)

        self.pushButton_exp_brows.clicked.connect(lambda: self.browsefiles('exp'))
        self.pushButton_stud_brows.clicked.connect(lambda: self.browsefiles('stud'))
        self.pushButton_time_brows.clicked.connect(lambda: self.browsefiles('time'))
    
    def browsefiles(self, category):
        fname=QFileDialog.getOpenFileName(self, 'Open file', os.path.join('scripts','data'),'CSV file (*.csv)')
        if category == 'time':
            self.lineEdit_time_csv.setText(fname[0])
            self.time_csv_path = fname[0]
            self.extract_sessions(self.time_csv_path)
        elif category == 'exp':
            self.lineEdit_exp_csv.setText(fname[0])
            self.exp_csv_path = fname[0]
        elif category == 'stud':
            self.lineEdit_stud_csv.setText(fname[0])
            self.stud_csv_path = fname[0]
    
    def extract_sessions(self, time_csv_path):
        self.session_list = seating.get_session_list(time_csv_path)
        #logging.debug(f'there are {len(self.session_list)} sessions in this course!')
        self.comboBox_session.clear()
        if self.session_list:
            self.comboBox_session.addItems(self.session_list)
        

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
        #self.coursename = self.lineEdit_coursename.text() 
        self.session   = self.comboBox_session.currentText()
        #self.TA_name    = self.lineEdit_ta.text() 
        self.n_group    = int(self.lineEdit_ngroups.text())
        self.n_benches    = int(self.lineEdit_nbenches.text())
        
        self.hostname   = self.lineEdit_host.text()
        self.portnumber = self.lineEdit_port.text()
        
        #self.data_dir   = self.lineEdit_data_dir.text()
        #self.exp_csv_path = os.path.join('scripts', self.data_dir, self.lineEdit_exp_csv.text() )
        #self.stud_csv_path = os.path.join('scripts', self.data_dir, self.lineEdit_stud_csv.text() )

        self.pkl_file_name   = self.set_pklfile_name()
        
        self.exp_id     = self.spinBox_exp_id.value()
        
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Inof")
        dlg.setText("Settings saved")
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Information)
        dlg.exec()
    
    def set_pklfile_name(self):
        pklfile_name_list = ['SeatingDB', self.semester, self.year, self.code, self.session.replace(" ", "")]
        pklfile_name = '_'.join(pklfile_name_list)+'.pkl'
        #self.lineEdit_pkl.setText(pklfile_name)    
        return pklfile_name

    def set_spin_value(self):
        self.exp_id = self.spinBox_exp_id.value()

    def generate_groups(self):
        n_stud = seating.get_number_of_students(self.stud_csv_path, self.session)
        if n_stud > self.n_benches * self.n_group:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"There are no enough seats for {n_stud} students. Either increase the number of groups or the number of benches per group and try again.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()
        else:
            gen_status = seating.make_groups(self.exp_csv_path, self.stud_csv_path, self.session, self.n_group, self.n_benches, self.pkl_file_name )
            if gen_status == False:
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText("Experiment list and/or Student list are(is) empty. Check if 'Session' matches with 'session_id' in both input csv files.")
                dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                dlg.exec()

    def check_pkl(self):
        pkl_path = os.path.join('scripts', 'src', 'pkl', self.pkl_file_name)

        if os.path.exists(pkl_path):
            seating.html_generator(self.pkl_file_name, self.coursename, self.code, self.TA_name)
        else:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            #dlg.setText(f"{self.lineEdit_pkl.text()} does not exit. Run Grouping first to generate it.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()

    def start_webserver_worker(self):
        self.thread[1] = WebServerThread(self.exp_id, self.hostname, self.portnumber, parent=None)
        self.thread[1].start()
        self.pushButton_copyfiles.setEnabled(False)
        self.spinBox_exp_id.setEnabled(False)
        self.pushButton_grouping.setEnabled(False)
        self.pushButton_htmlgen.setEnabled(False)
        self.pushButton_restartPCs.setEnabled(True)
        self.isWebServerRunning = True
    
    def stop_webserver_worker(self):
        self.thread[1].stop()
        self.pushButton_copyfiles.setEnabled(True)
        self.pushButton_grouping.setEnabled(True)
        self.pushButton_htmlgen.setEnabled(True)
        self.spinBox_exp_id.setEnabled(True)
        self.pushButton_restartPCs.setEnabled(False)
        self.isWebServerRunning = False

    def handleOutput(self, text, stdout):
        color = self.statusbox.textColor()
        self.statusbox.setTextColor(color)
        self.statusbox.setOpenExternalLinks(True)
        self.statusbox.append(text)
        self.statusbox.setTextColor(color)

    def closeEvent(self, event):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Warning")
        if self.isWebServerRunning:
            dlg.setText("The Webserver is running. Are sure you want to close the program? This will terminate the webserver.")
        else:
            dlg.setText("Are sure you want to close the program?")
        dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        button = dlg.exec()

        if button == QtWidgets.QMessageBox.StandardButton.Yes:
            #--- store the current setting in the system before closing the app
            #self.setting_Course.setValue('ta_name', self.lineEdit_ta.text())
            self.setting_Course.setValue('year', self.lineEdit_year.text() )
            self.setting_Course.setValue('semester', self.comboBox_semester.currentText())
            self.setting_Course.setValue('code', self.lineEdit_code.text() )
            #self.setting_Course.setValue('coursename', self.lineEdit_coursename.text() )
            self.setting_Course.setValue('session', self.comboBox_session.currentText())
            self.setting_Course.setValue('session_list', self.session_list)
            self.setting_Network.setValue('hostname', self.lineEdit_host.text())
            self.setting_Network.setValue('portnumber', self.lineEdit_port.text())
            #self.setting_Course.setValue('data_dir', self.lineEdit_data_dir.text())
            self.setting_Course.setValue('exp_csv_path', self.lineEdit_exp_csv.text())
            self.setting_Course.setValue('stud_csv_path', self.lineEdit_stud_csv.text())
            self.setting_Course.setValue('time_csv_path', self.lineEdit_time_csv.text())
            self.setting_Course.setValue('exp_id', int(self.spinBox_exp_id.value())  )
            self.setting_Course.setValue('n_group', int(self.lineEdit_ngroups.text()) )
            self.setting_Course.setValue('n_benches', int(self.lineEdit_nbenches.text()))
            try:
                if self.isWebServerRunning:
                    self.stop_webserver_worker()
                event.accept()
                logging.debug('The application exited properly.')
            except Exception as e:
                logging.error(f'The application exited improperly: {e}')
            
        else:
            event.ignore()
#--------------------------------------------------------------------------------
class WebServerThread(QtCore.QThread):
    def __init__(self, exp_id, host, port, parent=None ):
        super(WebServerThread, self).__init__(parent)
        self.exp_id=exp_id
        self.host = host
        self.port = port
        self.is_running = True
        
    def run(self):
        logging.info(f'Starting webserver for exp {self.exp_id}')

        self.myserver = MyWebServer(self.exp_id, self.host, self.port)
        self.myserver.run_webserver()

    def stop(self):
        self.is_running = False
        logging.info('Stopping webserver...')
        
        self.myserver.stop_webserver()
        self.terminate()

#-------------------------------------------------
if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()

    print('Welcome to YorkU PHYS Lab Seating Monitor')

    sys.exit(app.exec())