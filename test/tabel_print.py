import os
from PIL import Image, ImageFont, ImageDraw
from typing import DefaultDict
import pickle
import re
import warnings

# importing the module
import pandas as pd


def get_studList_header(col):
    header_10 = ["student_id","surname","first_name","email","session_id","lect_id","tutr_id","programme_title","study_level","registration_status"]
    header_9 = ["student_id","surname","first_name","email","session_id","lect_id","programme_title","study_level","registration_status"]
    return header_10 if col==10 else header_9
#----------

def concat_stud_lists(stud_csv_path_list):
    stud_dfs = []
    for i, path in enumerate(stud_csv_path_list):
        df = pd.read_csv(path, index_col= False, header=None)
        # handle two different data length in student list depending on the lab course
        n_col = len(list(df.columns))
        if n_col == 9 or n_col ==10:
            # adding header to student list
            df.columns = get_studList_header(n_col)
        else:
            print('number of columns in stud csv files is not supported. Suppoerted numbers are 9 and 10.')
    
        # drop nan
        df = df.dropna()
    
        # drop LAB 99
        df = df.loc[df['session_id'].str.strip()!='LAB 99']
    
        # append suffix to session_id
        if i >0:
            df['session_id'] = df['session_id'].add(f'_{i}')
        
        stud_dfs.append(df)

    # merge all lists into one df with distinc session_id
    return pd.concat(stud_dfs, axis=0)


if __name__ == '__main__':

    stud_csv_path_list = ['inputs/stud_2023PHYS1800A.csv', 'inputs/stud_2023PHYS1800B.csv']

    stud_df = concat_stud_lists(stud_csv_path_list)
    # filter the lists based on the given session_id
    
    session_id = 'LAB 01'
    stud_df = stud_df.loc[stud_df['session_id'].str.strip()==session_id]
 
    # displaying the DataFrame
    stud_df.style

    


