#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { chromium, firefox, webkit } from 'playwright';
import AxeBuilder from '@axe-core/playwright';

function args() {
  const out = {};
  for (let i = 2; i < process.argv.length; i += 1) {
    const key = process.argv[i];
    if (!key.startsWith('--')) continue;
    const name = key.slice(2);
    const value = process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[++i] : true;
    out[name] = value;
  }
  return out;
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function writeJson(file, value) { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n'); }
function slug(value) { return String(value || 'page').toLowerCase().replace(/[^a-z0-9가-힣]+/g, '-').replace(/^-|-$/g, '') || 'page'; }

const opt = args();
const runRoot = path.resolve(String(opt['run-root'] || ''));
const baseUrl = String(opt['base-url'] || '').replace(/\/$/, '');
const browserName = String(opt.browser || 'chromium');
if (!runRoot || !baseUrl) throw new Error('--run-root and --base-url are required');
const browserType = { chromium, firefox, webkit }[browserName];
if (!browserType) throw new Error(`unsupported browser ${browserName}`);
const inventory = readJson(path.join(runRoot, 'design', 'page-inventory.json'));
const pages = Array.isArray(inventory.pages) ? inventory.pages : [];
if (!pages.length) throw new Error('page inventory is empty');
const outDir = path.join(runRoot, 'test', 'browser', browserName);
fs.mkdirSync(outDir, { recursive: true });
const viewports = [
  { id: 'mobile', width: 390, height: 844 },
  { id: 'tablet', width: 768, height: 1024 },
  { id: 'desktop', width: 1440, height: 1000 },
];
const browser = await browserType.launch({ headless: true });
const result = { schemaVersion: '3.0', browser: browserName, baseUrl, startedAt: new Date().toISOString(), pages: [], summary: {} };
let hardFailures = 0;
try {
  for (let index = 0; index < pages.length; index += 1) {
    const p = pages[index];
    const pageId = String(p.pageId || `page-${index + 1}`);
    let route = String(p.route || p.url || p.path || (index === 0 ? '/' : `/${pageId}`));
    const url = /^https?:\/\//i.test(route) ? route : `${baseUrl}${route.startsWith('/') ? '' : '/'}${route}`;
    const pageResult = { pageId, route, url, viewports: [], consoleErrors: [], pageErrors: [], requestFailures: [], badResponses: [], brokenImages: [], axe: [] };
    for (const viewport of viewports) {
      const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, reducedMotion: 'no-preference' });
      const page = await context.newPage();
      page.on('console', msg => { if (msg.type() === 'error') pageResult.consoleErrors.push({ viewport: viewport.id, text: msg.text() }); });
      page.on('pageerror', err => pageResult.pageErrors.push({ viewport: viewport.id, text: String(err) }));
      page.on('requestfailed', req => pageResult.requestFailures.push({ viewport: viewport.id, url: req.url(), failure: req.failure() }));
      page.on('response', response => { if (response.status() >= 400) pageResult.badResponses.push({ viewport: viewport.id, url: response.url(), status: response.status() }); });
      let navigationStatus = 0;
      try {
        const response = await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
        navigationStatus = response?.status() || 0;
        await page.waitForTimeout(500);
      } catch (error) {
        pageResult.pageErrors.push({ viewport: viewport.id, text: `navigation: ${String(error)}` });
      }
      const broken = await page.locator('img').evaluateAll(images => images.filter(img => !img.complete || img.naturalWidth === 0).map(img => ({ src: img.currentSrc || img.src, alt: img.alt })));
      pageResult.brokenImages.push(...broken.map(item => ({ viewport: viewport.id, ...item })));
      const axe = await new AxeBuilder({ page }).analyze();
      const severe = axe.violations.filter(v => ['critical', 'serious'].includes(v.impact || ''));
      pageResult.axe.push({ viewport: viewport.id, violationCount: axe.violations.length, severeCount: severe.length, violations: axe.violations });
      const motion = await page.evaluate(() => ({
        animationCount: document.getAnimations().length,
        reducedMotionQuery: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        title: document.title,
      }));
      const screenshot = path.join(outDir, `${slug(pageId)}-${viewport.id}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      const failures = pageResult.consoleErrors.length + pageResult.pageErrors.length + pageResult.requestFailures.length + pageResult.badResponses.length + pageResult.brokenImages.length + severe.length + (motion.scrollWidth > motion.clientWidth + 2 ? 1 : 0) + (navigationStatus >= 400 || navigationStatus === 0 ? 1 : 0);
      if (failures) hardFailures += failures;
      pageResult.viewports.push({ ...viewport, navigationStatus, screenshot, motion, pass: failures === 0 });
      await context.close();
    }
    result.pages.push(pageResult);
  }
} finally {
  await browser.close();
}
result.finishedAt = new Date().toISOString();
result.summary = { pageCount: result.pages.length, viewportCount: result.pages.length * viewports.length, hardFailures, pass: hardFailures === 0 };
const resultFile = path.join(outDir, 'result.json');
writeJson(resultFile, result);
console.log(JSON.stringify({ resultFile, ...result.summary }, null, 2));
process.exit(hardFailures === 0 ? 0 : 1);
