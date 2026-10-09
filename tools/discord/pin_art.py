"""Audit and replace the bot's pinned information posts with brand kit panels."""
import hashlib
import json
from pathlib import Path
import re

from discord_setup import GUILD_ID, GUILD, HERE, ROOT, ScopeError, Setup, save_json

OUTPUT = ROOT / "menu/out_discord_pins"
TITLES = {
    "welcome": "WELCOME TO THE WORKSHOP", "rules": "WORKSHOP RULES", "announcements": "PROJECT UPDATES",
    "downloads": "GET GD'S MELEE", "introductions": "INTRODUCTIONS", "showcase": "CLIPS & CREATIONS",
    "suggestions": "SUGGESTIONS", "matchmaking": "FIND YOUR NEXT SET", "training": "TRAINING & LAB",
    "modding": "MODS & SCRIPTS", "staff_chat": "STAFF DESK", "help": "SETUP & SUPPORT", "bugs": "REPORT A BUG",
}


def materialize(setup, message, channel, key, forum=False):
    chunks = [message.get("content", "")] + [e.get("description", "") for e in message.get("embeds", [])]
    original = "\n\n".join(t for t in chunks if t)
    if not original:
        return None
    names = {c["id"]: c["name"] for c in setup.snapshot["channels"]}
    buttons, seen = [], set()
    for label, url in re.findall(r"\[([^]]+)\]\((https://[^)]+)\)", original):
        if url not in seen:
            buttons.append({"label": label, "url": url})
            seen.add(url)
    for cid in re.findall(r"<#([0-9]+)>", original):
        if cid not in names:
            raise ScopeError("Message references a channel outside the inspected server")
        url = f"https://discord.com/channels/{GUILD_ID}/{cid}"
        if url not in seen:
            buttons.append({"label": "#" + names[cid], "url": url})
            seen.add(url)
    text = re.sub(r"<#([0-9]+)>", lambda m: "#" + names[m[1]], original)
    return {"key": key, "title": TITLES.get(key, channel["name"].upper().replace("-", " ")),
            "text": text, "buttons": buttons, "channel_name": channel["name"], "channel_id": channel["id"],
            "message_id": message["id"], "forum": forum, "original_digest": hashlib.sha256(original.encode()).hexdigest()}


def audit(setup):
    id_to_key = {v["id"]: k for k, v in setup.state["messages"].items()}
    source, originals = [], []
    for channel in setup.snapshot["channels"]:
        if channel["type"] not in {0, 5}:
            continue
        pins = setup.api.request("GET", f"/channels/{channel['id']}/messages/pins")["items"]
        for pin in pins:
            message = pin["message"]
            if message.get("author", {}).get("id") != setup.snapshot["bot_id"]:
                continue
            key = id_to_key.get(message["id"], channel["name"] + "-" + message["id"])
            post = materialize(setup, message, channel, key)
            if post:
                source.append(post)
                originals.append(message)
    threads = setup.api.request("GET", GUILD + "/threads/active")["threads"]
    for thread in threads:
        if thread.get("guild_id") != GUILD_ID or not thread.get("flags", 0) & 2 or thread.get("owner_id") != setup.snapshot["bot_id"]:
            continue
        parent = next(c for c in setup.snapshot["channels"] if c["id"] == thread["parent_id"])
        setup.api.scope.channel_ids.add(thread["id"])
        messages = setup.api.request("GET", f"/channels/{thread['id']}/messages?limit=100")
        message = min((m for m in messages if m.get("author", {}).get("id") == setup.snapshot["bot_id"] and (m.get("embeds") or m.get("content"))), key=lambda m: int(m["id"]))
        key = next((k for k, tid in setup.state["forums"].items() if tid == thread["id"]), "guide-" + thread["id"])
        post = materialize(setup, message, dict(thread, name=parent["name"]), key, forum=True)
        if post:
            source.append(post)
            originals.append(message)
    rank = list(TITLES)
    source.sort(key=lambda p: rank.index(p["key"]) if p["key"] in rank else len(rank))
    if source:
        save_json("pin-art-source.json", {"guild_id": GUILD_ID, "posts": source})
        save_json("pin-art-before.json", originals)
    print(json.dumps({"text_posts_to_replace": len(source), "keys": [p["key"] for p in source]}), flush=True)


