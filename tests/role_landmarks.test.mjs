import assert from 'node:assert/strict';
import test from 'node:test';
import '../metropogits/viewer_assets/viewer-filters.js';

const engine = globalThis.METROPOGITS_FILTERS;
function fixture(rule = 'path.test-source', archetype = 'LIBRARY') {
  const buildings = Array.from({length: 400}, (_, i) => ({entityId: `f${String(i).padStart(3, '0')}`,
    districtId: 'd', x: (i % 20) * 7, z: Math.floor(i / 20) * 7,
    width: 6, depth: 6, height: 10, archetype, evidenceIds: ['ev']}));
  const scene = {buildings, networks: [], districts: [
    {id: 'root', parentId: null, x: 0, z: 0, width: 150, depth: 150},
    {id: 'd', parentId: 'root', x: 0, z: 0, width: 150, depth: 150}]};
  const ucg = {entities: buildings.map(b => ({id: b.entityId, kind: 'FILE', path: `src/${b.entityId}.java`})),
    evidence: [{evidenceId: 'ev', ruleId: rule}], edges: []};
  return {scene, ucg};
}
const policy = ({scene, ucg}, streets = []) => engine.createLodPolicy(scene, null, {rectangles: streets}, ucg);
const intersects = (a, b) => a.x < b.x + b.width && b.x < a.x + a.width
  && a.z < b.z + b.depth && b.z < a.z + a.depth;

test('changed physical footprints expand only affected aggregates without losing files', () => {
  const f = fixture(), baseline = policy(f), changed = baseline.aggregates[0];
  const p = engine.createLodPolicy(f.scene, null,
    {rectangles: [], orientedEntityIds: [changed.memberEntityIds[0]]}, f.ucg);
  assert.deepEqual(p.aggregates, baseline.aggregates.filter(a => a.id !== changed.id));
  const ids = f.scene.buildings.map(b => b.entityId);
  for (const level of ['overview', 'district', 'detail']) {
    const v = p.visibility(level, ids, []);
    assert.ok(changed.memberEntityIds.every(id => v.buildingIds.includes(id)));
    const represented = [...v.buildingIds, ...p.aggregates.filter(a => v.aggregateIds.includes(a.id))
      .flatMap(a => a.memberEntityIds)];
    assert.deepEqual(represented.sort(), ids.slice().sort());
  }
  const partial = p.visibility('overview', [changed.memberEntityIds[0]], []);
  assert.deepEqual(partial.buildingIds, [changed.memberEntityIds[0]]);
  assert.deepEqual(partial.aggregateIds, []);
});

test('same-role facilities promote in stages, keep exact membership and original geometry', () => {
  const f = fixture(), original = JSON.stringify(f), p = policy(f);
  const roles = p.aggregates.filter(a => a.role);
  assert.ok(roles.length > 0);
  assert.ok(roles.some(a => a.tier === 'campus'));
  const ids = p.aggregates.flatMap(a => a.memberEntityIds);
  assert.equal(ids.length, 400); assert.equal(new Set(ids).size, 400);
  assert.equal(JSON.stringify(f), original);
  const plots = p.aggregates.flatMap(a => a.plots.map(plot => ({...plot, id: a.id})));
  for (let i = 0; i < plots.length; i++) for (let j = i + 1; j < plots.length; j++) {
    if (plots[i].id !== plots[j].id) assert.ok(!intersects(plots[i], plots[j]));
  }
  for (const a of roles) {
    assert.ok(a.memberEntityIds.length >= 4); assert.ok(a.width <= 56 && a.depth <= 56);
    const part = engine.aggregateParts(a)[0];
    assert.equal(part.representedCount, a.memberEntityIds.length);
    for (const v of engine.roleVolumes(part)) {
      assert.ok(v.x >= a.x && v.z >= a.z && v.x + v.width <= a.x + a.width + 1e-9
        && v.z + v.depth <= a.z + a.depth + 1e-9 && v.y + v.height <= a.height + 1e-9);
    }
  }
  f.scene.buildings.reverse(); f.scene.districts.reverse(); f.ucg.entities.reverse();
  assert.deepEqual(policy(f).aggregates, p.aggregates);
});

