from pathlib import Path
import re

BASE_PATH = "/tennis-backstage-talks"
PUBLIC_DIR = Path("public")

NAV_HTML = f"""<nav class="bt-nav" aria-label="Main navigation"><a href="{BASE_PATH}/">TOP5</a><a href="{BASE_PATH}/all/">ALL</a><a href="{BASE_PATH}/results/">RESULTS</a></nav>"""

NAV_CSS = r"""
<style id="bt-nav-fix-style">
  .bt-nav {
    position: absolute;
    top: 12px;
    right: 18px;
    display: flex;
    gap: 14px;
    align-items: center;
    justify-content: flex-end;
    z-index: 999999;
    white-space: nowrap;
  }
  .bt-nav a {
    color: #ffffff;
    text-decoration: none;
    font-size: 14px;
    font-weight: 900;
    letter-spacing: 0.02em;
    line-height: 1.15;
  }
  .bt-nav a:hover {
    color: #38bdf8;
    text-decoration: underline;
  }
  body { position: relative; }
</style>
"""


def kill_bad_nav_in_head_area(html: str) -> str:
    # Work mostly on first part of file where the broken nav is generated.
    head = html[:12000]
    tail = html[12000:]

    # Remove our previous injected style/nav blocks.
    head = re.sub(r'<style[^>]*id=["\']bt-nav-fix-style["\'][\s\S]*?</style>', '', head, flags=re.I)
    head = re.sub(r'<nav[^>]*class=["\'][^"\']*bt-nav[^"\']*["\'][\s\S]*?</nav>', '', head, flags=re.I)

    # Remove any normal anchor-only TOP5/ALL/RESULTS groups.
    head = re.sub(
        r'(?:<a[^>]*>\s*TOP5\s*</a>\s*)+(?:<a[^>]*>\s*ALL\s*</a>\s*)+(?:<a[^>]*>\s*RESULTS\s*</a>\s*)+',
        '',
        head,
        flags=re.I,
    )

    # Remove escaped/broken text forms visible on page, including encoded quotes.
    patterns = [
        r'(?:&quot;|&#34;|"|”|“)?\s*(?:&gt;|>)\s*TOP5\s*(?:&quot;|&#34;|"|”|“)?\s*(?:&gt;|>)\s*ALL\s*(?:&quot;|&#34;|"|”|“)?\s*(?:&gt;|>)\s*RESULTS',
        r'(?:&quot;|&#34;|"|”|“)?\s*(?:&gt;|>)\s*TOP5\s*(?:&quot;|&#34;|"|”|“)?\s*(?:&gt;|>)\s*ALL',
        r'TOP5\s+ALL\s+RESULTS',
    ]
    for pattern in patterns:
        head = re.sub(pattern, '', head, flags=re.I)

    # Remove leftover empty absolute/right nav containers, if any.
    head = re.sub(r'<div[^>]*(?:right|top|nav)[^>]*>\s*</div>', '', head, flags=re.I)

    return head + tail


def insert_clean_nav(html: str) -> str:
    # Reinsert nav style.
    if '</head>' in html:
        html = html.replace('</head>', NAV_CSS + '\n</head>', 1)
    else:
        html = NAV_CSS + '\n' + html

    # Reinsert nav as first body child.
    body = re.search(r'<body[^>]*>', html, flags=re.I)
    if body:
        pos = body.end()
        return html[:pos] + '\n' + NAV_HTML + '\n' + html[pos:]

    return NAV_HTML + '\n' + html


def fix_file(path: Path) -> bool:
    original = path.read_text(encoding='utf-8', errors='replace')
    fixed = kill_bad_nav_in_head_area(original)
    fixed = insert_clean_nav(fixed)

    if fixed != original:
        path.write_text(fixed, encoding='utf-8')
        return True
    return False


def main() -> None:
    if not PUBLIC_DIR.exists():
        print('public directory does not exist, navigation fix skipped')
        return

    changed = []
    for html_file in PUBLIC_DIR.rglob('*.html'):
        if fix_file(html_file):
            changed.append(str(html_file))

    print(f'Navigation fix updated {len(changed)} HTML files')
    for item in changed:
        print(f'- {item}')


if __name__ == '__main__':
    main()
