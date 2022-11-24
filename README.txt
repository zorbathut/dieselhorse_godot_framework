
# Windows initial setup

* Install Python from https://www.python.org/downloads/
* Once it's installed, install Poetry from https://python-poetry.org/docs/
	* The easiest solution is to start Windows Powershell from your start menu, then paste in the following line:
		(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
* Install Visual Studio 2022 Community from https://visualstudio.microsoft.com/vs/
	* When installing, under Workloads, click "Desktop development with C++" and ".NET desktop development"



# Manjaro initial setup

* `pacman -S python3 poetry dotnet-sdk-6`



# To run the editor:

* Run `build_and_run_editor`

It will take a *long* time the first time, but will be pretty speedy after that.
