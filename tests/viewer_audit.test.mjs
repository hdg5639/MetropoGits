import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile, mkdir, mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Script } from 'node:vm';
import '../metropogits/viewer_assets/viewer-3d.js';
import '../metropogits/viewer_assets/viewer-filters.js';
import { Cdp, instrument, replaceOnce, summarize, reportHtml, prepare } from '../scripts/viewer_audit.mjs';

test('corridor visibility follows its actual contributing routes across filters and LOD', () => {
  const visible = globalThis.METROPOGITS_FILTERS.corridorVisible;
  const shared = {networkIds: ['a', 'b']};
  assert.equal(visible(shared, new Set(['a'])), true);
  assert.equal(visible(shared, new Set(['b'])), true);
  assert.equal(visible(shared, new Set(['c'])), false);
  assert.equal(visible(shared, new Set()), false);
  assert.equal(visible({}, new Set()), true); // legacy presentation data
});

test('static geometry cache survives animation ticks and invalidates visual state', () => {
  const cache = globalThis.METROPOGITS_GEOMETRY_CACHE();
  let builds = 0;
  const build = () => ({triangles: [++builds], lines: []});
  const first = cache('overview:0:none', build);
  assert.equal(cache('overview:0:none', build), first);
  for (const key of ['district:0:none', 'district:1:none', 'district:1:building:a']) {
    const geometry = cache(key, build);
    assert.equal(cache(key, build), geometry);
  }
  assert.equal(builds, 4);
  for (let frame = 0; frame < 60; frame += 1) cache('district:1:building:a', build);
  assert.equal(builds, 4);
  assert.equal(cache('district:1:building:a', build).triangles[0], 4);
});

test('cached picking matches independent projection, ordering and viewport culling', () => {
  const descriptors = Array.from({length:120}, (_,i)=>({id:`r${i}`,
    kind:['district','network','building','aggregate'][i%4],priority:[1,100,200,250][i%4],
    points:[[i%9-4,0,Math.floor(i/9)-6],[i%9-3,.2,Math.floor(i/9)-5]]}));
  descriptors.push({...descriptors[0],id:'shared'});
  const original=JSON.stringify(descriptors), cache=globalThis.METROPOGITS_PICK_PROJECTION(descriptors);
  assert.ok(cache.vertexCount < descriptors.reduce((n,r)=>n+r.points.length,0));
  for (let frame=0;frame<12;frame+=1) {
    const angle=frame*.35, c=Math.cos(angle), s=Math.sin(angle);
    const m=[c,.1,s,.03,0,1,0,0,-s,.3,c,.12,frame*.1,0,0,frame===11?-5:1];
    const width=600+frame*15, height=400+frame*9;
    const expected=descriptors.map(r=>{
      const points=r.points.map(([x,y,z])=>{
        const w=m[3]*x+m[7]*y+m[11]*z+m[15];
        if(w<=0) return null;
        return {x:((m[0]*x+m[4]*y+m[8]*z+m[12])/w*.5+.5)*width,
          y:(1-((m[1]*x+m[5]*y+m[9]*z+m[13])/w*.5+.5))*height,
          depth:(m[2]*x+m[6]*y+m[10]*z+m[14])/w};
      });
      if(points.some(p=>!p)) return null;
      const margin=r.kind==='network'?8:0;
      const minX=Math.min(...points.map(p=>p.x))-margin,maxX=Math.max(...points.map(p=>p.x))+margin;
      const minY=Math.min(...points.map(p=>p.y))-margin,maxY=Math.max(...points.map(p=>p.y))+margin;
      if(maxX<0||maxY<0||minX>width||minY>height) return null;
      return {id:r.id,priority:r.priority,minX,minY,maxX,maxY,depth:Math.min(...points.map(p=>p.depth))};
    }).filter(Boolean).sort((a,b)=>b.priority-a.priority||a.depth-b.depth);
    const actual=cache.project(m,width,height).map(r=>Object.fromEntries(Object.keys(expected[0]||{id:0}).map(k=>[k,r[k]])));
    assert.deepEqual(actual,expected);
  }
  assert.equal(JSON.stringify(descriptors),original);
});

