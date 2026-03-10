
# Knowledge Ingestion Pipeline Know-How

## Overview

This document describes the automated pipeline used to ingest technical manuals (PDFs) and extract deep knowledge (text + figures) into Markdown format.
This process was used for:

1. **Fischer Mechanical Tolerance Stackup** (Text Summarization + VLM Figure Analysis)
2. **CETOL 6 Sigma Manuals** (VLM Figure Analysis)

## Architecture

### 1. File Structure

* **Source:** PDF files (e.g., `Fischer_Tolerance.pdf`, `CETOL6-*.pdf`)
* **Intermediate:** Extracted images in `extracted/` folders.
* **Output:** `Knowledge.md` files containing structured text and analyzed figure insights.

### 2. Scripts

The pipeline consists of three main Python scripts located in `/home/node/clawd/` (Workspace):

#### A. `extract_cetol_figures.py` (or similar)

* **Purpose:** Extracts all images from PDF files.
* **Library:** `PyMuPDF` (fitz)
* **Logic:**
  * Iterates through pages.
  * Extracts images using `page.get_images()`.
  * Filters out small icons (< 5KB).
  * Saves as `PDFName_pgX_imgY.png`.

#### B. `ingest_cetol_documentation.py` (The VLM Analyzer)

* **Purpose:** Analyzes images using a local LLM (Ollama/Llava) to extract engineering insights.
* **Library:** `requests` (to Ollama API), `base64`.
* **Logic:**
  * Reads extracted images.
  * Sends to Ollama (`llava` model) with a specific engineering prompt:
    * "Describe geometry/tolerance loops"
    * "Identify mathematical models (Vector Loop, DOF)"
    * "Extract formulas"
  * Appends the response to the Knowledge Markdown file.

#### C. `wait_and_run_cetol.py` (The Orchestrator)

* **Purpose:** Chains tasks to run sequentially (Fischer -> Extract CETOL -> Analyze CETOL).
* **Logic:**
  * Monitors process list for `ingest_fischer_figures.py`.
  * Once finished, triggers Extraction.
  * Then triggers Analysis.

## How to Run (Reproduction)

### Prerequisites

* Docker Container (`clawdbot-gateway`)
* Ollama Service running (accessible via `host.docker.internal:11434`)
* PDFs placed in `consume/` directory.

### Command

```bash
# To run the full chain in background
nohup python3 wait_and_run_cetol.py > chain.log 2>&1 &
```

## Maintenance & Troubleshooting

* **Logs:** Check `extract_cetol.log` and `ingest_cetol.log`.
* **Stuck Process:** Use `ps aux | grep python` to find PIDs and `kill` if necessary.
* **Model:** Verify Ollama model availability (`curl http://host.docker.internal:11434/api/tags`).

## Artifact Locations

* **Workspace:** `/home/node/clawd/`
* **Obsidian Vault:** `/home/node/clawd/obsidian_vault/02_Knowledge/Tolerance_Analysis/`
