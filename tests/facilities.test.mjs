import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import '../metropogits/viewer_assets/viewer-3d.js';

const models = JSON.parse(await readFile(new URL('../metropogits/viewer_assets/facility-models.json', import.meta.url), 'utf8'));
globalThis.METROPOGITS_DATA = {facilityModels: models};

test('eleven imported-role facilities share exact bounded browser geometry', () => {
  const signatures = new Set();
  for (const [name, model] of Object.entries(models)) {
    const building = {entityId:'source:file',archetype:name,x:13,z:-5,width:6,depth:8,height:18};
    const before = JSON.stringify(building);
    const parts = METROPOGITS_BUILDING_FORMS.partsFor(building);
    assert.equal(parts.length, model.parts.length);
    assert.ok(parts.length <= 6);
    for (const p of parts) {
      assert.ok(p.x >= 13 && p.x+p.width <= 19+1e-9);
      assert.ok(p.z >= -5 && p.z+p.depth <= 3+1e-9);
      assert.ok(p.y >= 0 && p.y+p.height <= 18+1e-9);
      assert.ok(p.width>0 && p.depth>0 && p.height>0);
    }
    assert.equal(JSON.stringify(building), before);
    signatures.add(JSON.stringify(parts));
  }
  assert.equal(signatures.size, 11);
});

test('legacy artifacts do not require the new facility table', () => {
  delete globalThis.METROPOGITS_DATA;
  const old = {entityId:'old:file',archetype:'GATE',x:0,z:0,width:6,depth:6,height:18};
  assert.equal(METROPOGITS_BUILDING_FORMS.partsFor(old).length, 4);
  assert.ok(METROPOGITS_BUILDING_FORMS.partsFor({...old,archetype:'UNKNOWN'}).length > 0);
  globalThis.METROPOGITS_DATA = {facilityModels:models};
});
