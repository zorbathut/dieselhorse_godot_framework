
# Windows initial setup

* Install Python from https://www.python.org/downloads/
* Once it's installed, install Poetry from https://python-poetry.org/docs/
	* The easiest solution is to start Windows Powershell from your start menu, then paste in the following line:
		(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
* Install Visual Studio 2022 Community from https://visualstudio.microsoft.com/vs/
	* When installing, under Workloads, click "Desktop development with C++" and ".NET desktop development"



# Manjaro Linux initial setup

* `pamac install python python-poetry dotnet-sdk-6.0` (you don't need the supporting ASP.NET packages)
* a while ago there was a glitch in Manjaro that requires `python-tomli` as well; it might be fixed, if you're doing setup, try it without and see if it works



# To run the editor:

* Run `build_and_run_editor`

It will take a *long* time the first time, but will be pretty speedy after that.
