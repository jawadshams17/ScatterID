#!/usr/bin/env bash
# ==============================================================================
# ScatterID 2.0 -- Cross-Language Parity + Speed Comparison Test (RQ4 Extension)
# ==============================================================================
# Extends the existing offline_verify_parity.test.sh by logging wall-clock time
# per verifier so a real Node.js-vs-Python speed comparison can be reported in
# Table 4 of the paper.
#
# Outputs:
#   scripts/performance/parity_speed_rq4_<timestamp>.csv
#   scripts/performance/parity_speed_rq4_<timestamp>.json
#
# Methodology:
#   N_TRIALS credentials are generated (with real ML-DSA-65 signatures when
#   liboqs is available, or Level-1-only fixtures otherwise). Each credential is
#   verified by both Node.js and Python runtimes; wall-clock time is measured
#   at the shell level using date +%s%N.
#
# Usage:
#   bash tests/parity_speed_rq4.test.sh [--n 1000]
# ==============================================================================

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$DIR/.." && pwd)"
RESULTS_DIR="$ROOT_DIR/scripts/performance"
mkdir -p "$RESULTS_DIR"

N_TRIALS=1000
if [[ "${1:-}" == "--n" && -n "${2:-}" ]]; then
  N_TRIALS="$2"
fi

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
CSV_OUT="$RESULTS_DIR/parity_speed_rq4_${TIMESTAMP}.csv"
JSON_OUT="$RESULTS_DIR/parity_speed_rq4_${TIMESTAMP}.json"

GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
BOLD="\033[1m"
RESET="\033[0m"

cd "$ROOT_DIR"

# Resolve Python
if command -v python3 >/dev/null 2>&1 && python3 -c "import oqs" >/dev/null 2>&1; then
  PY_BIN="python3"
elif [ -x "/tmp/crypto_venv/bin/python3" ]; then
  PY_BIN="/tmp/crypto_venv/bin/python3"
else
  PY_BIN="python3"
fi

HAS_LIBOQS=false
$PY_BIN -c "import oqs" >/dev/null 2>&1 && HAS_LIBOQS=true || true

echo "======================================================================"
echo "  ScatterID 2.0 -- Cross-Language Parity + Speed (RQ4)"
echo "  N=$N_TRIALS trials | liboqs=$HAS_LIBOQS"
echo "======================================================================"

echo "runtime,trial,level1_only,verify_ms,result" > "$CSV_OUT"

PARITY_FAILURES=0
NODE_TIMES=()
PY_TIMES=()

# Generate a batch of test fixtures
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo -e "\n${BOLD}[1/2] Generating $N_TRIALS test fixtures...${RESET}"

if [ "$HAS_LIBOQS" = true ]; then
  LEVEL1_ONLY=false
  $PY_BIN - "$TMP_DIR" "$N_TRIALS" <<'PYEOF'
import oqs, json, os, hashlib, sys
outdir = sys.argv[1]
n = int(sys.argv[2])
with oqs.Signature("ML-DSA-65") as signer:
    pk = signer.generate_keypair()
    for i in range(n):
        claim = {"subject": f"did:scatterid:user:bench-{i}", "role": "Tester", "n": i}
        canonical = json.dumps(claim, sort_keys=True, separators=(",", ":"))
        salt = os.urandom(16)
        data_hash = hashlib.sha3_256(salt + canonical.encode()).hexdigest()
        sig = signer.sign(bytes.fromhex(data_hash))
        fixture = {
            "rawClaim": claim,
            "salt": salt.hex(),
            "dataHash": data_hash,
            "algorithm": "ML-DSA-65",
            "signature": sig.hex(),
            "publicKey": pk.hex(),
        }
        with open(os.path.join(outdir, f"fixture_{i:06d}.json"), "w") as f:
            json.dump(fixture, f)
print(f"[OK] Generated {n} signed fixtures", flush=True)
PYEOF
else
  LEVEL1_ONLY=true
  echo -e "${YELLOW}[INFO] liboqs unavailable -- Level-1 fixtures only${RESET}"
  $PY_BIN - "$TMP_DIR" "$N_TRIALS" <<'PYEOF'
import json, os, hashlib, sys
outdir = sys.argv[1]
n = int(sys.argv[2])
for i in range(n):
    claim = {"subject": f"did:scatterid:user:bench-{i}", "role": "Tester", "n": i}
    canonical = json.dumps(claim, sort_keys=True, separators=(",", ":"))
    salt = os.urandom(16)
    data_hash = hashlib.sha3_256(salt + canonical.encode()).hexdigest()
    fixture = {
        "rawClaim": claim,
        "salt": salt.hex(),
        "dataHash": data_hash,
        "algorithm": "ML-DSA-65",
    }
    with open(os.path.join(outdir, f"fixture_{i:06d}.json"), "w") as f:
        json.dump(fixture, f)
print(f"[OK] Generated {n} Level-1 fixtures", flush=True)
PYEOF
fi

