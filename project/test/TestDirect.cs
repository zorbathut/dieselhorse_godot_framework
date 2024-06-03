namespace Examples;

using GdUnit4;
using static GdUnit4.Assertions;

using Godot;

[TestSuite]
public class ExampleTest
{
    [TestCase]
    public void Success()
    {
        AssertBool(true).IsTrue();
    }

    [TestCase]
    public void DistanceSquaredTo()
    {
        AssertFloat(UtilMath.DistanceSquaredTo(new Rect2(0, 0, 10, 10), new Vector2(5, 5))).IsEqual(0);
    }
}
