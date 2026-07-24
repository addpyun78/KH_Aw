#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import lighthouse from 'lighthouse';
import * as chromeLauncher from 'chrome-launcher';
import { chromium } from 'playwright';
function args(){const o={};for(let i=2;i<process.argv.length;i++){if(!process.argv[i].startsWith('--'))continue;const k=process.argv[i].slice(2);o[k]=process.argv[i+1]&&!process.argv[i+1].startsWith('--')?process.argv[++i]:true;}return o;}
const opt=args();const runRoot=path.resolve(String(opt['run-root']||''));const url=String(opt.url||'');if(!runRoot||!url)throw new Error('--run-root and --url required');
const chrome=await chromeLauncher.launch({chromePath: chromium.executablePath(), chromeFlags:['--headless','--no-sandbox','--disable-gpu']});let lhr;try{const res=await lighthouse(url,{port:chrome.port,output:'json',logLevel:'error'});lhr=res.lhr;}finally{await chrome.kill();}
const scores={};for(const id of ['performance','accessibility','best-practices','seo'])scores[id]=Math.round((lhr.categories[id]?.score||0)*100);
const thresholds={performance:Number(opt.performance||70),accessibility:Number(opt.accessibility||90),'best-practices':Number(opt['best-practices']||85),seo:Number(opt.seo||80)};
const failures=Object.entries(thresholds).filter(([id,min])=>scores[id]<min);const outDir=path.join(runRoot,'test','lighthouse');fs.mkdirSync(outDir,{recursive:true});fs.writeFileSync(path.join(outDir,'report.json'),JSON.stringify(lhr,null,2)+'\n');fs.writeFileSync(path.join(outDir,'summary.json'),JSON.stringify({url,scores,thresholds,failures,pass:failures.length===0},null,2)+'\n');console.log(JSON.stringify({scores,thresholds,failures},null,2));process.exit(failures.length===0?0:1);
