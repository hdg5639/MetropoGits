import assert from 'node:assert/strict';
import test from 'node:test';
import '../metropogits/viewer_assets/viewer-filters.js';
const engine=globalThis.METROPOGITS_FILTERS;
test('compact aggregate ground follows masses without changing membership or allocated plots',()=>{
  const f={id:'a',x:0,z:0,width:100,depth:100,height:15,
    plots:[{x:0,z:0,width:100,depth:100}],memberEntityIds:['1','2','3','4'],
    archetypeCounts:[{archetype:'GENERIC_BUILDING',count:4}]};
  const frozen=JSON.stringify(f), parts=engine.aggregateParts(f), pads=engine.aggregateGroundPlots(f,true);
  assert.deepEqual(engine.aggregateGroundPlots(f,false),f.plots);
  assert.deepEqual(pads,parts.map(({x,z,width,depth})=>({x,z,width,depth})));
  assert.ok(pads.reduce((s,p)=>s+p.width*p.depth,0)<10000);
  for(const p of pads)assert.ok(p.x>=0&&p.z>=0&&p.x+p.width<=100&&p.z+p.depth<=100);
  assert.equal(JSON.stringify(f),frozen);
  assert.deepEqual(pads,engine.aggregateGroundPlots(f,true));
});
