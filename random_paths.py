import os
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
    Path(path).mkdir(
        parents=True,
        exist_ok=True,
    )


def copy_file(source, destination):
    source_path = Path(source)
    destination_path = Path(destination)

    if not source_path.exists():
        print(
            "SKIP COPY - SOURCE MISSING:",
            source,
        )

        return False

    ensure_dir(
        destination_path.parent
    )

    shutil.copy2(
        source_path,
        destination_path,
    )

    print(
        "COPIED:",
        source,
        "->",
        destination,
    )

    return True


def remove_path(path):
    target = Path(path)

    if not target.exists():
        return

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    print(
        "REMOVED OLD PATH:",
        path,
    )


def build_nav_html():
    links = [
        (
            f"{BASE_URL}/{CORQ_PATH}/",
            "Corq",
        ),
        (
            f"{BASE_URL}/{THINQ_PATH}/",
            "Thinq",
        ),
        (
            f"{BASE_URL}/{BLEND_PATH}/",
            "Blend",
        ),
        (
            f"{BASE_URL}/{CORQ_RSS_PATH}",
            "Corq RSS",
        ),
        (
            f"{BASE_URL}/{THINQ_RSS_PATH}",
            "Thinq RSS",
        ),
        (
            f"{BASE_URL}/{ALL_PATH}/",
            "All",
        ),
        (
            f"{BASE_URL}/{RESULTS_PATH}/",
            "Results",
        ),
    ]

    html_links = []

    for url, label in links:
        html_links.append(
            f'{url}{label}</a>'
        )

    return f"""
<nav class="nav" aria-label="Main navigation">
    {" ".join(html_links)}
</nav>
"""


def replace_navigation_in_file(path):
    file_path = Path(path)

    if not file_path.exists():
        print(
            "SKIP NAV FIX - FILE MISSING:",
            path,
        )

        return False

    text = file_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    nav_html = build_nav_html()

    new_text, count = re.subn(
        r'<nav class="nav" aria-label="Main navigation">.*?</nav>',
        nav_html,
        text,
        count=1,
        flags=re.DOTALL,
    )

    if count == 0:
        print(
            "NAV NOT FOUND:",
            path,
        )

        return False

    file_path.write_text(
        new_text,
        encoding="utf-8",
    )

    print(
        "NAV UPDATED:",
        path,
    )

    return True


def create_random_page_outputs():
    copied = []

    page_map = [
        (
            "public/index.html",
            f"public/{CORQ_PATH}/index.html",
        ),
        (
            "public/BsT/index.html",
            f"public/{THINQ_PATH}/index.html",
        ),
        (
            "public/Blend/index.html",
            f"public/{BLEND_PATH}/index.html",
        ),
        (
            "public/all/index.html",
            f"public/{ALL_PATH}/index.html",
        ),
        (
            "public/results/index.html",
            f"public/{RESULTS_PATH}/index.html",
        ),
    ]

    for source, destination in page_map:
        ok = copy_file(
            source,
            destination,
        )

        if ok:
            copied.append(destination)

    return copied


def create_random_rss_outputs():
    rss_map = [
        (
            "public/tennis.xml",
            f"public/{CORQ_RSS_PATH}",
        ),
        (
            "public/tennis_bst.xml",
            f"public/{THINQ_RSS_PATH}",
        ),
        (
            "public/tennis_blend.xml",
            f"public/{BLEND_RSS_PATH}",
        ),
    ]

    for source, destination in rss_map:
        copy_file(
            source,
            destination,
        )


def remove_old_public_paths():
    old_paths = [
        "public/index.html",
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
        f"public/{CORQ_PATH}/index.html",
        f"public/{THINQ_PATH}/index.html",
        f"public/{BLEND_PATH}/index.html",
        f"public/{ALL_PATH}/index.html",
        f"public/{RESULTS_PATH}/index.html",
        f"public/{CORQ_RSS_PATH}",
        f"public/{THINQ_RSS_PATH}",
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

        raise RuntimeError(
            "Random path output verification failed."
        )

    print("")
    print("RANDOM OUTPUT VERIFICATION OK")


def main():
    print("")
    print("=== RANDOM PATH REMAP START ===")

    copied_pages = create_random_page_outputs()

    create_random_rss_outputs()

    for path in copied_pages:
        replace_navigation_in_file(
            path
        )

    remove_old_public_paths()

    verify_random_outputs()

    print("=== RANDOM PATH REMAP DONE ===")
    print("")


if __name__ == "__main__":
    main()
