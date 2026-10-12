"""Fighter-level thrown_as authoring contract (geno.md 22.10, format 10).

Tokens and aliases match gn_vanilla in melee/pc/platform/geno_registry.c;
Nana is excluded by the engine's thrown_as parser. No retail data is needed.
"""

CHOICES = ("mario", "fox", "captain", "donkey", "kirby", "koopa", "link",
           "seak", "ness", "peach", "popo", "pikachu", "samus", "yoshi",
           "purin", "mewtwo", "luigi", "mars", "zelda", "clink", "drmario",
           "falco", "pichu", "gamewatch", "ganon", "emblem")
ALIASES = {"falcon": "captain", "dk": "donkey", "bowser": "koopa",
           "sheik": "seak", "jigglypuff": "purin", "marth": "mars",
           "younglink": "clink", "gnw": "gamewatch", "ganondorf": "ganon", "roy": "emblem"}


def validate(value):
    """Validate an engine token, preserving authored spelling and known aliases."""
    names = list(value.values()) if isinstance(value, dict) else [value]
    if isinstance(value, dict) and (not value or set(value) - {"default", "f", "b", "hi", "lw"}):
        raise ValueError("thrown_as as an object takes only default, f, b, hi, lw")
    if not all(isinstance(n, str) and (n.lower() in CHOICES or n.lower() in ALIASES) for n in names):
        raise ValueError("thrown_as must name a retail fighter other than Nana")
    return value


def apply(fighter, authored):
    """Carry an optional authored override into a generated base-none fighter."""
    if "thrown_as" not in authored:
        return
    value = validate(authored["thrown_as"])
    if fighter.get("define", {}).get("base") != "none":
        raise ValueError("thrown_as requires a define with base none")
    fighter["thrown_as"] = value
