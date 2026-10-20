import assert from 'node:assert/strict';
import test from 'node:test';
import '../metropogits/viewer_assets/viewer-filters.js';
const engine=globalThis.METROPOGITS_FILTERS;

function fixture(){
 const ids=['a','b','c','d'];
 const scene={districts:[{id:'root',parentId:null},{id:'d',parentId:'root'}],networks:[],
  buildings:ids.map((id,i)=>({entityId:id,districtId:'d',x:i*8,z:0,width:6,depth:6,height:10,
   archetype:'GATE',evidenceIds:['ev']}))};
 const facility={id:'visual:checked',districtId:'d',majorDistrictId:'d',memberEntityIds:ids,
  memberDistrictIds:['d'],role:'PAGE',tier:'center',title:'Page hall',evidenceIds:['ev'],
  x:0,z:0,width:30,depth:6,height:18,plots:[{x:0,z:0,width:30,depth:6}],
  archetypeCounts:[{archetype:'GATE',count:4}],
  physicalModel:{baseElevation:2,footprint:[[0,0],[30,0],[30,6],[0,6]],parts:[]}};
 const ucg={entities:ids.map(id=>({id,kind:'FILE',path:`src/${id}/page.tsx`})),edges:[],
  evidence:[{evidenceId:'ev',ruleId:'path.nextjs.app-page'}]};
 return {ids,scene,facility,ucg};
}

test('certified World compounds survive orientation guards and every LOD until explicit expansion',()=>{
 const {ids,scene,facility,ucg}=fixture();const original=JSON.stringify({scene,ucg,facility});
 const p=engine.createLodPolicy(scene,null,{rectangles:[],orientedEntityIds:ids,roleCompounds:[facility]},ucg);
 assert.deepEqual(p.aggregates,[facility]);assert.equal(p.facilityForEntity('a').id,facility.id);
 for(const lod of ['overview','district','detail']){
  assert.deepEqual(p.visibility(lod,ids,[]).aggregateIds,[facility.id]);
  assert.deepEqual(p.visibility(lod,ids,[]).buildingIds,[]);
  const expanded=p.visibility(lod,ids,[],null,new Set([facility.id]));
  assert.deepEqual(expanded.aggregateIds,[]);assert.deepEqual(expanded.buildingIds,ids);
 }
 assert.equal(engine.aggregateElevation(null,facility),2);
 assert.equal(JSON.stringify({scene,ucg,facility}),original);
});

test('World compound filtering never reintroduces hidden members or removes the legacy safety guard',()=>{
 const {ids,scene,facility,ucg}=fixture();
 const p=engine.createLodPolicy(scene,null,{rectangles:[],orientedEntityIds:ids,roleCompounds:[facility]},ucg);
 assert.deepEqual(p.visibility('detail',['a'],[]).aggregateIds,[]);
 assert.deepEqual(p.visibility('detail',['a'],[]).buildingIds,['a']);
 const legacy=engine.createLodPolicy(scene,null,{rectangles:[],orientedEntityIds:ids},ucg);
 assert.deepEqual(legacy.aggregates,[]);
 assert.deepEqual(legacy.visibility('overview',ids,[]).buildingIds,ids);
});

test('campus complexes retain mixed source membership at all LODs without inventing peer routes',()=>{
 const {ids,scene,facility,ucg}=fixture();
 facility.role='CAMPUS:VALIDATION';facility.campusProgram={kind:'VALIDATION',derived:true};
 facility.sourceEdgeIds=['original:a-to-target','original:b-to-target'];facility.sharedTargetIds=['actual-target'];
 scene.buildings[1].archetype='SERVICE_OFFICE';
 const frozen=JSON.stringify({scene,facility,ucg});
 const p=engine.createLodPolicy(scene,null,{rectangles:[],orientedEntityIds:ids,roleCompounds:[facility]},ucg);
 for(const lod of ['overview','district','detail']) {
  assert.deepEqual(p.visibility(lod,ids,[]).aggregateIds,[facility.id]);
  assert.deepEqual(p.visibility(lod,ids,[],null,new Set([facility.id])).buildingIds,ids);
 }
 assert.deepEqual(p.visibility('detail',['b'],[]).aggregateIds,[]);
 assert.deepEqual(p.visibility('detail',['b'],[]).buildingIds,['b']);
 assert.equal(JSON.stringify({scene,facility,ucg}),frozen);
});
