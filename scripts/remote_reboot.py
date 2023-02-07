import os
import logging
import re

logger = logging.getLogger(__name__)

class Remote_PC_Reboot:
    def __init__(self):
        logger.debug(f'Remote_PC_Reboot service initiated')
        return
    
    #------------------------------------------------------------

    def reboot_Pcs(self, pc_list):
        status = {}

        for targetPc in pc_list:
            try:
                os.system(r'shutdown -m \\' + targetPc+ ' -r -f -t 3')
                logger.info(f' Reboot command sent to {targetPc} successfully!')
                status[targetPc] = True
            except Exception as e:
                logger.error(f' Unable to send reboot command to {targetPc}: {e}')
                status[targetPc] = False
        
        return status


    def extract_gpc_list(self, pc_txt_path):
        gpc_list = []
        laptop_list = []
        laptop_identifier = re.compile('-L\d+')
        with open(pc_txt_path) as f_in:
            # loop over the lines and skip empty and commented out lines and make a list of PC names
            gpc_list = list(line for line in (l.strip() for l in f_in) if line and not line.startswith('#') and '-GR' in line)
            
            logging.debug(f'{len(gpc_list)} Group PCs found')
            
        with open(pc_txt_path) as f_in:
            # loop over the lines and skip empty and commented out lines and make a list of PC names
            laptop_list = list(line for line in (l.strip() for l in f_in) if line and not line.startswith('#') and laptop_identifier.search(line))
            
            logging.debug(f'{len(laptop_list)} Laptops found')
        
        
        return gpc_list, laptop_list