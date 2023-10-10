import os
from PIL import Image, ImageFont, ImageDraw
from typing import DefaultDict
import pickle
import re
import warnings

# Disable DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

def _load_student_groups(pkl_file):
    exp_dict = DefaultDict() # exp dict: key = exp_id , value = student_groups
    try:
        with open(pkl_file, 'rb') as pickle_file:

            exp_dict = pickle.load(pickle_file)
            print(f'file {pkl_file} is loaded successfully!')
    except:
        print(f'Failed to load {pkl_file}')
    
    return exp_dict

#----------------------------------------------------------------
def cord_map(room, gpc_map):

    g_cord_map = {}
    # relative coordination of the PHYS labs layouts
    for gpc in list(gpc_map.keys()):
        
        # Define a regular expression pattern to match "GR" followed by one or two digits and a dot 
        pattern = r'GR(\d{1,2})\.'
        match = re.search(pattern, gpc)
        if match:
            gpc_id = int(match.group(1))
            x = gpc_map[gpc][0]
            y = gpc_map[gpc][1]
            line_spacing = gpc_map[gpc][2]
            #rel_y = gpc_map[gpc][3]
            rel_cord= [[0, 0],[0, line_spacing],[0, 2*line_spacing],[0, 3*line_spacing]]
            tmp_cord = []
            
            for i in range(len(rel_cord)):
                tmp_cord.append([x+rel_cord[i][0], y+rel_cord[i][1]])
                
        g_cord_map[gpc_id] = tmp_cord

    return g_cord_map
#----------------------------------------
def print_on_layout(layout_src, gpc_map, room, room_list, exp_id, pkl_path): 
    
    if room not in room_list:
        print(f'{room} room is not supported')
        return
    
    out_dir = 'output_layout'

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    lab_layout_out_file = os.path.join(out_dir, 'lab_layout_grp.png')
    
    # g_cordination dictionary
    g_cord_dict = cord_map(room, gpc_map)
    
    text_char_limit = 20
    text_color = 'red'  
    
    
    # Open the layout image
    myLayout = Image.open(layout_src)

    # Create a font
    font_size = 65
    try:
        textFont = ImageFont.truetype('arial.ttf', font_size)
    except IOError:
        # If 'arial.ttf' is not found, load the default font
        textFont = ImageFont.load_default()
    
    
    # Create a drawing context
    editImage = ImageDraw.Draw(myLayout)

    # Define background color
    background_color = (154, 237, 176)  # Use (R, G, B) values for white background

    dict = _load_student_groups(pkl_path)

    for gpc in list(gpc_map.keys()):
        g_id = gpc_map[gpc][3] -1
        if g_id <len(dict[exp_id][2]):
            # Define a regular expression pattern to match "GR" followed by one or two digits and a dot 
            pattern = r'GR(\d{1,2})\.'
            match = re.search(pattern, gpc)
            if match:
                gpc_id = int(match.group(1))

            df = dict[exp_id][2][g_id].reset_index(drop=True)
            df.index += 1
       
            for i in range(len(df)):
                stud_name = df.iloc[i,2] +' '+ df.iloc[i,1]
            
                # Calculate the text size
                text_width, text_height = editImage.textsize(stud_name[:text_char_limit], font=textFont)
            
                # Calculate the position for text to be centered
                x = g_cord_dict[gpc_id][i][0]
                y = g_cord_dict[gpc_id][i][1]
           
                # Create a rectangle with the background color
                editImage.rectangle([x, y, x + text_width, y + text_height], fill=background_color)
            
                # Write the text on the colored background 
                editImage.text((x, y), stud_name[:text_char_limit], fill=text_color, font=textFont)

    #save Image
    try:
        myLayout.save(lab_layout_out_file)
        return lab_layout_out_file
    except:
        print('Could not write on the layout image.')  


layout_src = 'BC_102C_layout.png'
room = 'BC_102C'
room_list = ['BC_102C','BC_102D','BC_102F']
exp_id = 1
pkl_path = 'SeatingDB_Fall_2023_1411_LAB01.pkl'
gpc_map = {
    'SC-L-PH-BC3-GR1.yorku.yorku.ca' : [3650, 400 , 140, 1],
    'SC-L-PH-BC3-GR2.yorku.yorku.ca' : [2250, 400 , 140, 2],
    'SC-L-PH-BC3-GR3.yorku.yorku.ca' : [850, 400 , 140, 3],
    'SC-L-PH-BC3-GR4.yorku.yorku.ca' : [850 , 2280, 140, 4],
    'SC-L-PH-BC3-GR5.yorku.yorku.ca' : [2250, 2280, 140, 5],
    'SC-L-PH-BC3-GR6.yorku.yorku.ca' : [3650, 2280, 140, 6],
}

print_on_layout(layout_src, gpc_map, room, room_list, exp_id, pkl_path)


