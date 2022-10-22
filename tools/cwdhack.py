
import os

# right now poetry doesn't let us set the project directory, so we need to find the right directory for scripts first
def cwdhack():
    while not os.path.exists("README.txt"):
        os.chdir("..")
