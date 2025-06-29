
namespace Test;

[TestFixture]
public class Simple : Base
{
    [Test]
    public void AbsolutelyNothing()
    {
        // okay seriously this should always pass
    }

    [Test]
    public void GodotApi()
    {
        var container = new Godot.Container();
        container.GetParent();
    }

    [Test]
    public void JustInit()
    {
        Assert.IsTrue(Dec.Database.Count > 0);
    }

    [Test]
    public void NullException()
    {
        // this is here because there was a libgodot error that caused naturally-generated null exceptions to result in a process hardcrash
        try
        {
            List<int> list = null;
            list.Add(0);
        }
        catch (Exception e)
        {

        }
    }

    [Test]
    public void ContextCreation()
    {
        var playerInputShunt = new ReadWriteLockedResource<Foundation.SharedPlayerInput>(new Foundation.SharedPlayerInput());
        var context = new Foundation.Executor(playerInputShunt) { context = new Foundation.Context() { env = Genesis.CreateNewGame() } };
    }

    [Test]
    public void NullFrame()
    {
        var playerInputShunt = new ReadWriteLockedResource<Foundation.SharedPlayerInput>(new Foundation.SharedPlayerInput());
        var context = new Foundation.Executor(playerInputShunt) { context = new Foundation.Context() { env = Genesis.CreateNewGame() } };

        context.Process();
    }

    [Test]
    public void SpawnAndRun()
    {
        using var gameScoped = new GameScoped();

        Assert.AreEqual(0, gameScoped.Env.List.Count(e => e.HasComponent<Comp.Player>()));

        gameScoped.Process(new Comp.PlayerInput(), new Foundation.GlobalEventSpawn());

        Assert.AreEqual(1, gameScoped.Env.List.Count(e => e.HasComponent<Comp.Player>()));
    }

    [Test]
    public void DeadPlayer()
    {
        using var gameScoped = new GameScoped();
        gameScoped.Process(new Comp.PlayerInput(), new Foundation.GlobalEventSpawn());

        // kill the player's avatar
        gameScoped.Env.Remove(gameScoped.Env.List.Single(e => e.HasComponent<Comp.Avatar>()));

        // do we still run properly?
        gameScoped.Process(new Comp.PlayerInput());
    }
}
