"""Offline checks of a define's fighter-Lua module against the engine's API (docs/geno.md section 23).

The engine's own checks (frozen environment, closure scan, budgets) are native and run at load; this reads the module's TEXT and
reports what a miss there would cost at run time: a nil ctx field, a name the sandbox does not have, an undeclared or mistyped state
slot, a ctx.go to a state that does not exist, a hitbox mask outside 1..15. The API (ctx fields, commands, the allowlist) is read from
`pc/platform/geno_lua_core.h`, so this cannot drift from the engine.
"""
import re

from .source import read

SOURCE = "melee/pc/platform/geno_lua_core.h"
# Not in the sandbox (pairs/next/pcall/load/... by design: docs/geno.md 23.3). A module naming one faults the first time it runs.
ABSENT = {"pairs", "next", "pcall", "xpcall", "load", "loadstring", "dofile", "loadfile", "require", "tostring", "tonumber", "print",
          "rawget", "rawset", "rawequal", "rawlen", "setmetatable", "getmetatable", "collectgarbage", "string", "table", "os", "io",
          "debug", "coroutine", "utf8", "package", "_G", "_ENV"}


def api():
    """ctx.input / ctx.self fields, the ctx commands, the environment allowlist: read from glua_push_ctx and the allowlist tables."""
    core = read("pc/platform/geno_lua_core.h")
    push = core[core.index("static void glua_push_ctx"):]
    push = push[:push.index("\n}\n")]
    i_input, i_self = push.index('"input")'), push.index('"self")')
    setters = lambda seg: set(re.findall(r'glua_set(?:num|int|bool)\(L, "(\w+)"', seg))
    buttons = set(re.findall(r'"(\w+_(?:held|pressed))"', push[:i_input]))
    out = {"input": setters(push[:i_input]) | buttons,
           "self": setters(push[i_input:i_self]),
           "cmds": set(re.findall(r'lua_pushcfunction\(L, glua_\w+\);\s*lua_setfield\(L, -2, "(\w+)"\)', push))}
    out["fields"] = out["cmds"] | {"input", "self", "state"}
    env = core[core.index("static const char* const base[]"):]
    out["base"] = set(re.findall(r'"(\w+)"', env[:env.index("NULL}")])) | {"freeze"}
    mathf = env[env.index("mathf[]"):]
    out["math"] = set(re.findall(r'"(\w+)"', mathf[:mathf.index("NULL}")]))
    return out


