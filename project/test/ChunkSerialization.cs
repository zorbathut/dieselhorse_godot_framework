using System;
using System.Collections.Generic;
using System.Linq;
using Dec;
using GdUnit4;
using Map;
using Map.Utils;
using Chunk = Map.Utils.ChunkSerializer.Chunk;

namespace Test;

[TestSuite]
public class ChunkSerialization : Base
{
    [TestCase]
    public void TestSerialization()
    {
        base.Init();
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


        var wood = Database<ThingDec>.Get("Wood");
        var gneis = Database<ThingDec>.Get("Gneiss");
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
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Background, wood),
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Foreground, null)),
                    'b' => new ChunkSerializer.ChunkTile(
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Background, gneis),
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Foreground, null)),
                    'c' => new ChunkSerializer.ChunkTile(
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Background, gneis),
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Foreground, wood)),
                    'd' => new ChunkSerializer.ChunkTile(
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Background, wood),
                        new KeyValuePair<LayerDec, ThingDec>(LayerDecs.Foreground, gneis)),
                    _ => throw new ArgumentOutOfRangeException()
                };
                chunk.tileRows[y].Add(t);
            }
        }

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
    }
}