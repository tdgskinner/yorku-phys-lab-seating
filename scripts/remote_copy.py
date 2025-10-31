import os, stat, shutil
import logging
import time
import glob
import tempfile

logger = logging.getLogger(__name__)

def remove_readonly(func, path, _):
    "Removes read only property from a folder to allow it to be removed/overwritten"
    os.chmod(path, stat.S_IWRITE)
    func(path)

class Remote_GPC_manager:
    def __init__(self, localCopy):
        self.do_localCopy = localCopy # False = copy to remote target PC, True = copy to local PC (for test)
        logger.debug(f'remoteCopy service initiated with localCopy= {self.do_localCopy}')
    
    #------------------------------------------------------------
    def _force_copy(self, source, dest, type='f'):
        """
        Attempts to copy file/directory from given source path to destination path.
        
        Called by:
            class Remote_GPC_manager
                _server_dir_prep()
                
        Parameters
        ----------
        source : 
            Source path of the file to be copied
        dest : 
            Destination path for the file to be copied to
        type : 
            Whether the path refers to a directory or a file. The default is 'f' for file.

        Returns:
            None.

        """
        
        logger.debug(f'source_path: {source}')
        logger.debug(f'dest_path: {dest}')
        
        # Commented out due to unsafe copying, refreshing htmls would break and not update properly if copy peformed during a refresh - Leya, 10/10/25
        # Uncommented: I don't think the above issue actually occurs, and if it does it's rare enough to live with
        # Real source of problem: Python commands cannot delete folders set to "read only" in windows.
        # Fixed by removing this property when required. - Taylor 21/Oct/2025
        
        if type == 'dir':
            try:
                shutil.copytree(source, dest)
            except:
                shutil.rmtree(dest, onerror=remove_readonly)
                shutil.copytree(source, dest)            
        else:
            try:
                shutil.copy(source, dest)
            except:
                os.remove(dest)
                shutil.copy(source, dest)
        
        # # Possible fix for copying files/directories safely, works with local copy, but needs testing on actual group PCs - Leya, 10/10/25
        
        # # Sets max attempts to copy file/directory
        # copy_attempts = 3
        # # Sets a delay in between successive attempts to copy
        # delay = 2
        
        # # While there are still attempts to copy
        # while copy_attempts > 0:
            
        #     try:
        #         if type == 'dir':
        #             # Makes a temp directory for new directory and copies it to same path
        #             temp_dest = tempfile.mkdtemp(dir=os.path.dirname(dest))
        #             shutil.copytree(source, temp_dest, dirs_exist_ok=True)
                
        #         else:
        #             # Makes a temp file for new file in the destination directory, closes file descriptor
        #             fd, temp_dest = tempfile.mkstemp(dir=os.path.dirname(dest))
        #             os.close(fd)
        #             shutil.copy(source, temp_dest)
                
        #         # Atomically replace the old file/directory with the temp file/directory
        #         os.replace(temp_dest, dest)
        #         logger.info(f'"{dest}" updated successfully.')
        #         # Exit the while loop if successful
        #         return
            
        #     # If an attempt to copy fails
        #     except Exception as e:
        #         copy_attempts -= 1
        #         logger.info(f'Copy attempt failed for "{dest}": {e}. Retrying in {delay} seconds. ({copy_attempts} attempts remaining).')
                
        #         # Remove temp file/directory
        #         if temp_dest and os.path.exists(temp_dest):
        #             if type == 'dir':
        #                 shutil.rmtree(temp_dest)
        #             else:
        #                 os.remove(temp_dest)
                
        #         # Delays the next attempt if attempts still remaining
        #         if copy_attempts > 0:
        #             time.sleep(delay)
                    
        #         else:
        #             logger.error(f'All 3 attempts failed. Could not update "{dest}". Last error: {e}')
        #             # Exit the while loop after using up all attempts
        #             return
        
        
        
    #------------------------------------------------------------
    def _server_dir_prep(self, user_data_dir, exp_id, gpc, group_id, src_dir, code):
        """
        Called by: 
            
            class Remote_GPC_manager 
                run_copyfile()


        Returns
            None.

        """
        
        cwd = os.getcwd()
       
        if self.do_localCopy:
            #self.dest_path = src_dir
            self.dest_path = os.path.join(user_data_dir, f'output_{code}')
        else:
            self.dest_path = os.path.join(r'\\' + gpc, 'phys')
        
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
        # if os.path.exists(self.web_directory):
        #     shutil.rmtree(self.web_directory)
        
        if not(os.path.exists(self.web_directory)):
            os.makedirs(os.path.join(self.web_directory,'img'))
            os.makedirs(os.path.join(self.web_directory,'tip'))
        
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
            
        # Copy the lab_config_txt to only the Group 1 PC as a text file
        if "GR1" in gpc and self.lab_config_txt and not self.do_localCopy:
            try:
                self._copy_lab_config(self.lab_config_txt)
            except Exception as e:
                logger.error(f"Failed to copy lab_config.txt for {gpc}: {e}")

    #------------------------------------------------------------
    def run_copyfile(self, user_data_dir, exp_id, gpc, group_id, src_dir, code, lab_config_txt=None):
        """
        Called by:
            
            YorkULabSeating.py
                class CopyFileThread()
                    run()

        Returns:
            bool
            Returns true if file copying was successful, otherwise returns false.

        """
       
        try:
            # Save the lab config text in this class instance
            self.lab_config_txt = lab_config_txt
            self._server_dir_prep(user_data_dir, exp_id, gpc, group_id, src_dir, code)
            logger.info(f' Group ({group_id}) html file is copied to {gpc} successfully!')
            return True
        except Exception as e:
            logger.debug(f' Unable to copy html file to {gpc}: {e}')
            return False
    
    #------------------------------------------------------------
    def _copy_lab_config(self, lab_config_txt):
        
        # Create a temp file containing lab_config_txt
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as tmp_file:
            tmp_file.write(lab_config_txt)
            tmp_path = tmp_file.name
            
        try:
            # Place lab_config.txt in the web directory of the target PC
            dest_path = os.path.join(self.web_directory, "lab_config.txt")
            
            # Copy text file to web_directory
            self._force_copy(tmp_path, dest_path)
            logger.info(f"lab_config.txt copied to {dest_path}")
        
        except Exception as e:
            logger.error(f"Error copying lab_config.txt to {self.web_directory}: {e}")
            
        # Remove temp file after copying
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    
    #------------------------------------------------------------
    def read_lab_config(self, pc_name):
        """
        Reads lab_config.txt from the given PC's web directory folder.
        
        Parameters:
            pc_name: must be str of format: "SC-L-PH-BC3-GR1.yorku.yorku.ca"
            
        Returns:
            str containing lab config info, or error message
        """
        
        config_path = os.path.join(r'\\' + pc_name, 'phys', 'LabSeatingWeb', 'lab_config.txt')
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                return text or "(Empty config file)"
            else:
                return "(No config file found)"
        except Exception as e:
            return f"(Error reading from {pc_name}: {e})"
        

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