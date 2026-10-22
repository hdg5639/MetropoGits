import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import '../metropogits/viewer_assets/viewer-3d.js';

const {vertexFloats,faceCoordinates,polygonCoordinates,polygonNormal,sunMatrix,canopyMesh}=METROPOGITS_RENDER_MATERIALS;
const {transformPoint}=METROPOGITS_WEBGL_MATH;

test('facade coordinates remain local metres under arbitrary building rotation',()=>{
  for(const angle of [0,.37,Math.PI/2,2.7]) {
    const c=Math.cos(angle),s=Math.sin(angle);
    const points=[[0,0,0],[0,9,0],[6,9,0],[6,0,0]]
      .map(([x,y,z])=>[100+c*x-s*z,y+12,-40+s*x+c*z]);
    const before=JSON.stringify(points),coords=faceCoordinates(points);
    assert.ok(Math.abs(coords.extent[0]-6)<1e-12);
    assert.equal(coords.extent[1],9);
    assert.deepEqual(coords.uv[0],[0,0]);
    assert.ok(Math.abs(coords.uv[2][0]-6)<1e-12);
    assert.equal(coords.uv[2][1],9);
    assert.equal(JSON.stringify(points),before);
  }
});

test('sun frustum contains tall and negative-elevation surfaces, independent of camera',()=>{
  const points=[[-300,-12,-80],[220,68,150],[-300,68,150],[220,-12,-80]];
  const values=points.flatMap(p=>[...p,...new Array(vertexFloats-3).fill(0)]);
  const saved=JSON.stringify(values),matrix=sunMatrix(values);
  assert.deepEqual(sunMatrix(values),matrix);
  assert.equal(sunMatrix([]),null);
  for(const point of points) {
    const clip=transformPoint(matrix,point);
    for(const value of clip.slice(0,3))assert.ok(value>-1&&value<1);
  }
  assert.equal(JSON.stringify(values),saved);
  assert.ok(matrix.every(Number.isFinite));
});

test('gable polygons share one upright metric UV frame across every fan triangle',()=>{
  const gable=[[0,0,0],[8,0,0],[8,4,0],[4,6,0],[0,4,0]];
  for(const angle of [0,.67,2.1]) {
    const c=Math.cos(angle),s=Math.sin(angle);
    const points=gable.map(([x,y,z])=>[100+c*x-s*z,y+7,-30+s*x+c*z]);
    const original=JSON.stringify(points),coords=polygonCoordinates(points);
    assert.ok(Math.abs(coords.extent[0]-8)<1e-10);
    assert.ok(Math.abs(coords.extent[1]-6)<1e-10);
    assert.ok(Math.abs(coords.uv[0][1])<1e-10);
    assert.ok(Math.abs(coords.uv[1][1])<1e-10);
    assert.ok(Math.abs(coords.uv[2][1]-4)<1e-10);
    assert.ok(Math.abs(coords.uv[4][1]-4)<1e-10);
    for(let i=1;i<points.length-1;i++)for(const index of [0,i,i+1])
      assert.equal(coords.uv[index][1],points[index][1]-7);
    assert.equal(JSON.stringify(points),original);
  }
  for(const normal of [[0,1,0],[0,-1,0]]) {
    const frame=polygonCoordinates([[0,0,0],[0,0,2],[3,0,2],[3,0,0]],normal);
    assert.ok(frame.extent.every(v=>v>0&&Number.isFinite(v)));
  }
});

test('clipped water polygons recover a finite winding-preserving normal after collinear points',()=>{
  const river=[[0,.09,0],[0,.09,1],[0,.09,2],[1,.09,2],[1,.09,0]];
  assert.deepEqual(polygonNormal(river),[0,1,0]);
  assert.deepEqual(polygonNormal([...river].reverse()),[0,-1,0]);
  assert.deepEqual(polygonNormal([[0,0,0],[0,0,0],[0,0,0]]),[0,1,0]);
});

test('rounded foliage stays inside the old decorative reserve and faces outward',()=>{
  const tree={id:'fixed-seed-tree',center:[4,-5],radius:2,height:6,
    faces:[{points:[[4,11,-5],[4,17,-5]]}]};
  const original=JSON.stringify(tree),mesh=canopyMesh(tree);
  assert.deepEqual(canopyMesh(tree),mesh);
  assert.equal(mesh.faces.length,32);
  for(const face of mesh.faces)for(const [i,p]of face.points.entries()) {
    assert.ok(Math.hypot(p[0]-4,p[2]+5)<2*.8661);
    assert.ok(p[1]>=11&&p[1]<=17);
    const n=face.normals[i];
    assert.ok(Math.abs(Math.hypot(...n)-1)<1e-12);
    assert.ok((p[0]-4)*n[0]+(p[1]-(11+6*.64))*n[1]+(p[2]+5)*n[2]>0);
  }
  assert.equal(JSON.stringify(tree),original);
});

test('material/shadow controls preserve source inspection, batching and optional fallbacks',async()=>{
  const source=await readFile(new URL('../metropogits/viewer_assets/viewer-3d.js',import.meta.url),'utf8');
  assert.match(source,/OES_standard_derivatives/);
  assert.match(source,/if\(!fragmentHighp\)return null/);
  assert.match(source,/FRAMEBUFFER_COMPLETE/);
  assert.match(source,/sunShadow\.values===values/);
  assert.match(source,/sunShadow\?\.texture \|\| whiteTexture/);
  assert.match(source,/gl\.disable\(gl\.DITHER\)/);
  assert.match(source,/data\.landscape\.trees\.length<=4096/);
  assert.match(source,/materialButton\.setAttribute\('aria-pressed',String\(detailedMaterials\)\)/);
  assert.match(source,/gl\.uniform1f\(detailedLocation,0\)/);
  assert.match(source,/showRoleColors \|\| activeFilterCount\(\)>0 \|\| isSelected/);
  assert.match(source,/seed=floor\(v_surface\.w\+\.5\)/);
  assert.equal(vertexFloats,15);
});
