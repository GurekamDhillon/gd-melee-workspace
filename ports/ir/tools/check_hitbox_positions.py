#!/usr/bin/env python3
"""Check every converted ACMD capsule endpoint against installed Melee hitbox spheres.

The installed Pl*.dat supplies ftcmd words and Pl*AJ.dat supplies the converted FigaTree
pose. An optional LAB JPF/JPC log is checked for coverage of the tested clips and frames;
the archive remains the orientation source because the probe records positions only.
"""
import argparse
import json
import math
from pathlib import Path
import re

import numpy as np
from scipy.spatial.transform import Rotation

import acmd_to_ftcmd as FT
import convert_ultimate_anim as CA
import figatree as F
import plan_parts


def signed16(value):
    return value - 65536 if value & 32768 else value


def sphere(words, pose):
    w0, w1, w2 = words[:3]
    joint = (w0 >> 11) & 255
    if joint >= len(pose):
        raise ValueError(f"installed hitbox references joint {joint}, only {len(pose)} joints")
    local = np.array([signed16(w1 & 65535) / 256,
                      signed16((w2 >> 16) & 65535) / 256,
                      signed16(w2 & 65535) / 256, 1.0])
    return (pose[joint] @ local)[:3], (w1 >> 16) / 256


def uncovered_endpoints(source, converted, pose, joint_of, tolerance=.5):
    bone = source["bone"]
    if bone not in joint_of:
        raise ValueError(f"source hitbox bone {bone!r} has no converted joint")
    endpoints = [("start", (source["x"], source["y"], source["z"]))]
    ends = [source.get(k) for k in ("x2", "y2", "z2")]
    if any(v is not None for v in ends):
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in ends):
            raise ValueError("source capsule endpoint is unresolved")
        endpoints.append(("end", ends))
    rendered = [sphere(words, pose) for words in converted]
    missed = []
    for label, xyz in endpoints:
        point = (pose[joint_of[bone]] @ np.array([*xyz, 1.0]))[:3]
        if not any(np.linalg.norm(point - centre) <= radius + tolerance for centre, radius in rendered):
            missed.append(label)
    return missed


def uncovered_article_endpoints(source, converted, scale=1.0, tolerance=.5):
    """Weapon local coordinates; its unknown spawn transform is common to both sides."""
    if source["bone"] != "top":
        raise ValueError(f"article ATTACK bone {source['bone']!r} needs a weapon pose")
    points = [("start", [source[k] * scale for k in ("x", "y", "z")])]
    end = [source.get(k) for k in ("x2", "y2", "z2")]
    if any(v is not None for v in end):
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in end):
            raise ValueError("article capsule endpoint unresolved")
        points.append(("end", [v * scale for v in end]))
    spheres = [(np.asarray([box["offset"][2], box["offset"][1], box["offset"][0]]), box["size"])
               for box in converted]
    return [label for label, xyz in points
            if not any(np.linalg.norm(np.asarray(xyz) - centre) <= radius + tolerance
                       for centre, radius in spheres)]


def read_installed_words(writer, ftdata, row):
    if writer is None or ftdata is None:
        raise ValueError(f"row {row}: no installed script")
    motion = writer.u32(ftdata + 0xC)
    field = motion + row * 0x18 + 0xC
    if field not in writer.relocs:
        raise ValueError(f"row {row}: no installed script")
    from install_ultimate import cmd_len
    words, pos = [], writer.u32(field)
    for _ in range(10000):
        word = writer.u32(pos)
        length = cmd_len(word)
        if length < 1 or length > 16:
            raise ValueError(f"row {row}: invalid ftcmd length {length} at 0x{pos:X}")
        words.extend(writer.u32(pos + 4*i) for i in range(length))
        if word == 0:
            return words
        pos += 4 * length
    raise ValueError(f"row {row}: ftcmd has no End within 10000 commands")


