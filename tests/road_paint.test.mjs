import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import '../metropogits/viewer_assets/viewer-filters.js';
const engine=globalThis.METROPOGITS_FILTERS;
const fixture=JSON.parse(readFileSync(new URL('./fixtures/road-paint.json',import.meta.url),'utf8'));
function road(extra={}) {return {id:'s',kind:'DEPENDENCY_ROAD',access:false,width:2.5,routeIds:['r'],
  start:[0,0],end:[10,0],demand:{grade:'AVENUE',width:2.5,surface:'#404c58',lanePattern:'DASHED'},...extra};}
test('diagonal paint uses the shared physical path instead of the old orthogonal line',()=>{
  const paint=[{start:[2,2],end:[3,3]}];
  assert.deepEqual(engine.accessMarkingSegments(road({curves:{paintSegments:{s:paint},corners:[]}}),new Map()),paint);
  assert.deepEqual(engine.accessMarkingSegments(road({curves:{paintSegments:{s:[]},corners:[]}}),new Map()),[]);
});
test('arterial dashes match the CPU contract at negative coordinates, reversal and trims',()=>{
  for(const c of fixture) {
    const segment=road({start:c.start,end:c.end}), frozen=structuredClone(segment);
    assert.deepEqual(engine.accessMarkingSegments(segment,new Map([['s',c.trims]])),c.expected);
    assert.deepEqual(segment,frozen);
  }
});
test('subdivision does not restart paint phase or hide pavement',()=>{
  const whole=engine.accessMarkingSegments(road(),new Map());
  const split=[...engine.accessMarkingSegments(road({end:[3,0]}),new Map()),
    ...engine.accessMarkingSegments(road({start:[3,0]}),new Map())];
  assert.deepEqual(split,whole);
  for(const extra of [{access:true},{width:.7},{demand:{grade:'ALLEY',width:.9,lanePattern:'NONE'}}])
    assert.deepEqual(engine.accessMarkingSegments(road(extra),new Map()),[]);
});
test('paint stops at actual junction mouths and does not invent a roundabout',()=>{
  const segments=[road(),road({id:'w',end:[-10,0]}),road({id:'n',end:[0,10]})];
  const frame={segments,junctions:[{id:'j',point:[0,0],segmentIds:['s','w','n']}]};
  const joint=engine.accessJunctionGeometry(frame);
  for(const s of segments) for(const p of engine.accessMarkingSegments(s,joint.trims))
    for(const point of [p.start,p.end]) assert.ok(Math.hypot(...point)>=1.55-1e-8);
  for(const kind of ['HTTP_HIGHWAY','MESSAGING_PATH']) {
    const s=road({kind});
    assert.deepEqual(engine.accessMarkingSegments(s,new Map()),[{start:s.start,end:s.end}]);
    assert.equal(engine.accessRoadStyle(s).surface,kind==='HTTP_HIGHWAY'?'#f97316':'#a855f7');
  }
});
