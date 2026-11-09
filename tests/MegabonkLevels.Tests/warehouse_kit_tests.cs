using System.Numerics;

namespace MegabonkLevels.Tests;

public class WarehouseKitTests
{
    private static Vector3[] Quad(float x, float y = 0) => new[] { new Vector3(x,y,0), new Vector3(x+1,y,0), new Vector3(x+1,y,1), new Vector3(x,y,1) };
    private static readonly int[] Tris = { 0, 1, 2, 0, 2, 3 };
    private static readonly Vector2[] Uvs = { new(0,0), new(1,0), new(1,1), new(0,1) };

    [Fact]
    public void NormalizationReusesTranslatedRotatedAndResizedGeometry()
    {
        var original = Quad(0);
        var rotation = Quaternion.CreateFromYawPitchRoll(1.1f,0,0);
        var placed = original.Select(p => Vector3.Transform(p * new Vector3(3,1,2), rotation) + new Vector3(4,8,12)).ToArray();
        var a = WarehouseKit.Normalize(original,Uvs,Tris,new[] { "wood", "wood" },true,false);
        var b = WarehouseKit.Normalize(placed,Uvs,Tris,new[] { "wood", "wood" },true,false);
        Assert.Equal(a.Key,b.Key);
        for (var i=0;i<placed.Length;i++) Assert.True(Vector3.Distance(placed[i],b.ToWorld(b.Vertices[i])) < 1e-4f);
    }

    [Fact]
    public void ArtworkUvAndWindingParticipateInIdentity()
    {
        var a = WarehouseKit.Normalize(Quad(0),Uvs,Tris,new[] { "wood", "wood" },true,false);
        Assert.NotEqual(a.Key,WarehouseKit.Normalize(Quad(0),Uvs,Tris,new[] { "metal", "metal" },true,false).Key);
        Assert.NotEqual(a.Key,WarehouseKit.Normalize(Quad(0),Uvs.Select(uv => uv*.5f).ToArray(),Tris,new[] { "wood", "wood" },true,false).Key);
        Assert.NotEqual(a.Key,WarehouseKit.Normalize(Quad(0),Uvs,Tris,new[] { "wood", "wood" },false,false).Key);
    }

    [Fact]
    public void RigidModulesDoNotLoseTheirDimensions()
    {
        var a=WarehouseKit.Normalize(Quad(0),Uvs,Tris,new[] { "wood", "wood" },true,false,false);
        var b=WarehouseKit.Normalize(Quad(0).Select(p=>p*2).ToArray(),Uvs,Tris,new[] { "wood", "wood" },true,false,false);
        Assert.NotEqual(a.Key,b.Key);
        Assert.Equal(Vector3.One,a.Scale);
    }

    [Fact]
    public void AdjacentRoofQuadsMergeWithoutChangingAreaOrFacing()
    {
        var quads=Enumerable.Range(0,20).Select(i=>Quad(i)).ToArray();
        var merged=WarehouseKit.MergeRoof(quads,5);
        Assert.Equal(4,merged.Count);
        Assert.Equal(20,merged.Sum(WarehouseKit.Area),4);
        Assert.All(merged,q=>Assert.True(Vector3.Cross(q[1]-q[0],q[2]-q[0]).Y<0));
    }

    [Fact]
    public void RoofStepsHolesAndOppositeSidesAreNotFilled()
    {
        var quads=new[] { Quad(0),Quad(1,1),Quad(3),Quad(0).Reverse().ToArray() };
        Assert.Equal(4,WarehouseKit.MergeRoof(quads,100).Count);
    }

    [Fact]
    public void ThinRoofSkirtsRetainAUsableFrame()
    {
        var points=new[] { new Vector3(0,0,0),new Vector3(1,0,0),new Vector3(1,0.000001f,0),new Vector3(0,0.000001f,0) };
        var normalized=WarehouseKit.Normalize(points,Uvs,Tris,new[] { "roof","roof" },true,false);
        for (var i=0;i<points.Length;i++) Assert.True(Vector3.Distance(points[i],normalized.ToWorld(normalized.Vertices[i]))<1e-8f);
    }

