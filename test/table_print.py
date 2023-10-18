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


    stud_csv_path_list = ['inputs/stud_2023PHYS1800A.csv', 'inputs/stud_2023PHYS1800B.csv']

    df = concat_stud_lists(stud_csv_path_list)
    # filter the lists based on the given session_id
    
    session_id = 'LAB 01'
    Course = 'PHYS 1800'
    session_day = 'Wednesday, 9:30'
    Exp_id = 3
    
    df = df.loc[df['session_id'].str.strip()==session_id]
 
    df = df[['first_name', 'surname']]
    df = df.rename(columns={'first_name': 'First Name', 'surname': 'Last Name'})
    #df = df.sample()

    #add a new column
    df['Attendance'] = ''
    # Add an "Index" column starting from 1
    df.insert(0, ' ', range(1, 1 + len(df)))
    
    # Get column names from the DataFrame
    column_names = df.columns.tolist()

    # Create a LaTeX document
    # Define the width for specific columns

    geometry_options = {"tmargin": "0.3in", "lmargin": "1in", "bmargin": "0.2in", "rmargin": "1in"}

    doc = Document(geometry_options=geometry_options)
    doc.append(pl.NoEscape('{'))
    doc.append(pl.Command('pagenumbering', 'gobble'))
    doc.append(pl.Command('noindent'))
    #text_before_table = f"{Course} - {session_day} - {session_id}, Exp {Exp_id}.\n\n"
    text_before_table = f"{Course} - {session_day} - {session_id}, Exp {Exp_id}.\n\n"
    doc.append(utils.bold(text_before_table))
    text_before_table = f"Date: ________________          TA: ________________\n\n"
    doc.append(text_before_table)

    doc.append(pl.NoEscape('}'))

    # Create the Tabular environment with a dynamic number of columns
    #with doc.create(Tabular('|' + 'c|' * len(column_names))) as table:
    with doc.create(Tabular('|' + 'p{0.5cm}|' + 'p{3cm}|'+'p{3cm}|'+'p{4cm}|', pos='t', row_height=1.4)) as table:
        table.add_hline()
        table.add_row(column_names, mapper = utils.bold)  # Include the column names
        table.add_hline()
        counter = 1
        for i, row in df.iterrows():
            row_values = [row[column] for column in column_names]
            if (counter % 2) == 0:
                table.add_row(row_values)
            else:
                table.add_row(row_values, color="lightgray")
            table.add_hline()
            counter += 1
    
    
    # Save the PDF using pdflatex as the LaTeX compiler (assuming MiKTeX is installed)
    doc.generate_pdf('table_example', compiler='pdflatex', clean_tex=True)

    print("PDF has been created.")