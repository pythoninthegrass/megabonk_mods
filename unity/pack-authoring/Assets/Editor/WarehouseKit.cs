using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Numerics;

public static class WarehouseKit
{
    const float Epsilon = 0.00001f;

    public sealed class Normalized
    {
        public Vector3[] Vertices;
        public Vector3 Origin, X, Y, Z, Scale;
        public string Key;
        public string FrameKey;
        public Vector3 ToWorld(Vector3 p) => Origin + X * p.X * Scale.X + Y * p.Y * Scale.Y + Z * p.Z * Scale.Z;
    }

    public static Normalized Normalize(Vector3[] vertices, Vector2[] uvs, int[] triangles, string[] materials, bool collider, bool upright, bool resize = true, bool fixedAxes = false, bool looseBoard = false)
    {
        if (vertices.Length == 0 || vertices.Length != uvs.Length || triangles.Length % 3 != 0 || materials.Length != triangles.Length / 3)
            throw new ArgumentException("Invalid kit geometry.");
        Normalized best = null;
        var normals = Enumerable.Range(0, materials.Length).Select(i => Vector3.Cross(vertices[triangles[i*3+1]]-vertices[triangles[i*3]], vertices[triangles[i*3+2]]-vertices[triangles[i*3]])).ToArray();
        var up = normals.Where(n => n.LengthSquared()>1e-20f).Select(n => Vector3.Normalize(n).Y).DefaultIfEmpty(0).Max();
        for (var t = 0; t < materials.Length; t++)
        {
            if (normals[t].LengthSquared() < 1e-20f) continue;
            var normal = Vector3.Normalize(normals[t]);
            if (!fixedAxes && !upright && normal.Y < up - Epsilon) continue;
            for (var edge = 0; edge < 3; edge++)
            {
                var a = vertices[triangles[t*3+edge]];
                var b = vertices[triangles[t*3+(edge+1)%3]];
                if (Vector3.DistanceSquared(a,b)<Epsilon*Epsilon) continue;
                var uses = 0;
                for (var n = 0; n < materials.Length; n++)
                    if (normals[n].LengthSquared()>1e-20f && Vector3.Dot(Vector3.Normalize(normals[n]),normal)>0.999f)
                        for (var k = 0; k < 3; k++)
                            if (triangles[n*3+k]==triangles[t*3+edge] && triangles[n*3+(k+1)%3]==triangles[t*3+(edge+1)%3]
                                || triangles[n*3+k]==triangles[t*3+(edge+1)%3] && triangles[n*3+(k+1)%3]==triangles[t*3+edge]) uses++;
                if (!fixedAxes && uses>1) continue;
                var along = Vector3.Normalize(b-a);
                var x = upright ? Vector3.Normalize(Vector3.Cross(along,normal)) : along;
                var y = upright ? along : normal;
                var z = upright ? normal : Vector3.Normalize(Vector3.Cross(x,y));
                if (fixedAxes) { x=Vector3.UnitX; y=Vector3.UnitY; z=Vector3.UnitZ; }
                if (upright && y.Y < 0.5f) continue;
                var local = vertices.Select(p => new Vector3(Vector3.Dot(p-a,x),Vector3.Dot(p-a,y),Vector3.Dot(p-a,z))).ToArray();
                var min = local.Aggregate(Vector3.Min);
                var max = local.Aggregate(Vector3.Max);
                var centre = (min+max)/2;
                if (upright) centre.Y = min.Y;
                var size = resize ? max-min : Vector3.One;
                if (size.X < Epsilon) size.X = 1;
                if (size.Y < Epsilon) size.Y = 1;
                if (size.Z < Epsilon) size.Z = 1;
                var normalized = local.Select(p => (p-centre)/size).ToArray();
                var keys = new List<string>();
                for (var i = 0; i < materials.Length; i++)
                {
                    var corners = Enumerable.Range(0,3).Select(k => {
                        var index=triangles[i*3+k];
                        var p=normalized[index]; var uv=uvs[index];
                        return Q(p.X)+","+Q(p.Y)+","+Q(p.Z)+","+Q(uv.X)+","+Q(uv.Y);
                    }).ToArray();
                    var rotated=Enumerable.Range(0,3).Select(k=>string.Join(";",Enumerable.Range(0,3).Select(n=>corners[(k+n)%3]))).OrderBy(s=>s,StringComparer.Ordinal).First();
                    keys.Add(materials[i]+":"+rotated);
                }
                var key=(collider ? "solid:" : "open:")+string.Join("|",keys.OrderBy(s=>s,StringComparer.Ordinal));
                var frameKey=key;
                if (looseBoard)
                {
                    var artwork=new SortedSet<string>(StringComparer.Ordinal);
                    var orientation=new SortedSet<string>(StringComparer.Ordinal);
                    foreach (var material in materials.Distinct().OrderBy(m=>m,StringComparer.Ordinal))
                    {
                        var top=Enumerable.Range(0,materials.Length).Where(i=>materials[i]==material && normals[i].LengthSquared()>1e-20f && Vector3.Dot(Vector3.Normalize(normals[i]),y)>.99f)
                            .SelectMany(i=>Enumerable.Range(0,3).Select(k=>uvs[triangles[i*3+k]])).ToArray();
                        artwork.Add(material+(top.Length==0 ? "" : ":"+Q(top.Min(uv=>uv.X))+","+Q(top.Min(uv=>uv.Y))+","+Q(top.Max(uv=>uv.X))+","+Q(top.Max(uv=>uv.Y))));
                        foreach (var i in Enumerable.Range(0,materials.Length).Where(i=>materials[i]==material && normals[i].LengthSquared()>1e-20f && Vector3.Dot(Vector3.Normalize(normals[i]),y)>.99f))
                            for (var k=0;k<3;k++)
                            {
                                var index=triangles[i*3+k]; var p=normalized[index]; var uv=uvs[index];
                                orientation.Add(material+":"+Q(uv.X)+","+Q(uv.Y)+":"+Q(p.X)+","+Q(p.Y)+","+Q(p.Z));
                            }
                    }
                    key=(collider ? "solid:plank:" : "open:plank:")+string.Join("|",artwork);
                    frameKey=string.Join("|",orientation);
                }
                if (best == null || string.CompareOrdinal(key,best.Key)<0 || key==best.Key && string.CompareOrdinal(frameKey,best.FrameKey)<0)
                    best=new Normalized { Vertices=normalized,Origin=a+x*centre.X+y*centre.Y+z*centre.Z,X=x,Y=y,Z=z,Scale=size,Key=key,FrameKey=frameKey };
                if (fixedAxes) return best;
            }
        }
        return best ?? throw new ArgumentException("Kit geometry has no usable frame.");
    }