def hitbox_event_paths(words):
    """Enumerate every ftcmd branch, so a box on one branch cannot cover another."""
    from install_ultimate import cmd_len
    boundaries, at = set(), 0
    while at < len(words):
        boundaries.add(at)
        length = cmd_len(words[at])
        if length < 1 or at + length > len(words):
            raise ValueError(f"truncated ftcmd at word {at}")
        if words[at] == 0:
            break
        at += length
    else:
        final = words[at - length]
        if not (final >> 26 == 59 and (final >> 20) & 63 == 0x30 and
                (final >> 8) & 0xFF == 0):
            raise ValueError("ftcmd has no End or terminal Geno CHG")
    pending, paths = [(0, 0.0, [])], []
    seen_states = set()
    def state_key(i, frame, events):
        return (i, frame, tuple((f, kind, tuple(payload) if isinstance(payload, list) else payload)
                                for f, kind, payload in events))
    while pending:
        i, frame, events = pending.pop()
        key = state_key(i, frame, events)
        if key in seen_states:
            continue
        seen_states.add(key)
        if len(seen_states) > 10000:
            raise ValueError("more than 10000 distinct ftcmd hitbox states")
        steps = 0
        while True:
            steps += 1
            if steps > len(words) or i not in boundaries:
                raise ValueError(f"ftcmd branch reaches invalid word {i}")
            word = words[i]; op = word >> 26
            length = cmd_len(word)
            if word == 0 or (op == 59 and (word >> 20) & 63 == 0x30 and
                             (word >> 8) & 0xFF == 0):
                paths.append(events)
                break
            if op == 1:
                frame += word & 0x3FFFFFF
            elif op == 2:
                frame = word & 0x3FFFFFF
            elif op == 11:
                events.append((frame, "hit", words[i:i+5]))
            elif op == 15:
                events.append((frame, "remove", word & 0x3FFFFFF))
            elif op == 16:
                events.append((frame, "clear", None))
            elif op in (3, 4, 5, 6, 7, 8, 9):
                raise ValueError(f"ftcmd flow opcode {op} cannot be checked")
            elif op == 59:
                sub = (word >> 20) & 63
                if sub in (0x10, 0x12):
                    skip = words[i+2] if sub == 0x10 else words[i+3]
                    target = i + length + skip
                    if target not in boundaries:
                        raise ValueError(f"Geno conditional at word {i} skips to invalid word {target}")
                    pending.append((target, frame, events.copy()))
                elif sub == 0x11:
                    target = i + length + words[i+1]
                    if target not in boundaries:
                        raise ValueError(f"Geno skip at word {i} reaches invalid word {target}")
                    i = target
                    continue
                elif sub == 0x20 and words[i+1] not in (5, 6, 7):
                    raise ValueError(f"Geno hook {words[i+1]} cannot be position checked")
                elif sub == 0x13:
                    raise ValueError(f"Geno control subcommand {sub:#x} cannot be position checked")
            i += length
    unique = {}
    for events in paths:
        unique.setdefault(state_key(-1, 0, events), events)
    return list(unique.values())


def hitbox_events(words):
    paths = hitbox_event_paths(words)
    if len(paths) != 1:
        raise ValueError("ftcmd has multiple hitbox paths; check every path")
    return paths[0]


def check_unmapped_overlay(words, row, audited_base_rows, article_hooks_audited=False):
    """Only an inherited, separately audited script may lack its own source map."""
    from install_ultimate import cmd_len
    at = 0
    while at < len(words):
        word = words[at]
        if word == 0:
            return
        length = cmd_len(word)
        if length < 1 or at + length > len(words):
            raise ValueError(f"Geno overlay row {row} has truncated ftcmd")
        op = word >> 26
        if op == 11:
            raise ValueError(f"Geno overlay row {row} has hitboxes but no ACMD source mapping")
        if op == 59:
            sub = (word >> 20) & 63
            if sub == 0x13 and row not in audited_base_rows:
                raise ValueError(f"Geno overlay row {row} uses ORIG without an audited base row")
            if sub == 0x20 and (words[at+1] not in (5, 6, 7) or
                                (words[at+1] == 5 and not article_hooks_audited)):
                raise ValueError(f"Geno overlay row {row} calls an unaudited hook {words[at+1]}")
        at += length
    final = words[at - length] if at and words else 0
    if final >> 26 == 59 and (final >> 20) & 63 in (0x13, 0x30):
        return
    raise ValueError(f"Geno overlay row {row} has no End, ORIG, or terminal Geno CHG")


def live_spheres(events, frame):
    live = {}
    for at, kind, value in events:
        if at > frame:
            break
        if kind == "hit":
            live[(value[0] >> 23) & 7] = value
        elif kind == "remove":
            live.pop(value, None)
        else:
            live.clear()
    return list(live.values())


