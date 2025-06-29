
using Godot;

namespace Test;

public class Base
{
    [SetUp]
    public void SetUp()
    {
        LibGodot.StartIfNecessary();

        // find the only Bootstrap node and finish our init
        var sceneTree = Godot.Engine.GetMainLoop() as SceneTree;
        var bootstrap = sceneTree.Root.GetNode<Foundation.Bootstrap>("Bootstrap");
        bootstrap.InitCoreProviders();
    }
}