    [Fact]
    public void RoofSectionsClipLongFacesAndKeepSteppedGeometry()
    {
        var input=new[] { new[] { new Vector3(0,0,0),new Vector3(20,0,0),new Vector3(20,0,1),new Vector3(0,0,1) },Quad(0,2) };
        var sections=WarehouseKit.RoofSections(input,5);
        Assert.Equal(4,sections.Count);
        Assert.Equal(21,sections.Sum(section=>section.Sum(WarehouseKit.Area)),4);
        Assert.Contains(sections[0],polygon=>polygon.Any(p=>p.Y==2));
        Assert.All(sections,section=>Assert.True(section.SelectMany(p=>p).Max(p=>p.X)-section.SelectMany(p=>p).Min(p=>p.X)<=5.0001f));
    }

    [Fact]
    public void DisconnectedSignCopiesSplitButBackFacesStayTogether()
    {
        var groups=WarehouseKit.ConnectedFaces(new[] { Quad(0),Quad(0).Reverse().ToArray(),Quad(10) });
        Assert.Equal(2,groups.Count);
        Assert.Equal(new[] { 0,1 },groups[0]);
        Assert.Equal(new[] { 2 },groups[1]);
    }

    [Fact]
    public void LooseBoardIdentityIgnoresSubpixelJitterAndTheQuadDiagonal()
    {
        var jittered=Quad(0); jittered[2].X+=0.0001f;
        var a=WarehouseKit.Normalize(Quad(0),Uvs,Tris,new[] { "wood","wood" },true,false,looseBoard:true);
        var b=WarehouseKit.Normalize(jittered,Uvs,new[] { 0,1,3,1,2,3 },new[] { "wood","wood" },true,false,looseBoard:true);
        Assert.Equal(a.Key,b.Key);
        Assert.NotEqual(a.Key,WarehouseKit.Normalize(jittered,Uvs,new[] { 0,1,3,1,2,3 },new[] { "metal","metal" },true,false,looseBoard:true).Key);
    }

    [Fact]
    public void SharedVertexBoxesRetainPhysicalEdgesAsFrameCandidates()
    {
        var points=new[] { new Vector3(0,0,0),new Vector3(1,0,0),new Vector3(1,1,0),new Vector3(0,1,0),new Vector3(0,0,1),new Vector3(1,0,1),new Vector3(1,1,1),new Vector3(0,1,1) };
        var triangles=new[] { 0,2,1,0,3,2,4,5,6,4,6,7,0,4,7,0,7,3,1,2,6,1,6,5,0,1,5,0,5,4,3,7,6,3,6,2 };
        var normalized=WarehouseKit.Normalize(points,new Vector2[8],triangles,Enumerable.Repeat("post",12).ToArray(),true,false);
        for (var i=0;i<points.Length;i++) Assert.True(Vector3.Distance(points[i],normalized.ToWorld(normalized.Vertices[i]))<1e-5f);
    }

    [Fact]
    public void LoosePlanksUseArtworkVariantsRatherThanExtractionShapeJitter()
    {
        var skewed=Quad(0); skewed[2].X+=0.003f;
        var a=WarehouseKit.Normalize(Quad(0),Uvs,Tris,new[] { "wood","wood" },true,false,looseBoard:true);
        var b=WarehouseKit.Normalize(skewed,Uvs,Tris,new[] { "wood","wood" },true,false,looseBoard:true);
        Assert.Equal(a.Key,b.Key);
        Assert.NotEqual(a.Key,WarehouseKit.Normalize(skewed,Uvs.Select(uv=>uv*.5f).ToArray(),Tris,new[] { "wood","wood" },true,false,looseBoard:true).Key);
    }

    [Fact]
    public void FlatRoofSectionsBecomeOneReusableQuadWithoutFillingHoles()
    {
        var flat=WarehouseKit.RoofSections(Enumerable.Range(0,5).Select(i=>Quad(i)),5);
        Assert.Single(flat);
        Assert.Single(flat[0]);
        var hole=WarehouseKit.RoofSections(new[] { Quad(0),Quad(3) },5);
        Assert.Equal(2,hole[0].Count);
    }
}
