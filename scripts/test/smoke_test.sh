#!/usr/bin/env bash
# Smoke-test the Ghidra + C166 module install on a hand-assembled binary.
# Usage: scripts/test/smoke_test.sh   (from the repo root)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GHIDRA="$ROOT/tools/ghidra_12.2_PUBLIC"
WORK="$ROOT/out/smoke"
rm -rf "$WORK"; mkdir -p "$WORK/proj"

python -I "$ROOT/scripts/test/make_c166_smoke.py" "$WORK/c166_smoke.bin" >/dev/null

"$GHIDRA/support/analyzeHeadless.bat" "$WORK/proj" smoke \
    -import "$WORK/c166_smoke.bin" \
    -loader BinaryLoader -loader-baseAddr 0 \
    -processor "C166:LE:16:default" \
    -scriptPath "$ROOT/scripts/ghidra" \
    -postScript DumpListing.java 0 100 110 \
    -deleteProject > "$WORK/headless.log" 2>&1 || { tail -40 "$WORK/headless.log"; exit 1; }

grep -E "DumpListing.java> (LANG|INS)" "$WORK/headless.log" | sed 's/.*DumpListing.java> //' | tr -d '\r' | tee "$WORK/listing.txt"

python -I - "$WORK/listing.txt" "$ROOT/scripts/test" <<'PY'
import sys
sys.path.insert(0, sys.argv[2])
from make_c166_smoke import EXPECTED
got = {}
for line in open(sys.argv[1]):
    if line.startswith("INS "):
        addr, ins = line[4:].split("\t", 1)
        got[int(addr.split(":")[-1], 16)] = ins.split()[0].upper()
bad = [(hex(a), m, got.get(a)) for a, m in EXPECTED if got.get(a) != m]
print("SMOKE TEST", "FAILED: %s" % bad if bad else "PASSED (%d instructions)" % len(EXPECTED))
sys.exit(1 if bad else 0)
PY
