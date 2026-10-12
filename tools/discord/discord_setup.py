"""One-server Discord setup; token stays in the adjacent ignored .env."""

import argparse
import base64
import hashlib
import json
import mimetypes
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

GUILD_ID = "1552483229649477767"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GUILD = f"/guilds/{GUILD_ID}"
VIEW, SEND, ADMIN = 1 << 10, 1 << 11, 1 << 3
READONLY_DENY = SEND | (1 << 35) | (1 << 36) | (1 << 38)
BASE_PERMISSIONS = sum(1 << b for b in (6, 9, 10, 11, 14, 15, 16, 18, 20, 21, 25, 26, 31, 35, 37, 38))
MOD_PERMISSIONS = sum(1 << b for b in (1, 2, 7, 13, 22, 23, 24, 27, 34, 40, 51))


class ScopeError(RuntimeError):
    pass


class Scope:
    def __init__(self, channel_ids=()):
        self.channel_ids = set(channel_ids)

    def authorize(self, method, path, body=None):
        if method not in {"GET", "POST", "PATCH", "PUT"} or not re.fullmatch(r"/[A-Za-z0-9/@?=&_-]+", path):
            raise ScopeError("Unsupported operation or unsafe API path")
        allowed = method == "GET" and path in {
            "/users/@me", "/applications/@me", "/users/@me/guilds?limit=200",
        }
        clean = path.split("?", 1)[0]
        if clean == GUILD:
            allowed = method in {"GET", "PATCH"}
        elif clean in {GUILD + s for s in ("/channels", "/roles", "/emojis", "/auto-moderation/rules")}:
            allowed = method in {"GET", "POST"} or (method == "PATCH" and clean.endswith(("/channels", "/roles")))
        elif re.fullmatch(re.escape(GUILD) + r"/(roles|auto-moderation/rules)/[0-9]+", clean):
            allowed = method in {"GET", "PATCH"}
        elif clean == GUILD + "/onboarding":
            allowed = method in {"GET", "PUT"}
        elif clean == GUILD + "/welcome-screen":
            allowed = method in {"GET", "PATCH"}
        elif re.fullmatch(re.escape(GUILD) + r"/members/[0-9]+", clean):
            allowed = method == "GET"
        elif clean == GUILD + "/threads/active":
            allowed = method == "GET"
        channel = re.fullmatch(r"/channels/([0-9]+)(.*)", clean)
        if channel:
            cid, suffix = channel.groups()
            allowed = cid in self.channel_ids and (
                (suffix == "" and method in {"GET", "PATCH"})
                or (suffix == "/messages" and method in {"GET", "POST"})
                or (re.fullmatch(r"/messages/[0-9]+", suffix) and method in {"GET", "PATCH"})
                or (re.fullmatch(r"/messages/pins/[0-9]+", suffix) and method == "PUT")
                or (suffix == "/messages/pins" and method == "GET")
                or (suffix == "/threads" and method == "POST")
                or (suffix == "/invites" and method in {"GET", "POST"})
            )
        if isinstance(body, dict):
            for key in ("parent_id", "system_channel_id", "rules_channel_id", "public_updates_channel_id", "safety_alerts_channel_id"):
                if body.get(key) is not None and str(body[key]) not in self.channel_ids:
                    raise ScopeError(f"Unverified target channel in {key}")
        if not allowed:
            raise ScopeError("Request is outside the authorized server setup scope")


def validate_access(identity, application, guilds):
    if not identity.get("bot") or application.get("bot_public") is not False:
        raise ScopeError("Setup requires a private bot")
    if identity.get("id") != application.get("id"):
        raise ScopeError("Bot/application mismatch")
    if not isinstance(guilds, list) or len(guilds) != 1 or guilds[0].get("id") != GUILD_ID:
        raise ScopeError("Bot must be installed in exactly the authorized server")
    if not int(guilds[0].get("permissions", 0)) & ADMIN:
        raise ScopeError("Bot is missing Administrator permission")


def changed_fields(current, desired):
    def normalize(key, value):
        if key == "permission_overwrites":
            return sorted((str(o["id"]), int(o["type"]), int(o.get("allow", 0)), int(o.get("deny", 0))) for o in (value or []))
        if key == "permissions" and value is not None:
            return int(value)
        return value
    return {key: value for key, value in desired.items() if normalize(key, current.get(key)) != normalize(key, value)}