def authorize_threads(setup):
    threads = setup.api.request("GET", GUILD + "/threads/active")["threads"]
    for thread in threads:
        if thread.get("guild_id") == GUILD_ID:
            setup.api.scope.channel_ids.add(thread["id"])
    return {t["id"]: t for t in threads}


def publish(setup):
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    threads = authorize_threads(setup)
    setup.state.setdefault("image_posts", {})
    for post in manifest["posts"]:
        key, cid, mid = post["key"], post["channel_id"], post["message_id"]
        current = setup.api.request("GET", f"/channels/{cid}/messages/{mid}")
        if current.get("author", {}).get("id") != setup.snapshot["bot_id"]:
            raise ScopeError("Refusing to edit another author's message")
        if not current.get("pinned") and not (post["forum"] and threads.get(cid, {}).get("flags", 0) & 2):
            raise ScopeError("Message is no longer pinned")
        files, attachments, embeds = [], [], []
        digest = hashlib.sha256()
        for index, panel in enumerate(post["panels"]):
            path = OUTPUT / panel["file"]
            binary = path.read_bytes()
            digest.update(binary)
            files.append((path.name, binary))
            attachments.append({"id": index, "filename": path.name, "description": panel["alt"]})
            embeds.append({"image": {"url": "attachment://" + path.name}})
        components = []
        for start in range(0, len(post["buttons"]), 5):
            components.append({"type": 1, "components": [dict(type=2, style=5, **b) for b in post["buttons"][start:start + 5]]})
        payload = {"content": "", "embeds": embeds, "attachments": attachments, "components": components,
                   "allowed_mentions": {"parse": []}}
        if len(embeds) > 10 or len(components) > 5:
            raise RuntimeError("Discord message limits exceeded")
        setup.api.request("PATCH", f"/channels/{cid}/messages/{mid}", payload, files)
        setup.state["image_posts"][key] = {"channel_id": cid, "id": mid, "image_count": len(files), "digest": digest.hexdigest(), "forum": post["forum"]}
        setup.save()
        print(f"Replaced {key}: {len(files)} image panels", flush=True)
    verify(setup)


def verify(setup):
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    threads = authorize_threads(setup)
    results, issues = [], []
    for post in manifest["posts"]:
        cid, mid = post["channel_id"], post["message_id"]
        message = setup.api.request("GET", f"/channels/{cid}/messages/{mid}")
        images = [e.get("image", {}) for e in message.get("embeds", [])]
        if len(images) != len(post["panels"]) or not all(i.get("url", "").startswith("https://cdn.discordapp.com/attachments/") for i in images):
            issues.append(post["key"] + ": images missing")
        if message.get("content") or any(e.get("title") or e.get("description") or e.get("footer") for e in message.get("embeds", [])):
            issues.append(post["key"] + ": text embed remains")
        pinned = bool(message.get("pinned") or (post["forum"] and threads.get(cid, {}).get("flags", 0) & 2))
        if not pinned:
            issues.append(post["key"] + ": pin missing")
        buttons = [b for row in message.get("components", []) for b in row.get("components", [])]
        if [b.get("url") for b in buttons] != [b["url"] for b in post["buttons"]]:
            issues.append(post["key"] + ": navigation link mismatch")
        results.append({"key": post["key"], "images": len(images), "pinned": pinned, "buttons": len(buttons),
                        "url": f"https://discord.com/channels/{GUILD_ID}/{cid}/{mid}"})
    report = {"posts": results, "image_panels": sum(p["images"] for p in results), "issues": issues}
    save_json("pin-art-verification.json", report)
    print(json.dumps(report, indent=2), flush=True)
    if issues:
        raise RuntimeError("Image-post verification failed")


def invite(setup):
    cid = setup.state["channels"]["welcome"]
    invitations = setup.api.request("GET", f"/channels/{cid}/invites")
    invitation = next((v for v in invitations if v.get("max_age") == 0 and v.get("max_uses") == 0 and not v.get("temporary")), None)
    if invitation is None:
        invitation = setup.api.request("POST", f"/channels/{cid}/invites", {"max_age": 0, "max_uses": 0, "temporary": False, "unique": False})
    if invitation.get("guild", {}).get("id") != GUILD_ID:
        raise ScopeError("Unexpected invitation destination")
    value = {"guild_id": GUILD_ID, "url": "https://discord.gg/" + invitation["code"], "max_age": invitation["max_age"], "max_uses": invitation["max_uses"]}
    save_json("public-invite.json", value)
    print(json.dumps(value), flush=True)
