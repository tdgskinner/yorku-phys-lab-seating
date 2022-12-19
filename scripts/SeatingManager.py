#!/usr/bin/env python3
from typing import DefaultDict
import pandas
import numpy as np
import pickle
import logging
import random
import sys, os, shutil

logger = logging.getLogger(__name__)

#------------------------------------------------------------    
def _rand_group_maker(df, n_group, rand_grp = True):
    
    if rand_grp:
        df_shuffled = df.sample(frac=1)
    else:
        df_shuffled = df.sample(frac=1, random_state=42)
    
    df_splits = np.array_split(df_shuffled, int(n_group))
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
def get_number_of_students(stud_csv_path, session):
    # adding header to student list
    stud_df= pandas.read_csv(stud_csv_path, header=None, names=get_studList_header())
    #--- drop rows with nan
    stud_df = stud_df.dropna()
    stud_df=stud_df.dropna().reset_index(drop=True)

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
    return days_dicts[day_abr]

def get_session_list(time_csv_path):
    sessions = {}
    
    time_df = pandas.read_csv(time_csv_path)
    #--- drop rows with nan
    time_df = time_df.dropna()
    time_df=time_df.dropna().reset_index(drop=True)

    Type_list = list(time_df['Type'].str.strip())
    Day_list = list(time_df['Day'].str.strip())
    time_list = list(time_df['Start Time'].str.strip())
    ta_list = list(time_df['Instructor'].str.strip())
    session_list = list(zip(Type_list, Day_list, time_list, ta_list))
    
    for session in session_list:
        sessions[f'{day_map(session[1])}, {session[2]}'] = (session[0],session[3])
    
    return sessions

#------------------------------------------------------------
def get_studList_header():
    header = ["student_id","surname","first_name","email","session_id","lect_id","programme_title","study_level","registration_status"]
    return header
#------------------------------------------------------------        
def make_groups(exp_csv_path, stud_csv_path, time_csv_path, session_id, n_group, n_benches, pkl_file_name):
    exp_df= pandas.read_csv(exp_csv_path)  
    stud_df= pandas.read_csv(stud_csv_path, header=None, names= get_studList_header())
    time_df= pandas.read_csv(time_csv_path)

    #--- drop rows with nan
    exp_df = exp_df.dropna()
    exp_df = exp_df.dropna().reset_index(drop=True)
    stud_df = stud_df.dropna()
    stud_df = stud_df.dropna().reset_index(drop=True)
    time_df = time_df.dropna()
    time_df = time_df.dropna().reset_index(drop=True)

    
    # filter the lists based on the given session_id
    stud_df = stud_df.loc[stud_df['session_id'].str.strip()==session_id]

    exp_list = list(exp_df['exp_id'])
    stud_list = list(stud_df['student_id'])
    time_list = list(time_df['Type'])

    exp_dict = DefaultDict() # exp dict: key = exp_id , value = tuple of (exp meta data) and (student_groups)
    
    # fill the database dictionary
    if exp_list and stud_list and time_list:
        for exp in exp_list:
            students_splits = _rand_group_maker(stud_df, n_group)
            exp_dict[exp] = ( exp_df.loc[exp_df['exp_id']==exp], time_df.loc[time_df['Type'].str.strip()==session_id] , students_splits)
    else:
        logger.error('exp_list, time_list, or stud_list is empty')
        return None
        
    out_dir = 'output'
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
        return pkl_path
    except:
        logger.error(f' Failed to write {pkl_path} to disk', exc_info = True)
        return None
      
    
