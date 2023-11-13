#!/usr/bin/env python3
from typing import DefaultDict
import pandas
import numpy as np
import pickle
import logging
import random
import sys, os, shutil
import subprocess
import math
from PIL import Image, ImageFont, ImageDraw
import re

from pylatex import Document, Tabular, MultiColumn, VerticalSpace
import pylatex as pl
from pylatex.utils import NoEscape
from pylatex import utils, NewPage

logger = logging.getLogger(__name__)

#------------------------------------------------------------
def sort_helper(item):
            day_sort = {'Mon':1,'Tue':2,'Wed':3,'Thu':4,'Fri':5}
            time = item.split(",")[1].strip()
            time = int(time.split(":")[0])
            return (day_sort[item[:3]], time)
#------------------------------------------------------------
def is_file_locked(file_path):
    file_path = file_path + '.pdf'
    try:
        with open(file_path, 'w') as file:
            return False  # The file is not locked
    except PermissionError:
        return True  # The file is locked
#------------------------------------------------------------
def create_weekly_att(stud_csv_path_list, sessions, code, Exp_id):
    if sessions:
        session_keys_sorted = sorted(list(sessions.keys()), key=sort_helper)    
    
    session_ids = [sessions[key] for key in session_keys_sorted]
    
    df = concat_stud_lists(stud_csv_path_list)

    # Create a LaTeX document
    geometry_options = {"tmargin": "0.3in", "lmargin": "1in", "bmargin": "0.15in", "rmargin": "1in"}
    doc = Document(geometry_options=geometry_options)

    for session_id in session_ids:
        session_info = list(filter(lambda x: sessions[x] == session_id, sessions))[0]
        # Filter the data for the current session_id
        session_df = df.loc[df['session_id'].str.strip()==session_id]

        # Prepare the data for the table
        session_df = session_df[['first_name', 'surname']]
        session_df = session_df.rename(columns={'first_name': 'First Name', 'surname': 'Last Name'})
        session_df['Attendance'] = ''
        session_df.insert(0, ' ', range(1, 1 + len(session_df)))

        doc.append(pl.NoEscape('{'))
        doc.append(pl.Command('pagenumbering', 'gobble'))
        doc.append(pl.Command('noindent'))
        text_before_table = f"PHYS {code},  {session_info}, Exp {Exp_id}.\n\n"
        doc.append(utils.bold(text_before_table))
        text_before_table = f"Date: ________________          TA: ________________\n\n"
        doc.append(text_before_table)

        doc.append(pl.NoEscape('}'))

        # Create the Tabular environment
        with doc.create(Tabular('|' + 'p{0.5cm}|' + 'p{3cm}|' + 'p{3cm}|' + 'p{4cm}|', pos='t', row_height=1.3)) as table:
            table.add_hline()
            table.add_row(session_df.columns, mapper=utils.bold)  # Include the column names
            table.add_hline()
            counter = 1
            for i, row in session_df.iterrows():
                row_values = [row[column] for column in session_df.columns]
                if (counter % 2) == 0:
                    table.add_row(row_values)
                else:
                    #table.add_row(row_values, color="lightgray")
                    table.add_row(row_values, color="gray!10")
                table.add_hline()
                counter += 1

        # Add a page break after each table
        doc.append(NoEscape(r'\newpage'))

    # Save the multipage PDF using pdflatex as the LaTeX compiler
    output_dir = f'output_{code}'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    pdf_file_name = f'Weekly_att_Exp_{Exp_id}'
    pdf_file_path = os.path.join(output_dir, pdf_file_name)
    
    if is_file_locked(pdf_file_path):
        print("The PDF file is open in another application. Please close it to overwrite.")
        return None
    else:
        try:
            doc.generate_pdf(pdf_file_path, compiler='pdflatex', clean_tex=True)
            logger.info(f' Weekly attendance sheets are generated and written to {pdf_file_path}.pdf successfully!')
            return pdf_file_path+'.pdf'
        except subprocess.CalledProcessError as e:
            #logger.error("Error while generating PDF:", str(e))
            return None
        '''
        
        error_message = str(e)
        if "I can't write on file" in error_message:
            # Provide a message to the user
            logger.error("The PDF file is open in another application. Please close it to overwrite.")
        else:
            # Handle other subprocess errors if necessary
            logger.error("Error while generating PDF:", error_message)
        '''
    
    
    
