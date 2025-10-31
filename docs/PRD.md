# Product Requirements Document (PRD)
**Project Name:** Blockwise Extraction Comparison & Review (BECR)  
**Owner:** Cliff Thelin  
**Version:** 0.1 (Draft)  
**Last Updated:** 2025-10-25

## 1. 🧭 Purpose & Vision
### 1.1 Problem Statement
Text extraction from PDFs—especially scanned, rotated, or mixed-layout documents—varies widely by engine. Single-engine pipelines often distort text, miss rotated/vertical text, or hallucinate with no systematic comparison.

### 1.2 Product Vision
BECR is the **intelligent layer** that aligns multiple extraction/ocr/llm outputs at **block level**, scores them with language/layout-aware signals, and offers a **visual review UI** for manual override—ingesting internal and external results via a strict NDJSON schema.

## 2. 🧩 Key Objectives
- Deterministic **Global Block Grid (GBG)** with stable IDs.  
- **Shared orientation/deskew hints** so all engines benefit.  
- **Feature-based consensus** (length consistency, language fit, anomalies, context).  
- **Hallucination guard** + uncertainty flags.  
- **GUI** for side-by-side review and override.  
- **Strict NDJSON** I/O to accept external variations.  
- **TDD-first**, CI-gated development, push-button releases.

## 3. 📌 User Stories & Use Cases
Primary personas: Researcher/Engineer, Quality Reviewer, Integrator.

| # | As a… | I want to… | So that… | Acceptance Criteria |
|---|-------|------------|----------|----------------------|
| 1 | Researcher | Segment PDFs into stable blocks | All engines align to same units | Stable block IDs repeat across runs |
| 2 | Reviewer | See PDF crop + variations | I quickly pick the best | GUI shows crop + rows with metrics & diff |
| 3 | Developer | Import external NDJSON results | Use my own OCR outputs | NDJSON validates & maps to blocks |
| 4 | System | Auto-score & guard hallucinations | Avoid bad picks | Low language-fit/anomaly → flag not pick |
| 5 | Reviewer | Override consensus | Improve accuracy | Override updates consensus NDJSON live |
| 6 | Integrator | Export final NDJSON + stats | Downstream use | Valid NDJSON + summary report emitted |

## 4. 🏗️ System Architecture Overview
```
PDF → GBG (seed blocks) ← Orientation/Deskew
          ↓
    Variation Mapping (internal + external NDJSON)
          ↓
  Normalization → Feature Extraction → Consensus + Guard
          ↓
         GUI Review (override / accept)
          ↓
       NDJSON Export + Analytics
```

## 5. 🧪 Testing & Validation Strategy (TDD)
- Write tests **first** for: schema validation, GBG stability, normalization, features, consensus, GUI smoke.  
- **Golden tests**: small PDFs + known variations → exact consensus NDJSON.  
- CI: run unit, integration, and (optional) headed GUI tests on demand.

## 6. 🖼️ GUI Design (Review & Override)
- **Left**: PDF renderer with highlighted block; zoom & navigation.  
- **Right**: Variations table (engine, text, metrics, diff, pick).  
- Filters: flagged-only, by engine, by score.  
- Actions: Accept, Override, Flag for manual correction.

## 7. 📤 NDJSON Format Specification (v1)
**Input Variation (external or internal)**
```json
{
  "doc_id": "ULID-ABC",
  "page": 3,
  "block_id": "p3_122.0_408.0_140.0_60.0",
  "engine": "external-google-vision",
  "bbox": [122.0, 408.0, 140.0, 60.0],
  "raw_text": "This is the text extracted.",
  "engine_conf": 0.89,
  "orientation": 0
}
```

**Consensus Output**
```json
{
  "doc_id": "ULID-ABC",
  "page": 3,
  "block_id": "p3_122.0_408.0_140.0_60.0",
  "selected_engine": "paddleocr",
  "final_text": "This is the text extracted.",
  "consensus_score": 0.92,
  "anomaly_score": 0.03,
  "decision_reason": "highest_score",
  "engine_scores": {
    "tesseract": 0.81,
    "paddleocr": 0.92,
    "external-google-vision": 0.85
  }
}
```

## 8. 🧭 Roadmap & Phased Delivery
1) Repo + NDJSON + GBG + CI  
2) Features + consensus scoring  
3) GUI MVP (review/override)  
4) Anomaly guardrails  
5) Analytics & routing  
6) Release + docs

## 9. 🧰 Tools & Infrastructure
- Python 3.12, PyMuPDF, OpenCV, spaCy/langdetect/KenLM (opt), pytest(+pytest-qt), GitHub Actions, PySide6 (GUI).  
- GitHub Desktop for push-button commits/PRs/releases (no CLI).

## 10. 📏 Success Metrics
- Block ID stability: **100%** repeatable.  
- Consensus vs best single-engine: **+20–30%** error reduction on test sets.  
- GUI block switch latency: **< 100ms**.  
- Manual override rate on clean docs: **< 10%**.

## 11. ⚠️ Risks & Mitigations
- Engine format variance → strict schema, adapters.  
- Disagreement → thresholds + review-first.  
- GUI perf on large PDFs → pagination, lazy loads.  
- Confidence comparability → calibration.

## 12. 📚 Documentation & Governance
- Module READMEs, CONTRIBUTING, semantic versioning, CI gates for style/tests.

## 13. 🧪 Definition of Done (DoD)
- Tests pass; meets acceptance criteria; GUI behavior verified; docs updated; no terminal required to run tests/release.

## 14. 📦 Initial Deliverables (v0.1)
- This PRD (`docs/PRD.md`)  
- First test (`tests/unit/test_prd_spec.py`)  
- Immutable runners (GUI/CLI/tests)  
- Minimal scaffolding to satisfy imports