#------------------------------------------------------------
def html_generator(pkl_path):
    
    out_dir = 'output'
    html_dir = os.path.join(out_dir, 'html')

    logger.debug(f'pkl_path: {pkl_path}')
    logger.debug(f'html_dir: {html_dir}')
    

    #creating a fresh html directory
    if os.path.exists(html_dir):
        shutil.rmtree(html_dir)
    os.makedirs(html_dir)
    
    dict = _load_student_groups(pkl_path, print_result=False)
    
    n_exp = len(dict)
    logger.debug(f'n_exp: {n_exp}')
    n_group = len(dict[1][2])
    logger.debug(f'n_group: {n_group}')
 
    for e in range (1, n_exp+1, 1):
        output_dir = os.path.join(html_dir, f'exp{e}')
        df_exp_metadata = dict[e][0]
        df_time_metadata = dict[e][1]
        
        for g in range(n_group):
            df = dict[e][2][g].reset_index(drop=True)
            df.index += 1
            
            #creating output directory if not exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            f_html = os.path.join(output_dir, f'g{g+1}.html')
            
            with open(f_html, 'w') as html_seating_file:
                stud_list = []
                for i in range(len(df)):
                    row = '<div class="grid-item"><a href="#">'+df.iloc[i,2] +' '+ df.iloc[i,1]+'</a></div>'
                    stud_list.append(row)
                newline = "\n"
                #<iframe src="{os.path.join('tip', df_exp_metadata['exp_tip'].iloc[0]) }" style="background-color:rgb(255, 230, 230);border:2px solid #b71414;" width="100%" height="290px"></iframe> 
                seating_contents = f'''<!DOCTYPE html>
                            <html lang="en">
                            <head>
                            <META HTTP-EQUIV="CACHE-CONTROL" CONTENT="NO-CACHE">
                            <META HTTP-EQUIV="EXPIRES" CONTENT="Mon, 22 Jul 2002 11:12:01 GMT">
                            <meta name="viewport" content="width=device-width, initial-scale=1">
                            <meta http-equiv="refresh" content="60">
                            <link rel="stylesheet" href="style.css?v={round(random.randint(0, 1000)/100, 2 )}">
                            <script type="text/javascript" src="time.js"></script>
                            
                            </head>
                            <body>

                            <div class="row", style="padding:0cm">
                                <div class="column", style="width:20%">
                                    <img src=yorku-logo.jpg , style="height:30px">
                                </div>
                                <div class="column", style="width:65%">
                                    <h3 style="font-size:23px"><center>Session: {day_map(df_time_metadata['Day'].iloc[0])}, {df_time_metadata['Start Time'].iloc[0]}, TA: {df_time_metadata['Instructor'].iloc[0]}</center></h3>
                                </div>
                                <div class="column", style="width:15%"></div>
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
                                        <h4> Useful tip:</h4>
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
                                    <center> <img src={os.path.join('img', df_exp_metadata['exp_img'].iloc[0]) } style="height:500px" ></center>
                                </div>
                            </div>
                            </body>
                            </html>
                            '''
                try:
                    html_seating_file.write(seating_contents)
                except:
                    logger.error(f' Failed to write html files to disk', exc_info = True)
                    return None
    logger.info(f' Seating html files are generated and written to {html_dir} successfully!')
    return html_dir
    
    
                
#===========================================================================
'''
if __name__ == "__main__":
    logging.getlogger().setLevel(logger.DEBUG)
    config = conf.ConfigParser()
    configfile = 'config.conf'
    if os.path.isfile(configfile):
            config.read(configfile)
    else:
        logger.error(f'Config file {configfile} does not exist.\n Process terminated.')
    
    
    arg = sys.argv

    if (len(arg) !=2):
        logger.error('Missing argument: use either grouping: make randomized grouping of the students for each experiment, or htmlgen: to generate html files')
        exit()

    if arg[1].lower() != 'grouping' and arg[1].lower() != 'htmlgen':
        logger.error('accepted arguments: <grouping> OR <htmlgen>')
        exit()
    
    # parsing the config parameters
    exp_csv_path = os.path.join(config['Inputs']['data_dir'], config['Inputs']['exp_csv_file'] )
    stud_csv_path = os.path.join(config['Inputs']['data_dir'], config['Inputs']['stud_csv_file'] )
    n_group=int(config['Course']['max_groups'])
    n_benches=int(config['Course']['n_benches'])
    pkl_file = config['Database']['file_name']
    session = config['Course']['session']
    
    coursename= config['Course']['coursename']
    code = config['Course']['code']
    TA_name = config['Course']['TA_name']

    #-- Create experiment_student groups and store in pkl file (do this once per course)
    if arg[1].lower() == 'grouping':
        make_groups(exp_csv_path, stud_csv_path, session, n_group, n_benches, pkl_file, out_dir = 'src')

    
    elif arg[1].lower() == 'htmlgen':
        html_generator(pkl_file, coursename, code, TA_name, out_dir = 'src')
    
    '''