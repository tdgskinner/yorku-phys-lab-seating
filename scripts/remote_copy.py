import os, shutil
import logging
import time
import glob

logger = logging.getLogger(__name__)

class Remote_GPC_manager:
    def __init__(self, localCopy):
        self.do_localCopy = localCopy # False = copy to remote target PC, True = copy to local PC (for test)
        logger.debug(f'remoteCopy service initiated with localCopy= {self.do_localCopy}')
    
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
    def _server_dir_prep(self, user_data_dir, exp_id, gpc, group_id, src_dir, code):
        cwd = os.getcwd()
       
        if self.do_localCopy:
            #self.dest_path = src_dir
            self.dest_path = os.path.join(user_data_dir, f'output_{code}')
        else:
            self.dest_path =r'\\' + gpc+ r'\\phys'
        
        self.web_directory = os.path.join(self.dest_path,'LabSeatingWeb')
        out_dir = os.path.join(user_data_dir, f'output_{code}')
        
        layout_path = os.path.join(user_data_dir, 'output_layout', 'lab_layout_grp.png')
        
        css_path_1 = os.path.join(cwd, 'assets', 'style_small.css')
        css_path_2 = os.path.join(cwd, 'assets', 'style_large.css')
        css_path_3 = os.path.join(cwd, 'assets', 'style_all.css')
        
        YUlogo_path = os.path.join(cwd,'assets','yorku-logo.jpg')
        img_dir_path = os.path.join(src_dir ,'img')
        tip_dir_path = os.path.join(src_dir, 'tip')

        html_path = os.path.join(cwd, out_dir, 'html', f'exp{exp_id}')
        html_files = os.listdir(html_path)
        logger.debug(f'---img_dir_path= {img_dir_path}')
        
        #creating a fresh web_directory
        if os.path.exists(self.web_directory):
            shutil.rmtree(self.web_directory)
        
        os.makedirs(self.web_directory)
        
        self._force_copy(css_path_1, os.path.join(self.web_directory,'style_small.css'))
        self._force_copy(css_path_2, os.path.join(self.web_directory,'style_large.css'))
        self._force_copy(css_path_3, os.path.join(self.web_directory,'style_all.css'))
        self._force_copy(YUlogo_path, os.path.join(self.web_directory,'yorku-logo.jpg'))
        self._force_copy(img_dir_path, os.path.join(self.web_directory,'img'), type='dir')
        self._force_copy(tip_dir_path, os.path.join(self.web_directory,'tip'), type='dir')
        self._force_copy(layout_path, os.path.join(self.web_directory,'img','lab_layout_grp.png'))
        

        for f in html_files:
            if int(f.split('.')[0][1:])==group_id:
                self._force_copy(os.path.join(html_path, f), os.path.join(self.web_directory, 'index.html'))
        # copying comp. html to all PCs 
        self._force_copy(os.path.join(html_path, 'g99.html'), os.path.join(self.web_directory, 'index_all.html'))
        
        # copy g1.html to local PC for testing
        if self.do_localCopy:
            self._force_copy(os.path.join(html_path, 'g1.html'), os.path.join(self.web_directory, 'index.html'))

    #------------------------------------------------------------
    def run_copyfile(self, user_data_dir, exp_id, gpc, group_id, src_dir, code):
       
        try:
            self._server_dir_prep(user_data_dir, exp_id, gpc, group_id, src_dir, code)
            logger.info(f' Group ({group_id}) html file is copied to {gpc} successfully!')               
            return True
        except Exception as e:
            logger.debug(f' Unable to copy html file to {gpc}: {e}')
            return False

#===================================================================
class Remote_LPC_manager:
    def __init__(self, localCopy):
        self.do_localCopy = localCopy # False = copy to remote target PC, True = copy to local PC (for test)
        logger.debug(f'Remote_LPC_manager service initiated with localCopy= {self.do_localCopy}')
    
    #------------------------------------------------------------
    def run_copyfile(self, lpc, selected_files, dest_path):
        client_address = r'\\' + lpc
        destination_path = os.path.join(client_address, dest_path)
        
        failed_att = False
        
        for source_path in selected_files:
            source_name = os.path.basename(source_path)
            destination = os.path.join(destination_path, source_name)
            
            try:
                if not os.path.exists(destination_path):
                    os.makedirs(destination_path)
                shutil.copy(source_path, destination)
                logger.debug(f"Successfully copied file: {source_path} to {destination}")
            except Exception as e:
                failed_att = True
                logger.debug(f"Unable to copy file: {source_path} to {destination} - {e}")
                logger.info(f"Failed to copy all files to {destination}")
                return False
        
        if not failed_att:
            logger.info(f"Successfully copied all files to {destination}")
            return True
    
    #------------------------------------------------------------        
    def run_delete(self, lpc, to_delete_list, dest_path):
        client_address = r'\\' + lpc
        for to_delete in to_delete_list:
            path_to_delete = os.path.join(client_address, dest_path.strip(), to_delete)

            if os.path.isfile(path_to_delete):
                self.run_deletefile(client_address, path_to_delete)
            
            elif os.path.isdir(path_to_delete):
                self.run_rmTree(client_address, path_to_delete)
        return True

    #------------------------------------------------------------        
    def run_deletefile(self, client_address, file_to_delete):
        
        failed_att = False
        
        if '*' in file_to_delete:
            matching_files = glob.glob(file_to_delete)
            for matching_file in matching_files:
                try:
                    os.remove(matching_file)
                    logger.debug(f"Successfully deleted file: {matching_file}")
                except Exception as e:
                    failed_att = True
                    logger.debug(f"Failed to delete file: {matching_file} - {e}")
        else:
            try:
                os.remove(file_to_delete)
                logger.debug(f"Successfully deleted file: {file_to_delete}")
            except Exception as e:
                failed_att = True
                logger.debug(f"Failed to delete file: {file_to_delete} - {e}")
        
        if failed_att:
            logger.info(f"Failed to delete all files from {client_address}")
        
        else:
            logger.info(f"Successfully Deleted all files from {client_address}")
    
    #------------------------------------------------------------
    def run_rmTree(self, client_address, dir_to_delete):
        
        failed_att = False
        
        try:
            shutil.rmtree(dir_to_delete)
            logger.debug(f"Successfully deleted directory: {dir_to_delete}")
        except Exception as e:
            failed_att = True
            logger.debug(f"Failed to delete file: {dir_to_delete} - {e}")
        
        if failed_att:
            logger.info(f"Failed to delete all directories from {client_address}")
        
        else:
            logger.info(f"Successfully Deleted all directories from {client_address}")