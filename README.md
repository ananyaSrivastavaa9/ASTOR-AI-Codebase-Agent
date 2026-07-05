# ASTOR — AI Codebase Agent

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Gradio](https://img.shields.io/badge/Gradio-UI-F97316)
![Gemini](https://img.shields.io/badge/Gemini-API-4285F4?logo=google&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6F00)
![RAG](https://img.shields.io/badge/RAG-Hybrid_Retrieval-6366F1)
![Eval](https://img.shields.io/badge/Eval-20--Question_Benchmark-22C55E)

**Index Python repos. Retrieve the right source. Answer with citations.**

ASTOR is a measured retrieval + agent system for Python codebases — not a prompt pasted into an LLM. It indexes repositories with Tree-sitter, searches with hybrid vector + keyword retrieval, and answers through a Gemini tool-calling agent that cites the files it used.

| Metric | Result | Benchmark |
|--------|--------|-----------|
| **Retrieval accuracy** | **85%** (17/20) | 20-question Flask suite |
| **Answer accuracy** | **80%** (16/20) | Same suite, generation quality |
| **Retrieval before fixes** | ~25% | Same suite — pre hybrid-search fix |
| **Index optimization** | ~52s test run | Optimized multi-repo indexing workflow | 

> Most portfolio AI projects never measure retrieval. ASTOR does — with separate retrieval vs. generation metrics and a failure inspector.

---

## Demo

| | |
|---|---|
| **Demo video** | In progress — index → ask → cited answer walkthrough |
| **Live demo** | Hugging Face Spaces deployment planned |

<!-- Optional hero assets (add when ready):
  Banner:  python scripts/generate_banner.py  →  docs/assets/astor-banner.png
  GIF:     docs/assets/astor-demo.gif  (index → question → citation cards)
-->

---

## The problem

Exploring an unfamiliar Python codebase means grepping symbols, opening files, tracing imports, and still guessing at structure.

**Why a normal LLM over files is insufficient:**

| Approach | Failure mode |
|----------|--------------|
| Paste files into chat | Context windows truncate; large repos don't fit |
| Ask without retrieval | Model hallucinates APIs and file paths |
| Vector search alone | Identifier-heavy queries (`add_url_rule`, class names) embed weakly |
| No citations | Answers drift from actual source; impossible to verify |

ASTOR treats the codebase as a **retrieval problem first**, then an **agent problem**.

---

## Architecture

```mermaid
flowchart TB
    subgraph Index["Indexing (once per repo set)"]
        R[Local repo path(s)] --> W[walker.py]
        W --> P[parser.py<br/>Tree-sitter AST]
        P --> C[Function/class chunks]
        C --> E[SentenceTransformer<br/>all-MiniLM-L6-v2]
        E --> V[(ChromaDB<br/>persistent vectors)]
        C --> B[BM25 keyword index<br/>in-memory]
    end

    subgraph Query["Query path"]
        Q[Natural language question] --> UI[Gradio UI]
        UI --> A[agent.py<br/>Gemini tool loop]
        A --> S[search_codebase]
        S --> H[Hybrid retrieval<br/>vector + BM25 merge]
        H --> V
        H --> B
        A --> T[read_file · run_code · review_file · explain_repo]
        T --> AN[Grounded answer + Repo/File citations]
    end
```

**Not:** `User → LLM → answer`

**Actually:**

```
Repository
  → file walker          (walker.py)
  → Tree-sitter parsing  (parser.py)
  → function/class chunks
  → SentenceTransformer embeddings
  → ChromaDB vector storage
  → BM25 keyword index
  → hybrid retrieval     (indexer.py)
  → Gemini agent + tools (agent.py)
  → grounded answer + citations
```

Most AI demos stop at the last arrow. ASTOR engineers everything before it.

---

## Evaluation

A fixed **20-question Flask benchmark** with expected files and functions. Retrieval and generation are scored independently — so you can tell whether a failure is search or the model.

| Script | Role |
|--------|------|
| `eval/questions.py` | 20 Flask questions + expected file/function targets |
| `eval/run_eval.py` | Runs all questions; reports retrieval vs. answer accuracy |
| `eval/inspect_retrieval.py` | Diagnoses failures into three buckets |
| `eval/debug_single.py` | Dumps agent message history for one question |

**Failure diagnosis** (`inspect_retrieval.py`):

| Bucket | Meaning |
|--------|---------|
| Not indexed | Expected file never entered ChromaDB |
| Not chunked | File indexed but expected function missing from chunks |
| Ranking failed | Chunk exists but hybrid search didn't surface it |

```bash
python eval/run_eval.py
python eval/inspect_retrieval.py
```

**Final benchmark (Flask codebase):**

| Metric | Score |
|--------|-------|
| Retrieval accuracy | **85%** (17/20) |
| Answer accuracy | **80%** (16/20) |

The ~25% → 85% retrieval jump came from fixing hybrid search — not from switching models.

---

## Engineering problems discovered and solved

These are the threads that separate ASTOR from an API wrapper.

### 1. Hybrid retrieval blocked by an early return

**Symptom:** Natural-language questions over code failed retrieval (~25% accuracy).

**Root cause:** `indexer.search()` returned early when vector similarity was weak. BM25 never ran — but keyword matching is exactly what rescues queries like *"Where is `add_url_rule`?"* against raw source text.

**Fix:** Always run vector search and BM25, merge and deduplicate by `(file, start_line)`, and fall back only when **both** signals fail (`top_similarity < 0.35` and BM25 score is zero).

**Impact:** Retrieval **25% → 85%**.

### 2. ChromaDB path depended on working directory

**Symptom:** Running eval from `eval/` silently opened an empty database. Metrics looked broken; the index was fine.

**Root cause:** `DB_PATH` was relative to the process cwd, not the project.

**Fix:** Resolve `DB_PATH` relative to `indexer.py` (`os.path.dirname(__file__)`).

**Impact:** Eval became trustworthy; multi-entry-point usage stopped diverging.

### 3. Indexing wasted work on large multi-repo sets

**Symptom:** Multi-repo indexing had poor progress feedback and long-running operations.

**Fixes (production-inspired, not production-scale):**
- Batched `SentenceTransformer.encode()` and single `collection.add()` write
- Dedup chunks when repo paths overlap or nest
- Per-repo caps (600 files / 4000 chunks) so one huge repo cannot starve others
- Skip high-noise dirs in `walker.py` (`tests/`, `docs/`, `migrations/`, venvs, `.git`, …)
- Stage-level progress logs (walk → parse → embed → DB write)

**Result:** Indexing responsiveness improved; a smaller multi-repo test (Flask + second repo) completed in **~52 seconds** with visible progress.

---

## Retrieval pipeline

`indexer.search()` is the core engineering surface:

| Step | Implementation |
|------|----------------|
| Vector search | `all-MiniLM-L6-v2` embeddings in persistent ChromaDB (`db/`) |
| Keyword search | `rank_bm25` over tokenized chunks; top-3 merged in |
| Dedup | Merge by `(file, start_line)` across both channels |
| Empty index | Returns `"Please index a repo first"` |
| Low confidence | Rephrase prompt only when vector **and** BM25 both fail |

Source citations flow through `tools.py` as `Repo:` / `File:` pairs, rendered as UI chips in `app.py`.

---

## Multi-repository support

Index one or two local Python repos from the UI. Each chunk stores `repo_name` in metadata; citations show which repository an answer came from.

**Example:** Ask *"How is routing handled?"* after indexing Flask and Django — compare framework-specific implementations with repo-aware citations.

---

## Reliability

Built with production-inspired practices for a local research tool:

| Area | Detail |
|------|--------|
| API errors | Gemini retry on failure; clean user-facing message instead of traceback |
| Tool timeouts | `explain_repo`: 90s · `review_file`: 60s · default: 30s |
| Code execution | `run_code` in isolated subprocess, **5-second timeout** (not a security sandbox) |
| File reads | Safe handling for missing paths and invalid line ranges |
| Agent limits | Step cap (8) · conversation history cap (30 messages) |
| Search guard | Duplicate `search_codebase` blocked per question |
| Empty state | Clear fallback when no repository is indexed |

---

## Features

| Area | Detail |
|------|--------|
| **Indexing** | Tree-sitter chunks at function/class boundaries |
| **Multi-repo** | Two repo inputs from UI; `repo_name` on every chunk |
| **Hybrid search** | ChromaDB semantic + BM25 keyword, merged |
| **Agent tools** | Search, read, run code, review file, explain repo |
| **Citations** | Repo-aware `Repo:` / `File:` pairs in answers |
| **UI** | Gradio app with thinking trace, starter questions, citation cards |

Backend retrieval and eval are the primary value; the UI is the entry point.

---

## Tech stack

| Layer | Tools |
|-------|-------|
| UI | Gradio, Markdown rendering |
| LLM | Google Gemini API (`google-genai`) |
| Vector store | ChromaDB (persistent) |
| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`) |
| Keyword search | `rank_bm25` |
| Parsing | Tree-sitter (`tree-sitter-python`) |
| Config | `python-dotenv` |

---

## Setup

**Prerequisites:** Python 3.10+, [Gemini API key](https://aistudio.google.com/apikey)

```bash
git clone <your-repo-url>
cd codebase-agent
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create `.env`:

```env
GEMINI_API_KEY=your_key_here
```

Run:

```bash
python app.py
```

Enter one or two local repository paths → **Index this repo** → ask a question.

Optional — regenerate README banner: `python scripts/generate_banner.py` (requires `pillow`).

---

## Project structure

```
codebase-agent/
├── app.py                 # Gradio UI, citations, index/ask handlers
├── agent.py               # Gemini tool loop (sync + streaming)
├── indexer.py             # ChromaDB + embeddings + BM25 hybrid search
├── parser.py              # Tree-sitter chunk extraction
├── walker.py              # File discovery + ignore rules
├── tools.py               # search_codebase, read_file, run_code
├── config.py              # Model name, step/history limits
├── rag.py                 # RAG baseline (search → single LLM call)
├── scripts/
│   └── generate_banner.py # README banner generator
├── features/
│   ├── onboarding.py      # explain_repo tool
│   ├── code_review.py     # review_file tool
│   └── status_messages.py # Thinking-trace strings
└── eval/
    ├── questions.py         # 20-question Flask benchmark
    ├── run_eval.py          # Retrieval + answer accuracy
    ├── inspect_retrieval.py # Failure diagnosis
    └── debug_single.py      # Single-question trace dump
```

---

## Limitations

Honest scope — portfolio-grade engineering project, not a deployed product at scale:

- **Python only** — `.py` files via Tree-sitter; no other languages
- **Local paths** — repos on disk; no GitHub URL cloning
- **Chunk granularity** — function/class level; cross-file reasoning depends on retrieval quality
- **Single-machine** — in-process ChromaDB + BM25; no distributed or incremental indexing
- **LLM dependency** — requires live Gemini API; no offline mode
- **Code execution** — `run_code` has a timeout, not full sandbox isolation

---

## Interview talking points

If you have 5 minutes on this repo:

1. **Why hybrid retrieval for code** — embeddings miss identifier-heavy queries; BM25 compensates; an early-return bug proved it (25% → 85%).
2. **Eval-driven debugging** — separate retrieval vs. generation metrics; three-bucket inspector localizes failures to indexing, chunking, or ranking.
3. **Silent persistence bug** — cwd-relative `DB_PATH` broke eval until path was anchored to `indexer.py`.
4. **Indexing efficiency** — batched embed/write, dedup, per-repo caps, directory filtering; ~52s on a smaller multi-repo test.
5. **Agent discipline** — tool timeouts, retry handling, single-search guard, citation propagation from tool results to UI.

---

**ASTOR** — built, measured, debugged, and improved as a retrieval system first.
