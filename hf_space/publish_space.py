import os
from pathlib import Path

from huggingface_hub import HfApi, get_token

HERE = Path(__file__).resolve().parent
IGNORE_PATTERNS = [
    "publish_space.py",
    "tests_core.py",
    "__pycache__",
    "__pycache__/*",
    "*.pyc",
    ".git*",
    "._*",
    "**/._*",
    ".DS_Store",
    "**/.DS_Store",
]


def resolve_repo_id(api, token):
    repo_id = os.environ.get("HF_SPACE_REPO", "USER/heretically").strip()
    if not repo_id:
        repo_id = "USER/heretically"
    if repo_id.upper().startswith("USER/"):
        try:
            username = (api.whoami(token=token) or {}).get("name")
        except Exception as exc:
            raise SystemExit(
                "Set HF_SPACE_REPO=username/space-name (or log in with `hf auth login`)."
            ) from exc
        if not username:
            raise SystemExit("Could not determine your Hugging Face username.")
        repo_id = f"{username}/{repo_id.split('/', 1)[1]}"
    if "/" not in repo_id:
        raise SystemExit("HF_SPACE_REPO must look like username/space-name.")
    return repo_id


def main():
    token = os.environ.get("HF_TOKEN") or get_token()
    api = HfApi(token=token)
    repo_id = resolve_repo_id(api, token)

    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="gradio",
        private=False,
        exist_ok=True,
        token=token,
    )
    api.update_repo_settings(
        repo_id=repo_id,
        repo_type="space",
        private=False,
        token=token,
    )
    api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=str(HERE),
        ignore_patterns=IGNORE_PATTERNS,
        commit_message="Deploy Heretically Gradio leaderboard",
        token=token,
    )
    print(f"Space published: https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    main()
