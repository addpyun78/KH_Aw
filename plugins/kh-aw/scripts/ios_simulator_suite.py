#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, subprocess, time
from pathlib import Path

def run(cmd, timeout=120, check=True):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    if check and p.returncode!=0: raise RuntimeError(f"{' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',required=True);ap.add_argument('--device');ap.add_argument('--timeout',type=int,default=180);a=ap.parse_args()
    root=Path(a.run_root).resolve();out=root/'test'/'ios-simulator';out.mkdir(parents=True,exist_ok=True)
    if not shutil.which('xcrun') or not shutil.which('xcodebuild'): raise RuntimeError('xcrun and xcodebuild are required on macOS')
    devices=json.loads(run(['xcrun','simctl','list','devices','available','--json']).stdout)
    candidates=[]
    for runtime,items in devices.get('devices',{}).items():
        for item in items:
            if item.get('isAvailable'): candidates.append(item)
    chosen=next((x for x in candidates if a.device and (x.get('name')==a.device or x.get('udid')==a.device)), candidates[0] if candidates else None)
    if not chosen: raise RuntimeError('no available iOS simulator')
    udid=chosen['udid'];run(['xcrun','simctl','boot',udid],check=False);run(['xcrun','simctl','bootstatus',udid,'-b'],timeout=a.timeout)
    shot=out/'simulator-home.png';run(['xcrun','simctl','io',udid,'screenshot',str(shot)])
    info=run(['xcrun','simctl','list','devices',udid]).stdout;(out/'device.txt').write_text(info,encoding='utf-8')
    result={'schemaVersion':'3.0','device':chosen,'screenshotPath':str(shot),'pass':shot.is_file() and shot.stat().st_size>1000,'note':'Simulator health evidence. App build/UI tests are recorded separately.'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');run(['xcrun','simctl','shutdown',udid],check=False);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['pass'] else 1
if __name__=='__main__': raise SystemExit(main())
