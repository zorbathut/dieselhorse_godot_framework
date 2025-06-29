
using Dec;
using Godot;
using Map;
using Map.Utils;
using Chunk = Map.Utils.ChunkSerializer.Chunk;

namespace Test;

[TestFixture]
public class ChunkSerialization : Base
{
    [Dec.StaticReferences]
    public static class Decs
    {
        static Decs() { Dec.StaticReferencesAttribute.Initialized(); }

        public static ThingDec Wood;
        public static ThingDec Gneiss;
        public static ThingDec Chair;
        public static ThingDec PROTOTYPE_Berserker;
    }

    [Test]
    public void TestSerialization()
    {
        Chunk c = CreateChunk();

        var serializedResult = Recorder.Write(c);
        var serializedChunk = Recorder.Read<Chunk>(serializedResult);

        AssertSerializedChunkAndInitialChunkEquality(serializedChunk, c);
    }

    private Chunk CreateChunk()
    {
        var chunk = new Chunk() { tileRows = new List<List<ChunkSerializer.ChunkTile>>() };

        const int rowCount = 10;
        const int columnCount = 14;


        var chunkLines = new List<string>(rowCount)
        {
            "       a      ",
            "     aaaaaaaa ",
            "     aa     a ",
            "    ccaaaaaaaa",
            "   aaaaaddaaa ",
            "  a     a   a ",
            " aaa    a   a ",
            " aaaa   a   a ",
            "  aa a  a   a ",
            "bbaaaaabbbbbbb",
        };

        for (var y = 0; y < rowCount; y++)
        {
            chunk.tileRows.Add(new List<ChunkSerializer.ChunkTile>());
            var lineString = chunkLines[y];
            for (var x = 0; x < columnCount; x++)
            {
                var symbol = lineString[x];

                ChunkSerializer.ChunkTile t = symbol switch
                {
                    ' ' => new ChunkSerializer.ChunkTile(
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Background, null),
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Foreground, null)),
                    'a' => new ChunkSerializer.ChunkTile(
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Background, Decs.Wood),
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Foreground, null)),
                    'b' => new ChunkSerializer.ChunkTile(
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Background, Decs.Gneiss),
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Foreground, null)),
                    'c' => new ChunkSerializer.ChunkTile(
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Background, Decs.Gneiss),
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Foreground, Decs.Wood)),
                    'd' => new ChunkSerializer.ChunkTile(
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Background, Decs.Wood),
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Foreground, Decs.Gneiss)),
                    _ => throw new ArgumentOutOfRangeException()
                };
                chunk.tileRows[y].Add(t);
            }
        }

        chunk.things = new List<ChunkSerializer.ChunkThing>()
        {
            new() { dec = Decs.Chair, position = Vector2.Down }, new() { dec = Decs.Chair, position = Vector2.Left },
            new() { dec = Decs.PROTOTYPE_Berserker, position = Vector2.Down }, new() { dec = Decs.PROTOTYPE_Berserker, position = Vector2.Left },
        };

        return chunk;
    }

    private static void AssertSerializedChunkAndInitialChunkEquality(Chunk serializedChunk,
        Chunk initialChunk)
    {
        Assert.IsTrue(serializedChunk.tileRows.Count == initialChunk.tileRows.Count,
            "Serialized chunk should have the same number of tile rows as initial chunk!");
        for (var rowIndex = 0; rowIndex < serializedChunk.tileRows.Count; rowIndex++)
        {
            var row1 = serializedChunk.tileRows[rowIndex];
            var row2 = initialChunk.tileRows[rowIndex];

            for (var columnIndex = 0; columnIndex < row2.Count; columnIndex++)
            {
                Assert.IsTrue(row1[columnIndex].Equals(row2[columnIndex]));
            }
        }

        var originalComboCodes = initialChunk.comboCodes.OrderBy(c => c.Key).ToList();
        var serializedComboCodes = serializedChunk.comboCodes.OrderBy(c => c.Key).ToList();

        Assert.IsTrue(serializedComboCodes.Count == originalComboCodes.Count, "The chunks should have the same amount of character encodings");
        for (var i = 0; i < originalComboCodes.Count; i++)
        {
            Assert.IsTrue(originalComboCodes[i].Key == serializedComboCodes[i].Key, "Character mismatch between chunks");
            Assert.IsTrue(originalComboCodes[i].Value == serializedComboCodes[i].Value, $"Encoded tile data for character {originalComboCodes[i].Key} do not match between source and result");
        }

        var originalThings = SortChunkThingList(initialChunk.things);
        var serializedThings = SortChunkThingList(serializedChunk.things);

        AssertChunkThingEquality(originalThings, serializedThings);
    }

    private static List<ChunkSerializer.ChunkThing> SortChunkThingList(List<ChunkSerializer.ChunkThing> chunkThings)
    {
        return chunkThings.OrderBy(c => c.dec.DecName).ThenBy(c => c.position.X).ThenBy(c => c.position.Y).ToList();
    }

    private static void AssertChunkThingEquality(List<ChunkSerializer.ChunkThing> originalPlaceables, List<ChunkSerializer.ChunkThing> serializedPlaceables)
    {
        Assert.IsTrue(originalPlaceables.Count == serializedPlaceables.Count, $"The chunks should have the same amount of placeable keys");
        for (var rowIndex = 0; rowIndex < originalPlaceables.Count; rowIndex++)
        {
            var row1 = originalPlaceables[rowIndex];
            var row2 = serializedPlaceables[rowIndex];
            Assert.IsTrue(row1.dec == row2.dec && row1.position.IsEqualApprox(row2.position), $"The chunk things should be equal");
        }
    }
}

