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
    top: 16px;
    right: 24px;
    display: flex;
    gap: 16px;
    align-items: center;
    z-index: 50;
  }

  .bt-nav a {
    color: #ffffff;
    text-decoration: none;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.02em;
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


def strip_all_nav_like_blocks(html: str) -> str:
    # Remove nav blocks inserted by previous attempts.
    html = re.sub(
        r'<nav[^>]*class="[^"]*bt-nav[^"]*"[\s\S]*?</nav>',
        '',
        html,
        flags=re.I,
    )

    # Remove simple existing TOP5/ALL/RESULTS anchor groups, including absolute nav containers.
    html = re.sub(
        r'<div[^>]*>\s*(?:<a[^>]*>\s*TOP5\s*</a>\s*)+(?:<a[^>]*>\s*ALL\s*</a>\s*)+(?:<a[^>]*>\s*RESULTS\s*</a>\s*)+\s*</div>',
        '',
        html,
        flags=re.I,
    )

    # Remove raw broken escaped navigation text near generated header.
    broken_patterns = [
        r'"&gt;\s*TOP5\s*"&gt;\s*ALL\s*"&gt;\s*RESULTS',
        r'">\s*TOP5\s*">\s*ALL\s*">\s*RESULTS',
        r'&quot;&gt;\s*TOP5\s*&quot;&gt;\s*ALL\s*&quot;&gt;\s*RESULTS',
        r'(^|\n)\s*TOP5\s+ALL\s+RESULTS\s*(?=\n|<)',
    ]
    for pattern in broken_patterns:
        html = re.sub(pattern, '\n', html, flags=re.I)

    # Remove duplicate bare anchor sequences TOP5 ALL RESULTS if they are directly next to each other.
    html = re.sub(
        r'(?:<a[^>]*>\s*TOP5\s*</a>\s*){1,2}(?:<a[^>]*>\s*ALL\s*</a>\s*){1,2}(?:<a[^>]*>\s*RESULTS\s*</a>\s*){1,2}',
        '',
        html,
        flags=re.I,
    )

    return html


def ensure_style(html: str) -> str:
    html = re.sub(r'<style id="bt-nav-fix-style">[\s\S]*?</style>', '', html, flags=re.I)

    if "</head>" in html:
        return html.replace("</head>", NAV_CSS + "\n</head>", 1)

    return NAV_CSS + "\n" + html


def insert_nav_once(html: str) -> str:
    body_match = re.search(r'<body[^>]*>', html, flags=re.I)
    if body_match:
        insert_at = body_match.end()
        return html[:insert_at] + "\n" + NAV_HTML + "\n" + html[insert_at:]

    return NAV_HTML + "\n" + html


def fix_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    fixed = strip_all_nav_like_blocks(original)
    fixed = ensure_style(fixed)
    fixed = insert_nav_once(fixed)

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
