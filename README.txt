### Windows initial setup

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


### Mac initial setup

* Install the Command Line Tools For Xcode , or Xcode itself, from the App Store.
    * If you're not a programmer, the Command Line Tools are smaller and easier.
* Install Python from https://www.python.org/downloads/
* Install Python Poetry . . . somehow, I don't actually know how this gets installed. Maybe open a terminal and try `pipx install poetry`? Maybe the same thing, except `brew install poetry`? Let me know what ends up working so I can update this!
* Install the Vulkan SDK, which can be found at https://sdk.lunarg.com/sdk/download/latest/mac/vulkan-sdk.dmg
* Install the .NET SDK from https://dotnet.microsoft.com/en-us/download/dotnet/8.0


### If you happen to run Manjaro Linux, here's its initial setup

* `pamac install python python-poetry dotnet-sdk-8.0` (you don't need the supporting ASP.NET packages)
* It is also possible you'll need to install a C++ compiler. Let me know what it turned out you needed. This documentation is incomplete.
* A while ago there was a glitch in Manjaro that required `python-tomli` as well; it might be fixed by now, if you're following this guide, try it without and see if it works. If it doesn't, install that too.


### To run the editor:

* Run `build_and_run_editor.bat`
* (yes, even if you're not on Windows, just trust me; if you're on Mac, you will have to open a terminal in that directory, then type `./build_and_run_editor.bat`)

It will take a *long* time the first time, but will be pretty speedy after that. You should do this every time you pull new code.

From inside the editor, you can run the game with the play button in the top-right. If you're editing code, Visual Studio, VS Code, and Jetbrains Rider should all be able to run the game directly from the IDE, but note that *you have to run the editor once* to get things started or you'll get a gray screen without explanation.


### Exporting/deploying a build to the users

Open a commandline prompt. Run `tool.bat deploy --target=windows`. You'll find the generated build in the `deploy` directory.

Note that Godot tends to spit out a lot of false positive errors on the command line. You will probably see a bunch of those; they don't mean the build didn't work.

Most build settings can be configured inside the editor, under Project Settings.
