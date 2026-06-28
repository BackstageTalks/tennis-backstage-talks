import os
import re
import shutil

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"

ALIASES = {
    "source_manifest": "H4V34N1C3D4Y170",
    "source_audit": "H4V34N1C3D4Y171",

    "top_page": "H4V34N1C3D4Y180",
    "top_rss": "H4V34N1C3D4Y181",

    "top_results_page": "H4V34N1C3D4Y182",
    "top_results_rss": "H4V34N1C3D4Y183",

    "all_page": "H4V34N1C3D4Y184",
    "all_rss": "H4V34N1C3D4Y185",

    "all_results_page": "H4V34N1C3D4Y186",
    "all_results_rss": "H4V34N1C3D4Y187",
}


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def copy_file(src, dst):
    if not os.path.exists(src):
        print("ALIAS SKIP missing:", src)
        return False

    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    shutil.copyfile(src, dst)
    print("ALIAS COPY:", src, "->", dst)
    return True


def rewrite_rss_links(xml_text, target_url):
    """
    RSS zostane validný, ale všetky <link>...</link> budú smerovať
    na skrytý alias namiesto verejných starých URL.
    """
    return re.sub(
        r"<link>.*?</link>",
        f"<link>{target_url}</link>",
        xml_text,
        flags=re.DOTALL,
    )


def neutral_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>BackstageTalks</title>
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {
    font-family: Arial, sans-serif;
    background: #160f0f;
    color: #f4f4f4;
    margin: 0;
    padding: 40px;
}
.container {
    max-width: 720px;
    margin: 0 auto;
}
h1 {
    font-size: 34px;
}
p {
    color: #cfcfcf;
    font-size: 18px;
}
</style>
</head>
<body>
<div class="container">
<h1>BackstageTalks</h1>
<p>No public content available.</p>
</div>
</body>
</html>
"""


def neutral_rss(title="BackstageTalks"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{title}</title>
<link>{BASE}</link>
<description>No public content available</description>
</channel>
</rss>
"""


def publish_aliases():
    os.makedirs("public", exist_ok=True)

    # JSON aliases
    copy_file("public/source_manifest.json", f"public/{ALIASES['source_manifest']}")
    copy_file("public/source_audit.json", f"public/{ALIASES['source_audit']}")

    # TOP page
    copy_file("public/index.html", f"public/{ALIASES['top_page']}")

    # TOP RSS
    if os.path.exists("public/tennis.xml"):
        xml = read_text("public/tennis.xml")
        xml = rewrite_rss_links(xml, BASE + ALIASES["top_page"])
        write_text(f"public/{ALIASES['top_rss']}", xml)

    # TOP results page
    copy_file("public/results/index.html", f"public/{ALIASES['top_results_page']}")

    # TOP results RSS
    if os.path.exists("public/results.xml"):
        xml = read_text("public/results.xml")
        xml = rewrite_rss_links(xml, BASE + ALIASES["top_results_page"])
        write_text(f"public/{ALIASES['top_results_rss']}", xml)

    # ALL page
    copy_file("public/all/index.html", f"public/{ALIASES['all_page']}")

    # ALL RSS
    if os.path.exists("public/tennis_all.xml"):
        xml = read_text("public/tennis_all.xml")
        xml = rewrite_rss_links(xml, BASE + ALIASES["all_page"])
        write_text(f"public/{ALIASES['all_rss']}", xml)

    # ALL results page
    copy_file("public/all_results/index.html", f"public/{ALIASES['all_results_page']}")

    # ALL results RSS
    if os.path.exists("public/all_results.xml"):
        xml = read_text("public/all_results.xml")
        xml = rewrite_rss_links(xml, BASE + ALIASES["all_results_page"])
        write_text(f"public/{ALIASES['all_results_rss']}", xml)

    # robots.txt
    write_text(
        "public/robots.txt",
        "User-agent: *\nDisallow: /\n"
    )

    # Neutralize old public pages and feeds.
    write_text("public/index.html", neutral_html())
    write_text("public/tennis.xml", neutral_rss("BackstageTalks Tennis"))
    write_text("public/tennis_all.xml", neutral_rss("BackstageTalks Tennis ALL"))
    write_text("public/results.xml", neutral_rss("BackstageTalks Tennis Results"))
    write_text("public/all_results.xml", neutral_rss("BackstageTalks Tennis ALL Results"))

    os.makedirs("public/all", exist_ok=True)
    os.makedirs("public/results", exist_ok=True)
    os.makedirs("public/all_results", exist_ok=True)

    write_text("public/all/index.html", neutral_html())
    write_text("public/results/index.html", neutral_html())
    write_text("public/all_results/index.html", neutral_html())

    print("PRIVATE ALIASES GENERATED")
    for key, alias in ALIASES.items():
        print(key, "=>", BASE + alias)


if __name__ == "__main__":
    publish_aliases()
