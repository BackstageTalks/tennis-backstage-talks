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


def ensure_dir(path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path, content):
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def write_json(path, payload):
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def remove_file_if_exists(path):
    if os.path.isfile(path):
        print("REMOVE FILE BEFORE DIRECTORY ALIAS:", path)
        os.remove(path)


def copy_file(src, dst):
    if not os.path.exists(src):
        print("ALIAS SKIP missing:", src)
        return False

    ensure_dir(dst)
    shutil.copyfile(src, dst)
    print("ALIAS COPY:", src, "->", dst)
    return True


def placeholder_html(title, message):
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
        "BackstageTalks",
        "No public content available."
    )


def neutral_json():
    return {
