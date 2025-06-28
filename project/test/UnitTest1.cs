namespace planefarer_test;

public class Tests
{
    [SetUp]
    public void Setup()
    {
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

        LibGodot.StartIfNecessary();

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