def source_events(row, combo=False):
    tests = FT.combo_branch_tests(row) if combo else set()
    events = []
    for c in row["commands"]:
        if not FT.default_path(c.get("when", []), tests):
            continue
        name, at = c["cmd"], c["frame"]
        if name in ("ATTACK", "ATTACK_IGNORE_THROW", "CATCH"):
            if not c.get("named"):
                raise ValueError(f"{row['script']} frame {at}: {name} arguments unresolved")
            events.append((at, "hit", (name, dict(c["named"], _acmd_frame=at))))
        elif name in ("AttackModule::clear_all", "GrabModule::clear_all"):
            events.append((at, "clear", None))
        elif name in ("AttackModule::clear", "GrabModule::clear"):
            if not c.get("args") or not isinstance(c["args"][0], int):
                raise ValueError(f"{row['script']} frame {at}: {name} id unresolved")
            events.append((at, "remove", (name, c["args"][0])))
    return events


def live_source(events, frame):
    live = {}
    for at, kind, value in events:
        if at > frame:
            break
        if kind == "hit":
            cmd, n = value
            live[("catch" if cmd == "CATCH" else "attack", n["id"])] = n
        elif kind == "remove":
            cmd, hit_id = value
            live.pop(("catch" if cmd.startswith("Grab") else "attack", hit_id), None)
        else:
            live.clear()
    return list(live.values())


def pose_matrices(tree, plan, rest, frame):
    if len(tree["joints"]) != len(plan["joints"]):
        raise ValueError(f"installed animation has {len(tree['joints'])} joints; plan has {len(plan['joints'])}")
    matrices = []
    for j in plan["joints"]:
        i = j["index"]
        if j["synthesized"]:
            local = np.eye(4)
        else:
            trans, _, scale, angles = rest[j["name"]]
            t, s, r = trans.copy(), scale.copy(), angles.copy()
            for track in tree["joints"][i]:
                kind = track["type"]
                dest, axis = ((r, CA.ROT.index(kind)) if kind in CA.ROT else
                              (t, CA.TRA.index(kind)) if kind in CA.TRA else
                              (s, CA.SCA.index(kind)) if kind in CA.SCA else (None, None))
                if dest is None:
                    raise ValueError(f"unsupported FigaTree track type {kind}")
                dest[axis] = F.evaluate(track["keys"], frame)
            local = CA.srt(t, Rotation.from_euler("xyz", r), s)
        parent = j["parent"]
        matrices.append(matrices[parent] @ local if parent is not None else local)
    return matrices


def installed_tree(writer, ftdata, row, aj):
    motion = writer.u32(ftdata + 0xC)
    record = motion + row * 0x18
    start, size = writer.u32(record + 4), writer.u32(record + 8)
    if not size or start + size > len(aj):
        raise ValueError(f"row {row}: missing installed animation archive")
    return F.parse_archive(aj[start:start+size])


def game_time(frame, rates):
    game, current, last = 0.0, 1.0, 0.0
    for at, rate in rates:
        if at >= frame:
            break
        game += (at - last) * current
        last, current = at, rate
    return int(round(game + (frame - last) * current))


def overlay_source_events(row, entry):
    """Map ACMD clip frames and an explicit source-action boundary to game frames."""
    rates = entry.get("rates", [])
    events = [(game_time(at, rates), kind, value)
              for at, kind, value in source_events(row)]
    if "source_end" in entry:
        end = entry["source_end"]
        if not isinstance(end, (int, float)) or end <= 0:
            raise ValueError(f"invalid overlay source_end {end!r}")
        events.append((game_time(end, rates), "clear", None))
    return sorted(events, key=lambda e: e[0])


def overlay_words(path):
    words = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue
        words.extend(int(token, 16) for token in line.split())
    if not words:
        raise ValueError(f"Geno overlay {path} is empty")
    from install_ultimate import cmd_len
    at = 0
    final = None
    while at < len(words):
        final = words[at]
        length = cmd_len(final)
        if length < 1 or at + length > len(words):
            raise ValueError(f"Geno overlay {path} has truncated ftcmd")
        at += length
    if final != 0 and not (final >> 26 == 59 and (final >> 20) & 63 in (0x13, 0x30)):
        raise ValueError(f"Geno overlay {path} has no End, ORIG, or terminal Geno CHG")
    return words


