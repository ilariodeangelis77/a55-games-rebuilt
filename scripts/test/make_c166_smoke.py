"""Build a tiny hand-assembled C166 binary to smoke-test the Ghidra C166 module.

Encodings from the Infineon C166 Instruction Set Manual v2.0. Expected disassembly
is in EXPECTED; scripts/test/smoke_test.sh compares Ghidra's output against it.
"""
import sys
from pathlib import Path

prog = bytearray(b"\xFF" * 0x120)
prog[0x000:0x004] = bytes.fromhex("FA000001")  # JMPS 0x00, 0x0100   (reset vector)
code = bytes.fromhex(
    "E6F43412"  # 0x100 MOV  R4, #0x1234
    "E035"      # 0x104 MOV  R5, #3
    "0045"      # 0x106 ADD  R4, R5
    "F2F60040"  # 0x108 MOV  R6, 0x4000   (DPP1-relative data access)
    "BB01"      # 0x10C CALLR 0x110
    "0DFF"      # 0x10E JMPR cc_UC, 0x10E (spin)
    "CB00"      # 0x110 RET
)
prog[0x100:0x100 + len(code)] = code

EXPECTED = [
    (0x000, "JMPS"), (0x100, "MOV"), (0x104, "MOV"), (0x106, "ADD"),
    (0x108, "MOV"), (0x10C, "CALLR"), (0x10E, "JMPR"), (0x110, "RET"),
]

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out/c166_smoke.bin")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(prog)
    print(out)
