
using Godot;
using System;
using System.Threading;

namespace Test;

[SetUpFixture]
public class Fixture
{
    internal static ThreadLocal<bool> dispatchingNunit;

    internal static ThreadLocal<bool> handlingWarnings;
    internal static ThreadLocal<bool> handledWarning;

    internal static ThreadLocal<bool> handlingErrors;
    internal static ThreadLocal<bool> handledError;
    internal static ThreadLocal<Func<string, bool>> errorValidator;
    internal static ThreadLocal<Func<string, bool>> warningValidator;

    internal static ThreadLocal<bool> withinExpect;

    [OneTimeSetUp]
    public void OneTimeSetUp()
    {
        // Initialize ThreadLocal variables
        dispatchingNunit = new ThreadLocal<bool>(() => false);

        handlingWarnings = new ThreadLocal<bool>(() => false);
        handledWarning = new ThreadLocal<bool>(() => false);

        handlingErrors = new ThreadLocal<bool>(() => false);
        handledError = new ThreadLocal<bool>(() => false);
        errorValidator = new ThreadLocal<Func<string, bool>>(() => null);
        warningValidator = new ThreadLocal<Func<string, bool>>(() => null);

        withinExpect = new ThreadLocal<bool>(() => false);

        // Reset flags
        dispatchingNunit.Value = false;

        // Set up our hooks right now, just in case we get errors in LibGodot
        Foundation.Bootstrap.LogWarningSecondaryHook = (type, msg) =>
        {
            // avoid infinite recursion on errors
            if (dispatchingNunit.Value)
            {
                return;
            }

            string nunitError = null;

            if (type == UI.DebugConsole.InfoLine.Type.Warning)
            {
                if (handlingWarnings.Value)
                {
                    if (warningValidator.Value == null)
                    {
                        handledWarning.Value = true;
                    }
                    else if (warningValidator.Value(msg))
                    {
                        handledWarning.Value = true;
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
                if (handlingErrors.Value)
                {
                    if (errorValidator.Value == null)
                    {
                        handledError.Value = true;
                    }
                    else if (errorValidator.Value(msg))
                    {
                        handledError.Value = true;
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
                dispatchingNunit.Value = true;
                NUnit.Framework.Assert.Fail(nunitError);
                dispatchingNunit.Value = false;
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

    [OneTimeTearDown]
    public void OneTimeTearDown()
    {
        dispatchingNunit?.Dispose();

        handlingWarnings?.Dispose();
        handledWarning?.Dispose();

        handlingErrors?.Dispose();
        handledError?.Dispose();
        errorValidator?.Dispose();
        warningValidator?.Dispose();

        withinExpect?.Dispose();
    }
}

[Parallelizable]
public class Base
{
    protected enum ExpectationType
    {
        Disallow,
        Tolerate,
        Expect,
    }
    protected static void ExpectGeneral(Action action, string context = "unlabeled context", ExpectationType warning = ExpectationType.Disallow, Func<string, bool> warningValidator = null, ExpectationType error = ExpectationType.Disallow, Func<string, bool> errorValidator = null)
    {
        Assert.IsFalse(Fixture.withinExpect.Value);
        Fixture.withinExpect.Value = true;

        // Check initial states based on expectations
        if (warning != ExpectationType.Disallow)
        {
            Assert.IsFalse(Fixture.handlingWarnings.Value, "Already handling warnings");
            Fixture.handlingWarnings.Value = true;
            Fixture.handledWarning.Value = false;
            Fixture.warningValidator.Value = warningValidator;
        }

        if (error != ExpectationType.Disallow)
        {
            Assert.IsFalse(Fixture.handlingErrors.Value, "Already handling errors");
            Fixture.handlingErrors.Value = true;
            Fixture.handledError.Value = false;
            Fixture.errorValidator.Value = errorValidator;
        }

        // Execute the action
        action();

        // Check for expected errors
        if (error == ExpectationType.Expect)
        {
            Assert.IsTrue(Fixture.handlingErrors.Value);
            Fixture.handlingErrors.Value = false; // do this first so our assert doesn't get eaten :V
            Assert.IsTrue(Fixture.handledError.Value, $"Expected error in {context} but did not generate one");
        }

        // Check for expected warnings
        if (warning == ExpectationType.Expect)
        {
            Assert.IsTrue(Fixture.handlingWarnings.Value);
            Assert.IsTrue(Fixture.handledWarning.Value, $"Expected warning in {context} but did not generate one");
        }

        // Reset state
        Fixture.handlingWarnings.Value = false;
        Fixture.handledWarning.Value = false;
        Fixture.warningValidator.Value = null;
        Fixture.handlingErrors.Value = false;
        Fixture.handledError.Value = false;
        Fixture.errorValidator.Value = null;

        Fixture.withinExpect.Value = false;
    }

    protected static void ExpectWarnings(Action action, string context = "unlabeled context", Func<string, bool> warningValidator = null)
    {
        ExpectGeneral(action, context, ExpectationType.Expect, warningValidator, ExpectationType.Disallow, null);
    }

    // Return "true" if this is the expected error, "false" if this is a bad error
    protected static void ExpectErrors(Action action, string context = "unlabeled context", Func<string, bool> errorValidator = null)
    {
        ExpectGeneral(action, context, ExpectationType.Disallow, null, ExpectationType.Expect, errorValidator);
    }

    protected static void ExpectWarningsAndErrors(Action action, string context = "unlabeled context",
        Func<string, bool> warningValidator = null, Func<string, bool> errorValidator = null)
    {
        ExpectGeneral(action, context, ExpectationType.Expect, warningValidator, ExpectationType.Expect, errorValidator);
    }
}
