import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import '../metropogits/viewer_assets/viewer-filters.js';

const materialPart = METROPOGITS_FILTERS.materialPart;
const policy = {version:'building-materials/0.1', palettes:[['#b9b6aa','#717a7d']],
  roleColors:{GENERIC_BUILDING:'#a2adbb',SERVICE_OFFICE:'#60a5fa',LIBRARY:'#facc15'}};

test('architectural tones retain generic unknowns and distinguish only highest roof faces', () => {
  const b={entityId:'same-source',archetype:'SERVICE_OFFICE'}, p={y:0,height:10};
  assert.equal(materialPart(null,b,p,10),null);
  assert.equal(materialPart({...policy,version:'unknown'},b,p,10),null);
  const wall=materialPart(policy,b,p,10);
  assert.equal(wall.wall,'#b9b6aa');assert.notEqual(wall.roof,'#717a7d');
  assert.equal(materialPart(policy,b,p,11).roof,'#717a7d');
  assert.deepEqual(materialPart(policy,b,p,10,true),{wall:'#60a5fa',roof:'#60a5fa'});
  assert.deepEqual(materialPart(policy,{...b,archetype:'UNKNOWN'},p,10),{wall:'#b9b6aa',roof:'#717a7d'});
});

test('both renderers restore semantic tint for filters, selection and explicit mode', async () => {
  for(const name of ['viewer-3d.js','viewer.js']) {
    const text=await readFile(new URL('../metropogits/viewer_assets/'+name,import.meta.url),'utf8');
    assert.match(text,/showRoleColors \|\| activeFilterCount\(\) > 0 \|\| isSelected/);
    assert.match(text,/toggle-role-colors/);
    assert.match(text,/Not source material evidence/);
  }
  const webgl=await readFile(new URL('../metropogits/viewer_assets/viewer-3d.js',import.meta.url),'utf8');
  assert.match(webgl,/nextCacheKey = .*showRoleColors/);
});

test('entrance cladding is shared and gives way to semantic selection', () => {
  const decorated={...policy,detailColors:{12:['#354e59','#566771']}};
  const building={entityId:'source',archetype:'SERVICE_OFFICE'};
  const part={y:0,height:2,materialKind:12};
  assert.deepEqual(materialPart(decorated,building,part,10),{wall:'#354e59',roof:'#566771'});
  assert.deepEqual(materialPart(decorated,building,part,10,true),{wall:'#60a5fa',roof:'#60a5fa'});
});

test('persistent role-compound parts share neutral walls and only the highest roof accent', () => {
  const facility={entityId:'aggregate:actual-members',aggregateRole:'TEST',archetype:'LIBRARY',
    x:0,z:0,width:20,depth:20,height:15,tier:'campus'};
  const parts=METROPOGITS_FILTERS.roleVolumes(facility), original=JSON.stringify(parts);
  const top=Math.max(...parts.map(p=>p.y+p.height));
  const materials=parts.map(p=>materialPart(policy,facility,{...p,shade:0},top));
  assert.ok(materials.every(p=>p.wall==='#b9b6aa'));
  assert.equal(materials.filter(p=>p.roof!=='#717a7d').length,1);
  assert.equal(JSON.stringify(parts),original);
  assert.ok(parts.every(p=>materialPart(policy,facility,{...p,shade:0},top,true).wall==='#facc15'));
});