test('role facilities persist at all zooms; only explicit expansion exposes originals', () => {
  const f = fixture(), p = policy(f), ids = f.scene.buildings.map(b => b.entityId);
  const a = p.aggregates.find(a => a.role);
  for (const level of ['overview', 'district', 'detail']) {
    const v = p.visibility(level, ids, []);
    const represented = [...v.buildingIds, ...p.aggregates.filter(a => v.aggregateIds.includes(a.id)).flatMap(a => a.memberEntityIds)];
    assert.equal(new Set(represented).size, represented.length);
    assert.equal(represented.length, ids.length);
  }
  assert.equal(p.visibility('detail', ids, []).aggregateIds.length, p.aggregates.filter(a => a.role).length);
  const partial = p.visibility('overview', [a.memberEntityIds[0]], []);
  assert.deepEqual(partial.buildingIds, [a.memberEntityIds[0]]); assert.equal(partial.aggregateIds.length, 0);
  const selected = p.visibility('overview', ids, [], {kind: 'building', id: a.memberEntityIds[0]});
  assert.ok(!selected.buildingIds.includes(a.memberEntityIds[0])); assert.ok(selected.aggregateIds.includes(a.id));
  assert.equal(p.facilityForEntity(a.memberEntityIds[0]).id, a.id);
  for (const level of ['overview', 'district', 'detail']) {
    const expanded = p.visibility(level, ids, [], {kind: 'aggregate', id: a.id}, new Set([a.id]));
    assert.ok(!expanded.aggregateIds.includes(a.id));
    assert.ok(a.memberEntityIds.every(id => expanded.buildingIds.includes(id)));
    const otherRoles = p.aggregates.filter(b => b.role && b.id !== a.id);
    assert.ok(otherRoles.every(b => expanded.aggregateIds.includes(b.id)));
    const collapsed = p.visibility(level, ids, [], null, new Set());
    assert.ok(collapsed.aggregateIds.includes(a.id));
    assert.ok(a.memberEntityIds.every(id => !collapsed.buildingIds.includes(id)));
  }
  const pinned = p.visibility('detail', ids, [], {kind: 'aggregate', id: a.id});
  assert.ok(a.memberEntityIds.every(id => !pinned.buildingIds.includes(id)));
  assert.match(engine.aggregateLabel(a, new Map(f.ucg.entities.map(e => [e.id, e]))), /visual aggregate\nsrc\/[\s\S]*click to inspect/);
});

test('zoom does not flood routes; explicit all-routes and evidenced constituent focus remain available', () => {
  const f = fixture();
  f.ucg.edges = [{id: 'related', from: 'f000', to: 'f001'}, {id: 'other', from: 'f200', to: 'f201'}];
  f.scene.networks = Array.from({length: 100}, (_, i) => ({id: `route${i}`,
    edgeIds: [i === 99 ? 'related' : 'other'], kind: 'DEPENDENCY_ROAD', path: [[0, 0], [7, 0]]}));
  const p = policy(f), ids = f.scene.buildings.map(b => b.entityId), routes = f.scene.networks.map(n => n.id);
  assert.equal(p.visibility('district', ids, routes).networkIds.length, 64);
  assert.equal(p.visibility('detail', ids, routes).networkIds.length, 64);
  assert.equal(p.visibility('detail', ids, routes, null, new Set(), true).networkIds.length, 100);
  assert.deepEqual(p.visibility('detail', ids, routes, {kind: 'building', id: 'f000'}).networkIds, ['route99']);
  assert.deepEqual(p.visibility('detail', ids, routes, {kind: 'building', id: 'f010'}).networkIds, []);
  assert.deepEqual(p.visibility('detail', ids, [], {kind: 'building', id: 'f000'}).networkIds, []);
});

