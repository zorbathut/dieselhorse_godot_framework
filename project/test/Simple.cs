
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

        using var gameScoped = new GameScoped();

        Assert.AreEqual(0, gameScoped.Env.List.Count(e => e.HasComponent<Comp.Player>()));

        gameScoped.Process(new Comp.PlayerInput(), new Foundation.GlobalEventSpawn() { playerId = 0 });

        Assert.AreEqual(1, gameScoped.Env.List.Count(e => e.HasComponent<Comp.Player>()));
    }

    [TestCase]
    public void DeadPlayer()
    {
        Init();

        using var gameScoped = new GameScoped();
        gameScoped.Process(new Comp.PlayerInput(), new Foundation.GlobalEventSpawn() { playerId = 0 });

        // kill the player's avatar
        gameScoped.Env.Remove(gameScoped.Env.List.Single(e => e.HasComponent<Comp.Avatar>()));

        // do we still run properly?
        gameScoped.Process(new Comp.PlayerInput());
    }
}
