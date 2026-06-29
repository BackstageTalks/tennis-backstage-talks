import os
import re
import json
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


def write_json(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


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
    Prepíše všetky <link>...</link> v RSS na skrytý web alias.
    RSS zostane validné, ale nebude odkazovať na verejné staré URL.
    """
    return re.sub(
        r"<link>.*?</link>",
        f"<link>{target_url}</link>",
        xml_text,
        flags=re.DOTALL,
    )


def placeholder_rss(title, linked_page_alias, description="No content available yet"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{title}</title>
<link>{BASE + linked_page_alias}</link>
<description>{description}</description>
</channel>
</rss>
"""


def publish_rss_alias(src_xml, alias, linked_page_alias, title):
    """
    Vytvorí RSS aliasy:
    - public/H4...
    - public/H4....xml

    Ak zdrojový RSS ešte neexistuje, vytvorí validný placeholder RSS,
    aby link nikdy nekončil 404.
    """
    no_ext_path = f"public/{alias}"
    xml_path = f"public/{alias}.xml"

    if os.path.exists(src_xml):
        xml = read_text(src_xml)
        xml = rewrite_rss_links(xml, BASE + linked_page_alias)
        print("RSS ALIAS SOURCE FOUND:", src_xml)
    else:
        print("RSS ALIAS SOURCE MISSING, writing placeholder:", src_xml)
        xml = placeholder_rss(
            title=title,
            linked_page_alias=linked_page_alias,
            description="No content available yet"
        )

    write_text(no_ext_path, xml)
    write_text(xml_path, xml)

    print("RSS ALIAS WRITE:", no_ext_path)
    print("RSS ALIAS WRITE:", xml_path)

    return True


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


def neutral_json():
    return {
        "status": "NO_PUBLIC_CONTENT",
        "message": "No public content available."
    }


def write_robots_txt():
    """
    Nezakazujeme celé /, lebo niektoré RSS čítačky rešpektujú robots.txt.
    Namiesto toho neutralizujeme verejné stránky a nechávame skryté aliasy dostupné.
    """
    content = "\n".join([
        "User-agent: *",
        "Disallow: /tennis.xml",
        "Disallow: /tennis_all.xml",
        "Disallow: /results.xml",
        "Disallow: /all_results.xml",
        "Disallow: /all/",
        "Disallow: /results/",
        "Disallow: /all_results/",
        "Disallow: /source_manifest.json",
        "Disallow: /source_audit.json",
        ""
    ])

    write_text("public/robots.txt", content)


def publish_aliases():
    os.makedirs("public", exist_ok=True)

    # JSON aliases
    copy_file("public/source_manifest.json", f"public/{ALIASES['source_manifest']}")
    copy_file("public/source_audit.json", f"public/{ALIASES['source_audit']}")

    # TOP page
    copy_file("public/index.html", f"public/{ALIASES['top_page']}")

    # TOP RSS
    publish_rss_alias(
        src_xml="public/tennis.xml",
        alias=ALIASES["top_rss"],
        linked_page_alias=ALIASES["top_page"],
        title="BackstageTalks Tennis TOP 7 RSS",
    )

    # TOP results page
    copy_file("public/results/index.html", f"public/{ALIASES['top_results_page']}")

    # TOP results RSS
    publish_rss_alias(
        src_xml="public/results.xml",
        alias=ALIASES["top_results_rss"],
        linked_page_alias=ALIASES["top_results_page"],
        title="BackstageTalks Tennis TOP 7 Results RSS",
    )

    # ALL page
    copy_file("public/all/index.html", f"public/{ALIASES['all_page']}")

    # ALL RSS
    publish_rss_alias(
        src_xml="public/tennis_all.xml",
        alias=ALIASES["all_rss"],
        linked_page_alias=ALIASES["all_page"],
        title="BackstageTalks Tennis ALL RSS",
    )

    # ALL results page
    copy_file("public/all_results/index.html", f"public/{ALIASES['all_results_page']}")

    # ALL results RSS
    publish_rss_alias(
        src_xml="public/all_results.xml",
        alias=ALIASES["all_results_rss"],
        linked_page_alias=ALIASES["all_results_page"],
        title="BackstageTalks Tennis ALL Results RSS",
    )

    # robots.txt
    write_robots_txt()

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

    # Neutralize public technical JSON files after aliases are created.
    write_json("public/source_manifest.json", neutral_json())
    write_json("public/source_audit.json", neutral_json())

    print("PRIVATE ALIASES GENERATED")
    for key, alias in ALIASES.items():
        print(key, "=>", BASE + alias)

        if key.endswith("_rss"):
            print(key + "_xml", "=>", BASE + alias + ".xml")


if __name__ == "__main__":
    publish_aliases()
