import http.server
import socketserver
import os, shutil
import configparser as conf
import logging

class MyWebServer:
    def __init__(self, exp_id, hostname, serverport, destPc='sc-l-ph-dev-gp1'):
        self.exp_id = exp_id
        self.hostname = hostname
        self.serverport = int(serverport)
        self.dest_path =r'\\' + destPc+ r'\\seats'
        self.web_directory = os.path.join(self.dest_path,'LabSeatingWeb')

        logging.debug(f'directory= {self.web_directory}')
    
    #------------------------------------------------------------
    def _handler_from(self, directory):
        def _init(self, *args, **kwargs):
            return http.server.SimpleHTTPRequestHandler.__init__(self, *args, directory=self.directory, **kwargs)
        
        return type(f'HandlerFrom<{directory}>',
                (http.server.SimpleHTTPRequestHandler,),
                {'__init__': _init, 'directory': directory})
    
    #------------------------------------------------------------
    def _force_copy(self, source, dist, type='f'):
        logging.debug(f'source_path: {source}')
        logging.debug(f'dist_path: {dist}')

        if type == 'dir':
            try: 
                shutil.copytree(source, dist) 
            except:
                shutil.rmtree(dist)
                shutil.copytree(source, dist)
        else:
            
            try: 
                shutil.copy(source, dist)
            except:
                os.remove(dist)
                shutil.copy(source, dist)
    
    #------------------------------------------------------------
    def _server_dir_prep(self):
        cwd = os.getcwd()
        logging.debug(f'cwd: {cwd}')

        css_path = os.path.join(cwd, 'scripts', 'src', 'style.css')
        js_path = os.path.join(cwd, 'scripts', 'src', 'time.js')
        img_dir_path = os.path.join(cwd, 'scripts', 'src' ,'img')

        html_path = os.path.join(cwd, 'scripts', 'src', 'html', f'exp{self.exp_id}')
        html_files = os.listdir(html_path)
        logging.debug(f'html_path= {html_path}')
        
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
    def run_webserver(self):
        self._server_dir_prep()
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer((self.hostname, self.serverport), self._handler_from(self.web_directory))

        url = f'http://{self.hostname}:{self.serverport}'        
        try:
            logging.info(f'httpd server has been successfully started: <a href={url}>{url}</a>')
            self.httpd.serve_forever()
        except:
            logging.error('Unable to start the webserver')
    
    #------------------------------------------------------------
    def stop_webserver(self):
        self.httpd.server_close()
        logging.info('httpd server has been successfully stopped')


#===========================================================================
if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    config = conf.ConfigParser()
    configfile = 'config.conf'

    if os.path.isfile(configfile):
            config.read(configfile)
    else:
        logging.error(f'Config file {configfile} does not exist.\n Process terminated.')

    n_experiments = int(config['Course']['n_experiments'])

    exp_id = int(input("Enter the experiment id: "))
    if not 0 < exp_id <= n_experiments:
        logging.error(f'invalid experiment id. Please enter a number between 1 and {n_experiments}')
        exit()

    hostName = config['Network']['host_name']
    serverPort = int(config['Network']['server_port'])


    server = MyWebServer(exp_id, hostName, serverPort)
    server.run_webserver()