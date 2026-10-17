import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile, mkdir, mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Script } from 'node:vm';
import { Cdp, instrument, replaceOnce, summarize, reportHtml, prepare } from '../scripts/viewer_audit.mjs';

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
