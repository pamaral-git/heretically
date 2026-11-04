# [Heretically](https://heretically.streamlit.app) ◦ Uncensored AI Explorer 🔥

Heretic model discovery and comparative ranking based on HuggingFace.

Fork from [Heretic Models Explorer](https://huggingface.co/spaces/MuXodious/Heretic-Models-Explorer). Inspired greatly by [@p-e-w](https://github.com/p-e-w) [Heretic](https://github.com/p-e-w/heretic) and [Heretic Grimoire](https://huggingface.co/spaces/heretic-org/Heretic-Grimoire).

**Quick Start:**
- ☁️ Web Preview (Cloud): https://heretically.streamlit.app
- 🐳 Docker Self-host (Local): `git clone` → `docker compose up --pull always --build -d` → `http://localhost:8501`

🛠️ **Comparative Improvements:**

| Domain | Change | Impact |
| :--- | :--- | :--- | 
| **Performance** | Load Optimisation | More Parameters and filtering by Release date , Unknown dates and `?unknowns=` + Skips parsing ~2,000 files on boot. |
| **Caching** | Dedicated Popularity Store | Decoupled likes and downloads into `src/popularity_store.py` and `data/popularity.json` + Metadata syncs + Sidebar updating. |
| **Analytics** | Metric Dashboards | Replaced simple KL/Refusal badges with KL bands (0.01, 0.05, 0.15) and sample floors ($n < 50$) + Flagging 0% refusal rates that have high-divergence/low-sample. |

⚠️ **Current Limitations:** Date Logic (relies strictly on `created_at` and no fallback to `last_modified`) and Heuristics (static KL bands and sample floors without dynamic tuning).

🤗 **Reference:** [HuggingFace PR](https://huggingface.co/spaces/MuXodious/Heretic-Models-Explorer/commit/c5a3505f2df7445adcf61799902d1506906cd645)
