import sys, time , os, signal
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6 import uic

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
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi('YorkULabSeating.ui',self)

        stdout = OutputWrapper(self, True)
        stdout.outputWritten.connect(self.handleOutput)
        stderr = OutputWrapper(self, False)
        stderr.outputWritten.connect(self.handleOutput)


        self.exp_id     = self.spinBox_exp_id.value()
        self.pkl_file   = self.lineEdit_pkl.text()
        self.coursename = self.lineEdit_coursename.text() 
        self.code       = self.lineEdit_code.text() 
        self.TA_name    = self.lineEdit_ta.text() 
        self.data_dir   = self.lineEdit_data_dir.text()
        
        self.exp_csv_path = os.path.join('scripts', self.data_dir, self.lineEdit_exp_csv.text() )
        self.stud_csv_path = os.path.join('scripts', self.data_dir, self.lineEdit_stud_csv.text() )
        
        self.session    = self.lineEdit_session.text()
        self.n_group    = self.lineEdit_ngroups.text()
        self.hostname   = self.lineEdit_host.text()
        self.portnumber = self.lineEdit_port.text()
        self.thread={}

        #--slots
        self.pushButton_save_settings.clicked.connect(self.save_button_click)
        self.pushButton_grouping.clicked.connect(lambda: seating.make_groups(self.exp_csv_path, self.stud_csv_path, self.session, self.n_group, self.pkl_file )) 
        
        self.pushButton_htmlgen.clicked.connect(self.check_pkl)
        
        self.spinBox_exp_id.valueChanged.connect(self.set_spin_value)
        
        self.pushButton_start_webserver.clicked.connect(self.start_webserver_worker)
        self.pushButton_stop_webserver.clicked.connect(self.stop_webserver_worker)
    
    def save_button_click(self):
        self.exp_id     = self.spinBox_exp_id.value()
        self.pkl_file = self.lineEdit_pkl.text()
        self.coursename = self.lineEdit_coursename.text() 
        self.code       = self.lineEdit_code.text() 
        self.TA_name    = self.lineEdit_ta.text() 
        self.data_dir    = self.lineEdit_data_dir.text()
        
        self.exp_csv_path = os.path.join('scripts', self.data_dir, self.lineEdit_exp_csv.text() )
        self.stud_csv_path = os.path.join('scripts', self.data_dir, self.lineEdit_stud_csv.text() )
        
        self.session = self.lineEdit_session.text()
        self.n_group = self.lineEdit_ngroups.text()
        self.hostname   = self.lineEdit_host.text()
        self.portnumber = self.lineEdit_port.text()
        
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Inof")
        dlg.setText("Settings saved")
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Information)
        dlg.exec()
    
    def set_spin_value(self):
        self.exp_id = self.spinBox_exp_id.value()

    
    def check_pkl(self):
        pkl_path = os.path.join('scripts', 'src', 'pkl', self.pkl_file)

        if os.path.exists(pkl_path):
            seating.html_generator(self.pkl_file, self.coursename, self.code, self.TA_name)
        else:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"{self.lineEdit_pkl.text()} does not exit. Run Grouping first to generate it.")
            dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            dlg.exec()

    def start_webserver_worker(self):
        self.thread[1] = WebServerThread(self.exp_id, self.hostname, self.portnumber, parent=None)
        self.thread[1].start()
        self.pushButton_start_webserver.setEnabled(False)
        self.spinBox_exp_id.setEnabled(False)
        self.pushButton_stop_webserver.setEnabled(True)
    
    def stop_webserver_worker(self):
        self.thread[1].stop()
        self.pushButton_start_webserver.setEnabled(True)
        self.spinBox_exp_id.setEnabled(True)
        self.pushButton_stop_webserver.setEnabled(False)

    
    def handleOutput(self, text, stdout):
        color = self.statusbox.textColor()
        self.statusbox.setTextColor(color)
        #self.statusbox.insertPlainText(text)
        self.statusbox.append(text)
        self.statusbox.setTextColor(color)

    def closeEvent(self, event):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Warning")
        dlg.setText("Are sure you want to close the program?")
        dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        button = dlg.exec()

        if button == QtWidgets.QMessageBox.StandardButton.Yes:
            event.accept()
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
        #print(f'Starting webserver for exp {self.exp_id}')
        logging.info(f'Starting webserver for exp {self.exp_id}')

        self.myserver = MyWebServer(self.exp_id, self.host, self.port)
        self.myserver.run_webserver()

    def stop(self):
        self.is_running = False
        #print('Stopping webserver...')
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