# 🧠 Omni-Parser Pro: Industrial-Grade Knowledge Migration Engine

**"Transform your messy legacy data into a structured, high-performance Second Brain."**

Omni-Parser Pro is a surgical ETL (Extract, Transform, Load) pipeline designed to migrate complex data from **Evernote (.enex)** and **HTML** into a clean, future-proof **Obsidian Vault**.

---

## 🌟 Why Omni-Parser Pro?

Most migration tools fail on complex layouts or create "bloated" vaults with duplicate assets. This engine uses a **multi-stage validation approach** to ensure zero data loss and maximum queryability.

### 🛡️ Key Features

* **Pre-Flight Audit:** Detects structural risks (nested tables, merged cells) before the migration starts.
* **Surgical Transformation:** Uses a custom Pandoc-GFM engine to convert complex HTML into clean, readable Markdown.
* **Metadata Intelligence:** Automatically injects YAML Frontmatter (dates, source, tags), making your notes instantly compatible with the **Dataview** plugin.
* **Asset Optimization:** Implements **MD5 Hashing** to identify and remove duplicate images, reducing vault size by 20-40% on average.
* **Content Sanitization:** Deep-cleans "digital rot" (inline CSS, empty tags, broken links) for a pristine writing environment.

---

## 🏗️ Architecture & Pipeline Flow

The system operates as a linear, fail-safe pipeline to ensure data integrity at every step:

1.  **Auditor:** Heuristic risk assessment and complexity scoring.
2.  **Transformer:** High-fidelity conversion using Pandoc (GitHub Flavored Markdown).
3.  **Sanitizer:** Normalization of whitespace and link integrity.
4.  **Injector:** Automated metadata enrichment.
5.  **Optimizer:** Content-based asset deduplication and link re-mapping.



---

## 🚀 Quick Start

### 1. Prerequisites
* **Python 3.9+**
* **Pandoc** (Ensure it is installed and added to your system PATH)

### 2. Installation
```bash
# Clone the repository
git clone [https://github.com/angeawalabj/omni-parser-obsidian.git](https://github.com/angeawalabj/omni-parser-obsidian.git)
cd omni-parser-obsidian

# Install dependencies
pip install -r requirements.txt