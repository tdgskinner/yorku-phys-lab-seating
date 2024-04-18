#!/usr/bin/env python3
from typing import DefaultDict
import pandas
import numpy as np
import pandas as pd
import pickle
import logging
import random
import sys, os, shutil
import subprocess
import math
from PIL import Image, ImageFont, ImageDraw
import re

from pylatex import Document, Tabular
import pylatex as pl
from pylatex.utils import NoEscape
from pylatex import utils, NewPage
from datetime import datetime, timedelta

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
def create_weekly_att(user_data_dir, stud_csv_path_list, sessions, code, Exp_id, exp_title, extended_attlist_mode, att_column, customized_att):
    if sessions:
        session_keys_sorted = sorted(list(sessions.keys()), key=sort_helper)    
    
    session_ids = [sessions[key] for key in session_keys_sorted]
    logger.debug(f'session_ids: {session_ids}')
    
    df, date_modified = concat_stud_lists(stud_csv_path_list)

    # Create a LaTeX document
    if extended_attlist_mode:
        geometry_options = {"tmargin": "0.6in", "lmargin": "0.2in", "bmargin": "0.2in", "rmargin": "0.3in"}
    else:
        geometry_options = {"tmargin": "0.6in", "lmargin": "1in", "bmargin": "0.2in", "rmargin": "1in"}
    
    doc = Document(geometry_options=geometry_options)
    footer = ''
    footer_DB_time = f'DB last update: {date_modified}'

    for session_id in session_ids:
        session_info = list(filter(lambda x: sessions[x] == session_id, sessions))[0]
        # Filter the data for the current session_id
        session_df = df.loc[df['session_id'].str.strip()==session_id[0]]

        # Prepare the data for the table
        table_spec = '|' + 'p{0.4cm}|' + 'p{3.5cm}|' + 'p{3.5cm}|' + 'p{4cm}|'
        session_df = session_df[['first_name', 'surname']]
        session_df = session_df.rename(columns={'first_name': 'First Name', 'surname': 'Last Name'})
        
        if extended_attlist_mode and att_column:
            if not customized_att:
                columns_default = att_column.get('Extended (Default)')[0]
                footer = att_column.get('Extended (Default)')[1]
                table_spec_extended_def = '|' + 'p{0.4cm}|'
                
                for column_data in columns_default:
                    table_spec_extended_def += f"p{{{column_data['width']:.1f}cm}}|"
                    if column_data['title'] not in session_df.columns:
                        title_helper = column_data['title']
                        title_helper = title_helper.replace("\\n", "\n")
                        session_df[title_helper] = ''
                table_spec = table_spec_extended_def
            
            else: # for customized_att
                matching_exp_title = None
                for exp_title_json in att_column.keys():
                    if exp_title in exp_title_json:
                        matching_exp_title = exp_title_json
                        columns_customized = att_column.get(matching_exp_title)[0]
                        footer = att_column.get(matching_exp_title)[1]
                        table_spec_customized = '|' + 'p{0.4cm}|'
                
                        for column_data in columns_customized:
                            table_spec_customized += f"p{{{column_data['width']:.1f}cm}}|"
                            if column_data['title'] not in session_df.columns:
                                title_helper = column_data['title']
                                title_helper = title_helper.replace("\\n", "\n")
                                session_df[title_helper] = ''
                        table_spec = table_spec_customized
                        break
                    
                if not matching_exp_title: # when no matching exp_title is found
                    columns_default = att_column.get('Extended (Default)')[0]
                    footer = att_column.get('Extended (Default)')[1]
                    table_spec_extended_def = '|' + 'p{0.4cm}|'
            
                    for column_data in columns_default:
                        table_spec_extended_def += f"p{{{column_data['width']:.1f}cm}}|"
                        if column_data['title'] not in session_df.columns:
                            title_helper = column_data['title']
                            title_helper = title_helper.replace("\\n", "\n")
                            session_df[title_helper] = ''
                    table_spec = table_spec_extended_def           
                     
        else:
            session_df['Attendance'] = ''    

        session_df.insert(0, ' ', range(1, 1 + len(session_df)))
        
        doc.append(pl.NoEscape('{'))
        doc.append(pl.Command('pagenumbering', 'gobble'))
        doc.append(pl.Command('noindent'))
        
        text_before_table = f"PHYS {code},  {session_info}\n"
        doc.append(utils.bold(text_before_table))
        
        text_before_table = f"Exp {exp_title}\n\n"
        doc.append(text_before_table)
        
        text_before_table = f"Date: ________________          TA: ________________\n\n"
        doc.append(text_before_table)

        doc.append(pl.NoEscape('}'))
        
        
        # Create the Table
        with doc.create(Tabular(table_spec, pos='t', row_height=1.3)) as table:
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

        doc.append('\n\n\n')  # Add some space between table and caption
        footer = footer.replace(r'\n', r'\\')
        doc.append(footer)
        doc.append(pl.Command('vfill'))
        doc.append(pl.Command('tiny'))  # Set the font size to tiny
        doc.append(footer_DB_time)
        doc.append(pl.Command('normalsize'))  # Reset the font size to normal
        
        # Add a page break after each table
        doc.append(NoEscape(r'\newpage'))
        
    # Save the multipage PDF using pdflatex as the LaTeX compiler
    output_dir = os.path.join(user_data_dir, f'output_{code}')
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
        date_modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%b-%d-%Y at %I:%M %p')
        logging.debug(f'date modified (local time): {date_modified}')
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
    return pandas.concat(stud_dfs, axis=0), date_modified