test('unproven gates and generic files never become role landmarks', () => {
  for (const [rule, archetype] of [['unknown', 'GATE'], ['path.test-source', 'GENERIC_BUILDING'], ['unknown', 'LIBRARY']]) {
    assert.equal(policy(fixture(rule, archetype)).aggregates.filter(a => a.role).length, 0);
  }
});

test('District retains all files instead of sampling generic buildings', () => {
  const f = fixture('unknown', 'GENERIC_BUILDING'), p = policy(f);
  const ids = f.scene.buildings.map(b => b.entityId);
  assert.deepEqual(p.visibility('district', ids, []).buildingIds, p.visibility('detail', ids, []).buildingIds);
  assert.equal(p.visibility('district', ids, []).buildingIds.length, 400);
});

test('ordinary Overview masses retain source height bounds even for single-file plots',()=>{
  for(const count of [1,6,42,400]) {
    const f=fixture('unknown','GENERIC_BUILDING');
    f.scene.buildings=f.scene.buildings.slice(0,count);
    f.scene.buildings.forEach((b,i)=>{b.height=i%3===0?14:10;});
    const original=structuredClone(f), p=policy(f);
    const buildings=new Map(f.scene.buildings.map(b=>[b.entityId,b]));
    for(const a of p.aggregates) {
      assert.equal(a.height,Math.max(...a.memberEntityIds.map(id=>buildings.get(id).height)));
      const parts=engine.aggregateParts(a);
      assert.ok(parts.every(part=>part.height>0 && part.height<=a.height));
      assert.equal(parts.reduce((sum,part)=>sum+part.representedCount,0),a.memberEntityIds.length);
    }
    assert.deepEqual(f,original);
  }
});

test('page, API and test evidence never mix; module boundaries remain separate', () => {
  const f = fixture();
  f.ucg.evidence.push({evidenceId: 'page', ruleId: 'path.nextjs.app-page'},
    {evidenceId: 'api', ruleId: 'path.nextjs.route-handler'});
  for (const [i, b] of f.scene.buildings.entries()) {
    if (i % 20 < 12) { b.archetype = 'GATE'; b.evidenceIds = [i % 20 < 6 ? 'page' : 'api']; }
    f.ucg.entities[i].path = `${i % 20 < 3 ? 'one' : 'two'}/${b.entityId}.tsx`;
  }
  f.ucg.entities.push({id: 'm1', kind: 'MODULE', path: 'one'}, {id: 'm2', kind: 'MODULE', path: 'two'});
  const entities = new Map(f.ucg.entities.map(e => [e.id, e]));
  const roles = policy(f).aggregates.filter(a => a.role);
  assert.deepEqual(new Set(roles.map(a => a.role)), new Set(['TEST', 'PAGE', 'API']));
  for (const a of roles) {
    assert.equal(new Set(a.memberEntityIds.map(id => entities.get(id).path.split('/')[0])).size, 1);
    assert.equal(a.evidenceIds.length, 1);
  }
});

test('role compounds never cover corridors, unrelated buildings or distant parcels', () => {
  const f = fixture();
  const road = {x: 62.1, z: 0, width: 0.8, depth: 150};
  f.scene.buildings[44].archetype = 'GENERIC_BUILDING';
  const roles = policy(f, [road]).aggregates.filter(a => a.role);
  assert.ok(roles.length);
  for (const a of roles) {
    assert.ok(!intersects(a, road));
    for (const b of f.scene.buildings) if (!a.memberEntityIds.includes(b.entityId)) assert.ok(!intersects(a, b));
  }
  const sparse = fixture(); sparse.scene.buildings.forEach(b => { b.x *= 10; b.z *= 10; });
  assert.equal(policy(sparse).aggregates.filter(a => a.role).length, 0);
});
