
===================================================
Instructions:

1) edit/ check the config file

2) run python3 YorkU_Lab_SeatingManager.py with the option 'grouping' to generate the database file (.pkl)
   ==> this should be done only once. or any time that the student list changed, to update the database.
   ==> at each repeated execution, the grouping will be shuffled randomely.

3) run python3 YorkU_Lab_SeatingManager.py with option 'htmlgen' to generate the html files for experiment seatings.
   ==> this should be done only once. or any time that the database is updated (step 1), to regenerate the html files.

4) run webserver.py and pass the experiment_id as an argument [e.g., python3 webserver.py 5 ]. The web server should start and all 
   group computers should be able to load their dedicated page (eg., http://[hostname]:[port]/g1.html for group #1) in their own web-browser.
   It is recommended to bookmark this page.

Few additional notes:
1) the experiment images should be placed in src/img directory 
2) the CSS file should be placed in src directory
3) Pandas and numpy are required to be pre-installed
===================================================
September 2022:
The program is Written by:
Mohammad Kareem, Ph.D.
Research Associate
Department of Physics and Astronomy
York University
4700 Keele St, Toronto ON Canada M3J 1P3
Office: 234 Petrie Science and Engineering Bldg.
mkareem@yorku.ca


========
How to use the program:
1- Go to the setting page and insert the corresponding parameters. Please note the following:
a) the session input is case sensitive and should match with the 'session' in the input csv lists
b) Click on 'Grouping' on the main page to generate a .pkl file containing the seating details of all listed experiments and students in the given session. Repeat this process to generate separate .pkl files with unique names for each session id.
c) Grouping process tries to create a uniform number of students per group according to the 'Max # of groups' value. To have more students per group, reduce this value accordingly.
2- Once the .pkl files are generated, click on 'Generate Html' on the main page to generate the seating Html files per group. The seating Html files for each experiment will be stored in a separate directory labeled with the experiment id.
3 - Finally, on the main page, select the required experiment id and click on 'START webserver' to start hosting the selected experiment seating.
4 - From the group PCs, open a web browser and visit http://hostname:port/g<X>.html, where X is the group number.
5 - The GUI must be running during the lab session. Once the session is done, click on 'STOP webserver' and close the application.