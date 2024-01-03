import logging

logger = logging.getLogger(__name__)

def extract_pc_list(pc_txt_path):
    gpc_list = []
    laptop_list = []
    gpc_map ={}
    
    with open(pc_txt_path) as f_in:
        # loop over the lines and skip empty and commented out lines and make a list of PC names
        for l in f_in:
            line = l.strip()
            if line and not line.startswith('#'):
                tmp = line.split(',')
                tmp = [x.strip() for x in tmp]
                if tmp[-1].lower() == 'g':
                    gpc_list.append(tmp[0])
                    gpc_map[tmp[0]] = [int(tmp[1]), int(tmp[2]), int(tmp[3]), int(tmp[4])]
                elif tmp[-1].lower() == 'l':
                    laptop_list.append(tmp[0])

    logger.debug(f'gpc_list: {gpc_list}')
    logger.debug(f'laptop_list: {laptop_list}')
    
    logger.info(f'{len(gpc_list)} Group PCs found')
    logger.info(f'{len(laptop_list)} Laptops found')
    
    logger.debug(f'gpc_map.items: {gpc_map.items()}')
        
        
    return gpc_list, laptop_list, gpc_map