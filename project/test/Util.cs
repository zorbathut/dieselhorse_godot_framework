
using System.Collections;

namespace Test;

[AttributeUsage(AttributeTargets.Parameter, AllowMultiple = false, Inherited = false)]
public class ValuesAttribute : NUnit.Framework.ValuesAttribute, NUnit.Framework.Interfaces.IParameterDataSource
{
    public ValuesAttribute()
    {
    }

    /// <summary>
    /// Retrieves a list of arguments which can be passed to the specified parameter.
    /// </summary>
    /// <param name="parameter">The parameter of a parameterized test.</param>
    public new IEnumerable GetData(NUnit.Framework.Interfaces.IParameterInfo parameter)
    {
        if (parameter.ParameterType.BaseType == typeof(Dec.Dec))
        {
            LibGodot.StartIfNecessary();

            // remember to include inheritance
            return Dec.Database.List.Where(dec => dec.GetType() == parameter.ParameterType || dec.GetType().IsSubclassOf(parameter.ParameterType));
        }
        else
        {
            return base.GetData(parameter);
        }
    }
}
