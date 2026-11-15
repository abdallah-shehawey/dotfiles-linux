#!/usr/bin/env python3
"""Fix PES 2019's ~45 s white screen at start under Wine.

Cause: during start-up the protection code keeps a context on the main thread's
stack and updates two fields of it with locked xchg instructions. Under Wine the
stack lands so that both fields sit on byte 63 of a cache line, so every xchg is
a split lock (a bus lock): about 40,000 a second, IPC 0.01, ~41 s of CPU.
Where the stack lands depends on Wine's own start-up frames, so Windows does not
hit this.

Fix: the exe's entry point is a small page-touching stub (section .trace) that
ends in a jmp to the real entry. This rewrites it to call the real entry with the
stack moved down by SHIFT bytes, so the fields are no longer split. Only those
0x44 bytes change; the original bytes are checked before patching and restored
by "revert".

Measured (seconds until the game's first frame): on P-cores 47 original,
40 / 31 / 29 with shift 16 / 32 / 48; with start-up on the E-cores
(pes2019-cores.py) 15.5 original, 12.7 with shift 48. The game reached the title
screen in every test.

Usage: pes2019-stack-fix.py status | apply [16|32|48] | revert
"""
import os
import sys

# <games folder>/PES-2019/PES2019.exe, next to this script's common/ folder
EXE = os.environ.get("PES2019_EXE") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "PES-2019", "PES2019.exe")
OFFSET = 0x1173A220  # file offset of VA 0x151B3B020 (AddressOfEntryPoint)

ORIG = bytes.fromhex(
    "488da424d8ffffff505152803dceffffff007523488d05c54f4cee488d0d22000000"
    "488b104805001000004839c87cf2c605a9ffffff015a5958488d642428e99cefffff")
COMMON = ("4883ec28505152803dd2ffffff007523488d05c94f4cee488d0d26000000"
          "488b104805001000004839c87cf2c605adffffff015a5958")
STUBS = {
    16: bytes.fromhex(COMMON + "4883c420e8a1efffff4883c408c3"),
    32: bytes.fromhex(COMMON + "4883c410e8a1efffff4883c418c3"),
    48: bytes.fromhex(COMMON + "e8a5efffff4883c428c390909090"),
}
assert len(ORIG) == 0x44 and all(len(s) == 0x44 for s in STUBS.values())


def current():
    with open(EXE, "rb") as f:
        f.seek(OFFSET)
        data = f.read(0x44)
    if data == ORIG:
        return "original"
    for shift, stub in STUBS.items():
        if data == stub:
            return f"patched (stack shift {shift})"
    return "unknown"


def write(data):
    with open(EXE, "r+b") as f:
        f.seek(OFFSET)
        f.write(data)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if not os.path.isfile(EXE):
        sys.exit(f"no game exe at {EXE} (set PES2019_EXE to its path)")
    state = current()
    if state == "unknown":
        sys.exit(f"{EXE}: entry bytes are neither original nor a known patch, not touching it")
    if cmd == "status":
        print(state)
    elif cmd == "apply":
        shift = int(sys.argv[2]) if len(sys.argv) > 2 else 48  # measured best
        write(STUBS[shift])
        print(current())
    elif cmd == "revert":
        write(ORIG)
        print(current())
    else:
        sys.exit(__doc__)


main()
