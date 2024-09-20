
# Windows initial setup

* Install Python from https://www.python.org/downloads/
    * Don't uncheck the `py launcher` option, it's necessary. Default settings will do the right thing.
* Once it's installed, install Poetry from https://python-poetry.org/docs/
	* The easiest method is to start Windows Powershell from your start menu, then paste in the following line:
		(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
* Install either Visual Studio Build Tools or Visual Studio Community
    * If you're not a programmer, or have your own favorite programming environment, Build Tools is smaller and easier
        * Recommend downloading from https://aka.ms/vs/17/release/vs_BuildTools.exe
        * If you don't trust that link, go to https://visualstudio.microsoft.com/downloads/, scroll down to "Tools for Visual Studio", download Build Tools for Visual Studio 2022 (later is fine if they've released a new version)
	* If you want the full Visual Studio experience, go to https://visualstudio.microsoft.com/downloads/ and choose the Community Free Download
        * When installing, under Workloads, click "Desktop development with C++" and ".NET desktop build tools"



# If you happen to run Manjaro Linux, here's its initial setup

* `pamac install python python-poetry dotnet-sdk-8.0` (you don't need the supporting ASP.NET packages)
* It is also possible you'll need to install a C++ compiler. Let me know what it turned out you needed. This documentation is incomplete.
* A while ago there was a glitch in Manjaro that required `python-tomli` as well; it might be fixed by now, if you're following this guide, try it without and see if it works. If it doesn't, install that too.



# To run the editor:

* Run `build_and_run_editor`

It will take a *long* time the first time, but will be pretty speedy after that.

From inside the editor, you can run the game with the play button in the top-right. If you're editing code, Visual Studio, VS Code, and Jetbrains Rider should all be able to run the game directly from the IDE, but note that *you have to run the editor once* to get things started or you'll get a gray screen without explanation.
