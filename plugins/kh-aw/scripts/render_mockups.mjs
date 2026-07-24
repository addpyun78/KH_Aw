#!/usr/bin/env node
import { readFile } from 'node:fs/promises';
import { resolve, isAbsolute, join } from 'node:path';
import { pathToFileURL } from 'node:url';

function arg(name, fallback = '') {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
const runRoot = resolve(arg('--run-root', '.'));
const ledgerPath = join(runRoot, 'design', 'design-ledger.json');
const ledger = JSON.parse(await readFile(ledgerPath, 'utf8'));
let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch (error) {
  console.error('Playwright is not installed. Run npm install in the KH_Aw plugin directory, then retry.');
  process.exit(2);
}
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const results = [];
for (const pageSpec of ledger.pages || []) {
  const mockup = isAbsolute(pageSpec.mockupPath) ? pageSpec.mockupPath : join(runRoot, pageSpec.mockupPath);
  const screenshot = isAbsolute(pageSpec.screenshotPath) ? pageSpec.screenshotPath : join(runRoot, pageSpec.screenshotPath);
  const page = await context.newPage();
  await page.goto(pathToFileURL(mockup).href, { waitUntil: 'networkidle' });
  await page.screenshot({ path: screenshot, fullPage: true });
  results.push({ pageId: pageSpec.pageId, mockup, screenshot });
  await page.close();
}
const board = ledger.visualStructureBoard || {};
if (board.htmlPath && board.imagePath) {
  const html = isAbsolute(board.htmlPath) ? board.htmlPath : join(runRoot, board.htmlPath);
  const image = isAbsolute(board.imagePath) ? board.imagePath : join(runRoot, board.imagePath);
  const page = await context.newPage();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(pathToFileURL(html).href, { waitUntil: 'networkidle' });
  await page.screenshot({ path: image, fullPage: true });
  results.push({ pageId: '__board__', mockup: html, screenshot: image });
  await page.close();
}
await browser.close();
console.log(JSON.stringify({ ok: true, count: results.length, results }, null, 2));
