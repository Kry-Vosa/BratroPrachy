""" this whole thing is here for it to be OS independant. """

import subprocess

flags = None

if "CREATE_NO_WINDOW" in dir(subprocess):
    flags = subprocess.CREATE_NO_WINDOW

with open('last_run.log', 'w+') as f:
    subprocess.call(["py", "./src/prachy.py"], stdout=f, stderr=subprocess.STDOUT, creationflags=flags)