#------------------------------------------------------------    
def _rand_group_maker(df, n_group, n_benches, optimize = True, rand_grp = True):
    
    if rand_grp:
        df_shuffled = df.sample(frac=1)
    else:
        df_shuffled = df.sample(frac=1, random_state=42)
    
    df_splits = np.array_split(df_shuffled, int(n_group))
    
    # Keep maximum number of pair students working together
    if optimize:
        if sum(i <n_benches for i in [len(grp) for grp in df_splits]) > 1:
            if len(df_splits[-1])%2 ==1 and len(df_splits[-1]!=1):
                last, df_splits[-1] = df_splits[-1].iloc[-1], df_splits[-1].iloc[:-1]
                df_splits[-2].loc[len(df_splits[-2])] = last
            
    
    return df_splits

#------------------------------------------------------------        
def _load_student_groups(pkl_file, print_result= False):
    exp_dict = DefaultDict() # exp dict: key = exp_id , value = student_groups
    try:
        with open(pkl_file, 'rb') as pickle_file:

            exp_dict = pickle.load(pickle_file)
            logger.debug(f'file {pkl_file} is loaded successfully!')
    except:
        logger.error(f'Failed to load {pkl_file}', exc_info = True)
    
    if print_result:
        _print_exp_dict(exp_dict)
    
    return exp_dict

#------------------------------------------------------------    
def _print_exp_dict(dict):  
    n_exp = len(dict)
    n_group = len(dict[0])
    
    for exp in range(n_exp):
        print(f'exp {exp} list:f')
        for g in range(n_group):
            print(dict[exp][g])
            print('-------------------------------')
        print('===============================')
        
#------------------------------------------------------------
def concat_stud_lists(stud_csv_path_list):
    stud_dfs = []
    for i, path in enumerate(stud_csv_path_list):
        df = pandas.read_csv(path, index_col= False, header=None)
        # handle two different data length in student list depending on the lab course
        n_col = len(list(df.columns))
        if n_col == 9 or n_col ==10:
            # adding header to student list
            df.columns = get_studList_header(n_col)
        else:
            logger.error('number of columns in stud csv files is not supported. Suppoerted numbers are 9 and 10.')
    
        # drop nan
        df = df.dropna()
    
        # drop LAB 99
        df = df.loc[df['session_id'].str.strip()!='LAB 99']
    
        # append suffix to session_id
        if i >0:
            df['session_id'] = df['session_id'].add(f'_{i}')
        
        stud_dfs.append(df)

    # merge all lists into one df with distinc session_id
    return pandas.concat(stud_dfs, axis=0)


#------------------------------------------------------------
def get_number_of_students(stud_csv_path_list, session):
    
    stud_df = concat_stud_lists(stud_csv_path_list)
    
    # filter the list based on the given session_id
    stud_df = stud_df.loc[stud_df['session_id'].str.strip()==session]
    
    return len(stud_df)

#-----------------------------------------------------------
def day_map(day_abr):
    days_dicts = {
            'M':'Monday',
            'T':'Tuesday',
            'W':'Wednesday',
            'R':'Thursday',
            'F':'Friday',
            }
    return days_dicts[day_abr.strip()]

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

def get_room_list(pc_dir, pc_csv_path):
    rooms = {}
    pc_df = pandas.read_csv(pc_csv_path)
    #--- drop rows with nan
    pc_df = pc_df.dropna()
    pc_df = pc_df.dropna().reset_index(drop=True)

    Room_list = list(pc_df['Room'].str.strip())
    PC_list = list(pc_df['PC_list'].str.strip())
    layout_list = list(pc_df['room_layout'].str.strip())
    room_pc_map = list(zip(Room_list, PC_list, layout_list))

    for room in room_pc_map:
        rooms[room[0]] = [os.path.join(pc_dir, room[1]), os.path.join(pc_dir, 'layouts',room[2])]
    
    return rooms

def get_session_list(time_csv_path):
    sessions = {}
    
    time_df = pandas.read_csv(time_csv_path)
    #--- drop rows with nan
    time_df = time_df.dropna()
    time_df = time_df.dropna().reset_index(drop=True)

    Type_list = list(time_df['Type'].str.strip())
    Day_list = list(time_df['Day'].str.strip())
    time_list = list(time_df['Start Time'].str.strip())
    session_list = list(zip(Type_list, Day_list, time_list))
    
    for session in session_list:
        sessions[f'{day_map(session[1])}, {session[2]} - {session[0]}'] = session[0]
    
    return sessions

