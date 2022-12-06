import shutil
import os

destPc = 'sc-l-ph-dev-gp1'
source_path = os.getcwd()
file_name = 'YorkU_logo_L.png'
dest_path =r'\\' + destPc+ r'\\seats'

#shutil.copyfile(os.path.join(source_path, file_name), os.path.join(dest_path, file_name))
os.system(r"shutdown -m \\sc-l-ph-dev-gp1.yorku.yorku.ca -r -f -t 0")