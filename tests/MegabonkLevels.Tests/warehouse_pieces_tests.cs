using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;

namespace MegabonkLevels.Tests;

public class WarehousePiecesTests
{
    const string Table = """
        # Inventory

        Some prose that mentions a | piece-like | fragment | inline.

        | ID | Element | Groups | Faces | Module |
        | --- | --- | --- | --- | --- |
        | piece-taxi | Taxi car | 9D14F7B5, 041DA60F | 278-280,285-296 | prop |
        | piece-post | Single post | AAAA | 7 | wall |
        | added-post-0 | Rail post | `RailPosts[0]` |
        | settings-music | Music | `music` |

        """;

    static WarehousePieces.Piece P(int[] faces, string module = "prop", string id = "piece-x", string group = "G")
        => new(id, id, new[] { group }, faces, module);

    static Vector3 V(float x, float y, float z) => new(x, y, z);

    static void Near(Vector3 expected, Vector3 actual, int precision = 4)
    {
        Assert.Equal(expected.X, actual.X, precision);
        Assert.Equal(expected.Y, actual.Y, precision);
        Assert.Equal(expected.Z, actual.Z, precision);
    }

    [Fact]
    public void ParsesFiveCellPieceRowsAndSkipsEverythingElse()
    {
        var pieces = WarehousePieces.ParseInventory(Table);
        Assert.Equal(2, pieces.Count);
        Assert.Equal("piece-taxi", pieces[0].Id);
        Assert.Equal("Taxi car", pieces[0].Name);
        Assert.Equal(new[] { "9D14F7B5", "041DA60F" }, pieces[0].Groups);
        Assert.Equal(Enumerable.Range(278, 3).Concat(Enumerable.Range(285, 12)).ToArray(), pieces[0].Faces);
        Assert.Equal("prop", pieces[0].Module);
        Assert.Equal(new[] { "AAAA" }, pieces[1].Groups);
        Assert.Equal(new[] { 7 }, pieces[1].Faces);
        Assert.Equal("wall", pieces[1].Module);
    }

    [Theory]
    [InlineData("7", new[] { 7 })]
    [InlineData("3-5", new[] { 3, 4, 5 })]
    [InlineData(" 278-280 , 285 ", new[] { 278, 279, 280, 285 })]
    public void FaceRangesExpandInclusiveRangesAndCommas(string text, int[] expected)
        => Assert.Equal(expected, WarehousePieces.ParseFaceRanges(text));

    [Theory]
    [InlineData("0")]
    [InlineData("5-2")]
    [InlineData("abc")]
    [InlineData("1-")]
    [InlineData("")]
    public void FaceRangesRejectMalformedTokens(string text)
        => Assert.Throws<FormatException>(() => WarehousePieces.ParseFaceRanges(text));

    [Theory]
    [InlineData("| piece-a | A | G | 1 | wall | extra |")]
    [InlineData("| piece-a | A | G | 1 |")]
    [InlineData("| piece-a |  | G | 1 | wall |")]
    [InlineData("| piece-a | A | G | 1-0 | wall |")]
    public void ParseInventoryRejectsMalformedRows(string row)
        => Assert.Throws<FormatException>(() => WarehousePieces.ParseInventory("header\n" + row + "\n"));

    [Fact]
    public void CoverageAcceptsAnExactPartition()
        => Assert.Empty(WarehousePieces.CoverageErrors(new[] { P(new[] { 1, 2 }), P(new[] { 3 }, id: "piece-y") }, 3));

    [Fact]
    public void CoverageReportsUnassignedDuplicatedAndUnknownFaces()
    {
        var errors = WarehousePieces.CoverageErrors(new[] { P(new[] { 1, 2, 2 }), P(new[] { 2 }, id: "piece-y") }, 3);
        Assert.Contains(errors, e => e.Contains("unassigned face 3"));
        Assert.Contains(errors, e => e.Contains("face 2 assigned more than once"));
        Assert.Contains(WarehousePieces.CoverageErrors(new[] { P(new[] { 1, 2, 3, 4 }) }, 3), e => e.Contains("unknown face 4"));
        Assert.Contains(WarehousePieces.CoverageErrors(new[] { P(new[] { 0, 1, 2, 3 }) }, 3), e => e.Contains("unknown face 0"));
    }

