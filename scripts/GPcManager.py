import os
import logging
import re

logger = logging.getLogger(__name__)

def extract_pc_list(pc_txt_path):
    gpc_list = []
    laptop_list = []
    grp_identifier = re.compile('-G\D+')
    laptop_identifier = re.compile('-L\d+')
    with open(pc_txt_path) as f_in:
        # loop over the lines and skip empty and commented out lines and make a list of PC names
        gpc_list = list(line for line in (l.strip() for l in f_in) if line and not line.startswith('#') and grp_identifier.search(line))
        
        logging.debug(f'{len(gpc_list)} Group PCs found')
        
    with open(pc_txt_path) as f_in:
        # loop over the lines and skip empty and commented out lines and make a list of PC names
        laptop_list = list(line for line in (l.strip() for l in f_in) if line and not line.startswith('#') and laptop_identifier.search(line))
        
        logging.debug(f'{len(laptop_list)} Laptops found')
    
    
    return gpc_list, laptop_list