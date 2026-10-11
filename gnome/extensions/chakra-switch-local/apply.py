#!/usr/bin/env python3
"""Restore reviewed local Chakra sources without overwriting unknown upstream changes."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

LOCAL = Path(__file__).resolve().parent
EXT = Path.home() / ".local/share/gnome-shell/extensions/chakra-switch@narkagni"
SCHEMA = "org.gnome.shell.extensions.chakra-switch"
CHECK = "--check" in sys.argv
KNOWN = json.loads((LOCAL / "known-sources.json").read_text())
failed = False
changed = False
ours = set()
schemadir = EXT / "schemas"


def compiled_has_keys(xml):
    """True when gschemas.compiled already knows every key the XML declares."""
    declared = set(re.findall(r'<key name="([^"]+)"', xml.decode()))
    result = subprocess.run(["gsettings", "--schemadir", str(schemadir), "list-keys", SCHEMA],
                            capture_output=True, text=True)
    return result.returncode == 0 and declared <= set(result.stdout.split())


for name, entry in KNOWN.items():
    target = EXT / entry.get("path", f"src/{name}")
    snapshot = LOCAL / entry["snapshot"]
    if not target.exists() or not snapshot.exists():
        print(f"! {name}: missing source or snapshot")
        failed = True
        continue
    # Code that reads our schema keys must never run against upstream's schema.
    if entry.get("needs") and entry["needs"] not in ours:
        print(f"! {name}: held back until {entry['needs']} is ours")
        failed = True
        continue
    current, desired = target.read_bytes(), snapshot.read_bytes()
    if current == desired:
        print(f"  {name}: ok")
    elif hashlib.sha256(current).hexdigest() in entry["accepted"]:
        if CHECK:
            print(f"* {name}: MISSING local fixes")
            failed = True
            continue
        # Replace only the reviewed upstream or previous local version.
        temporary = target.with_name(target.name + ".local-tmp")
        temporary.write_bytes(desired)
        temporary.chmod(target.stat().st_mode & 0o777)
        temporary.replace(target)
        print(f"* {name}: applied")
        changed = True
    else:
        print(f"! {name}: SKIPPED unknown source; review upstream changes")
        failed = True
        continue
    if target.parent == schemadir and not compiled_has_keys(desired):
        if CHECK:
            print(f"* {name}: gschemas.compiled is stale")
            failed = True
            continue
        subprocess.run(["glib-compile-schemas", str(schemadir)], check=True)
        print(f"* {name}: compiled")
        changed = True
    ours.add(name)

keys = ["open-in-overview", "stagger-gap-ms", "ease-duration-ms", "focus-duration-ms",
        "peek-show-duration-ms", "peek-hide-duration-ms", "peek-opacity"]
values = []
for key in keys:
    result = subprocess.run(["gsettings", "--schemadir", str(schemadir),
                             "get", SCHEMA, key], capture_output=True, text=True)
    values.append(f"{key}={result.stdout.strip() if result.returncode == 0 else '<unavailable>'}")
print("\nsettings (yours, untouched): " + "  ".join(values))
if changed:
    print("\nSaved fixes installed. The running shell needs a reload or the next login to load them.")
sys.exit(1 if failed else 0)
