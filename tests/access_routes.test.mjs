import assert from 'node:assert/strict';
import {test} from 'node:test';
import '../metropogits/viewer_assets/viewer-filters.js';

const routing = {status:'COMPLETE',unresolvedEdgeIds:[],junctions:[], routes:[
  {id:'ab',source:'A',target:'B',kind:'DEPENDENCY_ROAD',networkIds:['n'],edgeIds:['edge-ab'],
    path:[[0,0],[0,7],[7,7],[7,0]],segmentIds:['a','shared','b']},
  {id:'cd',source:'C',target:'D',kind:'DEPENDENCY_ROAD',networkIds:['n'],edgeIds:['edge-cd'],
    path:[[-7,7],[0,7],[7,7],[14,7]],segmentIds:['c','shared','d']}
],segments:[
  {id:'a',routeIds:['ab'],access:true}, {id:'b',routeIds:['ab'],access:true},
  {id:'c',routeIds:['cd'],access:true}, {id:'d',routeIds:['cd'],access:true},
  {id:'shared',routeIds:['ab','cd'],access:false,kind:'DEPENDENCY_ROAD',start:[0,7],end:[7,7]}
]};
const policy=globalThis.METROPOGITS_FILTERS.createAccessPolicy(routing);
const files=new Set(['A','B','C','D']), networks=new Set(['n']);
test('shared geometry never creates an A to D relation or exposes unrelated branches',()=>{
  const frame=policy.frame('detail',files,networks,{kind:'building',id:'A'});
  assert.deepEqual([...frame.routeIds],['ab']);
  assert.deepEqual([...frame.segmentIds].sort(),['a','b','shared']);
  assert.deepEqual(policy.network('shared',frame.routeIds).edgeIds,['edge-ab']);
  assert.equal(frame.segments.every(s=>s.highlighted),true);
  const all=policy.frame('detail',files,networks,{kind:'building',id:'A'},true);
  assert.equal(all.routes.length,2);
  assert.equal(all.segments.find(s=>s.id==='d').highlighted,false);
});
test('filters exclude hidden endpoints even on shared segments',()=>{
  const frame=policy.frame('detail',new Set(['A','B']),networks,null);
  assert.deepEqual([...frame.routeIds],['ab']);
  assert.deepEqual(policy.network('shared',frame.routeIds).edgeIds,['edge-ab']);
});
test('selecting a shared segment exposes only its actual complete routes',()=>{
  const frame=policy.frame('overview',files,networks,{kind:'network',id:'shared'});
  assert.deepEqual([...frame.routeIds],['ab','cd']);
  assert.equal(frame.segmentIds.size,5);
});
test('synthetic follows stored endpoint paths and cannot branch at a junction',()=>{
  const route=routing.routes[0];
  assert.deepEqual(policy.position(route,0).point,[0,0]);
  assert.deepEqual(policy.position(route,1).point,[7,0]);
  for(let i=0;i<=100;i++) {
    const sample=policy.position(route,i/100);
    assert.ok(['a','shared','b'].includes(sample.segmentId));
    assert.ok(sample.point[0]>=0 && sample.point[0]<=7);
  }
});