echo -e "\n${BOLD}[2/2] Running cross-language verification timing...${RESET}"

PASS=0
FAIL=0

for i in $(seq 0 $((N_TRIALS - 1))); do
  FIXTURE=$(printf "$TMP_DIR/fixture_%06d.json" "$i")
  [ -f "$FIXTURE" ] || continue

  # ── Node.js timing ────────────────────────────────────────────────────────
  t0=$(date +%s%N)
  if node tools/verify_offline.js "$FIXTURE" >/dev/null 2>&1; then
    NODE_RES="PASS"
  else
    NODE_RES="FAIL"
    FAIL=$((FAIL + 1))
  fi
  t1=$(date +%s%N)
  NODE_MS=$(echo "scale=4; ($t1 - $t0)/1000000" | bc)
  echo "nodejs,$i,$LEVEL1_ONLY,$NODE_MS,$NODE_RES" >> "$CSV_OUT"

  # ── Python timing ─────────────────────────────────────────────────────────
  t0=$(date +%s%N)
  if $PY_BIN tools/verify_offline.py "$FIXTURE" >/dev/null 2>&1; then
    PY_RES="PASS"
  else
    PY_RES="FAIL"
    FAIL=$((FAIL + 1))
  fi
  t1=$(date +%s%N)
  PY_MS=$(echo "scale=4; ($t1 - $t0)/1000000" | bc)
  echo "python,$i,$LEVEL1_ONLY,$PY_MS,$PY_RES" >> "$CSV_OUT"

  # ── Parity check ─────────────────────────────────────────────────────────
  if [ "$NODE_RES" != "$PY_RES" ]; then
    PARITY_FAILURES=$((PARITY_FAILURES + 1))
  else
    PASS=$((PASS + 1))
  fi

  if (( (i + 1) % 100 == 0 )); then
    echo "  Progress: $((i + 1))/$N_TRIALS trials..."
  fi
done

# ── Compute and write summary ─────────────────────────────────────────────────
$PY_BIN - "$CSV_OUT" "$JSON_OUT" "$PARITY_FAILURES" "$N_TRIALS" "$LEVEL1_ONLY" <<'PYEOF'
import csv, json, statistics, sys

csv_path  = sys.argv[1]
json_path = sys.argv[2]
parity_failures = int(sys.argv[3])
n_trials  = int(sys.argv[4])
l1_only   = sys.argv[5].lower() == "true"

node_times, py_times = [], []
with open(csv_path) as f:
    for row in csv.DictReader(f):
        try:
            t = float(row["latency_ms"])
        except (ValueError, KeyError):
            continue
        if row["runtime"] == "nodejs":
            node_times.append(t)
        elif row["runtime"] == "python":
            py_times.append(t)

def stats(vals):
    if not vals:
        return {}
    return {
        "n":         len(vals),
        "mean_ms":   round(statistics.mean(vals), 3),
        "median_ms": round(statistics.median(vals), 3),
        "stdev_ms":  round(statistics.stdev(vals), 3) if len(vals) > 1 else 0,
        "p95_ms":    round(sorted(vals)[int(len(vals)*0.95)], 3),
    }

parity_pct = round((n_trials - parity_failures) / n_trials * 100, 2)
summary = {
    "n_trials":        n_trials,
    "level1_only":     l1_only,
    "parity_pct":      parity_pct,
    "parity_failures": parity_failures,
    "nodejs":          stats(node_times),
    "python":          stats(py_times),
}
speedup = None
if node_times and py_times:
    speedup = round(statistics.mean(py_times) / statistics.mean(node_times), 2)
    summary["nodejs_vs_python_speedup"] = speedup

with open(json_path, "w") as f:
    json.dump(summary, f, indent=2)

print("\n  === RQ4 Cross-Language Parity & Speed Summary ===")
print(f"  Trials         : {n_trials}")
print(f"  Parity         : {parity_pct}% ({parity_failures} disagreements)")
ns = summary["nodejs"]
ps = summary["python"]
print(f"  Node.js verify : mean={ns.get('mean_ms')}ms  p95={ns.get('p95_ms')}ms")
print(f"  Python  verify : mean={ps.get('mean_ms')}ms  p95={ps.get('p95_ms')}ms")
if speedup:
    faster = "Node.js" if speedup > 1 else "Python"
    ratio  = speedup if speedup >= 1 else round(1/speedup, 2)
    print(f"  Speed comparison: {faster} is {ratio}x faster (shell-level overhead included)")
PYEOF

echo ""
echo "======================================================================"
if [ "$PARITY_FAILURES" -eq 0 ]; then
  echo -e "${GREEN}[OK] 100% parity across $N_TRIALS trials${RESET}"
else
  echo -e "${RED}[WARN] $PARITY_FAILURES parity disagreements detected!${RESET}"
fi
echo -e "${GREEN}[OK] RQ4 results saved:${RESET}"
echo "       CSV : $CSV_OUT"
echo "       JSON: $JSON_OUT"
echo "======================================================================"
