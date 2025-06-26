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
    const string LIBGODOT_LIBRARY_NAME = "/home/zorba/werk/moonskrive/godot/bin/libgodot.universal.editor.dll";

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
}
