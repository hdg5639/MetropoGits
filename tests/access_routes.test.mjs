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

test('moved three-way junction preserves each trip destination without inventing turns',()=>{
  const r={status:'COMPLETE',unresolvedEdgeIds:[],junctions:[],segments:[
    {id:'a',kind:'DEPENDENCY_ROAD',start:[-10,0],end:[0,0],width:2,routeIds:['ab','ac']},
    {id:'b',kind:'DEPENDENCY_ROAD',start:[0,0],end:[10,0],width:2,routeIds:['ab']},
    {id:'c',kind:'DEPENDENCY_ROAD',start:[0,0],end:[0,10],width:2,routeIds:['ac']}],
    routes:[{id:'ab',source:'A',target:'B',kind:'DEPENDENCY_ROAD',edgeIds:['e-ab'],networkIds:['n'],path:[[-10,0],[0,0],[10,0]],segmentIds:['a','b']},
      {id:'ac',source:'A',target:'C',kind:'DEPENDENCY_ROAD',edgeIds:['e-ac'],networkIds:['n'],path:[[-10,0],[0,0],[0,10]],segmentIds:['a','c']}]};
  const hub=[1,2],curves={corners:[],segments:{a:[[-10,0],hub],b:[hub,[10,0]],c:[hub,[0,10]]}};
  const p=globalThis.METROPOGITS_FILTERS.createAccessPolicy(r,null,null,curves);
  for(const route of r.routes) {
    const end=route.path.at(-1), first=Math.hypot(11,2),last=Math.hypot(end[0]-1,end[1]-2);
    const point=p.position(route,first/(first+last)).point;
    assert.ok(Math.hypot(point[0]-hub[0],point[1]-hub[1])<1e-8);
    const destination=p.position(route,1).point;
    assert.ok(Math.hypot(destination[0]-end[0],destination[1]-end[1])<1e-8);
  }
  assert.deepEqual(p.network('b').edgeIds,['e-ab']);
  const frame=p.frame('detail',new Set(['A','B','C']),new Set(['n']),{kind:'network',id:'b'});
  assert.deepEqual([...frame.routeIds],['ab']);
  assert.ok(!frame.segmentIds.has('c'));
});

test('diagonal chains join across moved logical corners without changing source-target pairing',()=>{
  const r={status:'COMPLETE',unresolvedEdgeIds:[],junctions:[],segments:[
    {id:'a',kind:'DEPENDENCY_ROAD',start:[0,0],end:[10,0],width:2,routeIds:['forward','reverse']},
    {id:'b',kind:'DEPENDENCY_ROAD',start:[10,0],end:[10,10],width:2,routeIds:['forward','reverse']}],
    routes:[{id:'forward',source:'A',target:'B',kind:'DEPENDENCY_ROAD',edgeIds:['e1'],networkIds:['n'],path:[[0,0],[10,0],[10,10]],segmentIds:['a','b']},
      {id:'reverse',source:'B',target:'A',kind:'DEPENDENCY_ROAD',edgeIds:['e2'],networkIds:['n'],path:[[10,10],[10,0],[0,0]],segmentIds:['b','a']}]};
  const physical={segments:{a:[[0,0],[5,5]],b:[[5,5],[10,10]]},corners:[]};
  const p=globalThis.METROPOGITS_FILTERS.createAccessPolicy(r,null,null,physical);
  for(let i=0;i<=20;i++) {
    const a=p.position(r.routes[0],i/20),b=p.position(r.routes[1],1-i/20);
    assert.ok(Math.hypot(a.point[0]-b.point[0],a.point[1]-b.point[1])<1e-8);
    assert.ok(Math.abs(a.point[0]-a.point[1])<1e-8);
  }
  assert.deepEqual(p.network('a').edgeIds,['e1','e2']);
  assert.deepEqual(p.position(r.routes[0],.5).point,[5,5]);
});

test('curved shared segments drive exact inspection and forward/reverse synthetic trips',()=>{
  const r={status:'COMPLETE',unresolvedEdgeIds:[],junctions:[],segments:[
    {id:'curve',kind:'DEPENDENCY_ROAD',start:[0,0],end:[10,0],width:2,routeIds:['forward','reverse']}],
    routes:[{id:'forward',source:'A',target:'B',kind:'DEPENDENCY_ROAD',edgeIds:['e1'],networkIds:['n'],path:[[0,0],[10,0]],segmentIds:['curve']},
      {id:'reverse',source:'B',target:'A',kind:'DEPENDENCY_ROAD',edgeIds:['e2'],networkIds:['n'],path:[[10,0],[0,0]],segmentIds:['curve']}]};
  const path=[[0,0],[4,3],[6,3],[10,0]];
  const p=globalThis.METROPOGITS_FILTERS.createAccessPolicy(r,null,null,{segments:{curve:path},corners:[]});
  assert.deepEqual(p.network('curve').path,path);
  assert.deepEqual(p.network('curve').edgeIds,['e1','e2']);
  assert.deepEqual(p.position(r.routes[0],.5).point,[5,3]);
  assert.deepEqual(p.position(r.routes[1],.5).point,[5,3]);
  for(let i=0;i<=20;i++) {
    const a=p.position(r.routes[0],i/20),b=p.position(r.routes[1],1-i/20);
    assert.ok(Math.hypot(a.point[0]-b.point[0],a.point[1]-b.point[1])<1e-8);
    assert.equal(a.segmentId,'curve');
  }
  const f=p.frame('detail',new Set(['A','B']),new Set(['n']),{kind:'network',id:'curve',routeId:'forward'});
  assert.deepEqual([...f.routeIds],['forward']);
});
const files=new Set(['A','B','C','D']), networks=new Set(['n']);

