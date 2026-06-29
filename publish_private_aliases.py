import os
import re
import json
import shutil
import html

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"

ALIASES = {
    "links_page": "H4V34N1C3D4Y177",

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


def remove_file_if_exists(path):
    if os.path.isfile(path):
        print("REMOVE FILE BEFORE DIRECTORY ALIAS:", path)
        os.remove(path)


def placeholder_html(title="BackstageTalks", message="Content is not available yet."):
    safe_title = html.escape(str(title))
    safe_message = html.escape(str(message))

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>""" + safe_title + """</title>
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
    max-width: 760px;
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
<h1>""" + safe_title + """</h1>
<p>""" + safe_message + """</p>
</div>
</body>
</html>
"""


def neutral_html():
    return placeholder_html(
        title="BackstageTalks",
        message="No public content available."
    )


def neutral_rss(title="BackstageTalks"):
    safe_title = html.escape(str(title))

    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>""" + safe_title + """</title>
<link>""" + BASE + """</link>
<description>No public content available</description>
</channel>
</rss>
"""


def placeholder_rss(title, linked_page_alias, description="No content available yet"):
    safe_title = html.escape(str(title))
    safe_description = html.escape(str(description))
    linked_page_url = BASE + linked_page_alias + "/"

    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>""" + safe_title + """</title>
<link>""" + linked_page_url + """</link>
<description>""" + safe_description + """</description>
</channel>
</rss>
"""


def neutral_json():
    return {
        "status": "NO_PUBLIC_CONTENT",
        "message": "No public content available."
    }


def placeholder_json(name):
    return {
        "status": "PLACEHOLDER",
        "name": name,
        "message": "Content is not available yet."
    }


def copy_or_placeholder_json(src, alias_file, name):
    dst = "public/" + alias_file

    if os.path.exists(src):
        return copy_file(src, dst)

    print("JSON ALIAS SOURCE MISSING, writing placeholder:", src)
    write_json(dst, placeholder_json(name))
    return True


def copy_or_placeholder_html(src, alias_dir, title, message):
    """
    Web alias vytvárame iba ako adresár s index.html.

    Správna URL:
    /H4.../
    """
    direct_path = "public/" + alias_dir
    index_dst = "public/" + alias_dir + "/index.html"

    remove_file_if_exists(direct_path)

    if os.path.exists(src):
        content = read_text(src)
    else:
        print("HTML ALIAS SOURCE MISSING, writing placeholder:", src)
        content = placeholder_html(title=title, message=message)

    write_text(index_dst, content)

    print("HTML ALIAS WRITE:", index_dst)

    return True


def rewrite_rss_links(xml_text, target_url):
    replacement = "<link>" + target_url + "</link>"

    return re.sub(
        r"<link>.*?</link>",
        replacement,
        xml_text,
        flags=re.DOTALL,
    )


def publish_rss_alias(src_xml, alias, linked_page_alias, title):
    no_ext_path = "public/" + alias
    xml_path = "public/" + alias + ".xml"

    linked_page_url = BASE + linked_page_alias + "/"

    if os.path.exists(src_xml):
        xml = read_text(src_xml)
        xml = rewrite_rss_links(xml, linked_page_url)
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


def write_robots_txt():
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


def link_item(label, url, note=""):
    safe_label = html.escape(str(label))
    safe_url = html.escape(str(url))
    safe_note = html.escape(str(note))

    note_html = ""
    if note:
        note_html = "<div class='note'>" + safe_note + "</div>"

    return (
        "<div class='link-card'>\n"
        "  <div class='label'>" + safe_label + "</div>\n"
        "  <a href='" + safe_url + "' target='_blank' rel='noopener noreferrer'>" + safe_url + "</a>\n"
        "  " + note_html + "\n"
        "</div>\n"
    )


def create_links_page():
    """
    Central private link hub.

    URL:
    /H4V34N1C3D4Y177/
    """
    alias = ALIASES["links_page"]
    direct_path = "public/" + alias
    index_path = "public/" + alias + "/index.html"

    remove_file_if_exists(direct_path)

    links = [
        ("Source manifest:", BASE + ALIASES ("Source audit:", BASE + ALIASES["source_audit"], "Interný audit zdrojov"),

        ("TOP 7 web:", BASE + ALIASES["top_page"] + "/", "Denný TOP 7 výber"),
        ("TOP 7 RSS:", BASE + ALIASES["top_rss"] + ".xml", "RSS feed pre TOP 7"),

        ("TOP 7 výsledky web:", BASE + ALIASES["top_results_page"] + "/", "Vyhodnotenie TOP 7"),
        ("TOP 7 výsledky RSS:", BASE + ALIASES["top_results_rss"] + ".xml", "RSS výsledkov TOP 7"),

        ("ALL web:", BASE + ALIASES["all_page"] + "/", "Všetky dostupné pick-y"),
        ("ALL RSS:", BASE + ALIASES["all_rss"] + ".xml", "RSS všetkých dostupných pickov"),

        ("ALL výsledky web:", BASE + ALIASES["all_results_page"] + "/", "Vyhodnotenie ALL"),
        ("ALL výsledky RSS:", BASE + ALIASES["all_results_rss"] + ".xml", "RSS výsledkov ALL"),
    ]

    cards = "\n".join(link_item(label, url, note) for label, url, note in links)

    page = """<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="UTF-8">
<title>BackstageTalks Tennis Links</title>
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: #160f0f;
    color: #f4f4f4;
    margin: 0;
    padding: 22px;
}

