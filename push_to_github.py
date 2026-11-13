import os
import sys
from dulwich import porcelain
from dulwich.repo import Repo

REPO_PATH = os.path.abspath(os.path.dirname(__file__))
USERNAME = "fathimafarhana8714-rgb"
REPO_NAME = "rental-properties"

# Token from command line argument, environment variable, or interactive prompt
TOKEN = None
if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
    TOKEN = sys.argv[1]
elif "GITHUB_TOKEN" in os.environ:
    TOKEN = os.environ["GITHUB_TOKEN"]

if not TOKEN:
    print("No token provided. Please run as: python push_to_github.py <GITHUB_TOKEN>")
    print("Or set GITHUB_TOKEN environment variable.")
    try:
        TOKEN = input("Enter GitHub Personal Access Token: ").strip()
    except Exception:
        pass

if not TOKEN:
    print("[ERROR] GitHub token is required to push.")
    sys.exit(1)

REMOTE_URL = f"https://{USERNAME}:{TOKEN}@github.com/{USERNAME}/{REPO_NAME}.git"

print("=" * 60)
print(f"NEST KERALA - Push to GitHub ({USERNAME}/{REPO_NAME})")
print("=" * 60)
print(f"Repository Path: {REPO_PATH}")

try:
    repo = Repo(REPO_PATH)
except Exception as e:
    print(f"Error opening repo: {e}")
    sys.exit(1)

# Stage files
print("Staging modified and new files...")
staged = []
for root, dirs, files in os.walk(REPO_PATH):
    if any(ig in root for ig in [".venv", ".git", "__pycache__", "instance", ".pytest_cache"]):
        continue
    for file in files:
        if file.endswith((".pyc", ".db", ".sqlite3")) or file.startswith(".ssh_key") or file.startswith("id_ed25519") or file == "ssh_key_output.txt":
            continue
        rel_path = os.path.relpath(os.path.join(root, file), REPO_PATH).replace("\\", "/")
        staged.append(rel_path)

porcelain.add(repo, paths=staged)
print(f"Staged {len(staged)} files.")

# Check for commit
status = porcelain.status(repo)
has_changes = bool(status.staged['add'] or status.staged['modify'] or status.staged['delete'])

if has_changes:
    try:
        commit_id = porcelain.commit(
            repo,
            message=b"Add push helper script and update project configuration",
            author=b"Fathima Farhana <fathimafarhana8714@gmail.com>",
            committer=b"Fathima Farhana <fathimafarhana8714@gmail.com>"
        )
        print("Committed changes:", commit_id.decode() if isinstance(commit_id, bytes) else commit_id)
    except Exception as e:
        print(f"Commit note: {e}")
else:
    print("Working tree clean, no new commit needed.")

# Ensure HEAD is pointing to main
repo.refs[b'refs/heads/main'] = repo.head()
print(f"Active commit on main: {repo.head().decode('ascii')}")

# Push to rental-properties
print(f"\nPushing to GitHub (https://github.com/{USERNAME}/{REPO_NAME})...")
try:
    porcelain.push(repo, REMOTE_URL, refspecs=b"refs/heads/main:refs/heads/main", force=True)
    print(f"\n[SUCCESS] Code successfully pushed to https://github.com/{USERNAME}/{REPO_NAME} on branch main!")
except Exception as e:
    print(f"\n[ERROR] Push failed: {e}")
    sys.exit(1)
