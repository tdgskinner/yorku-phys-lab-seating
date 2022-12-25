#!/usr/bin/env python3
import pandas as pd
import os
import random


def day_map(day_abr):
    days_dicts = {
            'M':'Monday',
            'T':'Tuesday',
            'W':'Wednesday',
            'R':'Thursday',
            'F':'Friday',
            }
    return days_dicts[day_abr]

def get_studList_header(col):
    header_10 = ["student_id","surname","first_name","email","session_id","lect_id","tutr_id","programme_title","study_level","registration_status"]
    header_9 = ["student_id","surname","first_name","email","session_id","lect_id","programme_title","study_level","registration_status"]
    return header_10 if col==10 else header_9


path_list = [r'C:\Users\mkareem\Documents\PHYS_1801_W23\stud_2022PHYS1801M.csv', r'C:\Users\mkareem\Documents\PHYS_1801_W23\stud_2022PHYS1801N.csv']
stud_dfs = []

for i, path in enumerate(path_list):
    df = pd.read_csv(path, index_col= False, header=None)
    # handle two different data length in student list depending on the lab course
    n_col = len(list(df.columns))
    if n_col == 9 or n_col ==10:
        df.columns = get_studList_header(n_col)
    else:
        print('number of columns is not supported')
    
    # drop nan
    df = df.dropna()
    
    # drop LAB 99
    df = df.loc[df['session_id'].str.strip()!='LAB 99']
    
    # append suffix to session_id to concat multiple lists 
    df['session_id'] = df['session_id'].add(f'_{i}')
    stud_dfs.append(df)


print(stud_dfs[0]["session_id"])
print(stud_dfs[1]["session_id"])

merged_df = pd.concat(stud_dfs, axis=0)
print(merged_df["session_id"])
