from huggingface_hub import HfApi, CommitOperationAdd

api = HfApi()
repo = "MuXodious/Heretic-Models-Explorer"

ops = [
    CommitOperationAdd("src/streamlit_app.py", "src/streamlit_app.py"),
    CommitOperationAdd("src/popularity_store.py", "src/popularity_store.py"),
    CommitOperationAdd("src/heretically_preloader.py", "src/heretically_preloader.py"),
    CommitOperationAdd("app.py", "app.py"),
    CommitOperationAdd(".streamlit/config.toml", ".streamlit/config.toml"),
    CommitOperationAdd("data/popularity.json", "data/popularity.json"),
    CommitOperationAdd("requirements.txt", "requirements.txt"),
    CommitOperationAdd("Dockerfile", "Dockerfile"),
    CommitOperationAdd("docker-compose.yml", "docker-compose.yml"),
    CommitOperationAdd(".dockerignore", ".dockerignore"),
    CommitOperationAdd("README.md", "README.md"),
]

info = api.create_commit(
    repo_id=repo,
    repo_type="space",
    operations=ops,
    commit_message="feat: warm-paper redesign, past-month preloader, popularity store, Heretic v2 leaderboard",
    commit_description=(
        "Warm-paper editorial theme (.streamlit/config.toml), 25 (Top past month) preloader "
        "with Created/LastModified fallback, popularity_store in data/popularity.json, "
        "Heretic 2.x schema v4 metadata + percentile Leaderboard."
    ),
    create_pr=True,
)
print(info.pr_url or "check Discussions tab")
