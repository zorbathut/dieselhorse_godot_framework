
using GdUnit4;

namespace Test;

[TestSuite]
public class Simple : Base
{
    [TestCase]
    public void AbsolutelyNothing()
    {
        // okay seriously this should always pass
    }

    [TestCase]
    public void JustInit()
    {
        Init();

        Assert.IsTrue(Dec.Database.Count > 0);
    }

    [TestCase]
    public void ContextCreation()
    {
        Init();

        var context = new Foundation.ContextManager(Foundation.ContextUtil.CreateMap());
    }
}
