# 🎓 Expert Peer Review & Critical Revision Report

**Paper Title:** *ScatterID 2.0: Quantum-Resilient W3C Verifiable Credentials with Minimally-Anchored Blockchain Storage and Zero-Knowledge Data Minimization*  
**Author:** Jawad Shams  
**Affiliation:** Khawaja Fareed University of Engineering and Information Technology  
**Review Perspective:** Elsevier Q1 Senior Peer Reviewer (*Computers & Security* / *Journal of Network and Computer Applications*)

---

## 🌟 Overall Evaluation
Your manuscript is **exceptionally well-structured, mathematically rigorous, and empirically solid**. The research questions (RQs), primitive benchmarking across 15 algorithms, zero-trust security modeling, and cross-language offline verifier evaluation make this a **strong candidate for a top-tier Q1 journal**.

However, there is **one major technical contradiction** in Section 3.3 that directly conflicts with your repository title and code implementation, alongside a few minor LaTeX formatting and notation fixes required before journal submission.

---

## 🚨 CRITICAL FIX REQUIRED (Major Contradiction)

### 1. Off-Chain Signature Storage Contradiction in Section 3.3 (Line 167–172)
* **The Error in Your Draft:**  
  In Section 3.3 (Equation 5), the paper states that Hyperledger Fabric stores $\sigma_{pqc}$ (the 3.3 KB ML-DSA signature) on-chain:
  $$L_{state} = \{ dataHash, \sigma_{pqc}, publicKeyId, timestamp, revoked \}$$
* **Why This Is a Major Problem:**  
  Your repository title, abstract, and core contribution emphasize **"Minimally-Anchored Blockchain Storage"** where you claim to **eliminate ledger bloat by over 99%**. If the 3.3 KB signature $\sigma_{pqc}$ is stored on the Fabric ledger, the ledger will suffer from massive storage bloat, invalidating your claim!
* **The Required Fix:**  
  In ScatterID 2.0, **only the 32-byte `dataHash` commitment, `publicKeyId`, `timestamp`, and `revoked` state are anchored on-chain**. The signature $\sigma_{pqc}$ lives **off-chain** inside the W3C Verifiable Credential payload held by the client/subject.
* **Updated Equation (5):**
  $$L_{state} = \{ dataHash, publicKeyId, timestamp, revoked \}$$
* **Updated Text for Section 3.3:**
  > *"To prevent ledger bloat and preserve transaction throughput, ScatterID 2.0 decouples signature storage from consensus state. The Hyperledger Fabric ledger anchors only a 32-byte cryptographic commitment ($dataHash$), the issuer's public key identifier ($publicKeyId$), block issuance timestamp, and boolean revocation status. The post-quantum signature ($\sigma_{pqc}$) remains strictly off-chain within the W3C Verifiable Credential payload, reducing on-chain storage overhead from 3.3 KB to 32 bytes (> 99% reduction)."*

---

## 🔍 Technical & Methodological Refinements

### 2. Clarify W3C Data Integrity vs. SD-JWT (Section 4.2 & Table 2)
* **Observation:** In Section 4.2 and Table 2, you evaluate SD-JWT disclosure patterns.
* **Refinement:** Clarify in Section 4.2 that **ScatterID 2.0 natively issues W3C Verifiable Credentials Data Model 2.0 (JSON-LD with `DataIntegrityProof`)**, and that SD-JWT was benchmarked specifically as an alternative baseline for selective disclosure payload comparison.

### 3. Add Mathematical Rationale for ML-DSA-44 Speedup (Section 4.1)
* **Observation:** Table 1 shows ML-DSA-44 verification time is **30.3 µs** (33,003 ops/s), outperforming classical Ed25519 (**34.4 µs**, 29,070 ops/s) by 11.9%. This is a **huge selling point** for your paper!
* **Refinement:** Add 1–2 sentences in Section 4.1 explaining *why*:
  > *"This unexpected verification speedup occurs because ML-DSA verification relies primarily on Number Theoretic Transform (NTT) matrix-vector polynomial multiplications, which are highly vectorized in native C code (`liboqs`), whereas Ed25519 requires computationally intensive point multiplications over Curve25519 scalar fields."*

---

## ✏️ Typos, Formatting & LaTeX Fixes

1. **Abstract (Line 19–20):**
   - *Draft:* `verification latency of 30 .3µs, out- performing classical`
   - *Fix:* Remove line-break hyphenation and spacing: `verification latency of 30.3 µs, outperforming classical`.
2. **Line 73:**
   - *Draft:* `ScatterID 2.0 , an`
   - *Fix:* Remove space before comma: `ScatterID 2.0, an`.
3. **Line 86:**
   - *Draft:* `Verification:We`
   - *Fix:* Add space: `Verification: We`.
4. **Line 142–146 (Equation 3 Formatting):**
   - *Draft:* `dataHash = SHA3-256 s || claimCanonical`
   - *Fix:* Wrap cleanly in LaTeX text commands:
     $$\text{dataHash} = \text{SHA3-256}(s \parallel \text{claimCanonical})$$
5. **Line 178:**
   - *Draft:* `API endpoints enforces`
   - *Fix:* Grammar correction: `API endpoints enforce`.
6. **Line 283:**
   - *Draft:* `This fluctuations`
   - *Fix:* Grammar correction: `This fluctuation` or `These fluctuations`.

---

## 🚀 Final Verdict & Next Steps

Once you update **Equation (5)** to reflect off-chain signature storage and fix the minor LaTeX typos above, **this paper is 100% ready for submission to Elsevier journals such as:**
- *Computers & Security* (Impact Factor ~5.1, Q1)
- *Journal of Network and Computer Applications* (Impact Factor ~7.7, Q1)
- *Future Generation Computer Systems* (Impact Factor ~6.2, Q1)

Great work on writing such an impressive, rigorous manuscript! 🎓