    [Theory]
    [InlineData("main-transition", WarehousePieces.PivotRule.RidingTransition)]
    [InlineData("wall-transition", WarehousePieces.PivotRule.RidingTransition)]
    [InlineData("outer-bank", WarehousePieces.PivotRule.RidingTransition)]
    [InlineData("bank-end", WarehousePieces.PivotRule.RidingTransition)]
    [InlineData("hip", WarehousePieces.PivotRule.RidingTransition)]
    [InlineData("hip-apron", WarehousePieces.PivotRule.RidingTransition)]
    [InlineData("roll-in", WarehousePieces.PivotRule.RidingTransition)]
    [InlineData("kicker", WarehousePieces.PivotRule.RidingTransition)]
    [InlineData("convex-tip", WarehousePieces.PivotRule.RidingTransition)]
    [InlineData("deck", WarehousePieces.PivotRule.SurfaceCentre)]
    [InlineData("flat", WarehousePieces.PivotRule.SurfaceCentre)]
    [InlineData("floor", WarehousePieces.PivotRule.SurfaceCentre)]
    [InlineData("corner", WarehousePieces.PivotRule.CornerLipIntersection)]
    [InlineData("roof", WarehousePieces.PivotRule.LowerFaceCentre)]
    [InlineData("prop", WarehousePieces.PivotRule.BottomCentre)]
    [InlineData("wall", WarehousePieces.PivotRule.BottomCentre)]
    [InlineData("window", WarehousePieces.PivotRule.BottomCentre)]
    [InlineData("sign", WarehousePieces.PivotRule.BottomCentre)]
    [InlineData("support", WarehousePieces.PivotRule.BottomCentre)]
    [InlineData("rail", WarehousePieces.PivotRule.BottomCentre)]
    [InlineData("ledge", WarehousePieces.PivotRule.BottomCentre)]
    [InlineData("end-cap", WarehousePieces.PivotRule.BottomCentre)]
    [InlineData("suppressed-post", WarehousePieces.PivotRule.BottomCentre)]
    public void EveryInventoryModuleMapsToAConvention(string module, WarehousePieces.PivotRule expected)
        => Assert.Equal(expected, WarehousePieces.RuleFor(module));

    [Fact]
    public void UnknownModulesFailTheBuildRatherThanDefault()
        => Assert.Throws<ArgumentException>(() => WarehousePieces.RuleFor("quarter-pipe"));

    [Fact]
    public void RidingTransitionPivotsAtTheToeMidpointFacingLip()
    {
        var south = new[] { V(0, 0, 0), V(10, 0, 0), V(0, 1, -2), V(10, 1, -2), V(0, 2, -4), V(10, 2, -4) };
        var placement = WarehousePieces.ComputePlacement(WarehousePieces.PivotRule.RidingTransition, south);
        Near(new Vector3(5, 0, 0), placement.Pivot, 4);
        Assert.Equal(180f, placement.YawDegrees, 3);
    }

    [Fact]
    public void RidingTransitionYawFollowsTheLipDirection()
    {
        var east = new[] { V(0, 0, 0), V(0, 0, 10), V(0, 2, 0), V(0, 2, 10), V(2, 2, 0), V(2, 2, 10) };
        var placement = WarehousePieces.ComputePlacement(WarehousePieces.PivotRule.RidingTransition, east);
        Near(new Vector3(0, 0, 5), placement.Pivot, 4);
        Assert.Equal(90f, placement.YawDegrees, 3);
    }