def check_install(fighter, install, acmd, moveset, *, tolerance=.5, joint_probe=None,
                  overlay_sources=None):
    from install_ultimate import Writer, verify_moveset_audit
    from acmd_loss import verify_acmd_source
    install = Path(install)
    meta = json.loads((install / "INSTALL.json").read_text(encoding="utf-8"))
    source_bytes = verify_acmd_source(acmd)
    moves_doc = json.loads(Path(moveset).read_text(encoding="utf-8"))
    verify_moveset_audit(moves_doc, source_bytes)
    moves = moves_doc["rows"]
    all_source = {(r["agent"], r["script"]): r
                  for r in json.loads(source_bytes) if r["kind"] == "game"}
    source = {script: row for (agent, script), row in all_source.items() if agent == fighter}
    ir = json.loads((Path(CA.INSTANCES) / f"{fighter}.ultimate-body.ir.json").read_text(encoding="utf-8"))
    plan, rest = plan_parts.plan(ir), CA.rest_of(ir)
    joint_of = {j["name"].lower(): j["index"] for j in plan["joints"]}
    joint_of["top"] = 0
    writer = Writer((install / "files" / meta["pl"]).read_bytes())
    ftdata = writer.ar.public([s for s, _ in writer.ar.publics if s.startswith("ftData")][0])
    aj = install / "files" / (meta["pl"][:-4] + "AJ.dat")
    archive = aj.read_bytes()
    profile = install / "geno.json"
    profile_doc = json.loads(profile.read_text(encoding="utf-8")) if profile.exists() else {}
    installed_overlays = {o["index"]: o for fp in profile_doc.get("fighters", [])
                          for o in fp.get("subactions", [])}
    installed_articles = {a["name"]: a for fp in profile_doc.get("fighters", [])
                          for a in fp.get("articles", [])}
    installed_losses = json.loads((install / "conversion_losses.json").read_text(encoding="utf-8"))["losses"]
    approved_zero = {(loss["move"], loss["frame"]) for loss in installed_losses
                     if loss.get("allowlist") == {"kind": "case", "name": "ATTACK.zero_damage"}}
    reviewed_remaps = {(loss["move"], loss["frame"], int(match.group(1)))
                       for loss in installed_losses if loss.get("source") == "four-slot remap"
                       if (match := re.match(r"hitbox id (\d+)", loss["what"]))}
    state_anim = {s.get("subaction"): s.get("anim") for fp in profile_doc.get("fighters", [])
                  for s in fp.get("states", [])}
    findings, reviewed_uncovered, checked, branch_paths_excluded, reviewed_zero = [], [], 0, 0, 0
    trees_by_clip = {}

    def check_row(row, name, script, src_events, dst_paths, *, hold=False):
        nonlocal checked, reviewed_zero
        if script not in source:
            raise ValueError(f"installed row {row}: source ACMD script {script!r} missing")
        symbol, tree = installed_tree(writer, ftdata, row, archive)
        match = re.search(r"_ACTION_(\w+?)_figatree", symbol)
        if match:
            trees_by_clip[match.group(1)] = tree
        last = int(math.floor(tree["frames"]))
        late = [at for at, kind, _ in src_events if kind == "hit" and at > last]
        if hold and src_events:
            last = max(last, math.ceil(max(at for at, _, _ in src_events)))
            late = []  # Geno anim=hold keeps the last converted pose after its stand-in clip ends.
        if late:
            raise ValueError(f"{script}: source hitbox at frame {late[0]} exceeds installed clip end {last}")
        for frame in range(last + 1):
            boxes = live_source(src_events, frame)
            reviewed_zero += sum(1 for box in boxes if box.get("damage") == 0 and
                                 (f"{fighter}/{script}", box["_acmd_frame"]) in approved_zero)
            boxes = [box for box in boxes if not (box.get("damage") == 0 and
                     (f"{fighter}/{script}", box["_acmd_frame"]) in approved_zero)]
            if not boxes:
                continue
            pose = pose_matrices(tree, plan, rest, frame)
            for path_index, events in enumerate(dst_paths):
                spheres = live_spheres(events, frame)
                for box in boxes:
                    checked += 1
                    missed = uncovered_endpoints(box, spheres, pose, joint_of, tolerance)
                    if missed:
                        local = [("start", [box[k] for k in ("x", "y", "z")]),
                                 ("end", [box.get(k) for k in ("x2", "y2", "z2")])]
                        rendered = [sphere(words, pose) for words in spheres]
                        gaps = {}
                        for label, xyz in local:
                            if label not in missed or any(v is None for v in xyz):
                                continue
                            point = (pose[joint_of[box["bone"]]] @ np.array([*xyz, 1.0]))[:3]
                            gaps[label] = round(min((np.linalg.norm(point - centre) - radius - tolerance
                                                     for centre, radius in rendered), default=float("inf")), 4)
                        finding = {"move": name, "script": script, "row": row,
                                   "frame": frame, "path": path_index,
                                   "id": box["id"], "uncovered": missed, "outside_by": gaps}
                        if (f"{fighter}/{script}", box["_acmd_frame"], box["id"]) in reviewed_remaps:
                            reviewed_uncovered.append(finding)
                        else:
                            findings.append(finding)

    audited_base_rows = set()
    for row_id, move in moves.items():
        if move.get("words") is None:
            continue
        row, script = int(row_id), move["script"]
        audited_base_rows.add(row)
        if script not in source:
            raise ValueError(f"installed row {row}: source ACMD script {script!r} missing")
        check_row(row, move["name"], script,
                  source_events(source[script], combo=script + "2" in source),
                  hitbox_event_paths(read_installed_words(writer, ftdata, row)))
    if overlay_sources is not None:
        manifest = json.loads(Path(overlay_sources).read_text(encoding="utf-8"))
        if manifest.get("version") != 1 or not isinstance(manifest.get("rows"), list):
            raise ValueError("invalid Geno overlay source manifest")
        for entry in manifest["rows"]:
            row, script = entry["row"], entry["script"]
            if script not in source:
                raise ValueError(f"overlay row {row}: source ACMD script {script!r} missing")
            src = overlay_source_events(source[script], entry)
            if entry.get("file"):
                words = overlay_words(install / entry["file"])
            else:
                overlay = installed_overlays.get(row)
                if overlay is None or not overlay.get("words"):
                    raise ValueError(f"overlay row {row}: source map has no installed words")
                words = [int(w, 16) if isinstance(w, str) else w for w in overlay["words"]]
            try:
                paths = hitbox_event_paths(words)
            except ValueError as exc:
                raise ValueError(f"overlay row {row} {entry['name']} ({script}): {exc}") from exc
            if script in ("game_specials2", "game_specials3"):
                # Sonic Blade's two authored frame-3 branches are exhaustive: the previous
                # dash-hit flag is a boolean. Geno encodes EQ 0 and EQ 1 as separate IFs;
                # the syntactic path where both tests fail cannot occur at runtime.
                branches = [c for c in source[script]["commands"] if c["cmd"] == "ATTACK"
                            and c["frame"] == 3 and len(c.get("when", [])) == 1]
                if ({c["when"][0]["holds"] for c in branches} != {True, False} or
                        len({c["when"][0]["test"] for c in branches}) != 1):
                    raise ValueError(f"{script}: Sonic Blade hit branches are no longer exhaustive")
                viable = [path for path in paths if live_spheres(path, 3)]
                if len(viable) < 2:
                    raise ValueError(f"{script}: both Sonic Blade hit branches need converted spheres")
                branch_paths_excluded += len(paths) - len(viable)
                paths = viable
            if entry["name"] in ("LwAttack", "LwAttackAir"):
                back_name = "LwAttackBackAir" if entry["name"] == "LwAttackAir" else "LwAttackBack"
                if not any(other["name"] == back_name and other["script"] == script
                           for other in manifest["rows"]):
                    raise ValueError(f"{entry['name']}: redirected counter branch {back_name} is unaudited")
                viable = [path for path in paths if live_spheres(path, 7)]
                if not viable:
                    raise ValueError(f"{entry['name']}: no converted counter hit branch")
                branch_paths_excluded += len(paths) - len(viable)
                paths = viable
            check_row(row, entry["name"], script, src, paths,
                      hold=state_anim.get(row) == "hold")
        covered_rows = {entry["row"] for entry in manifest["rows"]}
        for entry in manifest.get("articles", []):
            name = entry["name"]
            article = installed_articles.get(name)
            if article is None:
                raise ValueError(f"source-mapped article {name} missing from installed profile")
            key = (entry["agent"], entry["script"])
            if key not in all_source:
                raise ValueError(f"article {name}: source ACMD {key} missing")
            for command in all_source[key]["commands"]:
                if command["cmd"] != "ATTACK":
                    continue
                box = command.get("named")
                if box is None:
                    raise ValueError(f"article {name}: ATTACK at {command['frame']} unresolved")
                start = int(command["frame"]) + 1
                converted = [h for h in article.get("hitboxes", [])
                             if h.get("source_id", h["slot"]) == box["id"] and h["start"] == start]
                checked += 1
                missed = uncovered_article_endpoints(box, converted, entry.get("scale", 1.0), tolerance)
                if missed:
                    findings.append({"move": name, "script": entry["script"], "article": name,
                                     "frame": start, "id": box["id"], "uncovered": missed})
        covered_articles = {entry["name"] for entry in manifest.get("articles", [])}
    else:
        covered_rows = set()
        covered_articles = set()
    if profile_doc:
        for fighter_profile in profile_doc.get("fighters", []):
            for overlay in fighter_profile.get("subactions", []):
                row = overlay["index"]
                if row in covered_rows:
                    continue
                if overlay.get("file"):
                    path = install / overlay["file"]
                    words = overlay_words(path)
                else:
                    words = [int(w, 16) if isinstance(w, str) else w for w in overlay.get("words", [])]
                check_unmapped_overlay(words, row, audited_base_rows, bool(covered_articles))
            for article in fighter_profile.get("articles", []):
                if article.get("hitboxes") and article["name"] not in covered_articles:
                    raise ValueError(f"Geno article {article['name']} has hitboxes but no ACMD source mapping")
    if not checked:
        raise ValueError("no Ultimate hitboxes were checked in installed fighter")
    probe_checked, probe_worst = 0, 0.0
    if joint_probe:
        import compare_joints as CJ
        chunks = {}
        real = [i for i, j in enumerate(plan["joints"]) if not j["synthesized"]]
        for line in Path(joint_probe).read_text(encoding="utf-8", errors="replace").splitlines():
            chunk = CJ.CHUNK.search(line)
            if chunk:
                chunks[int(chunk.group(1))] = chunk.group(2)
                continue
            end = CJ.END.search(line)
            if end:
                cells = [cell for k in sorted(chunks) for cell in chunks[k].split(";")]
                chunks = {}
                if len(cells) != int(end.group(4)):
                    raise ValueError("LAB joint-probe has incomplete JPC/JPE sample")
                line = f"JPF {end.group(1)} {end.group(2)} {end.group(3)} " + ";".join(cells)
            sample = CJ.LINE.search(line)
            if not sample:
                continue
            match = re.search(r"_ACTION_(\w+?)_figatree", sample.group(2))
            clip = match.group(1) if match else None
            if clip not in trees_by_clip:
                continue
            cells = sample.group(5).split(";")
            if len(cells) != len(plan["joints"]):
                raise ValueError(f"LAB joint-probe {clip}: {len(cells)} joints, expected {len(plan['joints'])}")
            game = np.array([[float(x) for x in cell.split(",")] if cell != "-" else [np.nan]*3
                             for cell in cells])
            use = [i for i in real if np.isfinite(game[i]).all()]
            if len(use) < 8:
                raise ValueError(f"LAB joint-probe {clip}: fewer than 8 valid joints")
            frame = float(sample.group(3))
            tree = trees_by_clip[clip]
            pose = pose_matrices(tree, plan, rest, min(max(frame, 0), tree["frames"]))
            predicted = np.array([p[:3, 3] for p in pose])
            fitted, scale = CJ.fit(predicted[use], game[use])
            error = float(np.linalg.norm(fitted - game[use], axis=1).max() / scale)
            probe_checked += 1
            probe_worst = max(probe_worst, error)
            if error > tolerance:
                raise ValueError(f"LAB joint-probe {clip} frame {frame:g}: joint error {error:.3f} > {tolerance}")
        if not probe_checked:
            raise ValueError("LAB joint-probe log has no samples for audited installed clips")
    report = {"fighter": fighter, "installed": str(install), "tolerance": tolerance,
              "hitbox_frames_checked": checked, "uncovered": findings,
              "reviewed_four_slot_uncovered": reviewed_uncovered,
              "infeasible_boolean_paths_excluded": branch_paths_excluded,
              "reviewed_zero_damage_frames_excluded": reviewed_zero,
              "probe_samples_checked": probe_checked, "worst_probe_joint_error": probe_worst}
    (install / "hitbox_positions.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if findings:
        first = findings[0]
        raise ValueError(f"{len(findings)} uncovered Ultimate hitboxes; first {first}")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fighter")
    ap.add_argument("install")
    ap.add_argument("--acmd", required=True)
    ap.add_argument("--moveset", required=True)
    ap.add_argument("--joint-probe")
    ap.add_argument("--tolerance", type=float, default=.5)
    args = ap.parse_args()
    if not 0 <= args.tolerance <= 5 or not math.isfinite(args.tolerance):
        ap.error("--tolerance must be finite and between 0 and 5")
    result = check_install(args.fighter, args.install, args.acmd, args.moveset,
                           tolerance=args.tolerance, joint_probe=args.joint_probe)
    print(f"checked {result['hitbox_frames_checked']} installed hitbox frames; all capsule endpoints covered")


if __name__ == "__main__":
    main()
