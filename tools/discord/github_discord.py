"""Publish only the Discord README link and original brand badge in two repos."""
import argparse
import base64
import difflib
import json
from pathlib import Path
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INVITE = json.loads((HERE / "public-invite.json").read_text())["url"]
REPOS = {
    "workspace": ("GurekamDhillon/gd-melee-workspace", "master", "docs/readme/brand/discord.svg"),
    "game": ("GurekamDhillon/melee", "pc-port", "pc/docs/readme/brand/discord.svg"),
}


def save(name, value):
    path = HERE / name
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def api(repo, endpoint, method="GET", payload=None):
    if repo not in {v[0] for v in REPOS.values()}:
        raise ValueError("Unexpected repo")
    command = ["gh", "api", "repos/" + repo + "/" + endpoint, "--method", method]
    if payload is not None:
        command += ["--input", str(save("github-request.json", payload))]
    result = subprocess.run(command, capture_output=True, encoding="utf-8", check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


def decode(response):
    return base64.b64decode(response["content"]).decode("utf-8")


def prepare(key):
    repo, branch, badge_path = REPOS[key]
    head = api(repo, "git/ref/heads/" + branch)["object"]["sha"]
    tree = api(repo, "git/commits/" + head)["tree"]["sha"]
    response = api(repo, "contents/README.md?ref=" + head)
    before = decode(response)
    if INVITE in before:
        raise RuntimeError("Discord invite already present; inspect before proceeding")
    lines = before.splitlines(keepends=True)
    license_index = next(i for i, line in enumerate(lines) if '<img alt="License' in line)
    newline = "\r\n" if lines[license_index].endswith("\r\n") else "\n"
    lines.insert(license_index, f'  <a href="{INVITE}"><img alt="Join GD\'s Workshop on Discord" src="{badge_path}" height="28"></a>{newline}')
    closing_index = next(i for i in range(license_index + 1, len(lines)) if "</p>" in lines[i])
    lines.insert(closing_index + 1, newline + f'<p align="center">Join <a href="{INVITE}">GD\'s Workshop on Discord</a> for matchmaking, setup help, bug reports, and modding.</p>{newline}')
    after = "".join(lines)
    badge = (ROOT / "menu/out_brand/badges/discord.svg").read_text(encoding="utf-8")
    assert after.count(INVITE) == 2
    assert "<svg" in badge and "<script" not in badge
    (HERE / (key + "-README-before.md")).write_text(before, encoding="utf-8", newline="")
    (HERE / (key + "-README-after.md")).write_text(after, encoding="utf-8", newline="")
    proposal = {"repo": repo, "branch": branch, "parent": head, "tree": {
        "base_tree": tree, "tree": [
            {"path": "README.md", "mode": "100644", "type": "blob", "content": after},
            {"path": badge_path, "mode": "100644", "type": "blob", "content": badge},
        ]}}
    save(key + "-github-proposal.json", proposal)
    print("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=repo + "/README.md", tofile=repo + "/README.md")))
    print("New badge: " + badge_path)


def publish(key):
    repo, branch, badge_path = REPOS[key]
    proposal = json.loads((HERE / (key + "-github-proposal.json")).read_text(encoding="utf-8"))
    assert proposal["repo"] == repo and proposal["branch"] == branch
    assert {e["path"] for e in proposal["tree"]["tree"]} == {"README.md", badge_path}
    if api(repo, "git/ref/heads/" + branch)["object"]["sha"] != proposal["parent"]:
        raise RuntimeError("Branch changed since review; prepare again")
    tree = api(repo, "git/trees", "POST", proposal["tree"])
    commit = api(repo, "git/commits", "POST", {
        "message": "docs: link the Discord community\n\nCo-Authored-By: Codex <noreply@openai.com>",
        "tree": tree["sha"], "parents": [proposal["parent"]],
    })
    change = api(repo, "commits/" + commit["sha"])
    assert {f["filename"] for f in change["files"]} == {"README.md", badge_path}
    assert all(f["status"] in {"added", "modified"} for f in change["files"])
    api(repo, "git/refs/heads/" + branch, "PATCH", {"sha": commit["sha"], "force": False})
    for entry in proposal["tree"]["tree"]:
        assert decode(api(repo, "contents/" + entry["path"] + "?ref=" + branch)) == entry["content"]
    report = {"repo": repo, "branch": branch, "commit": commit["sha"], "url": change["html_url"], "invite": INVITE,
              "files": [f["filename"] for f in change["files"]], "verified": True}
    save(key + "-github-published.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "publish"])
    parser.add_argument("repo", choices=REPOS)
    args = parser.parse_args()
    {"prepare": prepare, "publish": publish}[args.action](args.repo)