.container {
    max-width: 1000px;
    margin: 0 auto;
}

h1 {
    font-size: 42px;
    line-height: 1.1;
    margin: 26px 0 24px;
}

.grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
}

.link-card {
    background: #211818;
    border: 1px solid #352727;
    border-radius: 16px;
    padding: 16px;
}

.label {
    font-weight: 700;
    font-size: 18px;
    margin-bottom: 8px;
    color: #ffffff;
}

a {
    color: #8db7ff;
    word-break: break-all;
    font-size: 16px;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

.note {
    margin-top: 8px;
    color: #aaa;
    font-size: 14px;
}

.footer {
    color: #888;
    margin-top: 26px;
    font-size: 14px;
}

@media (min-width: 760px) {
    .grid {
        grid-template-columns: 1fr 1fr;
    }
}
</style>
</head>
<body>
<div class="container">
<h1>BackstageTalks Tennis Links</h1>

<div class="grid">
""" + cards + """
</div>

<div class="footer">
Generated by BackstageTalks Tennis workflow. Private alias link hub.
</div>
</div>
</body>
</html>
"""

    write_text(index_path, page)
    print("LINK HUB WRITE:", index_path)
    print("LINK HUB URL:", BASE + alias + "/")


def publish_aliases():
    os.makedirs("public", exist_ok=True)

    copy_or_placeholder_json(
        "public/source_manifest.json",
        ALIASES["source_manifest"],
        "source_manifest"
    )

    copy_or_placeholder_json(
        "public/source_audit.json",
        ALIASES["source_audit"],
        "source_audit"
    )

    copy_or_placeholder_html(
        "public/index.html",
        ALIASES["top_page"],
        "BackstageTalks Tennis TOP 7",
        "TOP 7 content is not available yet."
    )

    publish_rss_alias(
        src_xml="public/tennis.xml",
        alias=ALIASES["top_rss"],
        linked_page_alias=ALIASES["top_page"],
        title="BackstageTalks Tennis TOP 7 RSS",
    )

    copy_or_placeholder_html(
        "public/results/index.html",
        ALIASES["top_results_page"],
        "BackstageTalks Tennis TOP 7 Results",
        "TOP 7 results are not available yet."
    )

    publish_rss_alias(
        src_xml="public/results.xml",
        alias=ALIASES["top_results_rss"],
        linked_page_alias=ALIASES["top_results_page"],
        title="BackstageTalks Tennis TOP 7 Results RSS",
    )

    copy_or_placeholder_html(
        "public/all/index.html",
        ALIASES["all_page"],
        "BackstageTalks Tennis ALL",
        "ALL content is not available yet."
    )

    publish_rss_alias(
        src_xml="public/tennis_all.xml",
        alias=ALIASES["all_rss"],
        linked_page_alias=ALIASES["all_page"],
        title="BackstageTalks Tennis ALL RSS",
    )

    copy_or_placeholder_html(
        "public/all_results/index.html",
        ALIASES["all_results_page"],
        "BackstageTalks Tennis ALL Results",
        "ALL results are not available yet."
    )

    publish_rss_alias(
        src_xml="public/all_results.xml",
        alias=ALIASES["all_results_rss"],
        linked_page_alias=ALIASES["all_results_page"],
        title="BackstageTalks Tennis ALL Results RSS",
    )

    create_links_page()

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

    write_json("public/source_manifest.json", neutral_json())
    write_json("public/source_audit.json", neutral_json())

    print("PRIVATE ALIASES GENERATED")
    print("links_page =>", BASE + ALIASES["links_page"] + "/")
    print("source_manifest =>", BASE + ALIASES["source_manifest"])
    print("source_audit =>", BASE + ALIASES["source_audit"])
    print("top_page =>", BASE + ALIASES["top_page"] + "/")
    print("top_rss =>", BASE + ALIASES["top_rss"] + ".xml")
    print("top_results_page =>", BASE + ALIASES["top_results_page"] + "/")
    print("top_results_rss =>", BASE + ALIASES["top_results_rss"] + ".xml")
    print("all_page =>", BASE + ALIASES["all_page"] + "/")
    print("all_rss =>", BASE + ALIASES["all_rss"] + ".xml")
    print("all_results_page =>", BASE + ALIASES["all_results_page"] + "/")
    print("all_results_rss =>", BASE + ALIASES["all_results_rss"] + ".xml")


if __name__ == "__main__":
    publish_aliases()
