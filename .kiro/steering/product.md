# Product Overview

BECR (Blockwise Extraction Comparison & Review) is a test-driven system for comparing and reviewing text extraction results from PDFs at the block level.

## Core Purpose

The system addresses the problem of inconsistent PDF text extraction by providing an intelligent layer that:
- Aligns multiple OCR/extraction engine outputs at block level
- Scores variations using language and layout-aware signals  
- Offers a visual review UI for manual override
- Ingests internal and external results via strict NDJSON schema

## Key Components

- **Global Block Grid (GBG)**: Deterministic PDF segmentation with stable block IDs
- **Variation Mapping**: Handles internal and external engine outputs via NDJSON
- **Consensus Engine**: Feature-based scoring with hallucination guards
- **Review GUI**: PySide6 interface for side-by-side comparison and override
- **NDJSON I/O**: Strict schema validation for interoperability

## Target Users

- **Researchers/Engineers**: Need consistent PDF block segmentation across engines
- **Quality Reviewers**: Require visual comparison tools for accuracy validation
- **Integrators**: Want to incorporate external OCR results via standardized format

## Success Metrics

- 100% repeatable block ID stability
- 20-30% error reduction vs single-engine approaches
- <100ms GUI block switching latency
- <10% manual override rate on clean documents