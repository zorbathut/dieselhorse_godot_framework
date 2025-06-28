
namespace Test;

[TestFixture]
public class Color : Base
{
    [Test]
    public void OKLCH()
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
    }
}
