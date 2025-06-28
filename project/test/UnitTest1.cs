namespace planefarer_test;

public class Tests
{
    [SetUp]
    public void Setup()
    {
    }

    // Create your callback methods
    private static void InitializeCallback(IntPtr userdata, GDExtensionInitializationLevel level)
    {
        Console.WriteLine($"Initialize called with level: {level}");
    }

    private static void DeinitializeCallback(IntPtr userdata, GDExtensionInitializationLevel level)
    {
        Console.WriteLine($"Deinitialize called with level: {level}");
    }

    // Create delegates
    // note: these must never change! they must be kept in memory!
    private static GDExtensionInitializationCallback initDelegate = new GDExtensionInitializationCallback(InitializeCallback);
    private static GDExtensionInitializationCallback deinitDelegate = new GDExtensionInitializationCallback(DeinitializeCallback);

    private static bool InitCallback(IntPtr p_get_proc_address, IntPtr p_library, ref GDExtensionInitialization r_initialization)
    {
        Console.Error.WriteLine("yep yep");

        r_initialization.initialize = System.Runtime.InteropServices.Marshal.GetFunctionPointerForDelegate(initDelegate);
        r_initialization.deinitialize = System.Runtime.InteropServices.Marshal.GetFunctionPointerForDelegate(deinitDelegate);

        return true;
    }

    [Test]
    public void Test1()
    {
        var cc = new Converter.ColorConverter();

        {
            var c = cc.Read("oklch(70% 0.1 188)", new Dec.Context("test"));
            Assert.AreEqual(0.05818826f, c.R);
            Assert.AreEqual(0.44735658f, c.G);
            Assert.AreEqual(0.40130332f, c.B);
        }

        {
            var c = cc.Read("oklch(64.39% 0.0781 79)", new Dec.Context("test"));
            Assert.AreEqual(0.38660142f, c.R);
            Assert.AreEqual(0.24581487f, c.G);
            Assert.AreEqual(0.09080556f, c.B);
        }


        Console.Error.WriteLine("Hello Libgodot-csharp ! ");
        string program = "";

        string assemblyLocation = System.Reflection.Assembly.GetExecutingAssembly().Location;
        string buildDirectory = System.IO.Path.GetDirectoryName(assemblyLocation);
        string projectDirectory = System.IO.Path.GetFullPath(System.IO.Path.Combine(buildDirectory, @"../../../../"));

        List<string> arguments = new List<string> { program, "--path", projectDirectory, "--api_assemblies_dir", buildDirectory, "--headless" };

        Console.Error.WriteLine("argl");

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

        Console.Error.WriteLine("ferbi");

        // this is ghastly; we need to call InteropUtils.UnmanagedGetManaged(instance) to get the GodotInstance object

        Console.Error.WriteLine("snerble?");

        //instanceManaged.Start();

        var container = new Godot.Container();
        container.GetParent();
        /*
        bool success = LibGodot.libgodot_start_godot_instance(instance);
        while (LibGodot.libgodot_iteration_godot_instance(instance))
        {
        }*/

        Console.Error.WriteLine("derble.");
    }
}