def effective_permissions(roles, member_roles, overwrites):
    member_roles = set(member_roles)
    permissions = 0
    for role in roles:
        if role["id"] == GUILD_ID or role["id"] in member_roles:
            permissions |= int(role["permissions"])
    if permissions & ADMIN:
        return (1 << 64) - 1
    for overwrite in overwrites:
        if overwrite["id"] == GUILD_ID:
            permissions = (permissions & ~int(overwrite["deny"])) | int(overwrite["allow"])
    allow, deny = 0, 0
    for overwrite in overwrites:
        if overwrite["id"] in member_roles and overwrite["type"] == 0:
            allow |= int(overwrite["allow"])
            deny |= int(overwrite["deny"])
    return (permissions & ~deny) | allow


def role_is_higher(first, second):
    if first["id"] == second["id"] or first["id"] == GUILD_ID:
        return False
    if second["id"] == GUILD_ID:
        return True
    return (first["position"], -int(first["id"])) > (second["position"], -int(second["id"]))


def welcome_image(message):
    for embed in message.get("embeds", []):
        image = embed.get("image", {})
        url = image.get("url", "")
        if url.startswith("https://cdn.discordapp.com/attachments/") and image.get("width", 0) > 0 and image.get("height", 0) > 0:
            return {"url": url}
    return None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ScopeError("Redirect rejected; bot credentials may only go to discord.com")


class API:
    def __init__(self):
        config = {}
        for line in (HERE / ".env").read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip().strip("\"'")
        if config.get("DISCORD_GUILD_ID") != GUILD_ID:
            raise ScopeError("Configured guild does not match the fixed authorized server")
        self.token = config.get("DISCORD_BOT_TOKEN", "")
        if not self.token or any(c.isspace() for c in self.token):
            raise ScopeError("Missing or malformed local bot token")
        self.scope = Scope()
        self.opener = urllib.request.build_opener(NoRedirect())
        self.writes = 0

    def request(self, method, path, body=None, attachment=None):
        self.scope.authorize(method, path, body)
        headers = {"Authorization": "Bot " + self.token,
                   "User-Agent": "DiscordBot (https://github.com/GurekamDhillon/gd-melee-workspace, 1.0)"}
        data = None
        if body is not None:
            if attachment:
                boundary = "gdm_" + uuid.uuid4().hex
                files = [attachment] if isinstance(attachment, tuple) else attachment
                parts = [f"--{boundary}\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json\r\n\r\n".encode(), json.dumps(body).encode()]
                for index, (filename, binary) in enumerate(files):
                    if not re.fullmatch(r"[A-Za-z0-9_.-]+", filename):
                        raise ScopeError("Invalid attachment filename")
                    parts += [f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"files[{index}]\"; filename=\"{filename}\"\r\nContent-Type: {mimetypes.guess_type(filename)[0] or 'application/octet-stream'}\r\n\r\n".encode(), binary]
                parts.append(f"\r\n--{boundary}--\r\n".encode())
                data = b"".join(parts)
                headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
            else:
                data = json.dumps(body).encode("utf-8")
                headers["Content-Type"] = "application/json"
        if method != "GET":
            headers["X-Audit-Log-Reason"] = "GD-authorized%20Melee%20server%20setup"
        for attempt in range(6):
            request = urllib.request.Request("https://discord.com/api/v10" + path, data=data, headers=headers, method=method)
            try:
                with self.opener.open(request, timeout=25) as response:
                    raw = response.read()
                    result = json.loads(raw) if raw else None
                if method != "GET":
                    self.writes += 1
                return result
            except urllib.error.HTTPError as error:
                raw = error.read().decode("utf-8", errors="replace")
                try:
                    detail = json.loads(raw)
                except ValueError:
                    detail = {"message": "Non-JSON response"}
                if error.code == 429:
                    delay = float(detail.get("retry_after", 1)) + 0.15
                    if delay > 45:
                        raise RuntimeError(f"Discord rate limit: wait {delay:.0f}s before resuming") from None
                    print(f"Rate limited; retrying in {delay:.1f}s", flush=True)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"Discord {method} {path}: HTTP {error.code}, " + json.dumps(detail).replace(self.token, "[REDACTED]")) from None
            except urllib.error.URLError:
                raise RuntimeError("Could not connect to Discord; check network permissions") from None
        raise RuntimeError("Discord rate limit persisted after retries")

    def inspect(self):
        identity = self.request("GET", "/users/@me")
        app = self.request("GET", "/applications/@me")
        guilds = self.request("GET", "/users/@me/guilds?limit=200")
        validate_access(identity, app, guilds)
        guild = self.request("GET", GUILD + "?with_counts=true")
        if guild["id"] != GUILD_ID:
            raise ScopeError("Unexpected guild response")
        channels = self.request("GET", GUILD + "/channels")
        if any(c.get("guild_id") != GUILD_ID for c in channels):
            raise ScopeError("Unexpected channel guild")
        self.scope.channel_ids.update(c["id"] for c in channels)
        member = self.request("GET", GUILD + "/members/" + identity["id"])
        return {"guild": guild, "channels": channels, "bot_member": member, "bot_id": identity["id"],
                "application": {"id": app["id"], "name": app["name"], "bot_public": app["bot_public"]}}


