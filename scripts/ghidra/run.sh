#!/usr/bin/env bash
# Run a read-only postScript against the analyzed A55 program and print only its output lines.
# Usage: scripts/ghidra/run.sh <Script.java> [args...]
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
S="$1"; shift
"$ROOT/tools/ghidra_12.2_PUBLIC/support/analyzeHeadless.bat" "$ROOT/out/ghidra_projects" a55 \
  -process A55_LG7_V9_00800000.FLS -noanalysis -readOnly -scriptPath "$ROOT/scripts/ghidra" \
  -postScript "$S" "$@" 2>&1 | tr -d '\r' | awk -v s="${S}> " '
    index($0, s) { sub(/^.*> /, ""); sub(/ \(GhidraScript\) *$/, ""); print; inblk=1; next }
    /^(INFO|WARN|ERROR)  / { inblk=0; next }
    inblk { print }'
