
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

            initted = true;
        }
    }
}
