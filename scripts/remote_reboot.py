import os
import logging
import re

logger = logging.getLogger(__name__)

class Remote_PC_Reboot:
    def __init__(self):
        logger.debug(f'Remote_PC_Reboot service initiated')
        return
    
    #------------------------------------------------------------

    def reboot_Pcs(self, pc):
        try:
            os.system(r'shutdown -m \\' + pc+ ' -r -f -t 3')
            logger.info(f' Reboot command sent to {pc} successfully!')
            return True
        except Exception as e:
            logger.error(f' Unable to send reboot command to {pc}: {e}')
            return False