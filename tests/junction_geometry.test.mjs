import assert from 'node:assert/strict';
import {test} from 'node:test';
import '../metropogits/viewer_assets/viewer-filters.js';

const {accessJunctionGeometry:geometry,accessMarkingSegment:marking,accessRoadStyle:style} = globalThis.METROPOGITS_FILTERS;
function frame(ends, widths=[]) {
  const segments=ends.map((end,i)=>({id:`s${i}`,start:[10,20],end:[10+end[0],20+end[1]],
    width:widths[i] || 2,kind:'DEPENDENCY_ROAD',access:false,routeIds:['a','b','c','d']}));
  return {segments,junctions:[{id:'j',point:[10,20],segmentIds:segments.map(s=>s.id)}]};
}
function covered(x,z,segments) {
  return segments.some(s=>{
    const half=style(s).width/2;
    return s.start[1]===s.end[1] ? x>=Math.min(s.start[0],s.end[0])-1e-8 && x<=Math.max(s.start[0],s.end[0])+1e-8 && Math.abs(z-s.start[1])<=half+1e-8 :
      z>=Math.min(s.start[1],s.end[1])-1e-8 && z<=Math.max(s.start[1],s.end[1])+1e-8 && Math.abs(x-s.start[0])<=half+1e-8;
  });
}
function verifySurface(input,result) {
  for(const surface of result.surfaces) for(const [a,b,c,d] of surface.rectangles) {
    assert.ok(c>a && d>b);
    // Partition at every original road boundary, checking each subrectangle
    // independently of the production union/inset algorithm (not just vertices).
    const xs=[a,c],zs=[b,d];
    for(const s of input.segments) {
      const h=style(s).width/2;
      xs.push(s.start[0]-h,s.start[0],s.start[0]+h,s.end[0]);
      zs.push(s.start[1]-h,s.start[1],s.start[1]+h,s.end[1]);
    }
    const xx=[...new Set(xs.filter(x=>x>=a&&x<=c))].sort((x,y)=>x-y);
    const zz=[...new Set(zs.filter(z=>z>=b&&z<=d))].sort((x,y)=>x-y);
    for(let i=1;i<xx.length;i++) for(let j=1;j<zz.length;j++)
      assert.ok(covered((xx[i-1]+xx[i])/2,(zz[j-1]+zz[j])/2,input.segments), 'patch escaped certified pavement');
  }
}
test('T and X junctions connect asphalt without paving missing corners or changing routes',()=>{
  for(const ends of [[[7,0],[-7,0],[0,7]],[[7,0],[-7,0],[0,7],[0,-7]]]) {
    const input=frame(ends),original=structuredClone(input),result=geometry(input);
    assert.equal(result.surfaces.length,1);
    assert.ok(result.surfaces[0].rectangles.length>0);
    assert.ok(result.surfaces[0].rectangles.length<=12,'merged tiles stay bounded');
    verifySurface(input,result);
    // The joint center is asphalt, not the old overpainted shoulder cross.
    assert.ok(result.surfaces[0].rectangles.some(r=>r[0]<=10&&r[2]>=10&&r[1]<=20&&r[3]>=20));
    assert.deepEqual(input,original);
    for(const s of input.segments) {
      const paint=marking(s,result.trims);
      assert.ok(Math.hypot(paint.start[0]-10,paint.start[1]-20)>style(s).width/2);
      assert.deepEqual(paint.end,s.end);
    }
  }
});
test('unequal widths and short approaches remain within existing pavement',()=>{
  for(const widths of [[.45,2,1],[2,.45,.45],[1,1,1]]) {
    const input=frame([[.2,0],[-7,0],[0,7]],widths),result=geometry(input);
    verifySurface(input,result);
    assert.equal(marking(input.segments[0],result.trims),null);
  }
});
test('hidden approaches and different network kinds never create a junction',()=>{
  const input=frame([[7,0],[-7,0],[0,7]]);
  assert.equal(geometry({...input,segments:input.segments.slice(0,2)}).surfaces.length,0);
  input.segments[2].kind='HTTP_HIGHWAY';
  assert.equal(geometry(input).surfaces.length,0);
  assert.equal(geometry(null).surfaces.length,0);
});
test('geometry is deterministic under incident order and endpoint reversal',()=>{
  const input=frame([[7,0],[-7,0],[0,7]], [.45,2,1]);
  const expected=geometry(input);
  const reversed=structuredClone(input);
  reversed.junctions[0].segmentIds.reverse();reversed.segments.reverse();
  assert.deepEqual(geometry(reversed),expected);
  for(const s of reversed.segments) [s.start,s.end]=[s.end,s.start];
  const actual=geometry(reversed);
  assert.deepEqual(actual.surfaces,expected.surfaces);
  for(const [id,trim] of actual.trims) assert.deepEqual(trim,[...expected.trims.get(id)].reverse());
});
test('two close junctions omit exhausted paint without reversing or changing road endpoints',()=>{
  const s={id:'short',start:[0,0],end:[1,0]};
  assert.equal(marking(s,new Map([['short',[.6,.6]]])),null);
  assert.deepEqual(marking(s,new Map()),{start:s.start,end:s.end});
});
