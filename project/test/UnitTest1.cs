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
        LibGodot.StartIfNecessary();

        Console.Error.WriteLine($"{Dec.Database.Count}");
    }
}