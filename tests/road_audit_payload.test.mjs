import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {Script} from 'node:vm';
import {instrument} from '../scripts/viewer_audit.mjs';

test('shared-road audit returns one complete target without duplicating every physical path',async()=>{
  const code=instrument(await readFile(new URL('../metropogits/viewer_assets/viewer-3d.js',import.meta.url),'utf8'));
  const start=code.indexOf('roadTargets(identity = null)');
  const method=code.slice(start,code.indexOf('    accessTargets()',start)).trim().replace(/,$/,'');
  const regions=['a','b','c'].map((id,i)=>({id,kind:'network',minX:20+i*30,maxX:30+i*30,minY:20,maxY:30,
    points:[{x:20+i*30,y:20},{x:30+i*30,y:30}]}));
  const choices=Object.fromEntries(regions.map((r,i)=>[r.id,Array.from({length:i+2},(_,j)=>({id:`${r.id}-${j}`,
    source:'source',edgeIds:['edge'],segmentIds:['segment'],path:Array(10000).fill([1,2])}))]));
  const api=new Script(`({${method}})`).runInNewContext({hitRegions:regions,viewportWidth:1000,viewportHeight:1000,
    visibleBuildingIds:new Set(),visibleNetworkIds:new Set(),hitTest:x=>regions.find(r=>x>=r.minX&&x<=r.maxX),
    accessPolicy:{choices:id=>choices[id]}});
  const first=api.roadTargets();
  assert.equal(first.length,1);assert.equal(first[0].id,'a');assert.equal(first[0].choices.length,2);
  assert.ok(!('path' in first[0].choices[0]));assert.ok(JSON.stringify(first).length<1000);
  const requested=api.roadTargets('c');
  assert.equal(requested[0].id,'c');assert.equal(requested[0].choices.length,4);
  assert.equal(api.roadTargets('missing').length,0);
});
