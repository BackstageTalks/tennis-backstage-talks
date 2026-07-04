from pathlib import Path
import re

BASE_PATH = "/tennis-backstage-talks"
PUBLIC_DIR = Path("public")

NAV_HTML = f"""<nav class="bt-nav" aria-label="Main navigation">
  <a href="{BASE_PATH}/">TOP5</a>
  <a href="{BASE_PATH}/all/">ALL</a>
  <a href="{BASE_PATH}/results/">RESULTS</a>
</nav>"""

NAV_CSS = r"""
<style id="bt-nav-fix-style">
  .bt-nav {
    position: absolute;
    top: 18px;
    right: 24px;
    display: flex;
    gap: 14px;
    align-items: center;
    z-index: 50;
  }

  .bt-nav a {
    color: #ffffff;
    text-decoration: none;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .bt-nav a:hover {
    color: #93c5fd;
    text-decoration: underline;
  }

  body {
    position: relative;
  }
</style>
"""

BROKEN_NAV_PATTERNS = [
    r'"&gt;TOP5\s*"&gt;ALL\s*"&gt;RESULTS',
    r'">TOP5\s*">ALL\s*">RESULTS',
    r'&quot;&gt;TOP5\s*&quot;&gt;ALL\s*&quot;&gt;RESULTS',
]


def ensure_style(html: str) -> str:
    if 'id="bt-nav-fix-style"' in html:
        return html

    if "</head>" in html:
        return html.replace("</head>", NAV_CSS + "\n</head>", 1)

    return NAV_CSS + "\n" + html


def remove_existing_nav(html: str) -> str:
    html = re.sub(r'<nav[^>]*class="[^"]*bt-nav[^"]*"[\s\S]*?</nav>', '', html, flags=re.I)

    for pattern in BROKEN_NAV_PATTERNS:
        html = re.sub(pattern, '', html, flags=re.I)

    return html


def insert_nav(html: str) -> str:
    if '<nav class="bt-nav"' in html:
        return html

    body_open_match = re.search(r'<body[^>]*>', html, flags=re.I)
    if body_open_match:
        insert_at = body_open_match.end()
        return html[:insert_at] + "\n" + NAV_HTML + "\n" + html[insert_at:]

    return NAV_HTML + "\n" + html


def fix_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    fixed = original
    fixed = remove_existing_nav(fixed)
    fixed = ensure_style(fixed)
    fixed = insert_nav(fixed)

    if fixed != original:
        path.write_text(fixed, encoding="utf-8")
        return True

    return False


def main() -> None:
    if not PUBLIC_DIR.exists():
        print("public directory does not exist, skipping navigation fix")
        return

    changed = []
    for html_file in PUBLIC_DIR.rglob("*.html"):
        if fix_file(html_file):
            changed.append(str(html_file))

    print(f"Navigation fix updated {len(changed)} HTML files")
    for item in changed:
        print(f"- {item}")


if __name__ == "__main__":
    main()
