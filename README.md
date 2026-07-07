<p align="right">
  <img src="docs/assets/astor-logo.png" alt="ASTOR Logo" width="160"/>
</p>

<div align="center">
  <img src="docs/assets/astor-banner.png" width="100%" alt="ASTOR Banner"/>
</div>

<br/>

<div align="center">

### Retrieval-first AI Codebase Agent 
<strong>Ask anything about any codebase. Get grounded answers with source citations.</strong> 
Not a chatbot wrapper. A full retrieval pipeline that reads code the way engineers do. 
</div>

<br/>

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Gemini-Tool_Calling-4285F4?logo=google&logoColor=white"/>
  <img src="https://img.shields.io/badge/ChromaDB-Vector_Store-FF6F00"/>
  <img src="https://img.shields.io/badge/Retrieval-Hybrid_BM25_+_Vector-6366F1"/>
  <img src="https://img.shields.io/badge/Eval-85%25_Answer_Accuracy-22C55E"/>
  <img src="https://img.shields.io/badge/UI-Gradio-F97316"/>
</div>

<br/>

<div align="center">
  <a href="https://huggingface.co/spaces/ananyasrivastavaa9/ASTOR-AI-Codebase-Agent"><strong>🔗 Try Live Demo</strong></a>
  &nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="#quick-start"><strong>📦 Run Locally</strong></a>
  &nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="#benchmark"><strong>📊 Benchmark Results</strong></a>
</div>

---

## What ASTOR does

| Ask this | ASTOR does this |
|----------|----------------|
| *"Where is the bug in this error?"* | Traces the traceback → finds the exact line → explains the fix |
| *"Explain this repo to me"* | Reads entry points → generates a guided tour in 60 seconds |
| *"Review this file"* | Structured feedback like a senior engineer |
| *"How is routing handled?"* | Searches semantically + by keyword → cites exact file and line |
| *"Compare routing across Flask and Django"* | Multi-repo search with repo-aware citations |

---

## See it in action

> ASTOR in action — indexing, retrieval, debugging, and code understanding.

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/assets/demo-ask.gif" width="100%" style="border-radius:8px"/><br/>
      <sub><b>Ask a question — live retrieval trace</b></sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/assets/demo-bug.gif" width="100%" style="border-radius:8px"/><br/>
      <sub><b>Bug detective — paste error, get fix</b></sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/assets/demo-review.gif" width="100%" style="border-radius:8px"/><br/>
      <sub><b>Code review — structured feedback</b></sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/assets/demo-onboard.gif" width="100%" style="border-radius:8px"/><br/>
      <sub><b>Repo onboarding — 60 second tour</b></sub>
    </td>
  </tr>
</table>

---

## Benchmark

> Most AI projects ship without measuring retrieval quality. ASTOR has a fixed benchmark.

Tested on **20 questions about the Flask codebase** with known expected files and functions.

| Metric | Score |
|--------|-------|
| Retrieval accuracy | **85%** (17/20) |
| Answer accuracy | **80%** (16/20) |
| Improvement from hybrid search fix | **25% → 85%** |

Retrieval and generation scored **separately** — tells you exactly where failures happen.

```bash
python eval/run_eval.py          # full benchmark
python eval/inspect_retrieval.py # failure diagnosis
```

---

## The problem

Pasting code into ChatGPT fails at scale:
- Context windows truncate large repos
- Models hallucinate file paths and function names
- No verifiable source citations
- Degrades to "plausible guess" not "proven fact"

### The solution: retrieval first

Instead of `User → LLM → Answer`, ASTOR runs:

```
User question
    ↓
Indexing pipeline (once per repo)
  walker.py   → discover files, skip tests / venvs / .git
  parser.py   → Tree-sitter chunks at function/class boundaries
  indexer.py  → ChromaDB vectors + BM25 keywords
    ↓
Hybrid search (every query)
  ChromaDB semantic top-3 + BM25 keyword top-3
  merge · dedupe · confidence gate
    ↓
Gemini agent tools
  search_codebase  read_file  run_code  review_file  explain_repo
    ↓
Grounded answer with Repo: / File: citations
```

---

## Architecture

