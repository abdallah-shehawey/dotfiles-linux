#!/usr/bin/env python3
"""Read or change the resolution and full-screen flag in a PES settings.dat.

PES 2019 and PES 2021 keep their screen settings in
  ~/Documents/KONAMI/<game folder>/settings.dat
(Wine links the prefix's Documents to ~/Documents). The game's own Settings.exe
cannot list resolutions under Wine, so this edits the file directly.

Layout (measured on this laptop, Nov 2026):
  0x00  "WECF" magic
  0x04  size field (0x68 in PES 2019, 0x6b in PES 2021)
  0x08  flags, bit 0 = full screen
  0x0c  width  (little-endian uint32)
  0x10  height (little-endian uint32)
File sizes seen: PES 2019 = 352 bytes (a 104-byte file is read and rejected:
the game falls back to 1920x1080 windowed), PES 2021 = 612 bytes.
If the file does not exist yet, start the game once (or run its Settings.exe
and press OK) so it writes one, then edit it with this.

Usage:
  pes-settings-dat.py show FILE
  pes-settings-dat.py set FILE --width 2560 --height 1440 [--fullscreen on|off]

"set" copies FILE to FILE.bak-<date> first and changes only those fields.
"""
import shutil
import struct
import sys
import time

KNOWN_SIZES = {352: "PES 2019", 612: "PES 2021"}


def load(path):
    with open(path, "rb") as f:
        data = bytearray(f.read())
    if data[:4] != b"WECF":
        sys.exit(f"{path}: not a PES settings.dat (no WECF magic), not touching it")
    if len(data) < 0x14:
        sys.exit(f"{path}: too short ({len(data)} bytes)")
    return data


def show(path):
    data = load(path)
    flags, width, height = struct.unpack_from("<III", data, 0x08)
    game = KNOWN_SIZES.get(len(data), "unknown size, maybe a file the game rejects")
    print(f"file:       {path}")
    print(f"size:       {len(data)} bytes ({game})")
    print(f"flags:      0x{flags:x} (full screen: {'on' if flags & 1 else 'off'})")
    print(f"resolution: {width}x{height}")


def arg(args, name):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return None


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[0] not in ("show", "set"):
        sys.exit(__doc__)
    cmd, path = args[0], args[1]
    if cmd == "show":
        show(path)
        return
    data = load(path)
    if len(data) not in KNOWN_SIZES:
        sys.exit(f"{path}: {len(data)} bytes is not a size the game accepts "
                 f"({', '.join(f'{s} = {g}' for s, g in KNOWN_SIZES.items())}). "
                 "Let the game or its Settings.exe write a fresh file first.")
    width, height, full = arg(args, "--width"), arg(args, "--height"), arg(args, "--fullscreen")
    if not (width or height or full):
        sys.exit("nothing to change: give --width/--height and/or --fullscreen on|off")
    backup = f"{path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(path, backup)
    if width:
        struct.pack_into("<I", data, 0x0c, int(width))
    if height:
        struct.pack_into("<I", data, 0x10, int(height))
    if full:
        flags = struct.unpack_from("<I", data, 0x08)[0]
        flags = flags | 1 if full == "on" else flags & ~1
        struct.pack_into("<I", data, 0x08, flags)
    with open(path, "wb") as f:
        f.write(data)
    print(f"backup:     {backup}")
    show(path)


if __name__ == "__main__":
    main()
