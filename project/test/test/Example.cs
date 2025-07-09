
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
    public void FormatTest([Values] Image.Format format)
    {
        var image = Godot.Image.CreateEmpty(16, 16, false, format);
        var x = image.SavePngToBuffer();
        // make sure we got data out
        Assert.That(x.Length, Is.GreaterThan(0), "Image should have data in the buffer");
    }
}
