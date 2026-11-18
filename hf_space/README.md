---
title: Heretically
emoji: 🔥
colorFrom: yellow
colorTo: red
sdk: gradio
app_file: app.py
pinned: false
license: mit
short_description: Discover uncensored Heretic models on Hugging Face
---

# Heretically

Explore and Discover Uncensored Heretic tagged Models from Hugging Face.

Heretically is a Gradio leaderboard for models tagged
[`heretic`](https://huggingface.co/models?other=heretic). It reads the
`reproduce/reproduce.json` files written by Heretic 2.x (`scores`, schema v4),
falls back to legacy 1.x `metrics`, and finally falls back to parsing KL
divergence and refusal fractions from each model card. Models without parsed
metrics are hidden.

- **Quick scope (default):** models from the last 7 days, top 10 by downloads
  then likes, with fallback fill. The page auto-loads at most 10 models.
- **Load all:** parses every model carrying the `heretic` tag. This can take a
  few minutes and is never run at boot.
- **Leaderboard:** seven criteria are converted to percentile ranks and combined
  with adjustable weights into a 0-100 priority score. Search by model ID, pick
  top N, and download the current ranking as CSV.
- **Metadata:** Heretic 2.x/1.x detection, initial vs tuned refusals, sample
  size, likes, downloads, and model links.

## Free-tier note

This Space runs on free `cpu-basic`. It needs **no GPU, no ZeroGPU, and no
persistent storage**. All caches are in memory: metadata is cached for one hour
and per-model parsing is cached in-process. A cold start or refresh parses at
most the quick scope first.

## Credits and links

- Fork of [Heretic Models Explorer](https://huggingface.co/spaces/MuXodious/Heretic-Models-Explorer).
- Inspired by [Heretic](https://github.com/p-e-w/heretic) and the
  [Heretic Grimoire](https://huggingface.co/spaces/heretic-org/Heretic-Grimoire).
- Project: <https://heretic-project.org/>
- Dataset: [heretic-org/Multilingual-Harmless-Harmful](https://huggingface.co/datasets/heretic-org/Multilingual-Harmless-Harmful)
- Dataset: [darkc0de/The-Mind-of-XORTRON](https://huggingface.co/datasets/darkc0de/The-Mind-of-XORTRON)
