import os
import logging

logger = logging.getLogger(__name__)

def reboot_Pcs(pc_list):
    for targetPc in pc_list:
        try:
            os.system(r'shutdown -m \\' + targetPc+ '.yorku.yorku.ca -r -f -t 0')
            logger.debug(f' Reboot command sent to {targetPc} successfully!')
        except:
            logger.error(f' Unable to send reboot command to {targetPc}')


def extract_gpc_list(gpc_txt_path):
    gpc_list = []
    with open(gpc_txt_path) as f_in:
        # loop over the lines and skip empty and commented out lines and make a list of PC names
        gpc_list = list(line for line in (l.strip() for l in f_in) if line and not line.startswith('#'))
        logging.debug(f'{len(gpc_list)} Group PCs found')
        return gpc_list