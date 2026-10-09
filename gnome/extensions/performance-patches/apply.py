#!/usr/bin/env python3
"""Put the performance patches on the installed extensions, or take them off.

    apply.py            patch every file that is still the exact upstream original
    apply.py --check    report only
    apply.py --restore  put the upstream original back where our patch is installed

A file is replaced only when its sha256 equals the original or the patched copy
kept here. Anything else means the extension was updated: it is reported as
SKIPPED and left alone, and the patch has to be redone against the new version.
GNOME loads extension code once per session, so changes show after a log out.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTENSIONS = Path.home() / ".local/share/gnome-shell/extensions"
FILES = [
    "blur-my-shell@aunetx/components/appfolders.js",
    "app-grid-tuner@m-lab/extension.js",
    "runcat@kolesnikov.se/indicator.js",
    "system-monitor@gnome-shell-extensions.gcampax.github.com/extension.js",
    "Vitals@CoreCoding.com/sensors.js",
]

check = "--check" in sys.argv
restore = "--restore" in sys.argv
digest = lambda b: hashlib.sha256(b).hexdigest()
failed = changed = False

for relative in FILES:
    target = EXTENSIONS / relative
    original = (HERE / "original" / relative).read_bytes()
    patched = (HERE / "patched" / relative).read_bytes()
    want, other = (original, patched) if restore else (patched, original)
    if not target.exists():
        print(f"  {relative}: not installed")
        continue
    current = target.read_bytes()
    if current == want:
        print(f"  {relative}: ok")
    elif digest(current) == digest(other):
        if check:
            print(f"* {relative}: {'patched' if restore else 'NOT patched'}")
            failed = True
            continue
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_bytes(want)
        temporary.chmod(target.stat().st_mode & 0o777)
        temporary.replace(target)
        print(f"* {relative}: {'restored' if restore else 'patched'}")
        changed = True
    else:
        print(f"! {relative}: SKIPPED, the extension was updated; redo the patch against it")
        failed = True

if changed:
    print("\nLog out and back in to load the changed code.")
sys.exit(1 if failed else 0)
