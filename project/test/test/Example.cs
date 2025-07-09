
using Godot;

namespace Test;

[TestFixture]
public class Example
{
    [SetUp]
    public void SetUp()
    {
        LibGodot.StartIfNecessary();
    }

    [Test]
    public void Succeed()
    {
        var image = Godot.Image.CreateEmpty(16, 16, false, Image.Format.Dxt3);
        var x = image.SavePngToBuffer();
        // make sure we got data out
        Assert.That(x.Length, Is.GreaterThan(0), "Image should have data in the buffer");
    }

    [Test]
    public void Fail()
    {
        var image = Godot.Image.CreateEmpty(16, 16, false, Image.Format.Max);   // oh no my finger slipped, what a disaster
        var x = image.SavePngToBuffer();
        // make sure we got data out
        Assert.That(x.Length, Is.GreaterThan(0), "Image should have data in the buffer");
    }
}
