from pathlib import Path
import re

path = Path("render_site.py")

if not path.exists():
    raise FileNotFoundError("render_site.py not found in current directory")

text = path.read_text(encoding="utf-8")

replacements = {
    ".pick-name": """.pick-name {
    font-size: 18px;
    line-height: 1.18;
    font-weight: 900;
}""",
    ".pick-sub": """.pick-sub {
    color: var(--green);
    font-size: 13px;
    line-height: 1.15;
    margin-top: 4px;
    font-weight: 800;
}""",
    ".match-name": """.match-name {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.2;
    margin-top: 7px;
}""",
    ".match-meta": """.match-meta {
    color: var(--blue);
    font-size: 12px;
    line-height: 1.2;
    margin-top: 5px;
    font-weight: 700;
}""",
}

for selector, replacement in replacements.items():
    pattern = re.compile(r"" + re.escape(selector) + r"\s*\{[^}]*\}", re.MULTILINE)
    text, count = pattern.subn(replacement, text, count=1)

    if count == 0:
        raise RuntimeError(f"CSS block not found: {selector}")

path.write_text(text, encoding="utf-8")
print("Updated pick typography in render_site.py")
