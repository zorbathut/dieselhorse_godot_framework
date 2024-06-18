
# Windows initial setup

* Install Python from https://www.python.org/downloads/
* Once it's installed, install Poetry from https://python-poetry.org/docs/
	* The easiest method is to start Windows Powershell from your start menu, then paste in the following line:
		(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
* Install Visual Studio 2022 Community from https://visualstudio.microsoft.com/vs/
	* When installing, under Workloads, click "Desktop development with C++" and ".NET desktop development"



# If you happen to run Manjaro Linux, here's its initial setup

* `pamac install python python-poetry dotnet-sdk-8.0` (you don't need the supporting ASP.NET packages)
* a while ago there was a glitch in Manjaro that required `python-tomli` as well; it might be fixed by now, if you're following this guide, try it without and see if it works



# To run the editor:

* Run `build_and_run_editor`

It will take a *long* time the first time, but will be pretty speedy after that.
