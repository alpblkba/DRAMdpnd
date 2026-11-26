#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { spawn, spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const stage = process.argv[2];
if (!stage || !fs.statSync(stage, { throwIfNoEntry: false })?.isDirectory()) {
  console.error('record_browser_demos: pass an existing staging directory');
  process.exit(2);
}
const { chromium } = require(path.join(root, '.venv/playwright/node_modules/playwright'));
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const browserOptions = { headless: true };
if (process.env.DRAMDPD_CHROMIUM) browserOptions.executablePath = process.env.DRAMDPD_CHROMIUM;

async function record(name, action) {
  console.log(`${name}: opening headless Chromium`);
  const browser = await chromium.launch(browserOptions);
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: stage, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();
  console.log(`${name}: recording browser interaction`);
  try {
    await action(page);
    await page.screenshot({ path: path.join(stage, `${name}-final.png`) });
  } finally {
    await context.close();
    await browser.close();
  }
  fs.renameSync(await page.video().path(), path.join(stage, `${name}.webm`));
  console.log(`${name}: recorded genuine browser interaction`);
}

async function workbench(page) {
  const file = path.join(root, 'runs/workbench/index.html');
  if (!fs.existsSync(file)) throw new Error('generate the workbench with ./bin/dramdpnd ui --no-open first');
  await page.goto(pathToFileURL(file).href);
  await page.getByText('Simulator backends').waitFor();
  await delay(1200);
  await page.getByRole('button', { name: 'Run history' }).click();
  await page.locator('#run-artifact').selectOption('wmb');
  await page.locator('#run-status').selectOption('VALID');
  await page.locator('#run-body tr[data-id]').first().waitFor();
  await delay(1000);
  await page.evaluate(() => {
    document.querySelector('#run-body tr[data-id]').click();
    document.querySelector('[data-view="observations"]').click();
  });
  await page.getByRole('heading', { name: 'Native command distribution' }).waitFor();
  await delay(1800);
  await page.getByRole('button', { name: 'Dependability lab' }).click();
  await page.getByRole('heading', { name: 'Measurement definitions' }).scrollIntoViewIfNeeded();
  await delay(1500);
  await page.getByRole('button', { name: 'Run history' }).click();
  await page.locator('#run-artifact').selectOption('qprac');
  await page.locator('#run-status').selectOption('VALID');
  await page.locator('#run-body tr[data-id]').first().waitFor();
  await delay(1000);
  await page.evaluate(() => {
    document.querySelector('#run-body tr[data-id]').click();
    document.querySelector('[data-view="observations"]').click();
  });
  await page.getByRole('heading', { name: 'Native command distribution' }).waitFor();
  await delay(1700);
  await page.getByRole('button', { name: 'Dependability lab' }).click();
  await page.getByRole('heading', { name: 'Measurement definitions' }).scrollIntoViewIfNeeded();
  await delay(1800);
}

function verifiedRamulatorRun() {
  const code = 'import sys;sys.path.insert(0,"scripts");from evidence import discover,verify;from pathlib import Path;print(next(str(p) for p in discover() if p.parent.name=="ramulator" and verify(p)["status"]=="VALID" and any(p.glob("*.ram2bin"))))';
  const result = spawnSync('python3', ['-c', code], { cwd: root, encoding: 'utf8' });
  if (result.status !== 0) throw new Error('no validated upstream RAM2BIN run is available');
  return result.stdout.trim();
}

function startRamViz(traceDirectory) {
  const code = 'import sys;sys.path.insert(0,"external/ramulator2/python");from ramulator.visualizer import VisualizerServer;s=VisualizerServer(traces=sys.argv[1]);s.start();print("DEMO_URL="+s.link,flush=True);s.wait()';
  const child = spawn('python3', ['-u', '-c', code, traceDirectory], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, RAMULATOR_VISUALIZER_PORT: '33127' } });
  const ready = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('RamViz did not start within 60 seconds')), 60000);
    let output = '';
    child.stdout.on('data', bytes => {
      output += bytes.toString();
      const link = output.match(/^DEMO_URL=(.+)$/m);
      if (link) {
        clearTimeout(timeout);
        resolve(link[1]);
      }
    });
    child.stderr.resume();
    child.on('exit', () => { clearTimeout(timeout); reject(new Error('RamViz exited before becoming ready')); });
    child.on('error', error => { clearTimeout(timeout); reject(error); });
  });
  return { child, ready };
}

async function ramviz(page, url) {
  await page.goto(url);
  await page.getByText('trace.ch0.ram2bin').waitFor();
  await delay(900);
  await page.getByText('trace.ch0.ram2bin').click();
  await page.getByText('Timing parameters').waitFor();
  await delay(1100);
  await page.getByRole('button', { name: /Continue/ }).click();
  await page.getByText('VISIBLE WINDOW').waitFor();
  await page.getByRole('region', { name: 'Bank state' }).waitFor();
  await delay(1900);
  await page.getByRole('treeitem', { name: 'Bank 0' }).first().click();
  await page.getByText('Banks counted').waitFor();
  await page.getByText('same-group column command').waitFor();
  await delay(2100);
  await page.getByText('same-group column command').scrollIntoViewIfNeeded();
  await delay(1700);
}

(async () => {
  await record('workbench', workbench);
  const server = startRamViz(verifiedRamulatorRun());
  try {
    const url = await server.ready;
    await record('ramviz', page => ramviz(page, url));
  } finally {
    server.child.kill('SIGINT');
  }
})().catch(error => { console.error(`record_browser_demos: ${error.message}`); process.exitCode = 1; });
