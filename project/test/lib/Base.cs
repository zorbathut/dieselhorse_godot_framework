
using Godot;

namespace Test;

public class Base
{
    private static bool handlingError = false;

    [SetUp]
    public void SetUp()
    {
        // Reset flags
        handlingError = false;

        // Set up our hooks right now, just in case we get errors in LibGodot
        Foundation.Bootstrap.LogWarningSecondaryHook = msg =>
        {
            // if we just fail, we end up in infinite recursion
            if (!handlingError)
            {
                handlingError = true;
                NUnit.Framework.Assert.Fail(msg);
                handlingError = false;
            }
        };

        LibGodot.StartIfNecessary();

        // This is safe because this is all intrinsically single-threaded; we currently very much do not support multithreaded testing (maybe someday?)
        if (!Godot.GodotThread.IsMainThread())
        {
            Godot.GodotThread.SetThreadSafetyChecksEnabled(false);
        }

        // find the only Bootstrap node and finish our init
        var sceneTree = Godot.Engine.GetMainLoop() as SceneTree;
        var bootstrap = sceneTree.Root.GetNode<Foundation.Bootstrap>("Bootstrap");
        bootstrap.InitCoreProviders();
    }
}
