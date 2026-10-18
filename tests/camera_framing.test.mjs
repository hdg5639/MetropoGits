import assert from 'node:assert/strict';
import test from 'node:test';
import '../metropogits/viewer_assets/viewer-3d.js';
const {fitPerspective,lookAt,perspective,multiply,transformPoint}=globalThis.METROPOGITS_WEBGL_MATH;
const policy=globalThis.METROPOGITS_CAMERA_POLICY;
const camera={yaw:policy.yaw,pitch:policy.pitch,targetX:0,targetY:0,targetZ:0,distance:100};
function projection(c,aspect) {
 const h=Math.cos(c.pitch)*c.distance;
 const eye=[c.targetX+Math.sin(c.yaw)*h,c.targetY+Math.sin(c.pitch)*c.distance,c.targetZ+Math.cos(c.yaw)*h];
 return multiply(perspective(policy.fieldOfView,aspect,Math.max(.1,c.distance/250),c.distance*10),
   lookAt(eye,[c.targetX,c.targetY,c.targetZ],[0,1,0]));
}
function check(points,c,aspect) {
 const matrix=projection(c,aspect);
 for(const p of points) {
  const q=transformPoint(matrix,p);
  assert.ok(q[3]>0);
  assert.ok(Math.abs(q[0]/q[3])<=policy.horizontalMargin+1e-6);
  assert.ok(Math.abs(q[1]/q[3])<=policy.verticalMargin+1e-6);
  assert.ok(q[2]/q[3]>=-1 && q[2]/q[3]<=1);
 }
}
test('perspective fit contains every off-center point across aspect ratios and rotations',()=>{
 const points=[[-400,0,20],[-350,40,45],[200,0,400],[250,100,420],[0,5,100]];
 const original=structuredClone(points);
 for(const aspect of [.45,1,1.5,2.5])for(const yaw of [0,-.68,2])for(const pitch of [.16,.62,1.42]) {
  const c={...camera,yaw,pitch};
  const fitted=fitPerspective(points,c,policy,aspect);
  check(points,fitted,aspect);
  assert.ok(Math.abs(fitted.targetY-c.targetY)<1e-8,'zoom pivot must not move underground');
  assert.deepEqual(fitPerspective([...points].reverse(),c,policy,aspect),fitted);
  assert.deepEqual(c,{...camera,yaw,pitch});
 }
 assert.deepEqual(points,original);
});
test('lateral reframing improves a displaced city without dropping outliers',()=>{
 const points=[[500,0,500],[600,0,500],[500,0,600],[600,80,600],[-30,0,0]];
 const fitted=fitPerspective(points,camera,policy,1.5);
 check(points,fitted,1.5);
 // Reproduce the old center-locked search as an independent comparison.
 let low=8,high=5000;
 for(let i=0;i<40;i++) {
  const middle=(low+high)/2;
  try {check(points,{...camera,distance:middle},1.5);high=middle;}catch{low=middle;}
 }
 assert.ok(fitted.distance<high*.85);
 assert.notEqual(fitted.targetX,camera.targetX);
});
test('empty and degenerate framing remains finite and preserves orientation',()=>{
 assert.deepEqual(fitPerspective([],camera,policy,1),camera);
 for(const points of [[[0,0,0]],[[10,10,10],[10,10,10]],[[0,0,0],[0,900,0]]]) {
  const fitted=fitPerspective(points,camera,policy,1,8);
  assert.ok(Object.values(fitted).every(Number.isFinite));
  assert.equal(fitted.yaw,camera.yaw);assert.equal(fitted.pitch,camera.pitch);
  check(points,fitted,1);
 }
});

test('framing contains source and promoted silhouettes regardless of city population',()=>{
 const {lodFramingPoints}=globalThis.METROPOGITS_WEBGL_MATH;
 for(const count of [1,42,256,400]) {
  const buildings=Array.from({length:count},(_,i)=>({x:i%20*7,z:Math.floor(i/20)*7,width:6,depth:6,height:10}));
  buildings[count-1].height=70;
  const facilities=[{x:0,z:0,width:20,depth:20,height:30}];
  const frozen=structuredClone({buildings,facilities});
  const points=lodFramingPoints(buildings,facilities);
  assert.equal(points.length,(count+1)*4);
  assert.ok(points.some(p=>p[1]===32.4));
  assert.ok(points.some(p=>p[1]===70));
  for(const aspect of [.6,1.5,2.5]) check(points,fitPerspective(points,camera,policy,aspect),aspect);
  assert.deepEqual({buildings,facilities},frozen);
 }
});
