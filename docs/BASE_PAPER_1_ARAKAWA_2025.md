# Primary Base Paper Reference & Deep Analysis

### Paper Metadata
* **Title:** *Post-Quantum Cryptography for Verifiable Credentials: Comprehensive Performance Evaluation Including Selective Disclosure*
* **Author:** Masayoshi Arakawa
* **Publisher / Venue:** TechRxiv / IEEE
* **Publication Date:** October 23, 2025
* **DOI:** `10.36227/techrxiv.176118722.22701360/v1`

---

## 📌 Executive Summary of the Base Paper
This paper investigates the integration of NIST-standardized Post-Quantum Cryptography (**ML-DSA / Module-Lattice-Based Digital Signature Algorithm**) into Verifiable Credentials (VCs), specifically focusing on **Selective Disclosure JWTs (SD-JWT)**. 

Because traditional Verifiable Credentials rely on Elliptic Curve Cryptography (ECC, e.g., Ed25519 or ECDSA), they are vulnerable to **"Store-Now-Decrypt-Later"** attacks—where an adversary intercepts and stores signed credentials today to forge or decrypt them once quantum computers running Shor's algorithm become available.

---

## 🔬 Key Technical Contributions & Benchmark Findings

1. **PQC Integration with SD-JWT:**
   - Demonstrates the feasibility of executing selective disclosure over post-quantum signed credentials without revealing undisclosed identity attributes.
2. **Performance Benchmarking (`liboqs-rust`):**
   - Benchmarks key generation, signing latency, and verification latency for ML-DSA algorithms (ML-DSA-44, ML-DSA-65, ML-DSA-87) vs. classical Ed25519.
   - **Verification Speed Advantage:** ML-DSA-44 verification is surprisingly **faster** than Ed25519 verification due to lattice matrix-vector multiplication efficiency.
3. **The Core Trade-off (Payload Size Overhead):**
   - **Classical Ed25519 Signature:** ~64 bytes.
   - **Post-Quantum ML-DSA-65 Signature:** **3,293 bytes** (~3.3 KB).
   - **Impact:** Transmitting or storing full ML-DSA signed credentials directly over constrained channels or blockchain ledgers introduces heavy network and storage bloat.

---

## ⚔️ How ScatterID 2.0 Outperforms & Resolves this Base Paper's Limitations

| Feature / Metric | **Arakawa et al. (Base Paper)** | **ScatterID 2.0 (Your Framework)** |
| :--- | :--- | :--- |
| **Credential Standard** | SD-JWT | **W3C Verifiable Credentials (JSON-LD + DataIntegrityProof)** |
| **PQC Signature Scheme** | ML-DSA | **NIST FIPS 204 ML-DSA-65** |
| **Storage Architecture** | Full Credential + Signature in JWT | **Off-Chain Signature Storage + Minimally-Anchored Ledger State** |
| **Blockchain Integration** | None | **Hyperledger Fabric with Raft Consensus Anchoring** |
| **Ledger Storage Overhead** | ~3.3 KB per credential (if anchored) | **32 Bytes (SHA3-256 pre-image commitment)** |
| **Zero-Knowledge Method** | Disclosure HMAC hashes | **RFC 8785 JCS Canonicalization + 16-byte CSPRNG Salt** |
| **Ledger Bloat Reduction** | 0% (Unmitigated) | **> 99% Reduction** |

---

## 📝 Exact BibTeX Citation for Your Manuscript

```bibtex
@article{arakawa2025pqc_vc,
  title     = {Post-Quantum Cryptography for Verifiable Credentials: Comprehensive Performance Evaluation Including Selective Disclosure},
  author    = {Arakawa, Masayoshi},
  journal   = {TechRxiv preprint},
  doi       = {10.36227/techrxiv.176118722.22701360/v1},
  year      = {2025},
  month     = {October}
}
```

---

## 💬 Recommended Section 2 Literature Review Text:
> *"Arakawa et al. [Arakawa, 2025] evaluated the performance of NIST ML-DSA lattice signatures for Selective Disclosure Verifiable Credentials (SD-JWTs), observing that while ML-DSA achieves rapid verification times, its 3,293-byte signature payload introduces severe transmission and storage overheads. ScatterID 2.0 directly addresses this limitation by adopting an off-chain signature storage model coupled with a 32-byte SHA3-256 commitment anchored to Hyperledger Fabric, achieving quantum-resilient verification while mitigating ledger bloat by over 99%."*
