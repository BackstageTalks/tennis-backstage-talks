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


def ensure_parent(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path, content):
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def write_json(path, payload):
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def remove_file_if_exists(path):
    if os.path.isfile(path):
        os.remove(path)
        print("REMOVED FILE:", path)


def safe_copy(src, dst):
    if not os.path.exists(src):
        print("MISSING SOURCE:", src)
        return False

    ensure_parent(dst)
    shutil.copyfile(src, dst)
    print("COPIED:", src, "->", dst)
    return True


def html_page(title, body_html):
    safe_title = html.escape(str(title))

    return """<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="UTF-8">
<title>""" + safe_title + """</title>
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { box-sizing: border-box; }

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

p {
    color: #cfcfcf;
    font-size: 18px;
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
<h1>""" + safe_title + """</h1>
""" + body_html + """
</div>
</body>
</html>
"""


def neutral_html():
    return html_page(
        "BackstageTalks",
        "<p>No public content available.</p>"
    )


def placeholder_html(title, message):
    return html_page(
        title,
        "<p>" + html.escape(str(message)) + "</p>"
    )


def neutral_rss(title):
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


def placeholder_rss(title, linked_page_alias):
    safe_title = html.escape(str(title))
    linked_page_url = BASE + linked_page_alias + "/"

    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>""" + safe_title + """</title>
<link>""" + linked_page_url + """</link>
<description>No content available yet</description>
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


def publish_json_alias(src, alias, name):
    dst = "public/" + alias

    if not safe_copy(src, dst):
        write_json(dst, placeholder_json(name))
        print("WROTE JSON PLACEHOLDER:", dst)


def publish_html_alias(src, alias, title, message):
    remove_file_if_exists("public/" + alias)

    dst = "public/" + alias + "/index.html"

    if os.path.exists(src):
        write_text(dst, read_text(src))
        print("WROTE HTML ALIAS:", dst)
    else:
        write_text(dst, placeholder_html(title, message))
        print("WROTE HTML PLACEHOLDER:", dst)


def rewrite_rss_links(xml_text, target_url):
    return re.sub(
        r"<link>.*?</link>",
        "<link>" + target_url + "</link>",
        xml_text,
        flags=re.DOTALL
    )


def publish_rss_alias(src_xml, alias, linked_page_alias, title):
    xml_target = "public/" + alias + ".xml"
    no_ext_target = "public/" + alias
    linked_page_url = BASE + linked_page_alias + "/"

    if os.path.exists(src_xml):
        xml = rewrite_rss_links(read_text(src_xml), linked_page_url)
        print("RSS SOURCE FOUND:", src_xml)
    else:
        xml = placeholder_rss(title, linked_page_alias)
        print("RSS SOURCE MISSING, PLACEHOLDER:", src_xml)

    write_text(xml_target, xml)
    write_text(no_ext_target, xml)

    print("WROTE RSS ALIAS:", xml_target)
    print("WROTE RSS ALIAS:", no_ext_target)


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


def link_card(label, url, note):
    safe_label = html.escape(str(label))
    safe_url = html.escape(str(url))
    safe_note = html.escape(str(note))

    note_html = ""

    if safe_note:
        note_html = "<div class=\"note\">" + safe_note + "</div>"

    return (
        "<div class=\"link-card\">\n"
        "<div class=\"label\">" + safe_label + "</div>\n"
        "\""" + safe_url + "</a>\n"
        + note_html + "\n"
        "</div>\n"
    )


def create_links_page():
    alias = ALIASES["links_page"]
    remove_file_if_exists("public/" + alias)

    dst = "public/" + alias + "/index.html"

    links = [
        ("Source manifest:", BASE + ALIASES["source_manifest"], "Interná mapa zdrojov"),
        ("Source audit:", BASE + ALIASES["source_audit"], "Interný audit zdrojov"),

        ("TOP 7 web:", BASE + ALIASES["top_page"] + "/", "Denný TOP 7 výber"),
        ("TOP 7 RSS:", BASE + ALIASES["top_rss"] + ".xml", "RSS feed pre TOP 7"),

        ("TOP 7 výsledky web:", BASE + ALIASES["top_results_page"] + "/", "Vyhodnotenie TOP 7"),
        ("TOP 7 výsledky RSS:", BASE + ALIASES["top_results_rss"] + ".xml", "RSS výsledkov TOP 7"),

        ("ALL web:", BASE + ALIASES["all_page"] + "/", "Všetky dostupné pick-y"),
        ("ALL RSS:", BASE + ALIASES["all_rss"] + ".xml", "RSS všetkých dostupných pickov"),

        ("ALL výsledky web:", BASE + ALIASES["all_results_page"] + "/", "Vyhodnotenie ALL"),
        ("ALL výsledky RSS:", BASE + ALIASES["all_results_rss"] + ".xml", "RSS výsledkov ALL"),
    ]

    cards = ""

    for label, url, note in links:
        cards += link_card(label, url, note)

    body = (
        "<div class=\"grid\">\n"
        + cards
        + "\n</div>\n"
        + "<div class=\"footer\">Generated by BackstageTalks Tennis workflow.</div>"
    )

    write_text(dst, html_page("BackstageTalks Tennis Links", body))
    print("WROTE LINK HUB:", dst)


def publish_aliases():
    os.makedirs("public", exist_ok=True)

    publish_json_alias(
        "public/source_manifest.json",
        ALIASES["source_manifest"],
        "source_manifest"
    )

    publish_json_alias(
        "public/source_audit.json",
        ALIASES["source_audit"],
        "source_audit"
    )

    publish_html_alias(
        "public/index.html",
        ALIASES["top_page"],
        "BackstageTalks Tennis TOP 7",
        "TOP 7 content is not available yet."
    )

    publish_rss_alias(
        "public/tennis.xml",
        ALIASES["top_rss"],
        ALIASES["top_page"],
        "BackstageTalks Tennis TOP 7 RSS"
    )

    publish_html_alias(
        "public/results/index.html",
        ALIASES["top_results_page"],
        "BackstageTalks Tennis TOP 7 Results",
        "TOP 7 results are not available yet."
    )

    publish_rss_alias(
        "public/results.xml",
        ALIASES["top_results_rss"],
        ALIASES["top_results_page"],
        "BackstageTalks Tennis TOP 7 Results RSS"
    )

    publish_html_alias(
        "public/all/index.html",
        ALIASES["all_page"],
        "BackstageTalks Tennis ALL",
        "ALL content is not available yet."
    )

    publish_rss_alias(
        "public/tennis_all.xml",
        ALIASES["all_rss"],
        ALIASES["all_page"],
        "BackstageTalks Tennis ALL RSS"
    )

    publish_html_alias(
        "public/all_results/index.html",
        ALIASES["all_results_page"],
        "BackstageTalks Tennis ALL Results",
        "ALL results are not available yet."
    )

    publish_rss_alias(
        "public/all_results.xml",
        ALIASES["all_results_rss"],
        ALIASES["all_results_page"],
        "BackstageTalks Tennis ALL Results RSS"
    )

    create_links_page()

    write_robots_txt()

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

    for key, alias in ALIASES.items():
        if key.endswith("_rss"):
            print(key, "=>", BASE + alias + ".xml")
        elif key.endswith("_page") or key == "links_page":
            print(key, "=>", BASE + alias + "/")
        else:
            print(key, "=>", BASE + alias)


if __name__ == "__main__":
    publish_aliases()
