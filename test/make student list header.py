# -*- coding: utf-8 -*-
"""
Created on Tue Nov 25 14:02:18 2025

@author: Taylor
"""
import os, re, pandas

labPattern = r'^ LAB \d\d$'

path = r'C:\Users\Taylor\York University\SC-PHAS Labs - PHYS_seating_program_data\PHYS_1800_Seating_program_data\PHYS_1800_LD25'
path = os.path.join(path, 'stud_2025PHYS1800D.csv')
df = pandas.read_csv(path, index_col= False, header=None)

firstrow = df.loc[0]
test = re.search(labPattern, firstrow[5])