    static string Q(float value) => ((long)Math.Round(value/Epsilon)).ToString(CultureInfo.InvariantCulture);
    static string Point(Vector3 p) => Q(p.X)+","+Q(p.Y)+","+Q(p.Z);
    static string Edge(Vector3 a, Vector3 b) => string.CompareOrdinal(Point(a),Point(b))<0 ? Point(a)+":"+Point(b) : Point(b)+":"+Point(a);

    public static List<int[]> ConnectedFaces(Vector3[][] faces)
    {
        var groups=new List<List<int>>();
        for (var i=0;i<faces.Length;i++)
        {
            var touching=groups.Where(group=>group.Any(n=>faces[n].Any(a=>faces[i].Any(b=>Vector3.Distance(a,b)<Epsilon)))).ToList();
            var combined=new List<int> { i };
            foreach (var group in touching) { combined.AddRange(group); groups.Remove(group); }
            combined.Sort(); groups.Add(combined);
        }
        return groups.OrderBy(group=>group[0]).Select(group=>group.ToArray()).ToList();
    }

    public static float Area(Vector3[] polygon) => Enumerable.Range(1,polygon.Length-2).Sum(i=>Vector3.Cross(polygon[i]-polygon[0],polygon[i+1]-polygon[0]).Length()/2);

    public static List<List<Vector3[]>> RoofSections(IEnumerable<Vector3[]> quads, float cell)
    {
        if (cell<=0) throw new ArgumentException("Section size must be positive.");
        var sections=new SortedDictionary<(int X,int Z),List<Vector3[]>>();
        foreach (var quad in quads)
        {
            var min=quad.Aggregate(Vector3.Min); var max=quad.Aggregate(Vector3.Max);
            var x0=(int)MathF.Floor(min.X/cell); var z0=(int)MathF.Floor(min.Z/cell);
            var x1=Math.Max(x0,(int)MathF.Floor((max.X-1e-7f)/cell));
            var z1=Math.Max(z0,(int)MathF.Floor((max.Z-1e-7f)/cell));
            for (var x=x0;x<=x1;x++)
                for (var z=z0;z<=z1;z++)
                {
                    var polygon=Clip(Clip(Clip(Clip(quad,0,x*cell,true),0,(x+1)*cell,false),2,z*cell,true),2,(z+1)*cell,false);
                    if (polygon.Length<3 || Area(polygon)<1e-12f) continue;
                    if (!sections.TryGetValue((x,z),out var list)) sections[(x,z)]=list=new List<Vector3[]>();
                    list.Add(polygon);
                }
        }
        return sections.Values.Select(section=>
        {
            var points=section.SelectMany(p=>p).ToArray();
            var min=points.Aggregate(Vector3.Min); var max=points.Aggregate(Vector3.Max);
            var area=(max.X-min.X)*(max.Z-min.Z);
            if (max.Y-min.Y<1e-7f && area>0 && Math.Abs(section.Sum(Area)-area)<area*1e-5f
                && section.All(p=>Vector3.Cross(p[1]-p[0],p[2]-p[0]).Y<0))
                return new List<Vector3[]> { new[] { new Vector3(min.X,min.Y,min.Z),new Vector3(max.X,min.Y,min.Z),new Vector3(max.X,min.Y,max.Z),new Vector3(min.X,min.Y,max.Z) } };
            return section;
        }).ToList();
    }

