import os
import logging

logger = logging.getLogger(__name__)

def reboot_Pcs(pc_list):
    for targetPc in pc_list:
        try:
            os.system(r'shutdown -m \\' + targetPc+ ' -r -f -t 5')
            logger.info(f' Reboot command sent to {targetPc} successfully!')
        except:
            logger.error(f' Unable to send reboot command to {targetPc}')


def extract_gpc_list(pc_txt_path):
    gpc_list = []
    laptop_list = []
    with open(pc_txt_path) as f_in:
        # loop over the lines and skip empty and commented out lines and make a list of PC names
        gpc_list = list(line for line in (l.strip() for l in f_in) if line and not line.startswith('#') and 'BC-GR' in line)
        
        logging.debug(f'{len(gpc_list)} Group PCs found')
        
    with open(pc_txt_path) as f_in:
        # loop over the lines and skip empty and commented out lines and make a list of PC names
        laptop_list = list(line for line in (l.strip() for l in f_in) if line and not line.startswith('#') and 'BC-L' in line)
        
        logging.debug(f'{len(laptop_list)} Laptops found')
    
    
    return gpc_list, laptop_list