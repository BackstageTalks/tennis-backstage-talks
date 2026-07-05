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
    top: 14px;
    right: 20px;
    display: flex;
    gap: 16px;
    align-items: center;
    justify-content: flex-end;
    z-index: 9999;
  }

  .bt-nav a {
    color: #ffffff;
    text-decoration: none;
    font-size: 14px;
    font-weight: 900;
    letter-spacing: 0.02em;
    line-height: 1.1;
  }

  .bt-nav a:hover {
    color: #38bdf8;
    text-decoration: underline;
  }

  body {
    position: relative;
  }
</style>
"""


def strip_bad_navigation(html: str) -> str:
    # Remove previously injected navigation and style.
    html = re.sub(r'<style id="bt-nav-fix-style">[\s\S]*?</style>', '', html, flags=re.I)
    html = re.sub(r'<nav[^>]*class="[^"]*bt-nav[^"]*"[\s\S]*?</nav>', '', html, flags=re.I)

    # Remove broken escaped fragments visible as: ">TOP5 ">ALL ">RESULTS
    html = re.sub(r'"?>\s*TOP5\s*"?>\s*ALL\s*"?>\s*RESULTS', '', html, flags=re.I)
    html = re.sub(r'&quot;&gt;\s*TOP5\s*&quot;&gt;\s*ALL\s*&quot;&gt;\s*RESULTS', '', html, flags=re.I)
    html = re.sub(r'"&gt;\s*TOP5\s*"&gt;\s*ALL\s*"&gt;\s*RESULTS', '', html, flags=re.I)

    # Remove duplicate plain TOP5 ALL RESULTS text. This is intentionally conservative:
    # only sequences near the top body/header are removed.
    html = re.sub(r'(\s|\n)+TOP5\s+ALL\s+RESULTS(\s|\n)+', '\n', html, count=3, flags=re.I)

    # Remove simple old anchor sequences if the page generator added its own broken nav.
    html = re.sub(
        r'(?:<a[^>]*>\s*TOP5\s*</a>\s*)+(?:<a[^>]*>\s*ALL\s*</a>\s*)+(?:<a[^>]*>\s*RESULTS\s*</a>\s*)+',
        '',
        html,
        flags=re.I,
    )

    return html


def insert_style(html: str) -> str:
    if "</head>" in html:
        return html.replace("</head>", NAV_CSS + "\n</head>", 1)
    return NAV_CSS + "\n" + html


def insert_nav(html: str) -> str:
    match = re.search(r'<body[^>]*>', html, flags=re.I)
    if match:
        pos = match.end()
        return html[:pos] + "\n" + NAV_HTML + "\n" + html[pos:]
    return NAV_HTML + "\n" + html


def fix_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    fixed = strip_bad_navigation(original)
    fixed = insert_style(fixed)
    fixed = insert_nav(fixed)

    if fixed != original:
        path.write_text(fixed, encoding="utf-8")
        return True
    return False


def main() -> None:
    if not PUBLIC_DIR.exists():
        print("public directory does not exist, navigation fix skipped")
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
