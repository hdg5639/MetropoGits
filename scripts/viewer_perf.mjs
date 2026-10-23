// Interaction performance probe for a generated viewer (development tool, not shipped).
//
//   node scripts/viewer_perf.mjs <chrome.exe> <city-dir> [--runs N] [--out report.json]
//
// Launches an isolated Chrome profile with the real GPU (ANGLE/D3D11 on Windows) and with
// occlusion/background throttling disabled, so requestAnimationFrame keeps its cadence even
// when other windows cover the browser. A scripted session (wheel zoom across every LOD,
// drag orbit, building selection, zoom back out) is driven through synthetic input events
// while a page-side rAF loop records frame gaps per step. The viewer's own ?perf readout is
// read at the end for GPU main-pass time, the worst frame's stage breakdown and rebuild counts.
// Frame gaps are wall-clock presentation cadence on THIS machine: compare before/after runs
// on the same machine, never treat them as a hardware-independent budget.
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir, cpus, platform } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';

class Cdp {
  constructor(socket) {
    this.socket = socket; this.nextId = 1; this.pending = new Map();
    socket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      const entry = this.pending.get(message.id);
      if (!entry) return;
      this.pending.delete(message.id);
      if (message.error) entry.reject(new Error(`${message.error.message}`)); else entry.resolve(message.result);
    });
  }
  static async connect(url) {
    const socket = new WebSocket(url);
    await new Promise((resolve, reject) => { socket.addEventListener('open', resolve); socket.addEventListener('error', reject); });
    return new Cdp(socket);
  }
  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => { this.pending.set(id, { resolve, reject }); this.socket.send(JSON.stringify({ id, method, params })); });
  }
  async evaluate(expression, timeout = 180000) {
    const result = await Promise.race([
      this.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }),
      sleep(timeout).then(() => { throw new Error('evaluate timeout'); }),
    ]);
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
  }
  close() { this.socket.close(); }
}

// Runs inside the page. Every step is labelled so a hitch can be attributed to an interaction.
const SCENARIO = `(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const raf = () => new Promise((r) => requestAnimationFrame(r));
  const canvas = document.querySelector('canvas');
  const rect = canvas.getBoundingClientRect();
  const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
  canvas.setPointerCapture = () => {};
  const wheel = (deltaY) => canvas.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaY, clientX: cx, clientY: cy }));
  const pointer = (type, x, y) => canvas.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, button: 0, pointerId: 1 }));
  const steps = {};
  let step = 'idle', last = performance.now(), running = true;
  (async () => {
    while (running) {
      await raf();
      const now = performance.now(), gap = now - last; last = now;
      const s = steps[step] ||= { gaps: [] };
      s.gaps.push(gap);
    }
  })();
  const zoom = async (name, deltaY, frames) => { step = name; for (let i = 0; i < frames; i++) { wheel(deltaY); await raf(); } step = name + '-settle'; await sleep(900); };
  const click = async (name, x, y) => { step = name; pointer('pointerdown', x, y); pointer('pointerup', x, y); await sleep(700); };
  await sleep(4500);                       // first paint and idle prewarm
  step = 'idle'; await sleep(1500);
  await zoom('zoom-in-1', -40, 40);
  await zoom('zoom-in-2', -40, 40);
  await click('select-a', cx, cy);
  await click('select-b', cx + 60, cy + 40);
  step = 'orbit'; pointer('pointerdown', cx, cy);
  for (let i = 0; i < 120; i++) { pointer('pointermove', cx + i * 4, cy); await raf(); }
  pointer('pointerup', cx + 480, cy); step = 'orbit-settle'; await sleep(900);
  await zoom('zoom-out-1', 60, 60);
  await click('select-c', cx, cy);
  await zoom('zoom-out-2', 60, 120);
  running = false; await raf();
  const summary = {};
  for (const [name, s] of Object.entries(steps)) {
    const g = [...s.gaps].sort((a, b) => a - b);
    if (!g.length) continue;
    summary[name] = { frames: g.length, median: +g[g.length >> 1].toFixed(1), p95: +g[Math.floor(g.length * 0.95)].toFixed(1),
      max: +g.at(-1).toFixed(0), over50: g.filter((x) => x > 50).length, over100: g.filter((x) => x > 100).length };
  }
  const panel = [...document.querySelectorAll('pre')].map((e) => e.textContent).find((t) => /^MetropoGits perf/.test(t));
  return { summary, panel, visibility: document.visibilityState, geometry: window.__geo || null };
})()`;

