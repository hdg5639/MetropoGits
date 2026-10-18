import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
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
test('road hierarchy uses actual path count without enlarging safe pavement',()=>{
  for (const count of [1,3,4,100]) for (const access of [false,true]) {
    const segment={width:.45,access,routeIds:Array.from({length:count},(_,i)=>String(i))};
    const before=structuredClone(segment);
    const style=globalThis.METROPOGITS_FILTERS.accessRoadStyle(segment);
    assert.equal(style.shared,!access && count>=4);
    assert.equal(style.surface,style.shared?'#52677b':'#33465a');
    assert.ok(style.width<=segment.width);
    assert.deepEqual(segment,before);
  }
});
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
test('drill-down isolates one complete path and keeps context optional',()=>{
  const selected={kind:'network',id:'shared',routeId:'ab'};
  const frame=policy.frame('overview',files,networks,selected);
  assert.deepEqual([...frame.routeIds],['ab']);
  assert.deepEqual([...frame.segmentIds].sort(),['a','b','shared']);
  assert.ok(frame.segments.every(s=>s.highlighted));
  const context=policy.frame('detail',files,networks,selected,true);
  assert.deepEqual([...context.routeIds],['ab','cd']);
  assert.deepEqual(context.segments.filter(s=>s.highlighted).map(s=>s.id).sort(),['a','b','shared']);
  assert.deepEqual(policy.choices('shared',files,networks).map(r=>r.id),['ab','cd']);
  assert.deepEqual(policy.choices('n',files,networks).map(r=>r.id),['ab','cd']);
});
test('drill-down cannot escape its road or bypass endpoint and network filters',()=>{
  for(const selected of [{kind:'network',id:'a',routeId:'cd'}, {kind:'network',id:'shared',routeId:'missing'}]) {
    assert.equal(policy.frame('detail',files,networks,selected).routes.length,0);
  }
  const selected={kind:'network',id:'shared',routeId:'ab'};
  assert.equal(policy.frame('detail',new Set(['A','C','D']),networks,selected).routes.length,0);
  assert.deepEqual(policy.choices('shared',new Set(['C','D']),networks).map(r=>r.id),['cd']);
  assert.deepEqual(policy.choices('shared',files,new Set()),[]);
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

test('full-road demand and safe width survive filtering and single-path selection',()=>{
  const input=structuredClone(routing);
  input.segments.find(s=>s.id==='shared').width=1.2;
  const profile={grade:'TRUNK',label:'Interdistrict trunk demand',edgeCount:64,
    buildingCount:16,crossDistrictEdgeCount:16,width:1.2,targetWidth:3.5,surface:'#7897ac'};
  const graded=globalThis.METROPOGITS_FILTERS.createAccessPolicy(input,{segments:{shared:profile}});
  for(const selected of [null,{kind:'building',id:'A'},{kind:'network',id:'shared',routeId:'ab'}]) {
    const frame=graded.frame('detail',files,networks,selected);
    const segment=frame.segments.find(s=>s.id==='shared');
    const style=globalThis.METROPOGITS_FILTERS.accessRoadStyle(segment);
    assert.deepEqual(segment.demand,profile);
    assert.equal(style.width,1.2);
    assert.equal(style.surface,'#7897ac');
    assert.deepEqual(graded.network('shared',frame.routeIds).demand,profile);
    if(selected)assert.deepEqual(graded.network('shared',frame.routeIds).edgeIds,['edge-ab']);
  }
  const filtered=graded.frame('detail',new Set(['A','B']),networks,null);
  assert.deepEqual(filtered.segments.find(s=>s.id==='shared').demand,profile);
  assert.deepEqual(graded.position(input.routes[0],.5),policy.position(routing.routes[0],.5));
  assert.equal(input.segments[4].demand,undefined);
});

test('quantitative grade never changes semantic network colors or clearance',()=>{
  const engine=globalThis.METROPOGITS_FILTERS;
  for(const [kind,color] of [['HTTP_HIGHWAY','#f97316'],['MESSAGING_PATH','#a855f7']]) {
    const style=engine.accessRoadStyle({kind,width:.4,demand:{grade:'TRUNK',width:3.5,surface:'#7897ac'}});
    assert.equal(style.width,.4);assert.equal(style.surface,color);
  }
});

test('history handoff retains the selected frame routing and demand profiles',()=>{
  const frames=[{revision:'a',scene:{},ucg:{},routing:{id:'first'},roadHierarchy:{version:'road-hierarchy/0.1'}},
    {revision:'b',scene:{},ucg:{},routing:{id:'second'},roadHierarchy:{version:'road-hierarchy/0.1'}}];
  const source=readFileSync(new URL('../metropogits/viewer_assets/viewer-history.js',import.meta.url),'utf8');
  const context={METROPOGITS_HISTORY:{frames},location:{hash:'#revision=a'},URLSearchParams,
    document:{getElementById:()=>null}};
  vm.runInNewContext(source,context);
  assert.equal(context.METROPOGITS_DATA.routing,frames[0].routing);
  assert.equal(context.METROPOGITS_DATA.roadHierarchy,frames[0].roadHierarchy);
});