test('animation uses its own dynamic buffer and never disables static cache', async () => {
  const source = await readFile(new URL('../metropogits/viewer_assets/viewer-3d.js', import.meta.url), 'utf8');
  assert.ok(source.includes('bindAndDraw(activityBuffer, buildActivityGeometry(timestamp), gl.TRIANGLES, gl.DYNAMIC_DRAW)'));
  const staticBuilder = source.split('function buildUncachedGeometry(timestamp) {')[1].split('function buildActivityGeometry')[0];
  assert.ok(!staticBuilder.includes('syntheticActivity'));
  assert.ok(!staticBuilder.includes('pointAlongPath'));
  assert.ok(source.includes('projectionKey !== lastProjectionKey'));
});

test('instrumentation is isolated, parseable and fails closed on marker drift', async () => {
  const source = await readFile(new URL('../metropogits/viewer_assets/viewer-3d.js', import.meta.url), 'utf8');
  assert.ok(!source.includes('__METRO_AUDIT__'));
  const modified = instrument(source);
  new Script(modified);
  assert.equal(modified.match(/globalThis\.__METRO_AUDIT__ =/g).length, 1);
  assert.ok(modified.includes('auditLod || lodPolicy.levelForZoom'));
  assert.ok(modified.includes('geometryMs: auditGeometryEnd - auditStart'));
  assert.throws(() => instrument(source.replace('    renderLabels();', '    renderLabels(0);')), /marker changed/);
  assert.throws(() => replaceOnce('x x', 'x', 'y'), /marker changed/);
  assert.throws(() => instrument(modified), /marker changed/);
});

test('timing percentiles retain sample count and reject invalid samples', () => {
  assert.deepEqual(summarize([3, 1, 2]), {count: 3, median: 2, p95: 3, max: 3});
  assert.equal(summarize(Array.from({length:20}, (_, i) => i + 1)).p95, 19);
  for (const samples of [[], [NaN], [Infinity], [-1]]) assert.throws(() => summarize(samples));
});

test('CDP resolves results, records exceptions, rejects protocol errors and disconnects', async () => {
  class Socket extends EventTarget {
    send(value) { this.sent = JSON.parse(value); }
    message(value) { this.dispatchEvent(new MessageEvent('message', {data: JSON.stringify(value)})); }
  }
  const socket = new Socket();
  const cdp = new Cdp(socket);
  const success = cdp.evaluate('1');
  socket.message({id: socket.sent.id, result: {result: {value: 1}}});
  assert.equal(await success, 1);
  socket.message({method: 'Runtime.exceptionThrown', params: {description: 'bad'}});
  assert.equal(cdp.errors.length, 1);
  const failed = cdp.send('invalid');
  socket.message({id: socket.sent.id, error: {message: 'no method'}});
  await assert.rejects(failed, /no method/);
  const exception = cdp.evaluate('throw');
  socket.message({id: socket.sent.id, result: {exceptionDetails: {text: 'bad expression'}}});
  await assert.rejects(exception, /bad expression/);
  const closed = cdp.send('waiting');
  socket.dispatchEvent(new Event('close'));
  await assert.rejects(closed, /closed/);
  assert.equal(cdp.pending.size, 0);
});

test('audit rejects modified viewer code instead of executing it', async () => {
  const root = await mkdtemp(join(tmpdir(), 'metro-audit-test-'));
  try {
    await mkdir(join(root, 'input', 'assets'), {recursive: true});
    await writeFile(join(root, 'input', 'assets', 'viewer-3d.js'), 'throw new Error("untrusted");');
    await assert.rejects(prepare(join(root, 'input'), join(root, 'output')), /Stale or untrusted/);
    assert.equal(await readFile(join(root, 'input', 'assets', 'viewer-3d.js'), 'utf8'), 'throw new Error("untrusted");');
  } finally {
    await rm(root, {recursive: true, force: true});
  }
});

test('comparison gallery escapes paths and distinguishes scale modes and CPU timing', () => {
  const state = {counts: {blocks: 2, buildings: 0, networks: 1}, camera: {distance: 42}, lod: 'overview'};
  const view = {state, orbit: {cpuMs: {p95: 3}, inputToSubmitMs: {p95: 5}}, wheel: {cpuMs: {p95: 2}}};
  const report = {policy: {normalizedZooms: {overview: 1, district: 1.6, detail: 2.5}}, cases: [
    {input: '<img src=x onerror=alert(1)>', commonScale: state, views: {overview: view, district: view, detail: view}}
  ]};
  const html = reportHtml(report);
  assert.ok(!html.includes('<img src=x'));
  assert.ok(html.includes('&lt;img src=x'));
  assert.ok(html.includes('Same absolute camera distance'));
  assert.ok(html.includes('not GPU completion or display FPS'));
  assert.ok(html.includes('common-scale.png'));
});
