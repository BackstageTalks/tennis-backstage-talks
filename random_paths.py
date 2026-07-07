import re
import shutil
from pathlib import Path


BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

CORQ_PATH = "h4v34n1c3d4y180"
THINQ_PATH = "h4v34n1c3d4y181"
BLEND_PATH = "h4v34n1c3d4y182"
ALL_PATH = "h4v34n1c3d4y183"
RESULTS_PATH = "h4v34n1c3d4y184"

CORQ_RSS_PATH = "h4v34n1c3d4y185.xml"
THINQ_RSS_PATH = "h4v34n1c3d4y186.xml"
BLEND_RSS_PATH = "h4v34n1c3d4y187.xml"


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def html_link(url, label):
    return f'<a href="{url}">{label}</a>'


def copy_file(source, destination):
    source_path = Path(source)
    destination_path = Path(destination)

    if not source_path.exists():
        print("SKIP COPY - SOURCE MISSING:", source)
        return False

    ensure_dir(destination_path.parent)
    shutil.copy2(source_path, destination_path)
    print("COPIED:", source, "->", destination)
    return True


def remove_path(path):
    target = Path(path)

    if not target.exists():
        return

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    print("REMOVED OLD PATH:", path)


def create_root_redirect():
    root_path = Path("public/index.html")
    root_path.write_text(
        f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=./{CORQ_PATH}/">
  <title>BackstageTalks</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0f172a;
      color: #e5e7eb;
      font-family: Arial, Helvetica, sans-serif;
    }}
    a {{ color: #38bdf8; font-weight: 800; }}
  </style>
</head>
<body>
  <div>
    Redirecting to <a href="./{CORQ_PATH}/">Corq</a>...
  </div>
</body>
</html>
''',
        encoding="utf-8",
    )
    print("ROOT REDIRECT CREATED:", root_path)


def build_nav_html():
    links = [
        html_link(f"{BASE_URL}/{CORQ_PATH}/", "Corq"),
        html_link(f"{BASE_URL}/{THINQ_PATH}/", "Thinq"),
        html_link(f"{BASE_URL}/{BLEND_PATH}/", "Blend"),
        html_link(f"{BASE_URL}/{CORQ_RSS_PATH}", "Corq RSS"),
        html_link(f"{BASE_URL}/{THINQ_RSS_PATH}", "Thinq RSS"),
        html_link(f"{BASE_URL}/{BLEND_RSS_PATH}", "Blend RSS"),
        html_link(f"{BASE_URL}/{ALL_PATH}/", "All"),
        html_link(f"{BASE_URL}/{RESULTS_PATH}/", "Results"),
    ]

    return f'''
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
'''


def replace_navigation_in_file(path):
    file_path = Path(path)

    if not file_path.exists():
        print("SKIP NAV FIX - FILE MISSING:", path)
        return False

    text = file_path.read_text(encoding="utf-8", errors="replace")
    nav_html = build_nav_html()

    new_text, count = re.subn(
        r'<nav class="nav" aria-label="Main navigation">.*?</nav>',
        nav_html,
        text,
        count=1,
        flags=re.DOTALL,
    )

    if count == 0:
        print("NAV NOT FOUND:", path)
        return False

    file_path.write_text(new_text, encoding="utf-8")
    print("NAV UPDATED:", path)
    return True


def rewrite_rss_links(path, page_url):
    file_path = Path(path)

    if not file_path.exists():
        print("SKIP RSS LINK FIX - FILE MISSING:", path)
        return False

    text = file_path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r"<link>.*?</link>",
        f"<link>{page_url}</link>",
        text,
        flags=re.DOTALL,
    )
    file_path.write_text(text, encoding="utf-8")
    print("RSS LINKS UPDATED:", path, "->", page_url)
    return True


def create_placeholder_page(destination, title, message):
    destination_path = Path(destination)
    ensure_dir(destination_path.parent)
    nav_html = build_nav_html()
    page_html = f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ background:#0f172a; color:#e5e7eb; font-family:Arial,Helvetica,sans-serif; margin:0; padding:28px; }}
    .wrap {{ max-width:960px; margin:0 auto; }}
    .nav {{ display:flex; gap:18px; align-items:center; flex-wrap:wrap; margin-bottom:28px; }}
    .nav a {{ color:#e5e7eb; text-decoration:none; font-weight:900; font-size:14px; letter-spacing:.04em; }}
    .nav a:hover {{ color:#38bdf8; }}
    .card {{ background:#111827; border:1px solid #334155; border-radius:16px; padding:24px; }}
    h1 {{ margin-top:0; }}
    p {{ color:#94a3b8; line-height:1.6; }}
  </style>
</head>
<body>
  <div class="wrap">
    {nav_html}
    <div class="card">
      <h1>{title}</h1>
      <p>{message}</p>
    </div>
  </div>
</body>
</html>
'''
    destination_path.write_text(page_html, encoding="utf-8")
    print("PLACEHOLDER PAGE CREATED:", destination)
    return True


def create_placeholder_rss(destination):
    destination_path = Path(destination)
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>BackstageTalks Statistical Engine - Blend</title>
<link>{BASE_URL}/{BLEND_PATH}/</link>
<description>Blend RSS feed is available after Blend predictions are generated.</description>
</channel>
</rss>
'''
    destination_path.write_text(rss, encoding="utf-8")
    print("PLACEHOLDER RSS CREATED:", destination)
    return True


def create_random_page_outputs():
    copied = []

    page_map = [
        ("public/index.html", f"public/{CORQ_PATH}/index.html"),
        ("public/BsT/index.html", f"public/{THINQ_PATH}/index.html"),
        ("public/Blend/index.html", f"public/{BLEND_PATH}/index.html"),
        ("public/all/index.html", f"public/{ALL_PATH}/index.html"),
        ("public/results/index.html", f"public/{RESULTS_PATH}/index.html"),
    ]

    for source, destination in page_map:
        ok = copy_file(source, destination)
        if ok:
            copied.append(destination)

    if f"public/{BLEND_PATH}/index.html" not in copied:
        create_placeholder_page(
            f"public/{BLEND_PATH}/index.html",
            "Blend",
            "Blend page is prepared. Blend predictions will appear here after build_pages.py starts generating public/Blend/index.html.",
        )
        copied.append(f"public/{BLEND_PATH}/index.html")

    return copied


def create_random_rss_outputs():
    rss_map = [
        ("public/tennis.xml", f"public/{CORQ_RSS_PATH}", f"{BASE_URL}/{CORQ_PATH}/"),
        ("public/tennis_bst.xml", f"public/{THINQ_RSS_PATH}", f"{BASE_URL}/{THINQ_PATH}/"),
        ("public/tennis_blend.xml", f"public/{BLEND_RSS_PATH}", f"{BASE_URL}/{BLEND_PATH}/"),
    ]

    for source, destination, page_url in rss_map:
        ok = copy_file(source, destination)
        if ok:
            rewrite_rss_links(destination, page_url)

    if not Path(f"public/{BLEND_RSS_PATH}").exists():
        create_placeholder_rss(f"public/{BLEND_RSS_PATH}")


def remove_old_public_paths():
    old_paths = [
        "public/all",
        "public/BsT",
        "public/Blend",
        "public/results",
        "public/tennis.xml",
        "public/tennis_bst.xml",
        "public/tennis_blend.xml",
        "public/tennis_all.xml",
    ]

    for path in old_paths:
        remove_path(path)


def verify_random_outputs():
    required_files = [
        "public/index.html",
        f"public/{CORQ_PATH}/index.html",
        f"public/{THINQ_PATH}/index.html",
        f"public/{BLEND_PATH}/index.html",
        f"public/{ALL_PATH}/index.html",
        f"public/{RESULTS_PATH}/index.html",
        f"public/{CORQ_RSS_PATH}",
        f"public/{THINQ_RSS_PATH}",
        f"public/{BLEND_RSS_PATH}",
    ]

    missing = []

    for path in required_files:
        if not Path(path).exists():
            missing.append(path)

    if missing:
        print("")
        print("MISSING RANDOM OUTPUTS:")
        for path in missing:
            print(path)
        raise RuntimeError("Random path output verification failed.")

    print("")
    print("RANDOM OUTPUT VERIFICATION OK")


def main():
    print("")
    print("=== RANDOM PATH REMAP START ===")

    copied_pages = create_random_page_outputs()
    create_random_rss_outputs()

    for path in copied_pages:
        replace_navigation_in_file(path)

    remove_old_public_paths()
    create_root_redirect()
    verify_random_outputs()

    print("=== RANDOM PATH REMAP DONE ===")
    print("")


if __name__ == "__main__":
    main()