    [Fact]
    public void VerticalRidingModuleKeepsZeroYaw()
    {
        var plate = new[] { V(0, 0, 0), V(10, 0, 0), V(0, 5, 0), V(10, 5, 0) };
        var placement = WarehousePieces.ComputePlacement(WarehousePieces.PivotRule.RidingTransition, plate);
        Assert.Equal(0f, placement.YawDegrees, 3);
    }

    [Fact]
    public void SurfaceCentrePivotsAtTheTopCentroid()
    {
        var deck = new[] { V(0, 8, 0), V(6, 8, 0), V(6, 8.3f, 0), V(0, 8.3f, 0), V(0, 8, 3), V(6, 8, 3), V(6, 8.3f, 3), V(0, 8.3f, 3) };
        var placement = WarehousePieces.ComputePlacement(WarehousePieces.PivotRule.SurfaceCentre, deck);
        Near(new Vector3(3, 8.3f, 1.5f), placement.Pivot, 4);
        Assert.Equal(0f, placement.YawDegrees, 3);
    }

    [Fact]
    public void BottomCentrePivotsUnderThePiece()
    {
        var box = new[] { V(0, 0.5f, 0), V(6, 0.5f, 0), V(6, 3, 0), V(0, 3, 0), V(0, 0.5f, 3), V(6, 0.5f, 3), V(6, 3, 3), V(0, 3, 3) };
        var placement = WarehousePieces.ComputePlacement(WarehousePieces.PivotRule.BottomCentre, box);
        Near(new Vector3(3, 0.5f, 1.5f), placement.Pivot, 4);
    }

    [Fact]
    public void LowerFaceCentrePivotsAtThePanelCentre()
    {
        var quad = new[] { V(0, 10, 0), V(2, 10, 0), V(2, 10, 2), V(0, 10, 2) };
        var placement = WarehousePieces.ComputePlacement(WarehousePieces.PivotRule.LowerFaceCentre, quad);
        Near(new Vector3(1, 10, 1), placement.Pivot, 4);
    }

    [Fact]
    public void CornerPivotSitsAtTheExtendedLipLineIntersection()
    {
        var top = new[] { V(0, 8, 0), V(10, 8, 0), V(8, 8, 6), V(0, 8, 10) };
        var placement = WarehousePieces.ComputePlacement(WarehousePieces.PivotRule.CornerLipIntersection, top);
        Near(new Vector3(0, 8, 0), placement.Pivot, 3);
        Assert.Equal(0f, placement.YawDegrees, 3);
    }

    [Fact]
    public void CornerKeepsDeckHeightWithoutIntersectingLipLines()
    {
        var band = new[] { V(0, 8, 0), V(10, 8, 0), V(10, 8, 4), V(0, 8, 4) };
        var placement = WarehousePieces.ComputePlacement(WarehousePieces.PivotRule.CornerLipIntersection, band);
        Assert.Equal(8f, placement.Pivot.Y, 3);
    }

    [Fact]
    public void LocalRoundTripRestoresMeshSpaceVertices()
    {
        var verts = new[] { V(3.25f, 1.5f, -7.75f), V(-2.5f, 0f, 4.125f), V(9.875f, 4.5f, -1.25f), V(0.125f, 2.25f, 6.375f) };
        var placement = new WarehousePieces.Placement(V(1.5f, 0f, -3.5f), 37.5f);
        var local = WarehousePieces.ToLocal(verts, placement);
        var restored = local.Select(v => WarehousePieces.ToMeshSpace(v, placement)).ToArray();
        for (var i = 0; i < verts.Length; i++)
            Near(verts[i], restored[i], 4);
    }

    [Fact]
    public void EmptyVertexSetsFailRatherThanSilentlyDefault()
        => Assert.Throws<ArgumentException>(() => WarehousePieces.ComputePlacement(WarehousePieces.PivotRule.BottomCentre, Array.Empty<Vector3>()));
}
