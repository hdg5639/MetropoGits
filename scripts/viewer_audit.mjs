// Local, opt-in browser audit. Never loaded by the distributed viewer.
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { readFile, writeFile, mkdir, mkdtemp, copyFile } from 'node:fs/promises';
import { tmpdir, cpus, platform, release } from 'node:os';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const assets = resolve(dirname(fileURLToPath(import.meta.url)), '../metropogits/viewer_assets');
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');

export function replaceOnce(source, marker, replacement) {
  if (source.split(marker).length !== 2) throw new Error(`Audit marker changed: ${marker}`);
  return source.replace(marker, replacement);
}

export function summarize(samples) {
  if (!samples.length || samples.some((n) => !Number.isFinite(n) || n < 0)) {
    throw new Error('Expected nonempty finite, nonnegative timing samples');
  }
  const sorted = [...samples].sort((a, b) => a - b);
  return { count: sorted.length, median: sorted[Math.floor(sorted.length / 2)],
    p95: sorted[Math.ceil(sorted.length * .95) - 1], max: sorted.at(-1) };
}

export function instrument(source) {
  let result = replaceOnce(source, '  function render(timestamp = 0) {', `
  const auditFrames = [];
  let auditLod = null;
  let auditFirstDraw = null;
  let auditSequence = 0;
  function render(timestamp = 0) {
    const auditStart = performance.now();`);
  result = replaceOnce(result, '    renderLabels();', `    renderLabels();
    const ended = performance.now();
    auditFirstDraw ??= ended;
    auditSequence += 1;
    auditFrames.push({start: auditStart, end: ended, cpuMs: ended - auditStart,
      triangles: geometry.triangles.length / 27, lines: geometry.lines.length / 18});
    if (auditFrames.length > 1024) auditFrames.shift();`);
  result = replaceOnce(result, 'const nextDetailLevel = lodPolicy.levelForZoom(zoomRatio, filtered);',
    'const nextDetailLevel = auditLod || lodPolicy.levelForZoom(zoomRatio, filtered);');
  result = replaceOnce(result, '    const geometry = buildGeometry(timestamp);',
    '    const geometry = buildGeometry(timestamp);\n    const auditGeometryEnd = performance.now();');
  result = replaceOnce(result, '    hitRegions = buildHitRegions();',
    '    const auditDrawEnd = performance.now();\n    hitRegions = buildHitRegions();\n    const auditHitEnd = performance.now();');
  result = replaceOnce(result, 'cpuMs: ended - auditStart,', `cpuMs: ended - auditStart,
      geometryMs: auditGeometryEnd - auditStart, submitMs: auditDrawEnd - auditGeometryEnd,
      hitMs: auditHitEnd - auditDrawEnd, labelsMs: ended - auditHitEnd,`);
  return replaceOnce(result, '  new ResizeObserver(resize).observe(canvas);', `
  globalThis.__METRO_AUDIT__ = {
    configure(options = {}) {
      Object.assign(state, initialCamera);
      state.yaw = cameraPolicy.yaw;
      state.pitch = cameraPolicy.pitch;
      state.selected = null;
      auditLod = options.lod || null;
      state.distance = options.distance || initialCamera.distance / (options.zoom || 1);
      lodCacheKey = '';
      scheduleRender();
    },
    snapshot() {
      const debug = gl.getExtension('WEBGL_debug_renderer_info');
      return {
        renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
        firstDrawSubmittedMs: auditFirstDraw, sequence: auditSequence,
        camera: Object.fromEntries(Object.keys(initialCamera).map(key => [key, state[key]])),
        fittedDistance: initialCamera.distance, lod: currentDetailLevel,
        naturalLod: lodPolicy.levelForZoom(initialCamera.distance / state.distance, false),
        viewport: [viewportWidth, viewportHeight], canvas: [canvas.width, canvas.height],
        counts: {buildings: renderedBuildingIds.size, blocks: renderedAggregateIds.size,
          districts: renderedDistrictIds.size, networks: renderedNetworkIds.size,
          representedFiles: [...renderedAggregateIds].reduce((sum, id) => sum + aggregateFacilities.get(id).memberEntityIds.length, 0)},
        labels: [...document.querySelectorAll('.scene-label')].map(node => node.textContent),
        frames: auditFrames.slice(),
        canvasRect: {x: canvas.getBoundingClientRect().x, y: canvas.getBoundingClientRect().y}
      };
    }
  };
  new ResizeObserver(resize).observe(canvas);`);
}

