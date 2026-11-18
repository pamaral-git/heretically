# 🔥 Heretically

Explore and Discover Uncensored [Heretic](https://huggingface.co/models?other=heretic) tagged Models from Hugging Face.

Fork of [Heretic Models Explorer](https://huggingface.co/spaces/MuXodious/Heretic-Models-Explorer), inspired by [@p-e-w](https://github.com/p-e-w)'s [Heretic](https://github.com/p-e-w/heretic) and [Heretic Grimoire](https://huggingface.co/spaces/heretic-org/Heretic-Grimoire).

**Quick Start:**
- ☁️ **Streamlit Cloud**: https://heretically.streamlit.app (`app.py`)
- 🤗 **Hugging Face Public Space**: [`hf_space/`](hf_space/) standalone Gradio app (`python hf_space/publish_space.py`)
- 🐳 **Docker Self-host (Local)**: `git clone` → `docker compose up --pull always --build -d` → `http://localhost:8501`

🛠️ **Comparative Improvements:**

| Domain | Change | Impact |
| :--- | :--- | :--- |
| **Editorial UI** | Warm-Paper Design System | Light warm-paper palette (`#F7F4EE` paper, `#FDFBF7` cards, `#EFE9DF` raised, `#C2410C` ember) with `.streamlit/config.toml` + `Newsreader`, `Instrument Sans`, and `JetBrains Mono` typography. |
| **Fast Boot** | `25 (Top past month)` Pre-loader | `src/heretically_preloader.py` parses only the top 25 models from the last 30 days by downloads/likes on cold start (with `Created` → `LastModified` fallback and backfill), while `10 (Trending 7d)`, `50`, `100`, and `All` remain selectable. |
| **Toolbar & KPIs** | Compact 2-Tier Bar + KPI Strip | Inline Search, Sort, Load Scope, Release Date, Unknowns handling, Heretic generation pills, GGUF/quant toggle, and a 4-card KPI strip (`Models Shown`, `Heretic 2.x Share`, `Median KL`, `Lowest Refusal`). |
| **Caching** | Dedicated Popularity Store | Decoupled likes and downloads into `src/popularity_store.py` and `data/popularity.json` (persisted across rebuilds via `./data:/app/data`), avoiding expensive README/JSON re-parses when popularity changes. |
| **Analytics** | Adaptive Metrics & Flags | Adaptive KL bands (corpus tertiles with static fallback), median-based sample floors, 0%-refusal anomaly flags, plus derived `Refusal Drop` and `Sample Size` columns. |
| **Metadata** | Heretic v2 Detection | Reads plugin-based `reproduce.json` schema v4 (`environment.heretic.version`, `scores`) for Heretic 2.x, keeps legacy v1.x `metrics` support, falls back to model-card "made using Heretic vX" parsing, and exposes **Heretic Version / Gen / Version Source** columns. |
| **Ranking** | Priority Leaderboard | Candidate filters, 7 percentile-ranked criterion sliders (`0–100` Priority Score), Top Ranked Spotlight & Active Weights cards, CSV export, `Directional Ablation Trade-off Matrix` reference, and `Corpus Distribution Charts`. |
| **HF Space** | Standalone Gradio Package | Self-contained [`hf_space/`](hf_space/) Gradio leaderboard for the free `cpu-basic` tier with zero persistent storage and one-command public Space publishing. |

---

## Publishing & Deployment

### 1. GitHub
```bash
git status
git add .
git commit -m "Update Heretically UI, preloader, and HF Space config"
git push origin main
```

### 2. Streamlit Community Cloud
1. Connect repository `pamaral-git/heretic-model-explorer` on branch `main`.
2. Set **Main file path** to `app.py` (synced 1:1 with `src/streamlit_app.py`; theme loaded automatically from `.streamlit/config.toml`).

### 3. Hugging Face Public Spaces

**Option A — Free-tier Gradio Space (`hf_space/`, recommended for `cpu-basic`):**
```bash
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
# Optional; defaults to <your-hf-username>/heretically
export HF_SPACE_REPO=<your-hf-username>/heretically
python3 hf_space/publish_space.py
```
This creates a **public** Gradio Space (`private=False`) and uploads [`hf_space/`](hf_space/) cleanly while skipping caches and macOS metadata files.

**Option B — Upstream PR / Streamlit Space (`open_pr.py`):**
To propose changes upstream to `MuXodious/Heretic-Models-Explorer`, authenticate with `hf auth login` (or `HF_TOKEN`) and run:
```bash
python3 open_pr.py
```
If deploying the root `Dockerfile` directly as an HF Docker Space (`sdk: docker`), set `app_port: 8501` in that Space's `README.md` YAML frontmatter.

---

ℹ️ **Date Logic:** `Created` prefers Hugging Face's `created_at` and falls back to `last_modified` when a model has no creation date, so fewer models land in the unknown-date bucket.

🤗 **Reference:** [HuggingFace PR](https://huggingface.co/spaces/MuXodious/Heretic-Models-Explorer/commit/c5a3505f2df7445adcf61799902d1506906cd645)
