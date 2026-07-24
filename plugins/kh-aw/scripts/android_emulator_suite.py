#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def run(command: list[str], *, timeout: int = 60, check: bool = False, stdout=None):
    completed = subprocess.run(command, text=stdout is None, capture_output=stdout is None, timeout=timeout, stdout=stdout)
    if check and completed.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}\n{getattr(completed, 'stdout', '')}\n{getattr(completed, 'stderr', '')}")
    return completed


def main() -> int:
    parser = argparse.ArgumentParser(description="Boot and inspect an Android emulator without installing an APK")
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--avd")
    parser.add_argument("--serial", default="emulator-5554")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    run_root = Path(args.run_root).resolve()
    out = run_root / "test" / "android-emulator"
    out.mkdir(parents=True, exist_ok=True)
    emulator = shutil.which("emulator")
    adb = shutil.which("adb")
    if not emulator or not adb:
        raise RuntimeError("emulator and adb must both be installed")
    listed = run([emulator, "-list-avds"], timeout=30, check=True)
    avds = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
    avd = args.avd or (avds[0] if avds else "")
    if not avd:
        raise RuntimeError("no Android Virtual Device exists")
    process = None
    started_here = False
    result = {"schemaVersion": "3.0", "avd": avd, "serial": args.serial, "apkInstallExcluded": True, "commands": [], "pass": False}
    try:
        devices = run([adb, "devices"], timeout=20, check=True).stdout
        if args.serial not in devices:
            log = (out / "emulator-process.log").open("w", encoding="utf-8")
            command = [emulator, "-avd", avd, "-no-window", "-no-audio", "-no-boot-anim", "-gpu", "swiftshader_indirect", "-no-snapshot-save"]
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True)
            started_here = True
            result["commands"].append({"command": command, "pid": process.pid})
        deadline = time.monotonic() + args.timeout
        booted = False
        while time.monotonic() < deadline:
            try:
                devices = run([adb, "devices"], timeout=10).stdout
                if args.serial in devices:
                    boot = run([adb, "-s", args.serial, "shell", "getprop", "sys.boot_completed"], timeout=10).stdout.strip()
                    if boot == "1":
                        booted = True
                        break
            except Exception:
                pass
            time.sleep(3)
        if not booted:
            raise RuntimeError("emulator did not finish booting")
        props = run([adb, "-s", args.serial, "shell", "getprop"], timeout=30, check=True).stdout
        size = run([adb, "-s", args.serial, "shell", "wm", "size"], timeout=20, check=True).stdout
        density = run([adb, "-s", args.serial, "shell", "wm", "density"], timeout=20, check=True).stdout
        packages = run([adb, "-s", args.serial, "shell", "pm", "list", "packages"], timeout=30, check=True).stdout
        logcat = run([adb, "-s", args.serial, "logcat", "-d", "-v", "threadtime", "*:E"], timeout=30).stdout
        (out / "properties.txt").write_text(props, encoding="utf-8")
        (out / "display.txt").write_text(size + "\n" + density, encoding="utf-8")
        (out / "packages.txt").write_text(packages, encoding="utf-8")
        (out / "logcat-errors.txt").write_text(logcat, encoding="utf-8")
        screenshot = out / "system-screenshot.png"
        with screenshot.open("wb") as stream:
            completed = subprocess.run([adb, "-s", args.serial, "exec-out", "screencap", "-p"], stdout=stream, timeout=30)
        if completed.returncode != 0 or screenshot.stat().st_size < 1000:
            raise RuntimeError("failed to capture emulator system screenshot")
        result.update({
            "booted": True,
            "display": (size + " " + density).strip(),
            "propertiesPath": str(out / "properties.txt"),
            "logcatPath": str(out / "logcat-errors.txt"),
            "screenshotPath": str(screenshot),
            "pass": True,
            "note": "No APK was installed. This suite verifies SDK/AVD/ADB/emulator health only.",
        })
    finally:
        if started_here:
            try:
                run([adb, "-s", args.serial, "emu", "kill"], timeout=20)
            except Exception:
                if process is not None:
                    process.terminate()
        (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
