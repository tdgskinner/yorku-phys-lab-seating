#!/usr/bin/env python3
import pandas, os
import random


def get_session_list(time_csv_path):
    sessions = []
    days_dicts = {
            'M':'Monday',
            'T':'Tuesday',
            'W':'Wednesday',
            'R':'Thursday',
            'F':'Friday',
            }
    time_df= pandas.read_csv(time_csv_path)
    Day_list = list(time_df['Day'])
    
    time_list = list(time_df['Start Time'])
    session_list = list(zip(Day_list, time_list))

    for session in session_list:
        sessions.append(f'{days_dicts[session[0]]}, {session[1]}')

    return sessions

def get_number_of_students(stud_csv_path, session):
    print(f'stud_csv_path={stud_csv_path}')
    print(f'--session={session}')
    stud_df= pandas.read_csv(stud_csv_path)
    print(f'len of stud_df= {len(stud_df)}')

    # filter the list based on the given session_id
    stud_df = stud_df.loc[stud_df['session_id'].str.strip()==session]
    stud_list = list(stud_df['student_id'])
    print(f'len of filtered stud= {len(stud_list)}')
    
    return len(stud_list)

def make_groups(exp_csv_path):
    exp_df= pandas.read_csv(exp_csv_path)
    print(f'exp_df={exp_df}')

def get_css_ver():
    var = round(random.randint(0, 1000)/100, 2 )
    print(var)

get_css_ver()



#path = 'C:/Users/mkareem/OneDrive - York University/physLabTech/yorku-phys-lab-seating/scripts/data/PHYS2213_2022-23/exp_test.csv'
#sessions = make_groups(path)
#print(os.path.dirname(path))