def get_exp_list(exp_csv_path):
    exps = {}
    
    exp_df = pandas.read_csv(exp_csv_path)
    #--- drop rows with nan
    exp_df = exp_df.dropna()
    exp_df = exp_df.dropna().reset_index(drop=True)

    id_list = list(exp_df['exp_id'])
    title_list = list(exp_df['exp_title'].str.strip())
    
    exp_list = list(zip(id_list, title_list))
    
    for exp in exp_list:
        #exps[exp[0]] = f'{exp[0]}: {exp[1]}'
        exps[f'{exp[0]}: {exp[1]}'] = exp[0]
    
    return exps

#------------------------------------------------------------
def get_studList_header(col):
    header_10 = ["student_id","surname","first_name","email","session_id","lect_id","tutr_id","programme_title","study_level","registration_status"]
    header_9 = ["student_id","surname","first_name","email","session_id","lect_id","programme_title","study_level","registration_status"]
    return header_10 if col==10 else header_9

#------------------------------------------------------------        
def make_groups(exp_csv_path, stud_csv_path_list, time_csv_path, session_id, n_stud, n_benches, code, pkl_file_name):
    exp_df= pandas.read_csv(exp_csv_path)  
    time_df= pandas.read_csv(time_csv_path)
    stud_df = concat_stud_lists(stud_csv_path_list)

    #--- drop rows with nan
    exp_df = exp_df.dropna()
    exp_df = exp_df.dropna().reset_index(drop=True)
    time_df = time_df.dropna()
    time_df = time_df.dropna().reset_index(drop=True)
    
    # filter the lists based on the given session_id
    stud_df = stud_df.loc[stud_df['session_id'].str.strip()==session_id]

    exp_list = list(exp_df['exp_id'])
    stud_list = list(stud_df['student_id'])
    time_list = list(time_df['Type'].str.strip())

    exp_dict = DefaultDict() # exp dict: key = exp_id , value = tuple of (exp meta data) and (student_groups)
    
    n_group = math.ceil(n_stud/n_benches)
    # fill the database dictionary
    if exp_list and stud_list and time_list:
        for exp in exp_list:
            students_splits = _rand_group_maker(stud_df, n_group, n_benches, optimize=True)
            exp_dict[exp] = ( exp_df.loc[exp_df['exp_id']==exp], time_df.loc[time_df['Type'].str.strip()==session_id] , students_splits)
    else:
        logger.error('exp_list, time_list, or stud_list is empty')
        return None
        
    out_dir = f'output_{code}'
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    pkl_dir = os.path.join(out_dir, 'pkl')
    if not os.path.exists(pkl_dir):
        os.makedirs(pkl_dir)

    pkl_path = os.path.join(pkl_dir, pkl_file_name)

    logger.debug(f'pkl_path: {pkl_path}')

    # create a binary pickle file to store experiments dictionary
    pkl_f = open(pkl_path,"wb")

    # write the python object (dict) to pickle file
    try:
        pickle.dump(exp_dict, pkl_f)
        logger.info(f' File {pkl_path} is written to disk successfully!')
        
        # close file
        pkl_f.close()
        
        return pkl_path, n_group
    except:
        logger.error(f' Failed to write {pkl_path} to disk', exc_info = True)
        return None
      
    
