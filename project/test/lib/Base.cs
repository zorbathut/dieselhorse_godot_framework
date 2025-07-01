
using Godot;
using System;

namespace Test;

public class Base
{
    public bool dispatchingNunit = false;

    [OneTimeSetUp]
    public void OneTimeSetUp()
    {
        // Reset flags
        dispatchingNunit = false;

        // Set up our hooks right now, just in case we get errors in LibGodot
        Foundation.Bootstrap.LogWarningSecondaryHook = (type, msg) =>
        {
            // avoid infinite recursion on errors
            if (dispatchingNunit)
            {
                return;
            }

            string nunitError = null;

            if (type == UI.DebugConsole.InfoLine.Type.Warning)
            {
                if (handlingWarnings)
                {
                    if (warningValidator == null)
                    {
                        handledWarning = true;
                    }
                    else if (warningValidator(msg))
                    {
                        handledWarning = true;
                    }
                    else
                    {
                        nunitError = $"Warning fails validation: {msg}";
                    }
                }
                else
                {
                    nunitError = $"WARN: {msg}";
                }
            }
            else if (type == UI.DebugConsole.InfoLine.Type.Error)
            {
                if (handlingErrors)
                {
                    if (errorValidator == null)
                    {
                        handledError = true;
                    }
                    else if (errorValidator(msg))
                    {
                        handledError = true;
                    }
                    else
                    {
                        nunitError = $"Error fails validation: {msg}";
                    }
                }
                else
                {
                    nunitError = $"ERROR: {msg}";
                }
            }

            // if we just fail, we end up in infinite recursion, so let's not do that
            if (nunitError != null)
            {
                dispatchingNunit = true;
                NUnit.Framework.Assert.Fail(nunitError);
                dispatchingNunit = false;
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

    private bool handlingWarnings = false;
    private bool handledWarning = false;

    private bool handlingErrors = false;
    private bool handledError = false;
    private Func<string, bool> errorValidator = null;
    private Func<string, bool> warningValidator = null;

    protected enum ExpectationType
    {
        Disallow,
        Tolerate,
        Expect,
    }
    private bool withinExpect = false;
    protected void ExpectGeneral(Action action, string context = "unlabeled context", ExpectationType warning = ExpectationType.Disallow, Func<string, bool> warningValidator = null, ExpectationType error = ExpectationType.Disallow, Func<string, bool> errorValidator = null)
    {
        Assert.IsFalse(withinExpect);
        withinExpect = true;

        // Check initial states based on expectations
        if (warning != ExpectationType.Disallow)
        {
            Assert.IsFalse(handlingWarnings, "Already handling warnings");
            handlingWarnings = true;
            handledWarning = false;
            this.warningValidator = warningValidator;
        }

        if (error != ExpectationType.Disallow)
        {
            Assert.IsFalse(handlingErrors, "Already handling errors");
            handlingErrors = true;
            handledError = false;
            this.errorValidator = errorValidator;
        }

        // Execute the action
        action();

        // Check for expected errors
        if (error == ExpectationType.Expect)
        {
            Assert.IsTrue(handlingErrors);
            handlingErrors = false; // do this first so our assert doesn't get eaten :V
            Assert.IsTrue(handledError, $"Expected error in {context} but did not generate one");
        }

        // Check for expected warnings
        if (warning == ExpectationType.Expect)
        {
            Assert.IsTrue(handlingWarnings);
            Assert.IsTrue(handledWarning, $"Expected warning in {context} but did not generate one");
        }

        // Reset state
        handlingWarnings = false;
        handledWarning = false;
        this.warningValidator = null;
        handlingErrors = false;
        handledError = false;
        this.errorValidator = null;

        withinExpect = false;
    }

    protected void ExpectWarnings(Action action, string context = "unlabeled context", Func<string, bool> warningValidator = null)
    {
        ExpectGeneral(action, context, ExpectationType.Expect, warningValidator, ExpectationType.Disallow, null);
    }

    // Return "true" if this is the expected error, "false" if this is a bad error
    protected void ExpectErrors(Action action, string context = "unlabeled context", Func<string, bool> errorValidator = null)
    {
        ExpectGeneral(action, context, ExpectationType.Disallow, null, ExpectationType.Expect, errorValidator);
    }

    protected void ExpectWarningsAndErrors(Action action, string context = "unlabeled context",
        Func<string, bool> warningValidator = null, Func<string, bool> errorValidator = null)
    {
        ExpectGeneral(action, context, ExpectationType.Expect, warningValidator, ExpectationType.Expect, errorValidator);
    }
}