def save_json(name, value):
    target = HERE / name
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)


def image_data(path):
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


class Setup:
    def __init__(self):
        import blueprint
        self.bp = blueprint
        self.api = API()
        self.snapshot = self.api.inspect()
        if not (HERE / "before.json").exists():
            save_json("before.json", self.snapshot)
        self.state = json.loads((HERE / "state.json").read_text()) if (HERE / "state.json").exists() else {}
        for key in ("roles", "channels", "messages", "forums", "assets"):
            self.state.setdefault(key, {})
        self.channels = {c["id"]: c for c in self.snapshot["channels"]}
        self.roles = {r["id"]: r for r in self.snapshot["guild"]["roles"]}

    def save(self):
        save_json("state.json", self.state)

    def role(self, name, color, hoist):
        matches = [r for r in self.roles.values() if r["name"] == name]
        if len(matches) > 1:
            raise RuntimeError("Ambiguous duplicate role: " + name)
        desired = {"name": name, "permissions": str(MOD_PERMISSIONS if name == "Moderator" else 0),
                   "color": color, "hoist": hoist, "mentionable": False}
        existing = matches[0] if matches else None
        if existing:
            if existing.get("managed"):
                raise ScopeError("Refusing to change an integration-managed role")
            delta = changed_fields(existing, desired)
            role = self.api.request("PATCH", GUILD + "/roles/" + existing["id"], delta) if delta else existing
        else:
            role = self.api.request("POST", GUILD + "/roles", desired)
        self.roles[role["id"]] = role
        self.state["roles"][name] = role["id"]
        self.save()

    def overwrites(self, policy):
        moderator = self.state["roles"]["Moderator"]
        if policy == "readonly":
            return [{"id": GUILD_ID, "type": 0, "allow": "0", "deny": str(READONLY_DENY)},
                    {"id": moderator, "type": 0, "allow": str(READONLY_DENY), "deny": "0"}]
        if policy == "staff":
            return [{"id": GUILD_ID, "type": 0, "allow": "0", "deny": str(VIEW)},
                    {"id": moderator, "type": 0, "allow": str(VIEW | SEND | (1 << 16)), "deny": "0"}]
        return []

    def channel(self, key, desired, reuse=None):
        cid = self.state["channels"].get(key) or reuse
        existing = self.channels.get(cid)
        if existing is None:
            matches = [c for c in self.channels.values() if c["name"] == desired["name"] and c["type"] == desired["type"]]
            if len(matches) > 1:
                raise RuntimeError("Ambiguous channel: " + desired["name"])
            existing = matches[0] if matches else None
        if existing:
            if existing["type"] != desired["type"] and {existing["type"], desired["type"]} != {0, 5}:
                raise RuntimeError("Unexpected existing channel type")
            delta = changed_fields(existing, desired)
            result = self.api.request("PATCH", "/channels/" + existing["id"], delta) if delta else existing
        else:
            result = self.api.request("POST", GUILD + "/channels", desired)
        if result.get("guild_id") != GUILD_ID:
            raise ScopeError("Created channel did not belong to authorized server")
        self.api.scope.channel_ids.add(result["id"])
        self.channels[result["id"]] = result
        self.state["channels"][key] = result["id"]
        self.save()
        return result

    def create_layout(self):
        print("Configuring member and staff roles...", flush=True)
        for role in self.bp.ROLE_SPECS:
            self.role(*role)
        everyone = self.roles[GUILD_ID]
        if int(everyone["permissions"]) != BASE_PERMISSIONS:
            self.roles[GUILD_ID] = self.api.request("PATCH", GUILD + "/roles/" + GUILD_ID, {"permissions": str(BASE_PERMISSIONS)})
        policies = {key: policy for key, _, _, policy in self.bp.CATEGORIES}
        for key, name, reuse, policy in self.bp.CATEGORIES:
            self.channel(key, {"name": name, "type": 4, "permission_overwrites": self.overwrites(policy)}, reuse)
        print("Creating the channel layout...", flush=True)
        for spec in self.bp.CHANNELS:
            if spec[2] == 15:
                continue
            self.create_leaf(spec, policies, community=False)
        refs = self.state["channels"]
        current = self.api.request("GET", GUILD)
        settings = {"verification_level": 1, "explicit_content_filter": 2, "default_message_notifications": 1,
                    "system_channel_id": refs["introductions"], "system_channel_flags": 4 | 8 | 16 | 32,
                    "rules_channel_id": refs["rules"], "public_updates_channel_id": refs["discord_updates"],
                    "safety_alerts_channel_id": refs["discord_updates"],
                    "features": sorted(set(current["features"]) | {"COMMUNITY"}),
                    "preferred_locale": "en-US", "description": self.bp.DESCRIPTION}
        if not current.get("icon"):
            settings["icon"] = image_data(ROOT / "menu/out_brand/discord/server_icon_512.png")
        delta = changed_fields(current, settings)
        if delta:
            self.api.request("PATCH", GUILD, delta)
        print("Community enabled; creating tagged support forums...", flush=True)
        for spec in self.bp.CHANNELS:
            if spec[2] in {5, 15}:
                self.create_leaf(spec, policies, community=True)
        self.order_layout()

    def create_leaf(self, spec, policies, community):
        key, name, kind, category, topic, slowmode, reuse = spec
        if kind == 5 and not community:
            existing = self.channels.get(self.state["channels"].get(key), {})
            kind = 5 if existing.get("type") == 5 else 0
        desired = {"name": name, "type": kind, "parent_id": self.state["channels"][category],
                   "permission_overwrites": self.overwrites(policies[category]), "nsfw": False}
        if kind != 2:
            desired.update(topic=topic, rate_limit_per_user=slowmode)
        else:
            desired.update(bitrate=64000, user_limit=2 if key.startswith("friendlies") else 0, rtc_region=None)
        if kind == 15:
            existing = self.channels.get(self.state["channels"].get(key), {})
            old_tags = {t["name"]: t for t in existing.get("available_tags", [])}
            tags = []
            for name in self.bp.FORUM_TAGS[key]:
                tag = {"name": name, "moderated": name in {"Needs info", "Confirmed", "Fixed"}, "emoji_id": None, "emoji_name": None}
                if name in old_tags:
                    tag["id"] = old_tags[name]["id"]
                tags.append(tag)
            desired.update(available_tags=tags, default_auto_archive_duration=4320,
                           default_thread_rate_limit_per_user=3, default_sort_order=0, default_forum_layout=1, flags=16)
        self.channel(key, desired, reuse)

    def order_layout(self):
        channels = self.api.request("GET", GUILD + "/channels")
        category_ids = [self.state["channels"][c[0]] for c in self.bp.CATEGORIES]
        changes = []
        actual = [c["id"] for c in sorted(channels, key=lambda c: (c["position"], c["id"])) if c["type"] == 4]
        if actual != category_ids:
            changes.extend({"id": cid, "position": pos} for pos, cid in enumerate(category_ids))
        for key, _, _, _ in self.bp.CATEGORIES:
            desired = [self.state["channels"][s[0]] for s in self.bp.CHANNELS if s[3] == key]
            actual = [c["id"] for c in sorted(channels, key=lambda c: (c["position"], c["id"])) if c.get("parent_id") == self.state["channels"][key]]
            if actual != desired:
                changes.extend({"id": cid, "position": pos} for pos, cid in enumerate(desired))
        if changes:
            self.api.request("PATCH", GUILD + "/channels", changes)

    def create_emoji(self):
        print("Installing original GD brand emoji...", flush=True)
        existing = {e["name"]: e for e in self.api.request("GET", GUILD + "/emojis")}
        for path in sorted((ROOT / "menu/out_brand/discord/emoji").glob("*.png")):
            name = "gd_" + path.stem
            if name not in existing:
                self.api.request("POST", GUILD + "/emojis", {"name": name, "image": image_data(path), "roles": []})

    def embed(self, key, title, description):
        refs = {k: "<#" + v + ">" for k, v in self.state["channels"].items()}
        description = description.format_map(refs)
        if len(description) > 4096:
            raise RuntimeError("Embed too long: " + key)
        return {"title": title, "description": description, "color": 0xF0B429 if key in {"welcome", "downloads"} else 0x2F7CF0,
                "footer": {"text": "GD's Melee | " + key.replace("_", " ")}}

    def publish_posts(self):
        print("Publishing and pinning welcome and help posts...", flush=True)
        for key, (title, description) in self.bp.POSTS.items():
            if key in self.state.get("image_posts", {}):
                continue  # Image panels are maintained by art-apply.
            cid = self.state["channels"][key]
            embed = self.embed(key, title, description)
            messages = self.api.request("GET", "/channels/" + cid + "/messages?limit=100")
            existing = next((m for m in messages if m.get("author", {}).get("id") == self.snapshot["bot_id"] and
                             any(e.get("footer", {}).get("text") == embed["footer"]["text"] for e in m.get("embeds", []))), None)
            attachment = None
            if key == "welcome":
                if existing and welcome_image(existing):
                    embed["image"] = welcome_image(existing)
                else:
                    filename = "gds-melee-welcome.png"
                    embed["image"] = {"url": "attachment://" + filename}
                    attachment = (filename, (ROOT / "menu/out_brand/discord/server_banner_960x540.png").read_bytes())
            payload = {"embeds": [embed], "allowed_mentions": {"parse": []}}
            digest = hashlib.sha256(json.dumps([title, description], sort_keys=True).encode()).hexdigest()
            if existing:
                if self.state["messages"].get(key, {}).get("digest") != digest or attachment:
                    existing = self.api.request("PATCH", f"/channels/{cid}/messages/{existing['id']}", payload, attachment)
                message = existing
            else:
                payload["nonce"] = "gdsetup-" + key
                payload["enforce_nonce"] = True
                message = self.api.request("POST", "/channels/" + cid + "/messages", payload, attachment)
            self.state["messages"][key] = {"channel_id": cid, "id": message["id"], "digest": digest}
            self.save()
            if not message.get("pinned"):
                self.api.request("PUT", f"/channels/{cid}/messages/pins/{message['id']}")
        active = self.api.request("GET", GUILD + "/threads/active")["threads"]
        for thread in active:
            if thread.get("guild_id") == GUILD_ID:
                self.api.scope.channel_ids.add(thread["id"])
        for key, (title, description, tag_name) in self.bp.FORUM_GUIDES.items():
            if key in self.state.get("image_posts", {}):
                continue
            cid = self.state["channels"][key]
            thread = next((t for t in active if t.get("parent_id") == cid and t["name"] == title), None)
            if not thread:
                forum = self.api.request("GET", "/channels/" + cid)
                tag_id = next(t["id"] for t in forum["available_tags"] if t["name"] == tag_name)
                thread = self.api.request("POST", "/channels/" + cid + "/threads", {
                    "name": title, "auto_archive_duration": 10080, "applied_tags": [tag_id],
                    "message": {"embeds": [self.embed(key, title, description)], "allowed_mentions": {"parse": []}}})
                if thread.get("guild_id") != GUILD_ID:
                    raise ScopeError("Unexpected guide thread guild")
                self.api.scope.channel_ids.add(thread["id"])
            if not thread.get("flags", 0) & 2:
                self.api.request("PATCH", "/channels/" + thread["id"], {"flags": thread.get("flags", 0) | 2})
            self.state["forums"][key] = thread["id"]
            self.save()

    def moderation(self):
        print("Configuring native AutoMod...", flush=True)
        alert = {"type": 2, "metadata": {"channel_id": self.state["channels"]["mod_alerts"]}}
        specs = [
            ("Workshop | Mention spam", 5, {"mention_total_limit": 5, "mention_raid_protection_enabled": True}, "Please avoid mass mentions. Ask a moderator if you need to reach the group."),
            ("Workshop | Spam content", 3, {}, "This message was blocked as possible spam. Contact a moderator if it was a mistake."),
            ("Workshop | Harmful language", 4, {"presets": [2, 3], "allow_list": []}, "Please keep the Workshop respectful and safe to open. Contact a moderator if this was a mistake."),
        ]
        existing = {r["name"]: r for r in self.api.request("GET", GUILD + "/auto-moderation/rules")}
        for name, trigger, metadata, explanation in specs:
            desired = {"name": name, "event_type": 1, "trigger_metadata": metadata, "enabled": True,
                       "actions": [{"type": 1, "metadata": {"custom_message": explanation}}, alert],
                       "exempt_roles": [self.state["roles"]["Moderator"]], "exempt_channels": []}
            if name in existing:
                delta = changed_fields(existing[name], desired)
                if delta:
                    self.api.request("PATCH", GUILD + "/auto-moderation/rules/" + existing[name]["id"], delta)
            else:
                self.api.request("POST", GUILD + "/auto-moderation/rules", dict(desired, trigger_type=trigger))

    def onboarding(self):
        print("Configuring native onboarding and interest roles...", flush=True)
        c, r = self.state["channels"], self.state["roles"]
        current = self.api.request("GET", GUILD + "/onboarding")
        options = [
            {"title": "Play and practice", "description": "Find sets and explore the LAB.", "role_ids": [r["Player"]], "channel_ids": [c["matchmaking"], c["training"]], "emoji_name": "🎮"},
            {"title": "Make mods and scripts", "description": "Create and share original work.", "role_ids": [r["Modder"]], "channel_ids": [c["modding"], c["showcase"]], "emoji_name": "🛠️"},
            {"title": "Test and report bugs", "description": "Help improve the port.", "role_ids": [r["Playtester"]], "channel_ids": [c["bugs"], c["help"]], "emoji_name": "🧪"},
        ]
        title = "What brings you to GD's Melee?"
        prompt = {"title": title, "type": 0, "single_select": False, "required": False, "in_onboarding": True, "options": options}
        temporary_id = (int(time.time() * 1000) - 1420070400000) << 22
        prompt["id"] = str(temporary_id)
        for index, option in enumerate(options, 1):
            option["id"] = str(temporary_id + index)
        previous = next((p for p in current.get("prompts", []) if p["title"] == title), None)
        if previous:
            prompt["id"] = previous["id"]
            for option in options:
                old = next((o for o in previous["options"] if o["title"] == option["title"]), None)
                if old:
                    option["id"] = old["id"]
        desired = {"enabled": True, "mode": 0, "default_channel_ids": [c[k] for k in ("welcome", "rules", "general", "introductions", "showcase", "suggestions", "matchmaking")], "prompts": [prompt]}
        self.api.request("PUT", GUILD + "/onboarding", desired)
        self.state["onboarding_configured"] = True
        self.save()

    def verify(self):
        print("Verifying live server state and member permissions...", flush=True)
        snap = self.api.inspect()
        save_json("after.json", snap)
        channels = {c["id"]: c for c in snap["channels"]}
        roles = snap["guild"]["roles"]
        issues = []
        for key, name, kind, parent, _, _, _ in self.bp.CHANNELS:
            channel = channels.get(self.state["channels"].get(key), {})
            if channel.get("name") != name or channel.get("type") != kind or channel.get("parent_id") != self.state["channels"].get(parent):
                issues.append("Channel structure: " + key)
            overwrites = channel.get("permission_overwrites", [])
            for member_roles in [[], [self.state["roles"][n] for n in ("Player", "Modder", "Playtester", "Contributor")]]:
                perms = effective_permissions(roles, member_roles, overwrites)
                if parent == "staff" and perms & VIEW:
                    issues.append("Staff privacy: " + key)
                if parent != "staff" and not perms & VIEW:
                    issues.append("Public visibility: " + key)
                if parent == "start" and perms & READONLY_DENY:
                    issues.append("Read-only protection: " + key)
                if parent in {"community", "melee"} and not perms & SEND:
                    issues.append("Member posting: " + key)
            mod = effective_permissions(roles, [self.state["roles"]["Moderator"]], overwrites)
            if not mod & VIEW:
                issues.append("Moderator visibility: " + key)
        for role in roles:
            if role["id"] in self.state["roles"].values() and int(role["permissions"]) & ADMIN:
                issues.append("Unexpected administrator role: " + role["name"])
        bot_roles = [r for r in roles if r["id"] in snap["bot_member"]["roles"]]
        if any(not any(role_is_higher(bot, role) for bot in bot_roles) for role in roles if role["id"] in self.state["roles"].values()):
            issues.append("Bot role must be above all configured roles")
        for key, meta in self.state["messages"].items():
            message = self.api.request("GET", f"/channels/{meta['channel_id']}/messages/{meta['id']}")
            if not message.get("pinned") or message.get("author", {}).get("id") != snap["bot_id"]:
                issues.append("Pinned setup message: " + key)
            if key == "welcome" and not welcome_image(message):
                issues.append("Welcome artwork missing")
        active = self.api.request("GET", GUILD + "/threads/active")["threads"]
        for key, tid in self.state["forums"].items():
            thread = next((t for t in active if t["id"] == tid), {})
            if thread.get("parent_id") != self.state["channels"][key] or not thread.get("flags", 0) & 2:
                issues.append("Pinned forum guide: " + key)
        onboarding = self.api.request("GET", GUILD + "/onboarding")
        if not onboarding.get("enabled") or len(onboarding.get("default_channel_ids", [])) < 7:
            issues.append("Onboarding not enabled")
        automod = self.api.request("GET", GUILD + "/auto-moderation/rules")
        if len([r for r in automod if r["name"].startswith("Workshop |") and r["enabled"]]) != 3:
            issues.append("AutoMod rules missing")
        emojis = self.api.request("GET", GUILD + "/emojis")
        if len([e for e in emojis if e["name"].startswith("gd_")]) != 10:
            issues.append("Brand emoji missing")
        guild = snap["guild"]
        if "COMMUNITY" not in guild["features"] or guild["verification_level"] < 1 or guild["explicit_content_filter"] != 2 or guild["default_message_notifications"] != 1:
            issues.append("Community safety defaults mismatch")
        if not guild.get("icon"):
            issues.append("Server icon missing")
        report = {"guild_id": GUILD_ID, "server_name": guild["name"], "categories": len(self.bp.CATEGORIES),
                  "channels": len(self.bp.CHANNELS), "custom_roles": len(self.bp.ROLE_SPECS), "brand_emoji": len(emojis),
                  "pinned_posts": len(self.state["messages"]), "forum_guides": len(self.state["forums"]),
                  "onboarding_enabled": onboarding.get("enabled"), "automod_rules": len(automod), "issues": issues,
                  "server_url": "https://discord.com/channels/" + GUILD_ID,
                  "welcome_url": "https://discord.com/channels/" + GUILD_ID + "/" + self.state["channels"]["welcome"]}
        save_json("verification.json", report)
        print(json.dumps(report, indent=2), flush=True)
        if issues:
            raise RuntimeError("Live verification found issues; see verification.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("inspect", "apply", "verify", "art-audit", "art-apply", "art-verify", "invite"))
    args = parser.parse_args()
    setup = Setup()
    if args.action.startswith("art-") or args.action == "invite":
        import pin_art
        {"art-audit": pin_art.audit, "art-apply": pin_art.publish, "art-verify": pin_art.verify, "invite": pin_art.invite}[args.action](setup)
        return
    if args.action == "inspect":
        save_json("inspection.json", setup.snapshot)
        print(json.dumps({"guild_id": GUILD_ID, "name": setup.snapshot["guild"]["name"], "private_bot": True, "single_server": True}))
        if "welcome" in setup.state["messages"]:
            meta = setup.state["messages"]["welcome"]
            message = setup.api.request("GET", f"/channels/{meta['channel_id']}/messages/{meta['id']}")
            print(json.dumps({"welcome": {k: message.get(k) for k in ("id", "author", "embeds", "attachments", "pinned")}}, indent=2))
    elif args.action == "apply":
        setup.create_layout()
        setup.create_emoji()
        setup.publish_posts()
        setup.moderation()
        setup.onboarding()
        setup.verify()
    else:
        setup.verify()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ScopeError) as error:
        print("STOPPED: " + str(error), file=sys.stderr)
        sys.exit(1)
