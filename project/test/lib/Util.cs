
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;

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

public static class Util
{

    public struct InitResults
    {
        public Ghi.EntityComponent<Comp.Map> map;
        public Ghi.Entity avatar;
    }

    public static InitResults SetGameMap(GameScoped gameScoped, string[] mapLayout, (char, ThingDec)[] tileDecs)
    {
        var results = new InitResults();

        var mapEnt = Find.Environment.List.Single(ent => ent.HasComponent<Comp.Map>());
        var map = mapEnt.ComponentRW<Comp.Map>();
        results.map = Ghi.EntityComponent<Comp.Map>.From(mapEnt);

        int height = mapLayout.Length;
        int width = mapLayout[0].Length;
        Assert.IsTrue(mapLayout.All(line => line.Length == width), "All lines in the map layout must have the same length.");

        map.Resize(new Godot.Rect2I(Godot.Vector2I.Zero, new Godot.Vector2I(width, height)));

        Dictionary<char, ThingDec> decMap = tileDecs.ToDictionary(pair => pair.Item1, pair => pair.Item2);
        decMap.Add(' ', null);

        MapVector2Q? spawnPoint = null;
        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                char tileChar = mapLayout[y][x];
                if (tileChar == '*')
                {
                    spawnPoint = MapVector2Q.From(Ghi.EntityComponent<Comp.Map>.From(mapEnt), x, y + 1);
                    tileChar = ' ';
                }

                map.SetAt(x, y, global::Map.LayerDecs.Foreground, ThingDecWith<Prop.Tile.Base>.From(decMap[tileChar]));
            }
        }

        if (spawnPoint.HasValue)
        {
            var avatarRegion = ThingDecs.Avatar.Property<Prop.Region>().GetRegionTemplate(ActorRegionDecs.Base);
            var spawnRect = avatarRegion.Translated(spawnPoint.Value.vector.ToVector2() - avatarRegion.GetBC());

            gameScoped.Process(new Comp.PlayerInput(), Foundation.GlobalEventSpawn.Create(MapRect2Q.From(Ghi.EntityComponent<Comp.Map>.From(mapEnt), Rect2Q.FromRect2(spawnRect)).Grow(Q32.One / 1000)));

            // verify we spawned properly
            var avatar = Find.Globals.avatars.FirstOrDefault();
            var footPosition = avatar.GetRegion(ActorRegionDecs.Base).rect.GetBC();
            Assert.AreEqual(spawnPoint.Value.vector.Y.ToDouble(), footPosition.Y);
            Assert.AreEqualWithin(spawnPoint.Value.vector.X.ToDouble(), footPosition.X, 0.2f);

            results.avatar = avatar;
        }

        return results;
    }
}