#------------------------------------------------------------
def get_number_of_students(stud_csv_path_list, session):
    
    stud_df, _ = concat_stud_lists(stud_csv_path_list)
    
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
        sessions[f'{day_map(session[1])}, {session[2]} - {session[0]}'] = (session[0],session[1])
    logger.debug(f'sessions: {sessions}')
    return sessions

def get_exp_list(exp_csv_path):
    exps = {}
    
    exp_df = pandas.read_csv(exp_csv_path)
    #--- drop rows with nan
    exp_df = exp_df.dropna()
    exp_df = exp_df.dropna().reset_index(drop=True)

    id_list = list(exp_df['exp_id'])
    title_list = list(exp_df['exp_title'].str.strip())
    try:
        location_list = list(exp_df['location'].str.strip())
    except KeyError:
        location_list = []
    exp_list = list(zip(id_list, title_list))
    
    for exp in exp_list:
        #exps[exp[0]] = f'{exp[0]}: {exp[1]}'
        exps[f'{exp[0]}: {exp[1]}'] = exp[0]
    
    return exps, location_list

#------------------------------------------------------------
def get_studList_header(col):
    header_10 = ["student_id","surname","first_name","email","session_id","lect_id","tutr_id","programme_title","study_level","registration_status"]
    header_9 = ["student_id","surname","first_name","email","session_id","lect_id","programme_title","study_level","registration_status"]
    return header_10 if col==10 else header_9

