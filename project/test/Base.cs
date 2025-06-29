
using Godot;

namespace Test;

public class Base
{
    [SetUp]
    public void SetUp()
    {
        LibGodot.StartIfNecessary();

        // This is safe because this is all intrinsically single-threaded; we currently very much do not support multithreaded testing (maybe someday?)
        Godot.GodotThread.SetThreadSafetyChecksEnabled(false);

        // find the only Bootstrap node and finish our init
        var sceneTree = Godot.Engine.GetMainLoop() as SceneTree;
        var bootstrap = sceneTree.Root.GetNode<Foundation.Bootstrap>("Bootstrap");
        bootstrap.InitCoreProviders();
    }
}
