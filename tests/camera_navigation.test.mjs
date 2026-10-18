import assert from 'node:assert/strict';
import test from 'node:test';
import '../metropogits/viewer_assets/viewer-filters.js';
const {groundPan, cameraKeyAction} = globalThis.METROPOGITS_FILTERS;

test('major-district inspector counts descendants without counting adjacent modules', () => {
  const scene = {districts:[{id:'root',parentId:null},{id:'module',parentId:'root'},
    {id:'src',parentId:'module'},{id:'other',parentId:'root'}], buildings:[
    {entityId:'one',districtId:'module'},{entityId:'two',districtId:'src'},{entityId:'three',districtId:'other'}]};
  assert.deepEqual(globalThis.METROPOGITS_FILTERS.districtBuildings(scene,'module').map(b=>b.entityId),['one','two']);
  assert.deepEqual(globalThis.METROPOGITS_FILTERS.districtBuildings(scene,'missing'),[]);
});

test('ground pan preserves height, follows rotated screen axes and is reversible', () => {
  for (const yaw of [0, Math.PI / 2, Math.PI, -0.9]) {
    for (const pitch of [.16, .6, 1.42]) {
      const camera = {distance:100, pitch, yaw, targetY:12};
      const original = {...camera};
      const movement = groundPan(camera, 30, 20, 800, Math.PI / 4);
      const reverse = groundPan(camera, -30, -20, 800, Math.PI / 4);
      assert.deepEqual(camera, original);
      assert.ok(Math.abs(movement.x + reverse.x) < 1e-10);
      assert.ok(Math.abs(movement.z + reverse.z) < 1e-10);
      // View-space right and up projections compensate the original pixel drag.
      const scale = 2 * camera.distance * Math.tan(Math.PI / 8) / 800;
      assert.ok(Math.abs((movement.x*Math.cos(yaw)-movement.z*Math.sin(yaw))/scale + 30) < 1e-9);
      assert.ok(Math.abs((-movement.x*Math.sin(yaw)-movement.z*Math.cos(yaw))*Math.sin(pitch)/scale - 20) < 1e-9);
    }
  }
});

test('pan speed scales with zoom and viewport; extreme pitch stays finite', () => {
  const camera = {distance:100, pitch:.5, yaw:.7};
  const base = groundPan(camera, 20, 30, 500, .8);
  const closer = groundPan({...camera, distance:50}, 20, 30, 500, .8);
  const taller = groundPan(camera, 20, 30, 1000, .8);
  assert.deepEqual(closer, taller);
  assert.equal(base.x, closer.x * 2);
  assert.equal(base.z, closer.z * 2);
  assert.ok(Object.values(groundPan({...camera, pitch:0}, 20,30,0,.8)).every(Number.isFinite));
});

test('camera keys never hijack forms, editable controls or browser shortcuts', () => {
  assert.equal(cameraKeyAction({key:'W'}), 'pan-up');
  assert.equal(cameraKeyAction({key:'ArrowRight'}), 'pan-right');
  assert.equal(cameraKeyAction({key:'r'}), 'reset');
  for (const key of ['w', 'ArrowDown', 'r', '+']) {
    for (const flag of ['ctrlKey', 'metaKey', 'altKey', 'defaultPrevented']) {
      assert.equal(cameraKeyAction({key, [flag]:true}), null);
    }
    assert.equal(cameraKeyAction({key, target:{isContentEditable:true}}), null);
    assert.equal(cameraKeyAction({key, target:{closest:()=>({})}}), null);
  }
  assert.equal(cameraKeyAction({key:'Tab'}), null);
});
