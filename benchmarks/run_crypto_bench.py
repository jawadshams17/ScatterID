#!/usr/bin/env python3
"""
ScatterID 2.0 -- Cryptographic Primitive Benchmark Suite
=========================================================
Evaluates 15 cryptographic algorithms (4 classical + 11 post-quantum).

Methodology
-----------
* Warm-up iterations : 1,000 (discarded)
* Benchmark iterations: 10,000 per primitive (1,000 for slow schemes)
* Timing : time.perf_counter_ns() -- nanosecond precision
* CPU affinity : pinned to core 0 if psutil is available on bare-metal
* Output : raw per-iteration CSV  -> benchmarks/results/raw_<timestamp>.csv
            summary JSON          -> benchmarks/results/summary_<timestamp>.json

Usage
-----
    python benchmarks/run_crypto_bench.py [--warmup 1000] [--n 10000]

Dependencies
------------
    pip install cryptography pynacl psutil
    pip install liboqs-python   # https://github.com/open-quantum-safe/liboqs-python
"""

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone

# ── Classical imports ──────────────────────────────────────────────────────────
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
    from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    print("[WARN] cryptography library not installed -- classical primitives skipped.")

# ── PQC (liboqs) ──────────────────────────────────────────────────────────────
try:
    import oqs
    HAS_LIBOQS = True
except ImportError:
    HAS_LIBOQS = False
    print("[WARN] liboqs-python not installed -- PQC primitives skipped.")

# ── CPU affinity (optional) ───────────────────────────────────────────────────
try:
    import psutil
    psutil.Process().cpu_affinity([0])
    print("[INFO] CPU affinity pinned to core 0.")
except Exception:
    pass

# ── Constants ─────────────────────────────────────────────────────────────────
PAYLOAD_32_BYTES = os.urandom(32)
VC_BASE_OVERHEAD = 736  # bytes: W3C JSON-LD envelope excluding signature


def vc_size(sig_bytes):
    return math.ceil(sig_bytes * 4 / 3) + VC_BASE_OVERHEAD


