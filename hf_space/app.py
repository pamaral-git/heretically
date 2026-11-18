import os
import tempfile
import time

import gradio as gr
import pandas as pd

import heretically_core as core

_CSV_DIR = tempfile.mkdtemp(prefix="heretically_csv_")

DESCRIPTION = (
    "Explore and Discover Uncensored [Heretic](https://huggingface.co/models?other=heretic) tagged Models from Hugging Face\n"
    "🍴 Fork from Heretic Models Explorer. Inspired greatly by @p-e-w Heretic and Heretic Grimoire."
)

LINKS_MD = (
    "Fork of [Heretic Models Explorer](https://huggingface.co/spaces/MuXodious/Heretic-Models-Explorer), "
    "inspired by [Heretic](https://github.com/p-e-w/heretic). "
    "Links: [heretic-project.org](https://heretic-project.org/) · "
    "[Multilingual-Harmless-Harmful](https://huggingface.co/datasets/heretic-org/Multilingual-Harmless-Harmful) · "
    "[The-Mind-of-XORTRON](https://huggingface.co/datasets/darkc0de/The-Mind-of-XORTRON)"
)


def _empty_view():
    return pd.DataFrame(columns=core.DISPLAY_COLUMNS)


def _display_frame(frame):
    if frame is None or len(frame) == 0:
        return _empty_view()
    view = frame.copy()
    for column, digits in (
        ("KL Divergence", 4),
        ("Refusal Rate (%)", 1),
        ("Priority Score", 1),
        ("Sample Size", 0),
        ("Refusal Drop", 0),
    ):
        if column in view.columns:
            view[column] = pd.to_numeric(view[column], errors="coerce").round(digits)
    return view


def _weights(weight_values):
    return {
        criterion: float(value or 0)
        for criterion, value in zip(core.LEADERBOARD_CRITERIA, weight_values)
    }


def _build(rows, query, top_n_value, weight_values):
    if not rows:
        return _empty_view(), _empty_view(), 0, 0
    frame = pd.DataFrame(rows)
    frame = core.filter_by_query(frame, query)
    matched = len(frame)
    if matched == 0:
        return _empty_view(), _empty_view(), len(rows), 0
    ranked = core.build_leaderboard(
        frame,
        weights=_weights(weight_values),
        top_n=core.parse_top_n(top_n_value),
    )
    return _display_frame(ranked), ranked, len(rows), matched


def _plain_status(loaded, matched, total_weight):
    if loaded == 0:
        return "No models loaded yet. Click **Load trending (10)** or **Load all**."
    if total_weight <= 0:
        note = " All weights are zero, so every model gets a neutral score of 50."
    else:
        note = ""
    return (
        f"**{matched}** of **{loaded}** loaded models match the current search. "
        "Only models with parsed KL divergence and refusal metrics are shown." + note
    )


def _load_status(stats, loaded, matched, label):
    attempted = int(stats.get("attempted") or 0)
    metadata_total = int(stats.get("metadata_total") or 0)
    if loaded == 0:
        if attempted == 0:
            return f"⚠️ Hugging Face returned no heretic-tagged models for {label}."
        return (
            f"⚠️ Checked {attempted} {label} models, but none exposed parseable "
            "KL divergence and refusal metrics."
        )
    return (
        f"Loaded **{loaded}** of {attempted} checked models from **{label}** "
        f"({metadata_total} heretic-tagged models available). "
        f"**{matched}** match the current search. Only parsed models are shown."
    )


def _load_quick(query, top_n_value, *weight_values):
    try:
        rows, stats = core.load_trending(days=7, limit=10)
    except Exception as exc:
        return [], _empty_view(), f"⚠️ Could not load trending models: `{exc}`", None
    view, _, loaded, matched = _build(rows, query, top_n_value, weight_values)
    return (
        rows,
        view,
        _load_status(stats, loaded, matched, "trending (last 7 days)"),
        None,
    )


def _load_all(query, top_n_value, *weight_values):
    try:
        rows, stats = core.load_all()
    except Exception as exc:
        return [], _empty_view(), f"⚠️ Could not load all models: `{exc}`", None
    view, _, loaded, matched = _build(rows, query, top_n_value, weight_values)
    return (
        rows,
        view,
        _load_status(stats, loaded, matched, "all heretic-tagged models"),
        None,
    )


