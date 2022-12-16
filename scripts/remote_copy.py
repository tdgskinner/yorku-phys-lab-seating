import os, shutil
import logging

logger = logging.getLogger(__name__)

class MyRemoteCopyFile:
    def __init__(self):
        pass
    
    #------------------------------------------------------------
    def _force_copy(self, source, dest, type='f'):
        logger.debug(f'source_path: {source}')
        logger.debug(f'dist_path: {dest}')
        
        if type == 'dir':
            try: 
                shutil.copytree(source, dest) 
            except:
                shutil.rmtree(dest)
                shutil.copytree(source, dest)
        else: 
            try: 
                shutil.copy(source, dest)
            except:
                os.remove(dest)
                shutil.copy(source, dest)
        
    #------------------------------------------------------------
    def _server_dir_prep(self, exp_id, gpc):
        cwd = os.getcwd()
        logger.debug(f'cwd: {cwd}')

        self.dest_path =r'\\' + gpc+ r'\\phys'
        self.web_directory = os.path.join(self.dest_path,'LabSeatingWeb')

        css_path = os.path.join(cwd, 'scripts', 'src', 'style.css')
        js_path = os.path.join(cwd, 'scripts', 'src', 'time.js')
        img_dir_path = os.path.join(cwd, 'scripts', 'src' ,'img')

        html_path = os.path.join(cwd, 'scripts', 'src', 'html', f'exp{exp_id}')
        html_files = os.listdir(html_path)
        logger.debug(f'html_path= {html_path}')
        
        #creating a fresh web_directory
        if os.path.exists(self.web_directory):
            shutil.rmtree(self.web_directory)
        os.makedirs(self.web_directory)
        
        self._force_copy(css_path, os.path.join(self.web_directory,'style.css'))
        self._force_copy(js_path, os.path.join(self.web_directory,'time.js'))
        self._force_copy(img_dir_path, os.path.join(self.web_directory,'img'), type='dir')

        for f in html_files:
            self._force_copy(os.path.join(html_path, f), os.path.join(self.web_directory, f))
        
    #------------------------------------------------------------
    def run_copyfile(self, exp_id, gpc_list):
        status = {}
        for gpc in gpc_list:
            try:
                self._server_dir_prep(exp_id, gpc)
                logger.info(f' html files are copied in {gpc} successfully!')               
                status[gpc] = True        
            except Exception as e:
                logger.debug(f' Unable to copy files to group PC {gpc}: {e}')
                status[gpc] = False
        
        return status