test('city context hides minor decoration only and always exposes selected structure',()=>{
  const visible=globalThis.METROPOGITS_FILTERS.contextDetailVisible;
  assert.equal(visible(true,false,false,'minor',null),false);
  assert.equal(visible(true,false,true,'major',null),true);
  assert.equal(visible(true,false,false,'minor','minor'),true);
  assert.equal(visible(true,true,false,'minor',null),true);
  assert.equal(visible(false,false,false,'minor',null),true);
});

test('shared pavement is presentation only and survives exact filtering and animation',()=>{
  const pavement={segments:{shared:[{points:[[0,6],[7,6],[7,8],[0,8]],start:[0,7],end:[7,7],width:2,structural:true}]}};
  const p=globalThis.METROPOGITS_FILTERS.createAccessPolicy(routing,null,pavement);
  const frame=p.frame('detail',files,networks,{kind:'building',id:'A'});
  assert.deepEqual([...frame.routeIds],['ab']);
  assert.deepEqual(frame.segments.find(s=>s.id==='shared').pavement,pavement.segments.shared);
  assert.deepEqual(p.position(frame.animated[0],1).point,[7,0]);
  assert.deepEqual(p.network('shared',frame.routeIds).edgeIds,['edge-ab']);
  assert.equal(p.frame('detail',new Set(['C','D']),networks,{kind:'building',id:'A'}).routes.length,0);
});

test('paint never crosses a narrowed pavement throat',()=>{
  const s={id:'s',start:[0,0],end:[14,0],width:3.5,kind:'DEPENDENCY_ROAD',routeIds:['a'],
    demand:{grade:'AVENUE',width:2.5,lanePattern:'DASHED'},
    pavement:[{start:[0,0],end:[7,0],width:.75},{start:[7,0],end:[14,0],width:2.5}]};
  const paint=globalThis.METROPOGITS_FILTERS.accessMarkingSegments(s,new Map());
  assert.ok(paint.length);
  assert.ok(paint.every(p=>p.start[0]>=7&&p.end[0]<=14));
});
test('fallback review is paged, filter-aware and honest for legacy artifacts',()=>{
  const input=structuredClone(routing);
  input.routes=Array.from({length:70},(_,i)=>({...input.routes[1],id:`r${i}`}));
  input.streetGrid={assignment:{assignedRouteIds:[],fallbackRouteIds:input.routes.map(r=>r.id),
    fallbackReasons:input.routes.slice(0,35).map(r=>({routeId:r.id,reason:'distance_limit',latticeStepLimit:6}))}};
  const p=globalThis.METROPOGITS_FILTERS.createAccessPolicy(input);
  const first=p.failurePage(files,networks), second=p.failurePage(files,networks,25);
  assert.equal(first.total,70); assert.equal(first.rows.length,25); assert.equal(second.rows.length,25);
  assert.ok(first.rows.every(a=>second.rows.every(b=>a.id!==b.id)));
  assert.deepEqual(first.counts.map(c=>[c.reason,c.count]),[['distance_limit',35],['unrecorded',35]]);
  assert.equal(p.failurePage(files,networks,0,'distance_limit').total,35);
  assert.equal(p.failurePage(new Set(['A','B']),networks).total,0);
  assert.equal(p.failurePage(files,new Set()).total,0);
  assert.equal(p.assignmentReason('r0').latticeStepLimit,6);
  assert.match(p.assignmentReason('r69').label,/not recorded/);
  assert.equal(p.assignmentReason('missing'),null);
  assert.equal(policy.assignmentReason('ab'),null);
});
test('structural mode discloses fallback and preserves inspection and exact synthetic paths',()=>{
  const input=structuredClone(routing);
  input.streetGrid={assignment:{assignedRouteIds:['ab'],fallbackRouteIds:['cd']}};
  const p=globalThis.METROPOGITS_FILTERS.createAccessPolicy(input);
  const frame=p.frame('detail',files,networks,null);
  assert.deepEqual([...frame.routeIds],['ab']);
  assert.deepEqual(frame.animated.map(r=>r.id),['ab']);
  assert.match(p.streetStatus,/1\/2.*1 legacy paths/);
  for(const selected of [{kind:'building',id:'C'},{kind:'network',id:'c'}]) {
    const inspected=p.frame('overview',files,networks,selected);
    assert.deepEqual([...inspected.routeIds],['cd']);
    assert.equal(inspected.segmentIds.size,3);
    assert.deepEqual(p.position(inspected.animated[0],1).point,[14,7]);
  }
  assert.equal(p.frame('detail',files,networks,null,true).routes.length,2);
  assert.equal(p.frame('detail',new Set(['A','B']),networks,{kind:'building',id:'C'}).routes.length,0);
  assert.equal(p.choices('n',files,networks).length,2);
});
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