#------------------------------------------------------------        
def make_groups(user_data_dir, exp_csv_path, stud_csv_path_list, time_csv_path, session_id, n_stud, n_benches, code, pkl_file_name):
    exp_df= pandas.read_csv(exp_csv_path)  
    time_df= pandas.read_csv(time_csv_path)
    stud_df, _ = concat_stud_lists(stud_csv_path_list)

    #--- drop rows with nan
    exp_df = exp_df.dropna()
    exp_df = exp_df.dropna().reset_index(drop=True)
    time_df = time_df.dropna()
    time_df = time_df.dropna().reset_index(drop=True)
    
    # filter the lists based on the given session_id
    stud_df = stud_df.loc[stud_df['session_id'].str.strip()==session_id[0]]

    exp_list = list(exp_df['exp_id'])
    stud_list = list(stud_df['student_id'])
    time_list = list(time_df['Type'].str.strip())

    exp_dict = DefaultDict() # exp dict: key = exp_id , value = tuple of (exp meta data) and (student_groups)
    
    n_group = math.ceil(n_stud/n_benches)
    # fill the database dictionary
    if exp_list and stud_list and time_list:
        for exp in exp_list:
            students_splits = _rand_group_maker(stud_df, n_group, n_benches, optimize=True)
            exp_dict[exp] = ( exp_df.loc[exp_df['exp_id']==exp], time_df[(time_df['Type'].str.strip() == session_id[0]) & (time_df['Day'] == session_id[1])] , students_splits)
    else:
        logger.error('exp_list, time_list, or stud_list is empty')
        return None
       
    out_dir = os.path.join(user_data_dir, f'output_{code}')
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
def generate_html_table(stud_list, n_benches):
    num_stud = len(stud_list)
    num_rows = -(-n_benches // 2) if n_benches > 0 else 1  # Calculate number of rows based on n_benches
    
    html_table = "<tbody>\n"
    
    for i in range(num_rows):
        html_table += "  <tr>\n"
        for j in range(2):
            index = i * 2 + j
            if index < num_stud:
                html_table += f"    <td>{stud_list[index]}</td>\n"
            else:
                html_table += f"    <td> --- </td>\n"
        html_table += "  </tr>\n"
    
    html_table += "</tbody>"
    return html_table
#------------------------------------------------------------
def html_generator(user_data_dir, pkl_path, code, n_max_group, n_benches, version, css_file, css_file_all, ta_name = None):
    logger.debug(f'ta_name = {ta_name}')
    out_dir = os.path.join(user_data_dir, f'output_{code}')
    html_dir = os.path.join(out_dir, 'html')

    logger.debug(f'pkl_path: {pkl_path}')
    logger.debug(f'html_dir: {html_dir}')

    #html_grid_type= 4 if n_benches == 4 else 2
    

    #creating a fresh html directory
    if os.path.exists(html_dir):
        shutil.rmtree(html_dir)
    os.makedirs(html_dir)
    
    dict = _load_student_groups(pkl_path, print_result=False)
    
    n_exp = len(dict)
    n_group = len(dict[1][2])
    
    logger.debug(f'n_exp: {n_exp}')
    logger.debug(f'n_group: {n_group}')

    time_js = '''
        <script>
            function updateTime() {
              const now = new Date();
              const options = { hour: 'numeric', minute: 'numeric' };
              const timeElement = document.getElementById('time');
              timeElement.textContent = now.toLocaleTimeString([], options);
            }

            updateTime();
            setInterval(updateTime, 60000); // Update time every minute
        </script>
        '''
 
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
        html_all_generator_layout(e, code, output_dir, dict, df_exp_metadata, df_time_metadata, css_file_all, ta_name, version)
    
        for g in range(n_group):
            df = dict[e][2][g].reset_index(drop=True)
            df.index += 1
            
            f_html = os.path.join(output_dir, f'g{g+1}.html')
            
            with open(f_html, 'w') as html_seating_file:
                stud_list = []
                for i in range(len(df)):
                    row = df.iloc[i,2] +' '+ df.iloc[i,1]
                    stud_list.append(row)
                
                html_table = generate_html_table(stud_list, n_benches)
                
                seating_contents = f'''<!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <title>YU LabManager</title>
                        <meta http-equiv="refresh" content="15">
                        <link rel="stylesheet" type="text/css" href="{css_file}?v={round(random.randint(0, 1000)/100, 2 )}">
                    </head>
                    <body>
                    <header>
                        <div class="logo"></div>
                        <div class="session-info">PHYS {code}, Session: {day_map(df_time_metadata['Day'].iloc[0])}, {df_time_metadata['Start Time'].iloc[0]}, TA: {ta_name}</div>
                        <div id="time" class="session-info"></div>
                    </header>
                    <div class="main-body">
                        <div class="table-container">
                          <div class="group-header" style="width: calc(100% - 10px); margin-left: 5px;">Group {g+1}</div>
                          <table class="table" style="width: calc(100% - 10px); margin-left: 5px;">
                            {html_table}
                          </table>
                          <div class="tips-title">Useful Tips</div>
                          <div class="iframe-content" contenteditable="False">
                            <iframe src="tip/{df_exp_metadata['exp_tip'].iloc[0]}" frameborder="0"></iframe>
                          </div>
                        </div>
                        <div class="photo-container">
                          <div class="image-header">Exp {df_exp_metadata['exp_id'].iloc[0]}: {df_exp_metadata['exp_title'].iloc[0]}</div>
                          <div class="photo" style="background-image: url('img/{df_exp_metadata['exp_img'].iloc[0]}');">
                        </div>
                        </div>

                        <footer>
                            YU LabManager V{version}
                        </footer>

                        {time_js} 

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
                        row = ' --- '
                        blank_stud_list.append(row)
                    
                    blank_html_table = generate_html_table(blank_stud_list, n_benches)
                    blank_seating_contents = f'''<!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <title>YU LabManager</title>
                        <meta http-equiv="refresh" content="15">
                        <link rel="stylesheet" type="text/css" href="{css_file}?v={round(random.randint(0, 1000)/100, 2 )}">
                    </head>
                    <body>
                    <header>
                        <div class="logo"></div>
                        <div class="session-info">PHYS {code}, Session: {day_map(df_time_metadata['Day'].iloc[0])}, {df_time_metadata['Start Time'].iloc[0]}, TA: {ta_name}</div>
                        <div id="time" class="session-info"></div>
                    </header>
                    <div class="main-body">
                        <div class="table-container">
                          <div class="group-header" style="width: calc(100% - 10px); margin-left: 5px;">Group {g+1}</div>
                          <table class="table" style="width: calc(100% - 10px); margin-left: 5px;">
                            {blank_html_table}
                          </table>
                          <div class="tips-title">Useful Tips</div>
                          <div class="iframe-content" contenteditable="False">
                            <iframe src="{os.path.join('tip', df_exp_metadata['exp_tip'].iloc[0])}" frameborder="0"></iframe>
                          </div>
                        </div>
                        <div class="photo-container">
                          <div class="image-header">Exp {df_exp_metadata['exp_id'].iloc[0]}: {df_exp_metadata['exp_title'].iloc[0]}</div>
                          <div class="photo" style="background-image: url('img/{df_exp_metadata['exp_img'].iloc[0]}');">
                        </div>
                        </div>

                        <footer>
                            YU LabManager V{version}
                        </footer>
                        {time_js} 
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
def html_all_generator_grp(exp, n_max_group, n_benches ,code, output_dir, dict, df_exp_metadata, df_time_metadata, css_file_all, ta_name, version):
    n_group = len(dict[1][2])
    
    f_html = os.path.join(output_dir, 'g99.html')
    stud_list = []

    for g in range(n_group):
        df = dict[exp][2][g].reset_index(drop=True)
        df.index += 1
        _list = []
        for i in range(len(df)):
            row = df.iloc[i,2] +' '+ df.iloc[i,1]
            _list.append(row)
        
        stud_list.append(_list)
        
    
    newline = "\n"

    seating_header = f'''
        <header>
            <div class="logo"></div>
            <div class="session-info">PHYS {code}, Session: {day_map(df_time_metadata['Day'].iloc[0])}, {df_time_metadata['Start Time'].iloc[0]}, TA: {ta_name}</div>
            <div id="time" class="session-info"></div>
        </header>
    '''
    g_list = list(range(1, n_max_group+1))
    col1_groups =''
    col2_groups =''

    # column 1
    for g in g_list[:math.ceil(n_max_group/2)]:
        if g <= n_group:
            html_table = generate_html_table(stud_list[g-1], n_benches)
            col1_groups += f'''
                <div class="group-header" style="width: calc(100% - 10px); margin-left: 5px;">Group {g}</div>
                <table class="table" style="width: calc(100% - 10px); margin-left: 5px;">
                    {html_table}
                </table>
            '''
        # handeling empty groups

    # column 2
    for g in g_list[math.ceil(n_max_group/2):]:
        if g <= n_group:
            html_table = generate_html_table(stud_list[g-1], n_benches)
            col2_groups += f'''
                <div class="group-header" style="width: calc(100% - 10px); margin-left: 5px;">Group {g}</div>
                <table class="table" style="width: calc(100% - 10px); margin-left: 5px;">
                    {html_table}
                </table>
            '''
    # handeling empty groups
            
    seating_groups =f'''
        <div class="table-container", style="width:30%">
        {col1_groups}
        </div>
        <div class="table-container", style="width:30%">
        {col2_groups}
        </div>
    '''

    seating_img_tip = f'''
            <div class="photo-container_all">
                <div class="image-header">Exp {df_exp_metadata['exp_id'].iloc[0]}: {df_exp_metadata['exp_title'].iloc[0]}</div>
                <div class="photo_all" style="background-image: url('img/{df_exp_metadata['exp_img'].iloc[0]}');">
            </div>
            <div class="tips-title">Useful Tips</div>
            <div class="iframe-content_all" contenteditable="False">
                <iframe src="{os.path.join('tip', df_exp_metadata['exp_tip'].iloc[0])}" frameborder="0"></iframe>
            </div>  
    '''
    # constructing the html page
    time_js = '''
        <script>
            function updateTime() {
              const now = new Date();
              const options = { hour: 'numeric', minute: 'numeric' };
              const timeElement = document.getElementById('time');
              timeElement.textContent = now.toLocaleTimeString([], options);
            }

            updateTime();
            setInterval(updateTime, 60000); // Update time every minute
        </script>
        '''
    page_contents = f'''<!DOCTYPE html>
        <html lang="en">
        <head>
            <title>YU LabManager</title>
            <meta http-equiv="refresh" content="15">
            <link rel="stylesheet" type="text/css" href="{css_file_all}?v={round(random.randint(0, 1000)/100, 2 )}">
        </head>
        <body>
            {seating_header}
            <div class="main-body">
                {seating_groups}
                {seating_img_tip}
            </div>
            
            <footer>
                YU LabManager V{version}
            </footer>
            {time_js} 
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
def html_all_generator_layout(exp, code, output_dir, dict, df_exp_metadata, df_time_metadata, css_file_all, ta_name, version):
    n_group = len(dict[1][2])
    
    f_html = os.path.join(output_dir, 'g99.html')
    stud_list = []

    for g in range(n_group):
        df = dict[exp][2][g].reset_index(drop=True)
        df.index += 1
        _list = []
        for i in range(len(df)):
            row = df.iloc[i,2] +' '+ df.iloc[i,1]
            _list.append(row)
        
        stud_list.append(_list)
        
    
    newline = "\n"

    seating_header = f'''
        <header>
            <div class="logo"></div>
            <div class="session-info">PHYS {code}, Session: {day_map(df_time_metadata['Day'].iloc[0])}, {df_time_metadata['Start Time'].iloc[0]}, TA: {ta_name}</div>
            <div id="time" class="session-info"></div>
        </header>
    '''
            
    seating_layout =f'''
        <div class="layout-container">
            <div class="group-header" style="width: calc(100% - 10px); margin-left: 5px;">Groups</div>
            <div class="layout" style="background-image: url('img/lab_layout_grp.png');"></div>
        </div>
    '''

    seating_img_tip = f'''
            <div class="photo-container_all">
                <div class="image-header">Exp {df_exp_metadata['exp_id'].iloc[0]}: {df_exp_metadata['exp_title'].iloc[0]}</div>
                <div class="photo_all" style="background-image: url('img/{df_exp_metadata['exp_img'].iloc[0]}');"></div>
            <div class="tips-title">Useful Tips</div>
            <div class="iframe-content_all" contenteditable="False">
                <iframe src="{os.path.join('tip', df_exp_metadata['exp_tip'].iloc[0])}" frameborder="0"></iframe>
            </div>  
    '''
    # constructing the html page
    time_js = '''
        <script>
            function updateTime() {
              const now = new Date();
              const options = { hour: 'numeric', minute: 'numeric' };
              const timeElement = document.getElementById('time');
              timeElement.textContent = now.toLocaleTimeString([], options);
            }

            updateTime();
            setInterval(updateTime, 60000); // Update time every minute
        </script>
        '''
    page_contents = f'''<!DOCTYPE html>
        <html lang="en">
        <head>
            <title>YU LabManager</title>
            <meta http-equiv="refresh" content="15">
            <link rel="stylesheet" type="text/css" href="{css_file_all}?v={round(random.randint(0, 1000)/100, 2 )}">
        </head>
        <body>
            {seating_header}
            <div class="main-body">
                {seating_layout}
                {seating_img_tip}
            </div>
            
            <footer>
                YU LabManager V{version}
            </footer>
            {time_js} 
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
def print_on_layout(user_data_dir, gpc_map, room, room_list, exp_id, pkl_path):
    
    if room not in room_list:
        print(f'{room} room is not supported')
        return
    
    layout_src = room_list[room][1]
    out_dir = os.path.join(user_data_dir, 'output_layout')

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    lab_layout_out_file = os.path.join(out_dir, 'lab_layout_grp.png')
    
    # g_cordination dictionary
    g_cord_dict = cord_map(room, gpc_map)
    
    text_char_limit = 20
    text_color = 'black'  
    
    
    # Open the layout image
    if os.path.isfile(layout_src):
        myLayout = Image.open(layout_src)
    else:
        logger.error('Layout file does not exist!')
        return

    # Create a font
    font_size = 70
    font_path = os.path.join('scripts', 'arial.ttf')
    try:
        textFont = ImageFont.truetype(font_path, font_size)
    except IOError:
        # If 'arial.ttf' is not found, load the default font
        textFont = ImageFont.load_default()
    
    
    # Create a drawing context
    editImage = ImageDraw.Draw(myLayout)

    # Define background color
    background_color = (204, 229, 255)  # Use (R, G, B) values for white background

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
                #editImage.rectangle([x, y, x + text_width, y + text_height])
            
                # Write the text on the colored background 
                editImage.text((x, y), stud_name[:text_char_limit], fill=text_color, font=textFont)

    #save Image
    try:
        myLayout.save(lab_layout_out_file)
        return lab_layout_out_file
    except:
        logger.error('Could not write on the layout image.')

#------------------------------------------------------------
def generate_schedule(schedule_data_dict, time_csv_path, exp_list, code, location_list):
    weeks_list = list(schedule_data_dict.values())
    schedule_df = pd.DataFrame(columns=['start date', 'start time', 'end time', 'subject', 'Description', 'location'])
    days_index = {'M': 0, 'T': 1, 'W': 2, 'R': 3, 'F': 4}

    time_df = pd.read_csv(time_csv_path)
    # Drop rows with NaN and reset index
    time_df = time_df.dropna().reset_index(drop=True)

    # Assuming 'Start Time' and 'Duration' columns exist in your CSV
    start_time_list = time_df['Start Time']
    duration_list = time_df['Duration']
    end_time_list = []

    exp_title_list = [s.split(": ", 1)[1] if ": " in s else s for s in list(exp_list.keys())]

    # Calculate end times based on start times and durations
    for start_time, duration in zip(start_time_list, duration_list):
        start_time_obj = datetime.strptime(start_time, '%H:%M')
        duration_obj = timedelta(minutes=int(duration))
        end_time_obj = start_time_obj + duration_obj
        end_time_list.append(end_time_obj.strftime('%H:%M'))

    for i, week in enumerate(weeks_list):
        date_format = '%Y-%m-%d'
        date_obj = datetime.strptime(week, date_format)

        for index, row in time_df.iterrows():
            day = row['Day']
            start_time = row['Start Time']
            end_time = end_time_list[index]  # Use precomputed end_time
            type = row['Type']
            _date = date_obj + timedelta(days=days_index[day])

            # Append each new row to the DataFrame
            new_row = {'start date': _date.strftime('%Y-%m-%d'), 'start time': start_time,
                       'end time': end_time, 'subject': f'PHYS {code}', 'Description': f'{type} - {exp_title_list[i]}',
                       'location': location_list[i]}
            schedule_df = schedule_df.append(new_row, ignore_index=True)

    return schedule_df
