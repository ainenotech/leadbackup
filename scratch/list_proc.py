import subprocess
out = subprocess.check_output('wmic process where "name like \'python%.exe\'" get commandline,processid', shell=True, text=True)
print(out)