    static Vector3[] Clip(Vector3[] polygon, int axis, float boundary, bool above)
    {
        float Coord(Vector3 p) => axis==0 ? p.X : p.Z;
        bool Inside(Vector3 p) => above ? Coord(p)>=boundary : Coord(p)<=boundary;
        var result=new List<Vector3>();
        for (var i=0;i<polygon.Length;i++)
        {
            var a=polygon[i]; var b=polygon[(i+1)%polygon.Length];
            if (Inside(a)) result.Add(a);
            if (Inside(a)!=Inside(b)) result.Add(Vector3.Lerp(a,b,(boundary-Coord(a))/(Coord(b)-Coord(a))));
        }
        for (var i=result.Count-1;i>=0;i--)
            if (result.Count>1 && Vector3.DistanceSquared(result[i],result[(i+1)%result.Count])<1e-16f) result.RemoveAt(i);
        return result.ToArray();
    }

    public static List<Vector3[]> MergeRoof(IEnumerable<Vector3[]> source, float maximumArea)
    {
        var quads=source.Select(q=>q.ToArray()).ToList();
        bool changed;
        do
        {
            changed=false;
            var edges=new Dictionary<string,List<int>>(StringComparer.Ordinal);
            for (var i=0;i<quads.Count && !changed;i++)
                for (var e=0;e<4 && !changed;e++)
                {
                    var key=Edge(quads[i][e],quads[i][(e+1)%4]);
                    if (!edges.TryGetValue(key,out var neighbours)) edges[key]=neighbours=new List<int>();
                    foreach (var j in neighbours)
                    {
                        var merged=Union(quads[j],quads[i]);
                        if (merged == null || Area(merged)>maximumArea+Epsilon) continue;
                        quads[j]=merged;
                        quads.RemoveAt(i);
                        changed=true;
                        break;
                    }
                    if (!changed) neighbours.Add(i);
                }
        } while (changed);
        return quads;
    }

    static Vector3[] Union(Vector3[] a, Vector3[] b)
    {
        var na=Vector3.Cross(a[1]-a[0],a[2]-a[0]);
        var nb=Vector3.Cross(b[1]-b[0],b[2]-b[0]);
        if (na.LengthSquared()<Epsilon*Epsilon || nb.LengthSquared()<Epsilon*Epsilon) return null;
        na=Vector3.Normalize(na); nb=Vector3.Normalize(nb);
        if (Vector3.Dot(na,nb)<0.99999f || b.Any(p=>Math.Abs(Vector3.Dot(p-a[0],na))>Epsilon)) return null;
        var edges=new List<(Vector3 A,Vector3 B)>();
        foreach (var q in new[] { a,b })
            for (var i=0;i<4;i++)
            {
                var p=q[i]; var r=q[(i+1)%4];
                var reverse=edges.FindIndex(edge=>Vector3.Distance(edge.A,r)<Epsilon && Vector3.Distance(edge.B,p)<Epsilon);
                if (reverse>=0) edges.RemoveAt(reverse); else edges.Add((p,r));
            }
        if (edges.Count!=6) return null;
        var polygon=new List<Vector3> { edges[0].A };
        var end=edges[0].B; edges.RemoveAt(0);
        while (edges.Count>0)
        {
            polygon.Add(end);
            var next=edges.FindIndex(edge=>Vector3.Distance(edge.A,end)<Epsilon);
            if (next<0) return null;
            end=edges[next].B; edges.RemoveAt(next);
        }
        if (Vector3.Distance(end,polygon[0])>Epsilon) return null;
        for (var i=polygon.Count-1;i>=0;i--)
        {
            var before=polygon[(i+polygon.Count-1)%polygon.Count];
            var after=polygon[(i+1)%polygon.Count];
            if (Vector3.Cross(polygon[i]-before,after-polygon[i]).Length()<=Epsilon*(Vector3.Distance(before,polygon[i])+Vector3.Distance(after,polygon[i]))) polygon.RemoveAt(i);
        }
        if (polygon.Count!=4) return null;
        for (var i=0;i<4;i++)
            if (Vector3.Dot(Vector3.Cross(polygon[(i+1)%4]-polygon[i],polygon[(i+2)%4]-polygon[(i+1)%4]),na)<-Epsilon) return null;
        return polygon.ToArray();
    }
}
