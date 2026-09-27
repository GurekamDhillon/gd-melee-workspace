"""Render Discord information panels using the existing SVG menu brand kit.

python menu/pipeline/discord_pins.py --source <posts.json> --output <directory>
The output contains original SVG, 2x PNG, compact review sheets and a manifest.
"""
import argparse
import html
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
import build_brand as B

W = 640
LEFT, RIGHT = 38, 602
FONT, LEADING = 26, 34
CONTENT_MAX = 480


def runs(text):
    parts = re.split(r"(\*\*.*?\*\*)", text)
    result = []
    for part in parts:
        weight = "black" if part.startswith("**") else "bold"
        part = part.strip("*").replace("`", "")
        result.extend((word, weight) for word in re.findall(r"\s+|\S+", part))
    return result


def wrap(text, width):
    lines, line, used = [], [], 0
    for token, weight in runs(text):
        if not line and token.isspace():
            continue
        tw = B.face(weight).width(token, FONT)
        if used + tw > width and line:
            lines.append(line)
            line, used = [], 0
        if B.face(weight).width(token.rstrip(), FONT) > width:
            raise ValueError("Unbreakable word is too wide: " + token)
        line.append((token, weight))
        used += tw
    if line:
        lines.append(line)
    return lines


def blocks(text):
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    groups = []
    for para in text.split("\n\n"):
        lines = []
        for line in para.splitlines():
            lines.extend(wrap(line, RIGHT - LEFT))
        if lines:
            groups.append(lines)
    return groups


def paginate(groups):
    pages, page, used = [], [], 0
    for lines in groups:
        if len(lines) * LEADING > CONTENT_MAX:
            chunks = [lines[i:i + 10] for i in range(0, len(lines), 10)]
        else:
            chunks = [lines]
        for chunk in chunks:
            height = len(chunk) * LEADING + (22 if page else 0)
            if page and used + height > CONTENT_MAX:
                pages.append(page)
                page, used = [], 0
                height = len(chunk) * LEADING
            page.append(chunk)
            used += height
    if page:
        pages.append(page)
    def height(p):
        return sum(len(b) * LEADING for b in p) + max(0, len(p) - 1) * 22
    for i in range(len(pages) - 2, -1, -1):
        while len(pages[i]) > 1:
            before, after = pages[i], pages[i + 1]
            candidate_before, candidate_after = before[:-1], [before[-1]] + after
            if height(candidate_after) > CONTENT_MAX or abs(height(candidate_before) - height(candidate_after)) >= abs(height(before) - height(after)):
                break
            pages[i], pages[i + 1] = candidate_before, candidate_after
    return pages


def panel(post, content, number, count):
    text_height = sum(len(lines) * LEADING for lines in content) + 22 * max(0, len(content) - 1)
    H = max(348, 175 + text_height + 46)
    c = B.C
    body = B.bands(W, H, [(490, 85), (650, 130)], col=c["band"])
    body += '<path d="M0 0H640V7H0Z" fill="%s"/>' % c["gold"]
    logo, _, _ = B.place(B.wordmark_inline(B.LOGO_VARIANTS["dark"]), LEFT, 25, w=177)
    body += logo
    channel = "#" + post["channel_name"]
    body += B.text(channel, 16, RIGHT, 53, c["lilac"], f="bold", anchor="end")[0]
    title = post["title"]
    title_size = min(44, 530 / max(B.tw(title, 1), 1))
    shadow = B.text(title, title_size, 0, 0, c["ink"], f="black")[0]
    heading = B.text(title, title_size, 0, 0, c["bone"], f="black")[0]
    body += B.G(shadow, "translate(43 119) skewX(-14.036)")
    body += B.G(heading, "translate(38 114) skewX(-14.036)")
    body += '<path d="M38 135H582L577 151H38Z" fill="%s"/>' % c["cobalt"]
    body += '<path d="M38 135H113L109 151H38Z" fill="%s"/>' % c["gold"]
    y = 180
    bounds = []
    for pi, lines in enumerate(content):
        if pi:
            y += 22
        for line in lines:
            x = LEFT
            for token, weight in line:
                color = c["gold_lt"] if weight == "black" else c["bone"]
                body += B.text(token, FONT, x, y, color, f=weight)[0]
                x += B.face(weight).width(token, FONT)
            bounds.append({"x_end": x, "baseline": y})
            y += LEADING
    body += '<path d="M38 %dH602" stroke="%s" stroke-width="1.5"/>' % (H - 29, c["cobalt_hi"])
    if count > 1:
        body += B.text(f"{number:02d} / {count:02d}", 14, RIGHT, H - 10, c["lilac"], f="mono", anchor="end")[0]
    body += B.text("GD'S WORKSHOP", 13, LEFT, H - 10, c["lilac"], f="bold")[0]
    svg = B.svg(W, H, body, bg=c["night"])
    if any(b["x_end"] > RIGHT + 10 or b["baseline"] > H - 42 for b in bounds):
        raise ValueError("Text overflow on " + post["key"])
    return svg, H


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.source.read_text(encoding="utf-8"))
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"posts": [], "panel_count": 0, "logical_width": W, "body_font_size": FONT, "scale": 2}
    reviews = []
    with sync_playwright() as playwright:
        renderer = B.Renderer(playwright)
        try:
            for post in data["posts"]:
                text = post["text"]
                if post["key"] == "bugs":
                    text = text.replace("\n**Expected result:**", "\n\n**Expected result:**")
                pages = paginate(blocks(text))
                if not 1 <= len(pages) <= 10:
                    raise ValueError("Discord embed limit exceeded")
                entry = dict(post, panels=[])
                for n, content in enumerate(pages, 1):
                    svg, height = panel(post, content, n, len(pages))
                    stem = f"{post['key']}-{n:02d}"
                    (out / (stem + ".svg")).write_text(svg, encoding="utf-8")
                    bitmap = renderer.png(svg, W, height, scale=2, transparent=False).convert("RGB")
                    bitmap.save(out / (stem + ".png"), optimize=True)
                    plain = "\n\n".join("\n".join("".join(token for token, _ in line).rstrip() for line in lines) for lines in content)
                    alt = post["title"] + f" ({n}/{len(pages)}). " + plain
                    if len(alt) > 1024:
                        raise ValueError("Attachment alt text too long: " + stem)
                    entry["panels"].append({"file": stem + ".png", "width": bitmap.width, "height": bitmap.height,
                                             "alt": alt, "page": n})
                    thumb = bitmap.resize((384, round(bitmap.height * 384 / bitmap.width)), Image.Resampling.LANCZOS)
                    reviews.append((stem, thumb))
                    manifest["panel_count"] += 1
                manifest["posts"].append(entry)
                print(post["key"] + ": " + str(len(pages)) + " panels", flush=True)
        finally:
            renderer.b.close()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    for start in range(0, len(reviews), 6):
        subset = reviews[start:start + 6]
        cell_h = max(im.height for _, im in subset) + 30
        sheet = Image.new("RGB", (3 * 408, 2 * (cell_h + 18)), "#20232b")
        draw = ImageDraw.Draw(sheet)
        for i, (label, bitmap) in enumerate(subset):
            x, y = (i % 3) * 408 + 12, (i // 3) * (cell_h + 18) + 8
            draw.text((x, y), label, fill="white")
            sheet.paste(bitmap, (x, y + 22))
        sheet.save(out / f"review-{start // 6 + 1:02d}.png")
    print(json.dumps({"posts": len(manifest["posts"]), "panels": manifest["panel_count"], "output": str(out)}))


if __name__ == "__main__":
    main()
