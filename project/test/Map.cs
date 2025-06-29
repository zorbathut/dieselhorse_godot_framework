
namespace Test;

[TestFixture]
public class Map : Base
{
    [Test]
    public void Construction([Values] MapDec decs)
    {
        using var gameScoped = new GameScoped(decs);

         Assert.AreEqual(0, gameScoped.Env.List.Count(e => e.HasComponent<Comp.Player>()));

         // one frame with nothing
         gameScoped.Process(new Comp.PlayerInput());

         // one frame with spawn
         gameScoped.Process(new Comp.PlayerInput(), new Foundation.GlobalEventSpawn());

         // one frame with player
         gameScoped.Process(new Comp.PlayerInput());

        Assert.AreEqual(1, gameScoped.Env.List.Count(e => e.HasComponent<Comp.Player>()));
    }
}
