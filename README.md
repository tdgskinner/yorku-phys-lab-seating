# Installation:
- Install python 3, with pip and add it to the system's PATH
- Install the required dependencies:
```
pip3 install -r requirements.txt
```

# How to use the program:
1. Run the program from command-line/ terminal:
```
python3 YorkULabSeating.py
```

2. Go to the setting page and insert the corresponding parameters. Please note the following:

- The **Session** value is case sensitive and must match with the **session_id** in the input csv lists
- Click on **Grouping** on the main page to generate a .pkl file. This file contains the seating details for all listed experiments and students ***in the given session***. Repeat this process to generate separate .pkl files with unique names for each existing session_id.
- Grouping process tries to create a uniform number of students per group according to the **'Max # of groups'** value. To have more students per group, reduce this value accordingly.

3. Once the .pkl file is generated, click on 'Generate Html' on the main page to generate the seating Html files per group. The seating Html files for each experiment will be stored in a separate directory labelled with the experiment id for the selected .pkl file.

4. Finally, on the main page, select the required **experiment_id** and click on ***START webserver*** to start hosting the selected experiment seating.

5. From the group PCs, open a web browser and visit http://hostname:port/g[X].html, where [X] is the desired group number.

6. The GUI must be running during the lab session. Once the session is done, click on ***STOP webserver*** and close the application.
 
## Additional notes:
1. The experiment images should be placed in ```scripts/src/img``` directory 

2. The input CSV files should be placed in ```scripts/<data>``` directory. You can specify this directory in the **setting -> Input directory**

3. The Experiment csv file must contain the following columns:
 - ```exp_id, exp_title, day, date, time, exp_img, session_id```

4. The Student csv file must contain the following columns:
 - ```student_id, last_name, first_name, session_id```

---
---

**version 1.0, September 2022**

The program is Written by:

Mohammad Kareem, Ph.D.

Research Associate

Department of Physics and Astronomy

York University

4700 Keele St, Toronto ON Canada M3J 1P3

mkareem@yorku.ca