def _refresh(query, top_n_value, *weight_values):
    core.clear_caches()
    return _load_quick(query, top_n_value, *weight_values)


def _rerank(rows, query, top_n_value, *weight_values):
    view, _, loaded, matched = _build(rows, query, top_n_value, weight_values)
    return view, _plain_status(loaded, matched, sum(_weights(weight_values).values()))


def _prepare_csv(rows, query, top_n_value, *weight_values):
    _, ranked, _, _ = _build(rows, query, top_n_value, weight_values)
    payload = core.to_csv_bytes(ranked)
    if not payload:
        return None
    filename = f"heretically_leaderboard_{int(time.time() * 1000)}.csv"
    path = os.path.join(_CSV_DIR, filename)
    with open(path, "wb") as handle:
        handle.write(payload)
    return path


with gr.Blocks(title="Heretically") as demo:
    gr.Markdown("# 🔥 Heretically")
    gr.Markdown(DESCRIPTION)
    gr.Markdown(LINKS_MD)
    gr.Markdown(
        "**Only models with parsed KL divergence and refusal metrics are shown.** "
        "The quick scope parses at most 10 recent models on page load; "
        "**Load all** parses the full `heretic` tag and can take a few minutes. "
        "This Space runs on free `cpu-basic`: no GPU, ZeroGPU, or persistent storage."
    )

    rows_state = gr.State([])

    with gr.Row():
        quick_button = gr.Button("Load trending (10)", variant="primary")
        all_button = gr.Button("Load all")
        refresh_button = gr.Button("Refresh")

    status = gr.Markdown("Loading trending models (at most 10)...")

    with gr.Row():
        search = gr.Textbox(
            label="Search model ID",
            placeholder="e.g. Qwen, Llama, Mistral",
            scale=3,
        )
        top_n = gr.Dropdown(
            choices=["10", "25", "50", "100", "250", "All"],
            value="25",
            label="Top N",
            scale=1,
        )
        apply_button = gr.Button("Apply", scale=1)

    with gr.Accordion("Leaderboard weights", open=False):
        gr.Markdown(
            "Weights use percentile ranks, so one outlier cannot dominate. "
            "Set a weight to 0 to ignore that criterion."
        )
        weight_sliders = []
        for criterion, config in core.LEADERBOARD_CRITERIA.items():
            weight_sliders.append(
                gr.Slider(
                    minimum=0,
                    maximum=10,
                    value=float(config["default_weight"]),
                    step=0.5,
                    label=criterion,
                    info=config["help"],
                )
            )

    leaderboard = gr.Dataframe(
        value=_empty_view(),
        label="Ranked models",
        interactive=False,
        wrap=True,
    )

    with gr.Row():
        csv_button = gr.Button("Prepare CSV")
        csv_file = gr.File(label="Download ranked CSV")

    load_inputs = [search, top_n] + weight_sliders
    rerank_inputs = [rows_state, search, top_n] + weight_sliders
    load_outputs = [rows_state, leaderboard, status, csv_file]
    rerank_outputs = [leaderboard, status]

    quick_button.click(_load_quick, inputs=load_inputs, outputs=load_outputs)
    all_button.click(_load_all, inputs=load_inputs, outputs=load_outputs)
    refresh_button.click(_refresh, inputs=load_inputs, outputs=load_outputs)

    apply_button.click(_rerank, inputs=rerank_inputs, outputs=rerank_outputs)
    search.submit(_rerank, inputs=rerank_inputs, outputs=rerank_outputs)
    top_n.change(_rerank, inputs=rerank_inputs, outputs=rerank_outputs)
    for slider in weight_sliders:
        slider.change(_rerank, inputs=rerank_inputs, outputs=rerank_outputs)

    csv_button.click(_prepare_csv, inputs=rerank_inputs, outputs=csv_file)
    demo.load(_load_quick, inputs=load_inputs, outputs=load_outputs)


if __name__ == "__main__":
    demo.launch()