#------------------------------------------------------------
def html_generator(pkl_path, code, n_max_group, n_benches, version, ta_name = None):
    logger.debug(f'ta_name = {ta_name}')
    out_dir = f'output_{code}'
    html_dir = os.path.join(out_dir, 'html')

    logger.debug(f'pkl_path: {pkl_path}')
    logger.debug(f'html_dir: {html_dir}')
    

    #creating a fresh html directory
    if os.path.exists(html_dir):
        shutil.rmtree(html_dir)
    os.makedirs(html_dir)
    
    dict = _load_student_groups(pkl_path, print_result=False)
    
    n_exp = len(dict)
    n_group = len(dict[1][2])
    
    logger.debug(f'n_exp: {n_exp}')
    logger.debug(f'n_group: {n_group}')
 
    for e in range (1, n_exp+1, 1):
        output_dir = os.path.join(html_dir, f'exp{e}')

        #creating output directory if not exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        df_exp_metadata = dict[e][0]
        df_time_metadata = dict[e][1]

        if ta_name == None:
            ta_name = df_time_metadata['Instructor'].iloc[0]
        
        #creating html files
        comp_html_generator(e, n_max_group, code, output_dir, dict, df_exp_metadata, df_time_metadata, ta_name, version)
    
        for g in range(n_group):
            df = dict[e][2][g].reset_index(drop=True)
            df.index += 1
            
            f_html = os.path.join(output_dir, f'g{g+1}.html')
            
            with open(f_html, 'w') as html_seating_file:
                stud_list = []
                for i in range(len(df)):
                    row = '<div class="grid-item"><a href="#">'+df.iloc[i,2] +' '+ df.iloc[i,1]+'</a></div>'
                    stud_list.append(row)
                newline = "\n" 
                seating_contents = f'''<!DOCTYPE html>
                            <html lang="en">
                            <head>
                            <META HTTP-EQUIV="CACHE-CONTROL" CONTENT="NO-CACHE">
                            <META HTTP-EQUIV="EXPIRES" CONTENT="Mon, 22 Jul 2002 11:12:01 GMT">
                            <meta name="viewport" content="width=device-width, initial-scale=1">
                            <meta http-equiv="refresh" content="15">
                            <link rel="stylesheet" href="style.css?v={round(random.randint(0, 1000)/100, 2 )}">
                            <script type="text/javascript" src="time.js"></script>
                            
                            </head>
                            <body>

                            <div class="row", style="padding:0cm">
                                <div class="column", style="width:20%">
                                    <img src=yorku-logo.jpg , style="height:30px">
                                </div>
                                <div class="column", style="width:65%">
                                    <h3 style="font-size:23px"><center>PHYS {code}, Session: {day_map(df_time_metadata['Day'].iloc[0])}, {df_time_metadata['Start Time'].iloc[0]}, TA: {ta_name}</center></h3>
                                </div>
                                <div class="column", style="width:15%">
                                    <h3><span id="ct"> </span></h3>
                                </div>
                            </div>
                            
                            <div class="row", style="padding:0cm">
                                <div class="column", style="width:50%">
                                    <div class="vertical-menu", style="width:100%">
                                        <h2><a href="#" class="active"><b>Group {g+1}</b></a></h2>
                                        <div class="grid-container">
                                            {newline.join(stud for stud in stud_list)}
                                        </div>
                                        <h3> Useful tip:</h3>
                                            <iframe src="{os.path.join('tip', df_exp_metadata['exp_tip'].iloc[0]) }" 
                                                    style="background-color:rgb(255, 230, 230);border:2px solid #b71414;"
                                                    width="100%"
                                                    height="290px">
                                            </iframe>
                                    </div>
                                </div>

                                <div class="column", style="width:50%">
                                    <div class="vertical-menu", style="width:100%">
                                        <h2><a href="#" class="active"><b>{df_exp_metadata['exp_id'].iloc[0]}: {df_exp_metadata['exp_title'].iloc[0]}</b></a></h2>
                                    </div>
                                    <div class="wrapper">
                                        <img src={os.path.join('img', df_exp_metadata['exp_img'].iloc[0]) } >
                                    </div>
                                </div>
                            </div>
                            <div class ="footer">
                              YU LabManager V{version}
                            </div>
                            </body>
                            </html>
                            '''
                try:
                    html_seating_file.write(seating_contents)
                except:
                    logger.error(f' Failed to write html files to disk', exc_info = True)
                    return None
        
        #Creating blank html page
        if n_max_group > n_group:
            for g in range(n_group, n_max_group):
                blank_f_html = os.path.join(output_dir, f'g{g+1}.html')
                
                with open(blank_f_html, 'w') as blank_html_seating_file:
                    blank_stud_list = []
                    for i in range(n_benches):
                        row = '<div class="grid-item"><a href="#">  </a></div>'
                        blank_stud_list.append(row)
                    newline = "\n" 
                    blank_seating_contents = f'''<!DOCTYPE html>
                                <html lang="en">
                                <head>
                                <META HTTP-EQUIV="CACHE-CONTROL" CONTENT="NO-CACHE">
                                <META HTTP-EQUIV="EXPIRES" CONTENT="Mon, 22 Jul 2002 11:12:01 GMT">
                                <meta name="viewport" content="width=device-width, initial-scale=1">
                                <meta http-equiv="refresh" content="15">
                                <link rel="stylesheet" href="style.css?v={round(random.randint(0, 1000)/100, 2 )}">
                                <script type="text/javascript" src="time.js"></script>
                                
                                </head>
                                <body>

                                <div class="row", style="padding:0cm">
                                    <div class="column", style="width:20%">
                                        <img src=yorku-logo.jpg , style="height:30px">
                                    </div>
                                    <div class="column", style="width:65%">
                                        <h3 style="font-size:23px"><center>PHYS {code}, Session: {day_map(df_time_metadata['Day'].iloc[0])}, {df_time_metadata['Start Time'].iloc[0]}, TA: {ta_name}</center></h3>
                                    </div>
                                    <div class="column", style="width:15%">
                                        <h3><span id="ct"> </span></h3>
                                    </div>
                                </div>
                                
                                <div class="row", style="padding:0cm">
                                    <div class="column", style="width:50%">
                                        <div class="vertical-menu", style="width:100%">
                                            <h2><a href="#" class="active"><b>Group {g+1}</b></a></h2>
                                            <div class="grid-container">
                                                {newline.join(stud for stud in blank_stud_list)}
                                            </div>
                                            <h3> Useful tip:</h3>
                                                <iframe src="{os.path.join('tip', df_exp_metadata['exp_tip'].iloc[0]) }" 
                                                        style="background-color:rgb(255, 230, 230);border:2px solid #b71414;"
                                                        width="100%"
                                                        height="290px">
                                                </iframe>
                                        </div>
                                    </div>

                                    <div class="column", style="width:50%">
                                        <div class="vertical-menu", style="width:100%">
                                            <h2><a href="#" class="active"><b>{df_exp_metadata['exp_id'].iloc[0]}: {df_exp_metadata['exp_title'].iloc[0]}</b></a></h2>
                                        </div>
                                        <div class="wrapper">
                                            <img src={os.path.join('img', df_exp_metadata['exp_img'].iloc[0]) } >
                                        </div>
                                    </div>
                                </div>
                                <div class ="footer">
                                    YU LabManager V{version}
                                </div>
                                </body>
                                </html>
                                '''
                    try:
                        blank_html_seating_file.write(blank_seating_contents)
                    except:
                        logger.error(f' Failed to write blank html files to disk', exc_info = True)
                        return None

                
    logger.info(f' Seating html files are generated and written to {html_dir} successfully!')
    return html_dir
