
#if false
namespace Test;

public class Base
{
    private static bool initted = false;
    public void Init()
    {
        if (!initted)
        {
            // this is really not the right way to initialize, honestly
            var bootstrap = new Foundation.Bootstrap();
            bootstrap._Ready();

            // this is also not really the right way to initialize :V
            DebugOptions.Init(null);

            initted = true;
        }
    }
}
#endif
