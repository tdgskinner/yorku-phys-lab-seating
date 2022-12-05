#!/usr/bin/env python3
import pandas

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

path = '/Users/mohammad/cernbox/yorku-phys-lab-seating/scripts/data/PHYS2213_2022-23/time_2022PHYS2213A.csv'
sessions = get_session_list(path)

print(sessions)