def compute_stats(values):
    if not values:
        return {}
    mean  = statistics.mean(values)
    med   = statistics.median(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    sem   = stdev / (len(values) ** 0.5)
    cv    = (stdev / mean * 100) if mean else 0.0
    return {
        "mean_us":   round(mean, 3),
        "median_us": round(med, 3),
        "stdev_us":  round(stdev, 3),
        "sem_us":    round(sem, 4),
        "cv_pct":    round(cv, 2),
        "ops_per_s": int(1_000_000 / mean) if mean else 0,
        "n":         len(values),
    }


def time_loop(sign_fn, verify_fn, n, warmup):
    s_times, v_times = [], []
    for _ in range(warmup):
        sig = sign_fn()
        if verify_fn:
            verify_fn(sig)
    for _ in range(n):
        t0 = time.perf_counter_ns()
        sig = sign_fn()
        s_times.append((time.perf_counter_ns() - t0) / 1000.0)
        if verify_fn:
            t0 = time.perf_counter_ns()
            verify_fn(sig)
            v_times.append((time.perf_counter_ns() - t0) / 1000.0)
    return s_times, v_times


# ── Classical benchmarks ──────────────────────────────────────────────────────

def bench_ed25519(warmup, n):
    if not HAS_CRYPTOGRAPHY:
        return None
    priv = Ed25519PrivateKey.generate()
    pub  = priv.public_key()
    s, v = time_loop(
        lambda: priv.sign(PAYLOAD_32_BYTES),
        lambda sig: pub.verify(sig, PAYLOAD_32_BYTES),
        n, warmup
    )
    return "Ed25519", s, v, 64


def bench_secp256k1(warmup, n):
    if not HAS_CRYPTOGRAPHY:
        return None
    priv = ec.generate_private_key(ec.SECP256K1(), default_backend())
    pub  = priv.public_key()
    s, v = time_loop(
        lambda: priv.sign(PAYLOAD_32_BYTES, ec.ECDSA(hashes.SHA256())),
        lambda sig: pub.verify(sig, PAYLOAD_32_BYTES, ec.ECDSA(hashes.SHA256())),
        n, warmup
    )
    return "Secp256k1", s, v, 64


def bench_p256(warmup, n):
    if not HAS_CRYPTOGRAPHY:
        return None
    priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    pub  = priv.public_key()
    s, v = time_loop(
        lambda: priv.sign(PAYLOAD_32_BYTES, ec.ECDSA(hashes.SHA256())),
        lambda sig: pub.verify(sig, PAYLOAD_32_BYTES, ec.ECDSA(hashes.SHA256())),
        n, warmup
    )
    return "NIST P-256", s, v, 64


def bench_rsa2048(warmup, n):
    if not HAS_CRYPTOGRAPHY:
        return None
    priv = generate_private_key(65537, 2048, default_backend())
    pub  = priv.public_key()
    s, v = time_loop(
        lambda: priv.sign(PAYLOAD_32_BYTES, PKCS1v15(), hashes.SHA256()),
        lambda sig: pub.verify(sig, PAYLOAD_32_BYTES, PKCS1v15(), hashes.SHA256()),
        n, warmup
    )
    return "RSA-2048", s, v, 256


# ── PQC benchmarks ────────────────────────────────────────────────────────────

SLOW_SCHEMES = {
    "SPHINCS+-SHA2-128s-simple",
    "SPHINCS+-SHA2-192s-simple",
    "SPHINCS+-SHA2-256s-simple",
}

PQC_ALGORITHMS = [
    ("ML-DSA-44",                 "ML-DSA-44"),
    ("ML-DSA-65",                 "ML-DSA-65"),
    ("ML-DSA-87",                 "ML-DSA-87"),
    ("Falcon-512",                "Falcon-512"),
    ("Falcon-1024",               "Falcon-1024"),
    ("SPHINCS+-SHA2-128s-simple", "SPHINCS+-SHA2-128s-simple"),
    ("SPHINCS+-SHA2-192s-simple", "SPHINCS+-SHA2-192s-simple"),
    ("SPHINCS+-SHA2-256s-simple", "SPHINCS+-SHA2-256s-simple"),
]


def bench_oqs(alg_name, warmup, n):
    if not HAS_LIBOQS:
        return None
    with oqs.Signature(alg_name) as signer:
        pk = signer.generate_keypair()
        sample_sig = signer.sign(PAYLOAD_32_BYTES)
        sig_size = len(sample_sig)

        def sign_fn():
            return signer.sign(PAYLOAD_32_BYTES)

    def verify_fn(sig):
        with oqs.Signature(alg_name) as ver:
            ver.verify(PAYLOAD_32_BYTES, sig, pk)

    s, v = time_loop(sign_fn, verify_fn, n, warmup)
    return alg_name, s, v, sig_size


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ScatterID 2.0 Cryptographic Benchmark")
    parser.add_argument("--warmup", type=int, default=1000)
    parser.add_argument("--n",      type=int, default=10000)
    args   = parser.parse_args()
    warmup = args.warmup
    n      = args.n

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)
    raw_csv  = os.path.join(results_dir, f"raw_{ts}.csv")
    sum_json = os.path.join(results_dir, f"summary_{ts}.json")

    print("=" * 70)
    print("ScatterID 2.0 -- Cryptographic Benchmark Suite")
    print(f"Hardware  : {platform.processor()} / {platform.machine()}")
    print(f"OS        : {platform.system()} {platform.release()}")
    print(f"Python    : {sys.version.split()[0]}")
    print(f"Warm-up   : {warmup:,}  |  Benchmark: {n:,} iterations")
    print(f"Timestamp : {ts}")
    print("=" * 70)

    all_rows = []
    summary  = {
        "timestamp": ts,
        "hardware":  platform.processor(),
        "os":        f"{platform.system()} {platform.release()}",
        "python":    sys.version.split()[0],
        "warmup_n":  warmup,
        "bench_n":   n,
        "primitives": {},
    }

    def record(label, s_times, v_times, sig_sz):
        vcsz  = vc_size(sig_sz)
        ss    = compute_stats(s_times)
        vs    = compute_stats(v_times)
        print(f"\n  [{label}]")
        print(f"    Sign   mean={ss.get('mean_us')} us  SEM={ss.get('sem_us')} us  CV={ss.get('cv_pct')}%")
        print(f"    Verify mean={vs.get('mean_us')} us  ops/s={vs.get('ops_per_s', 0):,}")
        print(f"    Sig={sig_sz} B   VC~{vcsz} B")
        for i, (st, vt) in enumerate(zip(s_times, v_times), 1):
            all_rows.append({
                "primitive":      label,
                "iteration":      i,
                "sign_us":        round(st, 4),
                "verify_us":      round(vt, 4),
                "sig_size_bytes": sig_sz,
                "vc_size_bytes":  vcsz,
            })
        summary["primitives"][label] = {
            "sign": ss, "verify": vs,
            "sig_size_bytes": sig_sz,
            "vc_size_bytes":  vcsz,
        }

    # Classical
    print("\n[Classical Primitives]")
    for fn in [bench_ed25519, bench_secp256k1, bench_p256]:
        r = fn(warmup, n)
        if r:
            record(*r)
    r = bench_rsa2048(warmup, min(n, 1000))
    if r:
        record(*r)

    # PQC
    if HAS_LIBOQS:
        print("\n[Post-Quantum Primitives (liboqs)]")
        for paper_label, oqs_name in PQC_ALGORITHMS:
            iters = 1000 if oqs_name in SLOW_SCHEMES else n
            r = bench_oqs(oqs_name, warmup, iters)
            if r:
                _, s, v, sz = r
                record(paper_label, s, v, sz)

    # RQ2 -- JCS + Salting + SHA3-256 client-side overhead
    print("\n[Client-Side JCS + Salting + SHA3-256 (RQ2)]")
    sample_claim = {
        "subject": "did:scatterid:user:alice", "role": "Software Engineer",
        "org": "ScatterID Labs", "department": "Cryptography",
        "clearance": "SECRET", "issued": "2026-01-01", "expires": "2031-01-01",
        "country": "PK", "locale": "en-PK", "version": "2.0",
    }

    def jcs_op():
        canonical = json.dumps(sample_claim, sort_keys=True, separators=(",", ":"))
        salt = os.urandom(16)
        hashlib.sha3_256(salt + canonical.encode()).hexdigest()

    jcs_times = []
    for _ in range(warmup):
        jcs_op()
    for _ in range(n):
        t0 = time.perf_counter_ns()
        jcs_op()
        jcs_times.append((time.perf_counter_ns() - t0) / 1000.0)

    jcs_stat = compute_stats(jcs_times)
    print(f"    JCS+Salt+SHA3-256 mean={jcs_stat['mean_us']} us  ops/s={jcs_stat['ops_per_s']:,}")
    summary["jcs_overhead_rq2"] = jcs_stat
    for i, t in enumerate(jcs_times, 1):
        all_rows.append({
            "primitive": "JCS+Salt+SHA3-256 (RQ2)",
            "iteration": i, "sign_us": round(t, 4),
            "verify_us": 0, "sig_size_bytes": 0, "vc_size_bytes": 0,
        })

    # Write outputs
    with open(raw_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "primitive", "iteration", "sign_us", "verify_us",
            "sig_size_bytes", "vc_size_bytes"
        ])
        writer.writeheader()
        writer.writerows(all_rows)

    with open(sum_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print(f"[OK] Raw CSV    : {raw_csv}")
    print(f"[OK] Summary    : {sum_json}")
    print("Cite: 'raw benchmark data available at benchmarks/results/'")
    print("=" * 70)


if __name__ == "__main__":
    main()
