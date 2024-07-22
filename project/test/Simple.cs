
using System.Linq;
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

        var playerInputShunt = new ReadWriteLockedResource<Foundation.SharedPlayerInput>(new Foundation.SharedPlayerInput());
        var context = new Foundation.Executor(playerInputShunt) { context = Foundation.ContextUtil.CreateMap() };
    }

    [TestCase]
    public void NullFrame()
    {
        Init();

        var playerInputShunt = new ReadWriteLockedResource<Foundation.SharedPlayerInput>(new Foundation.SharedPlayerInput());
        var context = new Foundation.Executor(playerInputShunt) { context = Foundation.ContextUtil.CreateMap() };

        context.Process();
    }

    [TestCase]
    public void SpawnAndRun()
    {
        Init();

        var playerInputShunt = new ReadWriteLockedResource<Foundation.SharedPlayerInput>(new Foundation.SharedPlayerInput());
        var context = new Foundation.Executor(playerInputShunt) { context = Foundation.ContextUtil.CreateMap() };

        using var envscope = new Ghi.Environment.Scope(context.context.env);

        {
            using var writeable = playerInputShunt.Write();
            var frame = new Foundation.InputAccumulator.Frame();
            frame.events = new System.Collections.Generic.List<Foundation.GlobalEvent>();
            frame.events.Add(new Foundation.GlobalEventSpawn() { playerId = 0 });

            writeable.Resource.data.Add((context.context.env.SingletonRO<Comp.Global>().timeFrame + 1, frame));
        }

        Assert.AreEqual(0, context.context.env.List.Count(e => e.HasComponent<Comp.Player>()));

        context.Process();

        Assert.AreEqual(1, context.context.env.List.Count(e => e.HasComponent<Comp.Player>()));
    }
}
