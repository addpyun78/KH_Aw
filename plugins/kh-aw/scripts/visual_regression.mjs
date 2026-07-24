#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import pixelmatch from 'pixelmatch';
import { PNG } from 'pngjs';
function args(){const o={};for(let i=2;i<process.argv.length;i++){if(!process.argv[i].startsWith('--'))continue;const k=process.argv[i].slice(2);o[k]=process.argv[i+1]&&!process.argv[i+1].startsWith('--')?process.argv[++i]:true;}return o;}
function read(f){return JSON.parse(fs.readFileSync(f,'utf8'));}
function write(f,v){fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,JSON.stringify(v,null,2)+'\n');}
function resolveRun(root,p){return path.isAbsolute(p)?p:path.join(root,p);}
const opt=args();const runRoot=path.resolve(String(opt['run-root']||''));const browser=String(opt.browser||'chromium');const threshold=Number(opt.threshold||0.35);
const design=read(path.join(runRoot,'design','design-ledger.json'));const browserResult=read(path.join(runRoot,'test','browser',browser,'result.json'));
const actualMap=new Map(browserResult.pages.map(p=>[String(p.pageId),p.viewports.find(v=>v.id==='mobile')?.screenshot]));
const outDir=path.join(runRoot,'test','visual-regression');fs.mkdirSync(outDir,{recursive:true});const checks=[];let failed=0;
for(const page of design.pages||[]){const pageId=String(page.pageId||'');const expected=resolveRun(runRoot,String(page.screenshotPath||''));const actual=actualMap.get(pageId);if(!expected||!actual||!fs.existsSync(expected)||!fs.existsSync(actual)){checks.push({pageId,pass:false,error:'missing expected or actual screenshot'});failed++;continue;}
 const a=PNG.sync.read(fs.readFileSync(expected));const b=PNG.sync.read(fs.readFileSync(actual));const width=Math.min(a.width,b.width),height=Math.min(a.height,b.height);const diff=new PNG({width,height});
 const aa={data:a.data,width:a.width,height:a.height};const bb={data:b.data,width:b.width,height:b.height};
 let mismatch=1;if(a.width===b.width&&a.height===b.height){const pixels=pixelmatch(aa.data,bb.data,diff.data,width,height,{threshold:0.15});mismatch=pixels/(width*height);}const diffPath=path.join(outDir,`${pageId||'page'}-diff.png`);fs.writeFileSync(diffPath,PNG.sync.write(diff));const pass=mismatch<=threshold;if(!pass)failed++;checks.push({pageId,expected,actual,diffPath,mismatchRatio:mismatch,allowedRatio:threshold,pass});}
const result={schemaVersion:'3.0',browser,threshold,checks,pass:failed===0,failed};const resultFile=path.join(outDir,'result.json');write(resultFile,result);console.log(JSON.stringify({resultFile,failed},null,2));process.exit(failed===0?0:1);
