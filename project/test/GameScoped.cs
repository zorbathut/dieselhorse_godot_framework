
using System;

namespace Test;

public class GameScoped : System.IDisposable
{
    public Foundation.Executor executor;

    public Ghi.Environment Env => executor.context.env;

    private ReadWriteLockedResource<Foundation.SharedPlayerInput> playerInputShunt = new ReadWriteLockedResource<Foundation.SharedPlayerInput>(new Foundation.SharedPlayerInput());

    private Ghi.Environment.Scope scope;

    public GameScoped()
    {
        executor = new Foundation.Executor(playerInputShunt) { context = Foundation.ContextUtil.CreateMap() };

        scope = new Ghi.Environment.Scope(Env);
    }

    public void Process(Comp.PlayerInput input, Foundation.GlobalEvent globalEvent = null)
    {
        // just in case we're not scoped
        using var envscope = new Ghi.Environment.Scope(Env);

        {
            using var writeable = playerInputShunt.Write();

            var frame = new Foundation.InputAccumulator.Frame();
            frame.inputs[0] = input;

            if (globalEvent != null)
            {
                frame.events = new();
                frame.events.Add(globalEvent);
            }

            writeable.Resource.data.Add((Env.SingletonRO<Comp.Global>().timestamp + Duration.FromFrames(1), frame));
        }

        executor.Process();
    }

    public void Dispose()
    {
        scope.Dispose();
    }
}
