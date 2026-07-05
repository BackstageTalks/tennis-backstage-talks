from pathlib import Path
import re

PUBLIC_DIR = Path("public")

LAYOUT_TUNE_CSS = r"""
<style id="bt-layout-tune-style">
  /* Match Intelligence layout tuning */
  .intel {
    min-width: 490px !important;
  }

  .intel-layout {
    display: grid !important;
    grid-template-columns: 138px 138px 172px !important;
    gap: 10px !important;
    align-items: stretch !important;
  }

  .intel-box {
    min-height: 108px !important;
    padding: 10px 10px !important;
    overflow: visible !important;
  }

  .data-ai-box,
  .marq-ai-box {
    min-width: 138px !important;
  }

  .sets-box {
    min-width: 172px !important;
  }

  .sets-box .intel-row {
    grid-template-columns: 62px minmax(82px, 1fr) !important;
    column-gap: 8px !important;
  }

  .sets-box .intel-row span:first-child,
  .sets-box .intel-row span:last-child {
    white-space: nowrap !important;
  }

  .ai-diff {
    margin-top: 6px !important;
    padding-top: 5px !important;
    border-top: 1px solid rgba(148, 163, 184, .25) !important;
    font-size: 10px !important;
    line-height: 1.2 !important;
    text-align: right !important;
    font-weight: 900 !important;
    white-space: nowrap !important;
  }

  .marq-signal {
    min-height: 38px !important;
  }

  @media (max-width: 1200px) {
    .intel {
      min-width: 230px !important;
    }

    .intel-layout {
      grid-template-columns: 1fr !important;
    }

    .data-ai-box,
    .marq-ai-box,
    .sets-box {
      min-width: 0 !important;
    }
  }
</style>
"""


def inject_layout_css(html: str) -> str:
    html = re.sub(
        r'<style[^>]*id=["\']bt-layout-tune-style["\'][\s\S]*?</style>',
        '',
        html,
        flags=re.I,
    )

    if "</head>" in html:
        return html.replace("</head>", LAYOUT_TUNE_CSS + "\n</head>", 1)

    return LAYOUT_TUNE_CSS + "\n" + html


def fix_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    fixed = inject_layout_css(original)
    if fixed != original:
        path.write_text(fixed, encoding="utf-8")
        return True
    return False


def main() -> None:
    if not PUBLIC_DIR.exists():
        print("public directory does not exist, layout tune skipped")
        return

    changed = []
    for html_file in PUBLIC_DIR.rglob("*.html"):
        if fix_file(html_file):
            changed.append(str(html_file))

    print(f"Layout tune updated {len(changed)} HTML files")
    for item in changed:
        print(f"- {item}")


if __name__ == "__main__":
    main()