async function main() {
  const args = process.argv.slice(2);
  const outIndex = args.indexOf('--out');
  const out = outIndex >= 0 ? args.splice(outIndex, 2)[1] : null;
  const profileOnly = args.includes('--profile') ? args.splice(args.indexOf('--profile'), 1) && true : false;
  const runsIndex = args.indexOf('--runs');
  const runs = runsIndex >= 0 ? Number(args.splice(runsIndex, 2)[1]) : 1;
  const [browser, directory] = args;
  if (!browser || !directory) throw new Error('usage: viewer_perf.mjs <chrome.exe> <city-dir> [--runs N] [--out report.json]');
  const profile = await mkdtemp(join(tmpdir(), 'metropogits-perf-'));
  const child = spawn(browser, ['--headless=new', '--no-first-run', '--no-default-browser-check', `--user-data-dir=${profile}`,
    '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1', '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows', '--disable-background-timer-throttling',
    '--disable-features=CalculateNativeWinOcclusion', '--window-size=1280,800', 'about:blank'], { windowsHide: true, stdio: 'ignore' });
  let cdp;
  const report = { tool: 'viewer-perf/0.1', environment: { platform: platform(), cpu: cpus()[0]?.model, node: process.version }, runs: [] };
  try {
    let port; const deadline = Date.now() + 20000;
    while (!port && Date.now() < deadline) {
      try { port = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; } catch { await sleep(100); }
    }
    if (!port) throw new Error('Browser startup timeout');
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    cdp = await Cdp.connect(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
    await cdp.send('Page.enable'); await cdp.send('Runtime.enable');
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
    report.environment.browser = (await cdp.send('Browser.getVersion')).product;
    for (let run = 1; run <= runs; run++) {
      if (profileOnly) {
        await cdp.send('Profiler.enable'); await cdp.send('Profiler.setSamplingInterval', { interval: 200 }); await cdp.send('Profiler.start');
      }
      const navigated = Date.now();
      await cdp.send('Page.navigate', { url: pathToFileURL(join(directory, 'index.html')).href + `?perf&run=${run}` });
      for (const start = Date.now(); !(await cdp.evaluate('Boolean(document.querySelector("canvas")) && [...document.querySelectorAll("pre")].some((e) => /frame gap/.test(e.textContent))').catch(() => false)); ) {
        if (Date.now() - start > 60000) throw new Error('Viewer failed to initialise'); await sleep(50);
      }
      const loadMs = Date.now() - navigated;
      const resources = await cdp.evaluate(`performance.getEntriesByType('resource').map((e) => [e.name.split('/').pop(), Math.round(e.duration), e.decodedBodySize])`);
      if (run === 1) {
        report.environment.renderer = await cdp.evaluate(`(() => { const g = document.createElement('canvas').getContext('webgl');
          const e = g.getExtension('WEBGL_debug_renderer_info'); return e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'unknown'; })()`);
      }
      if (profileOnly) {
        await sleep(4000);
        const { profile: cpu } = await cdp.send('Profiler.stop');
        const self = new Map(); const byId = new Map(cpu.nodes.map((node) => [node.id, node]));
        const dt = cpu.timeDeltas; 
        cpu.samples.forEach((id, i) => { const node = byId.get(id); const f = node.callFrame; const key = `${f.functionName || '(anon)'} ${f.url.split('/').pop()}:${f.lineNumber + 1}`; self.set(key, (self.get(key) || 0) + (dt[i] || 0) / 1000); });
        const top = [...self.entries()].sort((x, y) => y[1] - x[1]).slice(0, 25);
        console.log('top self-time (ms) during load + idle prewarm:'); for (const [name, ms] of top) console.log(String(ms.toFixed(0)).padStart(7) + '  ' + name);
        continue;
      }
      const result = await cdp.evaluate(SCENARIO);
      result.loadMs = loadMs; result.resources = resources;
      report.runs.push(result);
      console.log('navigation to first perf readout: ' + loadMs + ' ms; scripts: ' + resources.map(([n, ms, size]) => n + ' ' + ms + 'ms/' + (size / 1e6).toFixed(1) + 'MB').join(', '));
      console.log(`\n== run ${run} (${result.visibility}) ==`);
      for (const [name, s] of Object.entries(result.summary)) {
        console.log(`${name.padEnd(18)} frames ${String(s.frames).padStart(3)}  median ${String(s.median).padStart(5)}  p95 ${String(s.p95).padStart(6)}  max ${String(s.max).padStart(5)}  >50ms ${s.over50}  >100ms ${s.over100}`);
      }
      console.log(result.panel);
    }
    console.log(`\nrenderer: ${report.environment.renderer}`);
    if (out) await writeFile(out, JSON.stringify(report, null, 2));
  } finally {
    cdp?.close(); child.kill();
  }
}
main().catch((error) => { console.error(error); process.exit(1); });
