
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public enum GDExtensionInitializationLevel
{
    GDEXTENSION_INITIALIZATION_CORE,
    GDEXTENSION_INITIALIZATION_SERVERS,
    GDEXTENSION_INITIALIZATION_SCENE,
    GDEXTENSION_INITIALIZATION_EDITOR,
    GDEXTENSION_MAX_INITIALIZATION_LEVEL
}

[UnmanagedFunctionPointer(CallingConvention.Cdecl)]
public delegate void GDExtensionInitializationCallback(IntPtr userdata, GDExtensionInitializationLevel level);

[StructLayout(LayoutKind.Sequential)]
public struct GDExtensionInitialization
{
    public GDExtensionInitializationLevel minimum_initialization_level;
    public IntPtr userdata;
    public IntPtr initialize;
    public IntPtr deinitialize;
}

[UnmanagedFunctionPointer(CallingConvention.Cdecl)]
public delegate bool GDExtensionInitializationFunction(IntPtr p_get_proc_address, IntPtr p_library, ref GDExtensionInitialization r_initialization);

[UnmanagedFunctionPointer(CallingConvention.Cdecl)]
public delegate void InvokeCallback(IntPtr p_data);

[UnmanagedFunctionPointer(CallingConvention.Cdecl)]
public delegate void InvokeCallbackFunction(InvokeCallback p_callback, IntPtr p_callback_data, IntPtr p_executor_data);

public class LibGodot
{
    const string LIBGODOT_LIBRARY_NAME = "../../../../../godot/bin/libgodot.universal.editor.dll";

    [DllImport(LIBGODOT_LIBRARY_NAME, CallingConvention = CallingConvention.Cdecl)]
    public static extern IntPtr libgodot_create_godot_instance(
        int p_argc,
        [MarshalAs(UnmanagedType.LPArray, ArraySubType = UnmanagedType.LPStr)] string[] p_argv,
        GDExtensionInitializationFunction p_init_func,
        InvokeCallbackFunction p_async_func,
        IntPtr p_async_data,
        InvokeCallbackFunction p_sync_func,
        IntPtr p_sync_data);

    [DllImport(LIBGODOT_LIBRARY_NAME, CallingConvention = CallingConvention.Cdecl)]
    public static extern void libgodot_destroy_godot_instance(IntPtr p_godot_instance);

    // setup process
    private static void InitializeCallback(IntPtr userdata, GDExtensionInitializationLevel level) { }
    private static void DeinitializeCallback(IntPtr userdata, GDExtensionInitializationLevel level) { }

    // note: these must never change! they must be kept in memory or things crash!
    private static GDExtensionInitializationCallback initDelegate = new GDExtensionInitializationCallback(InitializeCallback);
    private static GDExtensionInitializationCallback deinitDelegate = new GDExtensionInitializationCallback(DeinitializeCallback);

    private static bool InitCallback(IntPtr p_get_proc_address, IntPtr p_library, ref GDExtensionInitialization r_initialization)
    {
        r_initialization.initialize = System.Runtime.InteropServices.Marshal.GetFunctionPointerForDelegate(initDelegate);
        r_initialization.deinitialize = System.Runtime.InteropServices.Marshal.GetFunctionPointerForDelegate(deinitDelegate);

        return true;
    }

    private static bool running = false;
    public static void StartIfNecessary()
    {
        if (running)
        {
            return;
        }

        // we need to touch *something* in the Planefarer DLL to ensure it gets loaded into the default load context before Godot tries to shove it into the plugin context, soon followed by nunit making a second copy of it and everything going all fucky
        // yes this is pretty gnarly
        var _ = Find.Game;

        string assemblyLocation = System.Reflection.Assembly.GetExecutingAssembly().Location;
        string buildDirectory = System.IO.Path.GetDirectoryName(assemblyLocation);
        string projectDirectory = System.IO.Path.GetFullPath(System.IO.Path.Combine(buildDirectory, @"../../../../"));

        List<string> arguments = new List<string> { ".", "--path", projectDirectory, "--api_assemblies_dir", buildDirectory, "--headless" };

        IntPtr instance = LibGodot.libgodot_create_godot_instance(arguments.Count, arguments.ToArray(),
            InitCallback,
            null,
            0,
            null,
            0);
        if (instance == IntPtr.Zero)
        {
            Console.Error.WriteLine("Error creating Godot instance");
            Environment.Exit(1);
        }

        running = true;
    }
}