def strip(text):
    """The code with comments blanked and string contents emptied, same length, so offsets and line numbers hold."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("--", i):
            m = re.match(r"--\[(=*)\[", text[i:])
            if m:
                end = text.find("]" + m.group(1) + "]", i)
                end = n if end < 0 else end + len(m.group(1)) + 2
            else:
                end = text.find("\n", i)
                end = n if end < 0 else end
            out.append(re.sub(r"[^\n]", " ", text[i:end]))
            i = end
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            closed = j < n and text[j] == c
            out.append(c + " " * max(0, j - i - 1) + (c if closed else ""))
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def check(text, state_decl, state_names, diagnostic, path):
    """Returns diagnostics for the module `text`. state_decl: {slot: "int"|"float"|"bool"}; state_names: the define's Geno state names."""
    try:
        a = api()
    except (OSError, ValueError):
        return []
    errors = []
    code = strip(text)
    line = lambda pos: code.count("\n", 0, pos) + 1
    # the ctx parameter of every module function (almost always "ctx")
    params = set(re.findall(r"\bfunction\s*[\w.:]*\s*\(\s*(\w+)", code)) or {"ctx"}
    ctx = "(?:" + "|".join(sorted(params)) + ")"
    alias = {kind: {kind} | set(re.findall(r"\blocal\s+(\w+)\s*=\s*" + ctx + r"\s*\.\s*" + kind + r"\b(?!\s*\.)", code))
             for kind in ("state", "self", "input")}
    for m in re.finditer(r"\b" + ctx + r"\s*\.\s*(\w+)", code):
        if m.group(1) not in a["fields"]:
            errors.append(diagnostic(path, f"line {line(m.start())}: ctx.{m.group(1)} does not exist (ctx has {', '.join(sorted(a['fields']))})", SOURCE))
    for kind in ("self", "input"):
        direct = [(m.start(), m.group(1)) for m in re.finditer(r"\b" + ctx + r"\s*\.\s*" + kind + r"\s*\.\s*(\w+)", code)]
        names = sorted(alias[kind] - {kind})
        via = [(m.start(), m.group(2)) for m in re.finditer(r"\b(" + "|".join(names) + r")\s*\.\s*(\w+)", code)] if names else []
        for pos, name in direct + via:
            if name not in a[kind]:
                errors.append(diagnostic(path, f"line {line(pos)}: ctx.{kind}.{name} does not exist (nil at run time; known: {', '.join(sorted(a[kind]))})", SOURCE))
    slot_names = sorted(alias["state"] - {"state"})
    slot = r"\b(?:" + ctx + r"\s*\.\s*state" + "".join("|" + n for n in ["state"] + slot_names) + r")\s*\.\s*(\w+)"
    for m in re.finditer(slot, code):
        if m.group(1) not in state_decl:
            errors.append(diagnostic(path + ".state", f"line {line(m.start())}: the module uses ctx.state.{m.group(1)}, which is not declared (a fault at run time)", SOURCE))
    # a literal assigned alone: the first token, not followed by an operator (so `charge = 1.5 * x` and `flag = 1 and y` are not judged)
    for m in re.finditer(slot + r"\s*=(?!=)\s*([^\s;,)]+)(?!\s*(?:[-+*/%^<>=~.,)]|\band\b|\bor\b))", code):
        kind, value = state_decl.get(m.group(1)), m.group(2)
        if kind == "bool" and re.fullmatch(r"-?\d+(\.\d+)?", value):
            errors.append(diagnostic(path + ".state", f"line {line(m.start())}: ctx.state.{m.group(1)} is a bool slot; a number is a fault at run time", SOURCE))
        elif kind == "int" and re.fullmatch(r"-?\d+\.\d*|-?\d*\.\d+|true|false", value):
            errors.append(diagnostic(path + ".state", f"line {line(m.start())}: ctx.state.{m.group(1)} is an int slot; {value} does not fit (a fault at run time)", SOURCE))
        elif kind == "float" and value in ("true", "false"):
            errors.append(diagnostic(path + ".state", f"line {line(m.start())}: ctx.state.{m.group(1)} is a float slot; a boolean is a fault at run time", SOURCE))
    targets = set(state_names) | {"auto", "helpless"}
    for m in re.finditer(r"\b" + ctx + r"\s*\.\s*go\s*\(\s*([\"'])(.*?)\1", text):   # on the raw text: the name is inside the string
        if m.group(2) not in targets:
            errors.append(diagnostic(path, f"ctx.go({m.group(2)!r}): no state of that name (states: {', '.join(sorted(targets))}); a fault at run time", SOURCE))
    for m in re.finditer(r"\b" + ctx + r"\s*\.\s*hitbox_damage\s*\(\s*(-?\d+)\s*,", code):
        if not 1 <= int(m.group(1)) <= 15:
            errors.append(diagnostic(path, f"line {line(m.start())}: ctx.hitbox_damage mask {m.group(1)} is outside 1..15 (bit n = hitbox slot n)", SOURCE))
    for m in re.finditer(r"(?<![\w.:])(\w+)\b", code):
        word = m.group(1)
        if word in ABSENT and not re.match(r"\s*=(?!=)", code[m.end():]) and code[max(0, m.start() - 6):m.start()].strip() != "local":
            allowed = ", ".join(sorted(a["base"])) + ", math." + "{" + ", ".join(sorted(a["math"])) + "}"
            errors.append(diagnostic(path, f"line {line(m.start())}: {word} is not in the sandbox (allowed: {allowed})", SOURCE))
    for m in re.finditer(r"(?<![\w.])math\s*\.\s*(\w+)", code):
        if m.group(1) not in a["math"]:
            errors.append(diagnostic(path, f"line {line(m.start())}: math.{m.group(1)} is not in the sandbox (allowed: {', '.join(sorted(a['math']))})", SOURCE))
    return errors