#------------------------------------------------------------
def comp_html_generator(exp, n_max_group, code, output_dir, dict, df_exp_metadata, df_time_metadata, ta_name, version):
    n_group = len(dict[1][2])
    
    f_html = os.path.join(output_dir, 'g99.html')
    stud_list = []

    blank_group = []
    for i in range(4):
        row = '<div class="grid-item"><a href="#">  </a></div>'
        blank_group.append(row)

    for g in range(n_group):
        df = dict[exp][2][g].reset_index(drop=True)
        df.index += 1
        _list = []
        for i in range(len(df)):
            row = '<div class="grid-item"><a href="#">'+df.iloc[i,2] +' '+ df.iloc[i,1]+'</a></div>'
            _list.append(row)
       
        stud_list.append(_list)     
    
    newline = "\n"

    seating_header = f'''
        <div class="row">
            <div class="column", style="width:20%">
                <img src=yorku-logo.jpg , style="height:30px; padding:0cm">
            </div>
            <div class="column", style="width:65%">
                <h3 style="font-size:23px"><center>PHYS {code}, Session: {day_map(df_time_metadata['Day'].iloc[0])}, {df_time_metadata['Start Time'].iloc[0]}, TA: {ta_name}</center></h3>
            </div>
            <div class="column", style="width:15%">
                <h3><span id="ct"> </span></h3>
            </div>
        </div>
    '''
    g_list = list(range(1, n_max_group+1))
    col1_groups =''
    col2_groups =''

    # column 1
    for g in g_list[:math.ceil(n_max_group/2)]:
        if g <= n_group:
            col1_groups += f'''
                <div class="vertical-menu", style="width:100%">
                    <h2><a href="#" class="active"><b>Group {g}</b></a></h2>
                    <div class="grid-container">
                        {newline.join(stud for stud in stud_list[g-1])}
                    </div>
                </div>
            '''
        # handeling empty groups
        else:
            col1_groups += f'''
                <div class="vertical-menu", style="width:100%">
                    <h2><a href="#" class="active"><b>Group {g}</b></a></h2>
                    <div class="grid-container">
                        {newline.join(stud for stud in blank_group)}
                    </div>
                </div>
            '''

    # column 2
    for g in g_list[math.ceil(n_max_group/2):]:
        if g <= n_group:
            col2_groups += f'''
                <div class="vertical-menu", style="width:100%">
                    <h2><a href="#" class="active"><b>Group {g}</b></a></h2>
                    <div class="grid-container">
                        {newline.join(stud for stud in stud_list[g-1])}
                    </div>
                </div>
            '''
        # handeling empty groups
        else:
            col2_groups += f'''
                <div class="vertical-menu", style="width:100%">
                    <h2><a href="#" class="active"><b>Group {g}</b></a></h2>
                    <div class="grid-container">
                        {newline.join(stud for stud in blank_group)}
                    </div>
                </div>
            '''
    seating_groups =f'''
        <div class="row", style="padding:0cm">
        <div class="column", style="width:30%">
        {col1_groups}
        </div>
        <div class="column", style="width:30%">
        {col2_groups}
        </div>
    '''

    seating_img_tip = f'''
        <div class="column", style="width:40%">
                        <div class="vertical-menu", style="width:100%">
                            <h2><a href="#" class="active"><b>{df_exp_metadata['exp_id'].iloc[0]}: {df_exp_metadata['exp_title'].iloc[0]}</b></a></h2>
                        </div>
                        <div class="wrapper_all">
                            <img src={os.path.join('img', df_exp_metadata['exp_img'].iloc[0]) } >
                        </div>
                        <div class="wrapper_all_tip">
                        <h3> Useful tip:</h3>
                            <iframe src="{os.path.join('tip', df_exp_metadata['exp_tip'].iloc[0]) }" 
                                style="background-color:rgb(255, 230, 230);border:2px solid #b71414;"
                                width="100%"
                                height="300px">
                            </iframe>
                        </div>
                    </div>
                </div>  
    '''
    # constructing the html page
    page_contents = f'''<!DOCTYPE html>
        <html lang="en">
        <head>
            <META HTTP-EQUIV="CACHE-CONTROL" CONTENT="NO-CACHE">
            <META HTTP-EQUIV="EXPIRES" CONTENT="Mon, 22 Jul 2002 11:12:01 GMT">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta http-equiv="refresh" content="15">
            <link rel="stylesheet" href="style.css?v={round(random.randint(0, 1000)/100, 2 )}">
            <script type="text/javascript" src="time.js"></script>                
        </head>

        <body>
            {seating_header}
            {seating_groups}
            {seating_img_tip}
            <div class ="footer">
                YU LabManager V{version}
            </div>
        </body>
        
        </html>
    '''

    with open(f_html, 'w') as html_seating_file:

        try:
            html_seating_file.write(page_contents)
            return True
        except:
            logger.error(f' Failed to write html files to disk', exc_info = True)
            return None











#------------------------------------------------------------
def print_on_layout(gpc_map, room, room_list, exp_id, pkl_path):
    
    if room not in room_list:
        print(f'{room} room is not supported')
        return
    
    layout_src = room_list[room][1]
    out_dir = 'output_layout'

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    lab_layout_out_file = os.path.join(out_dir, 'lab_layout_grp.png')
    
    # g_cordination dictionary
    g_cord_dict = cord_map(room, gpc_map)
    
    text_char_limit = 20
    text_color = 'red'  
    
    
    # Open the layout image
    if os.path.isfile(layout_src):
        myLayout = Image.open(layout_src)
    else:
        logger.error('Layout file does not exist!')
        return

    # Create a font
    font_size = 65
    font_path = os.path.join('scripts', 'arial.ttf')
    try:
        textFont = ImageFont.truetype(font_path, font_size)
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
        logger.error('Could not write on the layout image.')

    