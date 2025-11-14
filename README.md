# Installation (for development):
- Install python 3, with pip (or anaconda) and add it to the system's PATH
- Install the required dependencies:

- pip3 install -r requirements.txt
- A LaTeX compiler is needed to generate the weekly attendance sheets. [MikTex](https://miktex.org/download) is recommended for windows users.


# How to use the program:
1. Run the program from command line/terminal (alternately, use the compiled .exe):
```
python YorkULabSeating.py
```

2. Go to the settings tab and browse for the course directory. This directory should contain exp_*.csv (experiments table), stud_*.csv (enrolled students list), and time_*.csv (weekly lab schedule).

3. Browse for the PC list directory. This directory must contain pc_room_map.csv (mapping room with PC list file and layput). The .txt files contain the group PC and laptop names, layout coordinates and group number assigned to each group PC.

4. Fill the Course Details accordingly.

5. From the Settings tab, one can reboot the group PCs and laptops if needed.
   
7. Copy/delete files allows you to copy/delete a selected list of files from the host PC to/from the listed laptops of the selected room, to the given destination path.

8. From the Main tab:
- Select the session and room 
- Click on **Generate groups** to generate a .pkl file. This file contains the seating details for all listed experiments and students ***in the given session***.
- Click on **Generate html** to create the corresponding html files for the lab's display, containing the students' names/group.
- Select the Experiment name
- Click on **Copy Files to group PCs** to copy the generated html files to the group PCs. 
 
## Additional notes:

- Each Group PC must be set to automatically display **index.html** page in Windows Kiosk mode.
- The grouping process tries to create a uniform number (as much as possible) of students per group according to the 'Max # of groups' value.
- Single and weekly attendance sheets can be generated and printed from the main tab.


**version 8.0.1, Nov. 2025**

Developed by Mohammad Kareem, updated by Taylor Skinner & Leya Herschel

Department of Physics & Astronomy
Faculty of Science | York University
Petrie Science & Engineering
4700 Keele Street Toronto ON, Canada M3J 1P3

