import os
from PIL import Image, ImageFont, ImageDraw
from typing import DefaultDict
import pickle
import re
import warnings

# importing the module
import pandas as pd
from pylatex import Document, Tabular, MultiColumn, VerticalSpace
import pylatex as pl
from pylatex.utils import NoEscape
from pylatex import utils, NewPage


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

def create_weekly_att(df, session_id, Course, session_day, Exp_id, output_path):
    pass

#=============================================================
if __name__ == '__main__':
    
    Course = 'PHYS 1800'
    session_day = 'Wednesday, 9:30'
    Exp_id = 3

    # Define your session IDs
    session_ids = ['LAB 01', 'LAB 02', 'LAB 03']

    # Load and concatenate student data
    stud_csv_path_list = ['inputs/stud_2023PHYS1800A.csv', 'inputs/stud_2023PHYS1800B.csv']
    df = concat_stud_lists(stud_csv_path_list)

    # Create a LaTeX document
    geometry_options = {"tmargin": "0.3in", "lmargin": "1in", "bmargin": "0.2in", "rmargin": "1in"}
    doc = Document(geometry_options=geometry_options)

    for session_id in session_ids:
        # Filter the data for the current session_id
        session_df = df.loc[df['session_id'].str.strip()==session_id]

        # Prepare the data for the table
        session_df = session_df[['first_name', 'surname']]
        session_df = session_df.rename(columns={'first_name': 'First Name', 'surname': 'Last Name'})
        session_df['Attendance'] = ''
        session_df.insert(0, ' ', range(1, 1 + len(session_df)))

        # Define text before the table
        text_before_table = f"{Course} - {session_day} - {session_id}, Exp {Exp_id}.\n\n"

        doc.append(pl.NoEscape('{'))
        doc.append(pl.Command('pagenumbering', 'gobble'))
        doc.append(pl.Command('noindent'))
        text_before_table = f"{Course} - {session_day} - {session_id}, Exp {Exp_id}.\n\n"
        doc.append(utils.bold(text_before_table))
        text_before_table = f"Date: ________________          TA: ________________\n\n"
        doc.append(text_before_table)

        doc.append(pl.NoEscape('}'))

        # Create the Tabular environment
        with doc.create(Tabular('|' + 'p{0.5cm}|' + 'p{3cm}|' + 'p{3cm}|' + 'p{4cm}|', pos='t', row_height=1.4)) as table:
            table.add_hline()
            table.add_row(session_df.columns, mapper=utils.bold)  # Include the column names
            table.add_hline()
            counter = 1
            for i, row in session_df.iterrows():
                row_values = [row[column] for column in session_df.columns]
                if (counter % 2) == 0:
                    table.add_row(row_values)
                else:
                    table.add_row(row_values, color="lightgray")
                table.add_hline()
                counter += 1

        # Add a page break after each table
        doc.append(NoEscape(r'\newpage'))

    # Save the multipage PDF using pdflatex as the LaTeX compiler
    doc.generate_pdf('attendance_sheets', compiler='pdflatex', clean_tex=True)

    print("PDF has been created.")