export class Cdp {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 0;
    this.pending = new Map();
    this.errors = [];
    socket.addEventListener('message', ({data}) => {
      const message = JSON.parse(data);
      if (message.method === 'Runtime.exceptionThrown') this.errors.push(message.params);
      const item = this.pending.get(message.id);
      if (!item) return;
      clearTimeout(item.timer);
      this.pending.delete(message.id);
      if (message.error) item.reject(new Error(JSON.stringify(message.error)));
      else item.resolve(message.result);
    });
    socket.addEventListener('close', () => {
      for (const item of this.pending.values()) {
        clearTimeout(item.timer);
        item.reject(new Error('Browser connection closed'));
      }
      this.pending.clear();
    });
  }
  static async connect(url) {
    const socket = new WebSocket(url);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => { socket.close(); reject(new Error('CDP connect timeout')); }, 10000);
      socket.addEventListener('open', () => { clearTimeout(timer); resolve(); }, {once: true});
      socket.addEventListener('error', () => { clearTimeout(timer); reject(new Error('CDP connect failed')); }, {once: true});
    });
    return new Cdp(socket);
  }
  send(method, params = {}) {
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP timeout: ${method}`));
      }, 30000);
      this.pending.set(id, {resolve, reject, timer});
      try { this.socket.send(JSON.stringify({id, method, params})); }
      catch (error) { clearTimeout(timer); this.pending.delete(id); reject(error); }
    });
  }
  async evaluate(expression) {
    const response = await this.send('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
    if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails));
    return response.result.value;
  }
}

const snapshot = (cdp) => cdp.evaluate('__METRO_AUDIT__.snapshot()');
async function nextDraw(cdp, sequence) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    const result = await snapshot(cdp);
    if (result.sequence > sequence) return result;
    await sleep(10);
  }
  throw new Error('No viewer draw after input');
}
async function configure(cdp, options) {
  const before = await snapshot(cdp);
  await cdp.evaluate(`__METRO_AUDIT__.configure(${JSON.stringify(options)})`);
  return nextDraw(cdp, before.sequence);
}

// Trusted UI events exercise the actual orbit/wheel handlers, one completed draw
// per input. Round trips / compositor / GPU waiting are NOT measured as CPU time.
async function interaction(cdp, kind, samples) {
  let state = await snapshot(cdp);
  const x = Math.round(state.canvasRect.x + state.viewport[0] / 2);
  const y = Math.round(state.canvasRect.y + state.viewport[1] / 2);
  const observed = [];
  if (kind === 'orbit') await cdp.send('Input.dispatchMouseEvent', {type: 'mousePressed', x, y, button: 'left', clickCount: 1});
  try {
    for (let i = 0; i < samples + 5; i++) {
      const before = state;
      const started = await cdp.evaluate('performance.now()');
      await cdp.send('Input.dispatchMouseEvent', kind === 'orbit'
        ? {type: 'mouseMoved', x: x + (i % 2 ? 0 : 4), y, buttons: 1}
        : {type: 'mouseWheel', x, y, deltaX: 0, deltaY: i % 2 ? -12 : 12});
      state = await nextDraw(cdp, before.sequence);
      const frame = state.frames.at(-1);
      const changed = kind === 'orbit' ? state.camera.yaw !== before.camera.yaw : state.camera.distance !== before.camera.distance;
      if (!changed) throw new Error(`${kind} input did not change the camera`);
      if (i >= 5) observed.push({cpuMs: frame.cpuMs, geometryMs: frame.geometryMs,
        submitMs: frame.submitMs, hitMs: frame.hitMs, labelsMs: frame.labelsMs,
        inputToSubmitMs: frame.end - started});
    }
  } finally {
    if (kind === 'orbit') await cdp.send('Input.dispatchMouseEvent', {type: 'mouseReleased', x, y, button: 'left', clickCount: 1});
  }
  return {cpuMs: summarize(observed.map(s => s.cpuMs)),
    stages: Object.fromEntries(['geometryMs', 'submitMs', 'hitMs', 'labelsMs']
      .map(key => [key, summarize(observed.map(s => s[key]))])),
    inputToSubmitMs: summarize(observed.map(s => s.inputToSubmitMs)), samples: observed};
}

export function reportHtml(report) {
  const escape = value => String(value).replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
  const cells = (mode) => report.cases.map((item, index) => {
    const state = mode === 'common-scale' ? item.commonScale : item.views[mode].state;
    return `<figure><h3>Case ${index + 1}</h3><a href="case-${index + 1}/${mode}.png"><img alt="Case ${index + 1}, ${mode}" src="case-${index + 1}/${mode}.png"></a>
      <figcaption>${escape(item.input)}<br>${state.counts.blocks} blocks / ${state.counts.buildings} individual buildings / ${state.counts.networks} routes
      <br>Distance ${state.camera.distance.toFixed(2)}; LOD ${escape(state.lod)}</figcaption></figure>`;
  }).join('');
  const rows = report.cases.flatMap((item, index) => Object.entries(item.views).map(([lod, view]) =>
    `<tr><td>${index + 1}</td><td>${escape(lod)}</td><td>${view.orbit.cpuMs.p95.toFixed(1)}</td><td>${view.wheel.cpuMs.p95.toFixed(1)}</td><td>${view.orbit.inputToSubmitMs.p95.toFixed(1)}</td></tr>`)).join('');
  return `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'unsafe-inline'">
    <title>MetropoGits controlled WebGL comparison</title><style>
    body{font:16px system-ui;background:#0b1220;color:#dce4ef;margin:24px}a{color:#6ed3ff}
    .pair{display:flex;gap:16px}figure{flex:1;min-width:0;margin:0}img{width:100%}figcaption{overflow-wrap:anywhere;color:#a8b8cb;font-size:13px}
    table{border-collapse:collapse}td,th{padding:8px;border:1px solid #445}section{margin:32px 0}
    @media(max-width:900px){.pair{display:block}figure{margin-bottom:20px}}</style>
    <h1>Controlled WebGL comparison</h1><p>1280 × 800, DPR 1, yaw −0.68, pitch 0.62. Synthetic activity off.</p>
    <p>Software SwiftShader. Timings measure JavaScript draw submission, <strong>not GPU completion or display FPS</strong>.
    Input latency includes CDP dispatch and scheduling. Counts are LOD submissions, not on-screen visibility.</p>
    <p><a href="report.json">Raw report, environment, hashes and samples</a>. Local development evidence; do not publish private metadata.</p>
    <table><tr><th>Case</th><th>LOD</th><th>Orbit CPU p95 ms</th><th>Wheel CPU p95 ms</th><th>Orbit input-to-submit p95 ms</th></tr>${rows}</table>
    ${['overview','district','detail','common-scale'].map(mode => `<section><h2>${mode}</h2><p>${mode === 'common-scale'
      ? 'Same absolute camera distance, same overview LOD, each city centered on its own bounds.'
      : `Same fit-relative zoom (${report.policy.normalizedZooms[mode]}×), natural LOD. District/detail intentionally zoom into the city, so cropped edges are expected.`}</p><div class="pair">${cells(mode)}</div></section>`).join('')}
    </html>`;
}

export async function prepare(input, output) {
  await mkdir(join(output, 'assets'), {recursive: true});
  const hashes = {};
  for (const name of ['viewer-3d.js', 'viewer.js', 'viewer-filters.js', 'viewer-activity.js', 'viewer.css']) {
    const bytes = await readFile(join(input, 'assets', name));
    const bundled = await readFile(join(assets, name));
    if (!bytes.equals(bundled)) throw new Error(`Stale or untrusted viewer asset: ${name}; rebuild input first`);
    hashes[name] = sha256(bytes);
    await writeFile(join(output, 'assets', name), name === 'viewer-3d.js' ? instrument(bytes.toString('utf8')) : bytes);
  }
  for (const name of ['index.html', 'assets/viewer-data.js', 'preview.svg']) {
    const bytes = await readFile(join(input, name));
    hashes[name] = sha256(bytes);
    await copyFile(join(input, name), join(output, name));
  }
  for (const name of ['graph.ucg.json', 'city.json', 'manifest.json']) hashes[name] = sha256(await readFile(join(input, name)));
  return hashes;
}

export async function runAudit(browser, output, inputs, samples = 20) {
  // A new directory prevents accidental overwrite of previous captures or inputs.
  await mkdir(output);
  const profile = await mkdtemp(join(tmpdir(), 'metropogits-audit-'));
  const process = spawn(browser, ['--headless=new', '--no-first-run', '--no-default-browser-check',
    `--user-data-dir=${profile}`, '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1',
    '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-background-networking', 'about:blank'],
  {windowsHide: true, stdio: 'ignore'});
  let launchError;
  process.on('error', (error) => { launchError = error; });
  let cdp;
  const report = {version: 'viewer-audit/0.1', environment: {platform: platform(), osRelease: release(),
    cpu: cpus()[0]?.model, node: globalThis.process.version, gpuMode: 'headless SwiftShader (software)',
    profile}, policy: {viewport: [1280, 800], deviceScaleFactor: 1, samples, warmup: 5,
    yaw: -.68, pitch: .62, normalizedZooms: {overview: 1, district: 1.6, detail: 2.5},
    timing: 'JS draw submission CPU and CDP-input-to-submission latency; not GPU completion or FPS'}, cases: []};
  try {
    let port;
    const deadline = Date.now() + 20000;
    while (!port && Date.now() < deadline) {
      if (launchError) throw launchError;
      if (process.exitCode !== null) throw new Error(`Browser exited: ${process.exitCode}`);
      try { port = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; }
      catch { await sleep(100); }
    }
    if (!port) throw new Error('Browser startup timeout');
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    cdp = await Cdp.connect(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
    report.environment.browser = await cdp.send('Browser.getVersion');
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Emulation.setDeviceMetricsOverride', {width: 1280, height: 800, deviceScaleFactor: 1, mobile: false});
    for (const [index, input] of inputs.entries()) {
      const directory = join(output, `case-${index + 1}`);
      const hashes = await prepare(input, directory);
      await cdp.send('Page.navigate', {url: pathToFileURL(join(directory, 'index.html')).href});
      const deadline = Date.now() + 30000;
      while (!(await cdp.evaluate('Boolean(globalThis.__METRO_AUDIT__?.snapshot().firstDrawSubmittedMs)'))) {
        if (Date.now() > deadline) throw new Error('Viewer failed to initialize (WebGL required)');
        await sleep(100);
      }
      const initial = await snapshot(cdp);
      const result = {input, hashes, initial, views: {}};
      report.cases.push(result);
      console.log(`Loaded case ${index + 1}: ${initial.firstDrawSubmittedMs.toFixed(1)} ms to first draw submission`);
      for (const [lod, zoom] of Object.entries(report.policy.normalizedZooms)) {
        const state = await configure(cdp, {zoom});
        if (state.lod !== lod) throw new Error(`Natural LOD mismatch: expected ${lod}, got ${state.lod}`);
        const png = await cdp.send('Page.captureScreenshot', {format: 'png'});
        await writeFile(join(directory, `${lod}.png`), Buffer.from(png.data, 'base64'));
        const orbit = await interaction(cdp, 'orbit', samples);
        await configure(cdp, {zoom});
        const wheel = await interaction(cdp, 'wheel', samples);
        result.views[lod] = {state, orbit, wheel};
        console.log(`  ${lod}: orbit CPU p95=${orbit.cpuMs.p95.toFixed(1)} ms`);
      }
    }
    const distance = Math.max(...report.cases.map(c => c.initial.fittedDistance));
    report.policy.commonDistance = distance;
    // Exact common world scale, same LOD; no resize or repacking of city data.
    for (const [index, result] of report.cases.entries()) {
      const directory = join(output, `case-${index + 1}`);
      await cdp.send('Page.navigate', {url: pathToFileURL(join(directory, 'index.html')).href});
      const deadline = Date.now() + 30000;
      while (!(await cdp.evaluate('Boolean(globalThis.__METRO_AUDIT__?.snapshot().firstDrawSubmittedMs)'))) {
        if (Date.now() > deadline) throw new Error('Viewer reload timeout');
        await sleep(100);
      }
      result.commonScale = await configure(cdp, {distance, lod: 'overview'});
      const png = await cdp.send('Page.captureScreenshot', {format: 'png'});
      await writeFile(join(directory, 'common-scale.png'), Buffer.from(png.data, 'base64'));
    }
    if (cdp.errors.length) throw new Error(`Browser exceptions: ${JSON.stringify(cdp.errors)}`);
    await writeFile(join(output, 'report.json'), JSON.stringify(report, null, 2));
    await writeFile(join(output, 'index.html'), reportHtml(report));
    return report;
  } finally {
    if (cdp) {
      try { await cdp.send('Browser.close'); } catch { /* Connection closes during shutdown. */ }
      cdp.socket.close();
    }
    // Only terminate the browser process this invocation owns. Keep its isolated
    // profile for failure diagnosis; never delete user browser/workspace data.
    if (process.exitCode === null) process.kill();
  }
}

if (globalThis.process.argv[1] && import.meta.url === pathToFileURL(resolve(globalThis.process.argv[1])).href) {
  const [browser, output, ...inputs] = globalThis.process.argv.slice(2);
  if (!browser || !output || !inputs.length) {
    console.error('Usage: node scripts/viewer_audit.mjs <chrome-executable> <new-output-directory> <built-city-directory> [...]');
    globalThis.process.exitCode = 2;
  } else {
    runAudit(resolve(browser), resolve(output), inputs.map(p => resolve(p))).catch(error => {
      console.error(error);
      globalThis.process.exitCode = 1;
    });
  }
}
