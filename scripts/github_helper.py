import os
import subprocess
from pathlib import Path
from github import Github, Auth, GithubException, UnknownObjectException

from scripts.config import GITHUB_REPO, POSTS_DIR, DRY_RUN


def get_github_token():
    """Retrieve GitHub token from environment variable or gh CLI."""
    token = os.getenv('GITHUB_TOKEN')
    if token and token != "ghp_your_personal_access_token_here":
        return token

    try:
        gh_token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip()
        if gh_token:
            return gh_token
    except Exception:
        pass

    return None


def get_github_repo():
    """Initialize Github API client and return target repository."""
    token = get_github_token()
    if not token:
        raise ValueError("GitHub Token not found. Log in with `gh auth login` or set GITHUB_TOKEN.")

    auth = Auth.Token(token)
    gh_client = Github(auth=auth)
    return gh_client.get_repo(GITHUB_REPO)


def publish_to_github(repo, filename, content, subject):
    """Publish or update Markdown post in target GitHub repository."""
    path = f"{POSTS_DIR}/{filename}" if POSTS_DIR else filename
    commit_message = f"Add newsletter: {subject}"

    if DRY_RUN or repo is None:
        local_path = Path(path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content, encoding='utf-8')
        print(f"[DRY-RUN] Saved post locally to: {local_path.resolve()}")
        return

    try:
        existing_file = repo.get_contents(path)
        print(f"[INFO] Updating existing post on GitHub: {path}")
        repo.update_file(
            path=path,
            message=f"Update newsletter: {subject}",
            content=content,
            sha=existing_file.sha
        )
        print(f"[SUCCESS] Updated post on GitHub: {path}")
    except (UnknownObjectException, GithubException) as ge:
        if getattr(ge, 'status', None) in (404,):
            print(f"[INFO] Creating new post on GitHub: {path}")
            try:
                repo.create_file(path=path, message=commit_message, content=content)
                print(f"[SUCCESS] Created post on GitHub: {path}")
                return
            except Exception as create_err:
                print(f"[WARNING] Create file failed ({create_err}), attempting update fallback...")

        # SHA mismatch or conflict fallback: fetch latest sha and update
        try:
            latest = repo.get_contents(path)
            repo.update_file(path=path, message=f"Update newsletter: {subject}", content=content, sha=latest.sha)
            print(f"[SUCCESS] Updated post on GitHub (with fresh SHA): {path}")
        except Exception as err:
            print(f"[ERROR] Could not publish post '{path}' to GitHub: {err}")
