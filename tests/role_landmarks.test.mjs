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

test('LOD has no duplicate files; partial filtering and selection expose originals', () => {
  const f = fixture(), p = policy(f), ids = f.scene.buildings.map(b => b.entityId);
  const a = p.aggregates.find(a => a.role);
  for (const level of ['overview', 'district', 'detail']) {
    const v = p.visibility(level, ids, []);
    const represented = [...v.buildingIds, ...p.aggregates.filter(a => v.aggregateIds.includes(a.id)).flatMap(a => a.memberEntityIds)];
    assert.equal(new Set(represented).size, represented.length);
    assert.equal(represented.length, ids.length);
  }
  assert.equal(p.visibility('detail', ids, []).aggregateIds.length, 0);
  const partial = p.visibility('overview', [a.memberEntityIds[0]], []);
  assert.deepEqual(partial.buildingIds, [a.memberEntityIds[0]]); assert.equal(partial.aggregateIds.length, 0);
  const selected = p.visibility('overview', ids, [], {kind: 'building', id: a.memberEntityIds[0]});
  assert.ok(selected.buildingIds.includes(a.memberEntityIds[0])); assert.ok(!selected.aggregateIds.includes(a.id));
  const pinned = p.visibility('detail', ids, [], {kind: 'aggregate', id: a.id});
  assert.ok(a.memberEntityIds.every(id => !pinned.buildingIds.includes(id)));
  assert.match(engine.aggregateLabel(a, new Map(f.ucg.entities.map(e => [e.id, e]))), /visual aggregate\nsrc\/[\s\S]*click to inspect/);
});

test('unproven gates and generic files never become role landmarks', () => {
  for (const [rule, archetype] of [['unknown', 'GATE'], ['path.test-source', 'GENERIC_BUILDING'], ['unknown', 'LIBRARY']]) {
    assert.equal(policy(fixture(rule, archetype)).aggregates.filter(a => a.role).length, 0);
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