```
┌─────────────────── INDEX (once per repo) ──────────────────┐
│                                                            │
│  repo path ──► walker.py ──► parser.py ──► chunks          │
│                                  │                         │
│                    SentenceTransformer (all-MiniLM-L6-v2)  │
│                         ├──► ChromaDB  (persistent)        │
│                         └──► BM25 index (in-memory)        │
│                                                            │
└────────────────────────────────────────────────────────────┘

┌─────────────────── QUERY (every question) ─────────────────┐
│                                                            │
│  question ──► agent.py ──► tools ──► indexer.search()      │
│                                           │                │
│                           vector top-3 + BM25 top-3        │
│                           merge · dedupe · fallback        │
│                                           │                │
│                         answer + Repo / File citations     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

| Component | File | Role |
|-----------|------|------|
| File discovery | `walker.py` | Walk repo, skip noise |
| AST parsing | `parser.py` | Tree-sitter function/class chunks |
| Hybrid search | `indexer.py` | ChromaDB + BM25 merge |
| Agent loop | `agent.py` | Gemini tool-calling, retries, step limits |
| Tools | `tools.py` | search · read · run · review · explain |
| UI | `app.py` | Gradio — index, ask, citation cards |

---

## Key engineering decisions

### Why tree-sitter instead of line splitting?

Naive chunking cuts functions in half. A half-function is meaningless to an LLM. Tree-sitter reads Python grammar and splits at actual function and class boundaries — one complete, meaningful unit per chunk. This is the single biggest factor in retrieval quality.

### Why hybrid search (vector + BM25)?

Vector search finds semantically similar code but misses exact identifier matches. BM25 finds exact keywords but misses paraphrased queries. Running both and merging results covers cases neither handles alone. This fixed a 25% → 85% retrieval jump in the benchmark.

### Why the ReAct agent loop instead of single-shot RAG?

Single RAG makes one retrieval call and answers. The ReAct loop lets the agent think, call a tool, see the result, and decide what to do next — exactly like a developer would. This enables multi-step reasoning: search → read the file → verify → answer. The difference shows most on complex questions that need 2+ tool calls.

---

## Features

| Feature | What it does |
|---------|-------------|
| **Hybrid retrieval** | ChromaDB semantic + BM25 keyword, merged and deduped |
| **AST-aware chunks** | Tree-sitter function/class boundaries — not line splits |
| **Bug detective** | Paste error → traces traceback → explains fix |
| **Code review** | Structured feedback: Issues / Security / Suggestions / Good parts |
| **Repo onboarding** | Guided tour of any codebase in 60 seconds |
| **Multi-repo search** | Index 2 repos, search across both with repo-aware citations |
| **Live execution trace** | Shows retrieval and tool progress |

---

## Quick start

**Requires:** Python 3.10+, [Gemini API key](https://aistudio.google.com/apikey)

```bash
git clone https://github.com/ananyaSrivastavaa9/ASTOR-AI-Codebase-Agent.git
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

Enter one or two local repo paths → index → ask anything.

---

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | Gemini (`google-genai`) | Function calling + agent workflows |
| Vectors | ChromaDB | Persistent, local, no server |
| Embeddings | `all-MiniLM-L6-v2` | Fast, accurate, runs locally |
| Keywords | `rank_bm25` | Exact identifier search |
| Parsing | Tree-sitter | AST-level code chunking |
| UI | Gradio | Fast to build, HuggingFace native |

---

## Agent reliability

| Control | Detail |
|---------|--------|
| API failures | Retry with clean error surface |
| Step limit | 8 agent steps per question |
| History cap | 30 messages |
| Tool timeouts | explain_repo 90s · review_file 60s · default 30s |
| run_code | Subprocess · 5s timeout |
| Empty index | `"Please index a repo first"` fallback |
| Search guard | One `search_codebase` call per question |

---

## Project structure

```
codebase-agent/
├── app.py                    # Gradio UI
├── agent.py                 # Gemini ReAct agent loop
├── indexer.py               # ChromaDB + BM25 retrieval
├── parser.py                # Tree-sitter AST chunks
├── walker.py                # Repository scanner
├── tools.py                 # Agent tools
├── config.py                # Runtime configuration
├── rag.py                   # RAG baseline
├── requirements.txt
│
├── features/
│   ├── bug_detective.py
│   ├── code_review.py
│   └── onboarding.py
│
├── eval/
│   ├── questions.py
│   ├── run_eval.py
│   └── inspect_retrieval.py
│
├── docs/
│   └── assets/
│       ├── astor-banner.png
│       └── astor-logo.png
│
└── scripts/
    └── generate_banner.py
```

---

## Limitations

- Python only (`.py` files)
- Local paths only — no GitHub URL cloning
- In-process ChromaDB — no distributed indexing
- Live Gemini API required — no offline mode
- `run_code` uses timeout only, not full sandbox

---

<div align="center">
  <sub>Measured, debugged, and improved as a retrieval system — not a chatbot wrapper.</sub>
</div>