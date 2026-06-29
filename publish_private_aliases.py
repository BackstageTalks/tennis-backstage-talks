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


def placeholder_html(title="BackstageTalks", message="Content is not available yet."):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {{
    font-family: Arial, sans-serif;
    background: #160f0f;
    color: #f4f4f4;
    margin: 0;
    padding: 40px;
}}
.container {{
    max-width: 720px;
    margin: 0 auto;
}}
h1 {{
    font-size: 34px;
}}
p {{
    color: #cfcfcf;
    font-size: 18px;
}}
</style>
</head>
<body>
<div class="container">
<h1>{title}</h1>
<p>{message}</p>
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
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{title}</title>
<link>{BASE}</link>
<description>No public content available</description>
</channel>
</rss>
"""


def placeholder_rss(title, linked_page_alias, description="No content available yet"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{title}</title>
<link>{BASE + linked_page_alias + "/"}</link>
<description>{description}</description>
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


def copy_or_placeholder_html(src, alias_dir, title, message):
    dst = f"public/{alias_dir}/index.html"

    if os.path.exists(src):
        return copy_file(src, dst)

    print("HTML ALIAS SOURCE MISSING, writing placeholder:", src)
    write_text(dst, placeholder_html(title=title, message=message))
    return True


def copy_or_placeholder_json(src, alias_file, name):
    dst = f"public/{alias_file}"

    if os.path.exists(src):
        return copy_file(src, dst)

    print("JSON ALIAS SOURCE MISSING, writing placeholder:", src)
    write_json(dst, placeholder_json(name))
    return True


def rewrite_rss_links(xml_text, target_url):
    return re.sub(
        r"<link>.*?</link>",
        f"<link>*target_url}</link>",
        xml_t*xt,
        flags=re.DOTALL,
    )*

def publish_rss_alias(src_xml, a*ias, linked_page_alias, title):
  * no_ext_path = f"public/{alias}"
 *  xml_path = f"public/{alias}.xml"*
    linked_page_url = BASE + link*d_page_alias + "/"

    if os.path*exists(src_xml):
        xml = rea*_text(src_xml)
        xml = rewri*e_rss_links(xml, linked_page_url)
*       print("RSS ALIAS SOURCE FOU*D:", src_xml)
    else:
        pr*nt("RSS ALIAS SOURCE MISSING, writ*ng placeholder:", src_xml)
       *xml = placeholder_rss(
           *title=title,
            linked_pa*e_alias=linked_page_alias,
       *    description="No content availa*le yet"
        )

    write_text(*o_ext_path, xml)
    write_text(xm*_path, xml)

    print("RSS ALIAS *RITE:", no_ext_path)
    print("RS* ALIAS WRITE:", xml_path)

    ret*rn True


def write_robots_txt():
*   content = "\n".join([
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
    ]*

    write_text("public/robots.tx*", content)


def publish_aliases(*:
    os.makedirs("public", exist_*k=True)

    # JSON aliases
    co*y_or_placeholder_json(
        "pu*lic/source_manifest.json",
       *ALIASES["source_manifest"],
      * "source_manifest"
    )

    copy*or_placeholder_json(
        "publ*c/source_audit.json",
        ALIA*ES["source_audit"],
        "sourc*_audit"
    )

    # TOP page as d*rectory/index.html
    copy_or_pla*eholder_html(
        "public/inde*.html",
        ALIASES["top_page"],
        "BackstageTalks Tennis T*P 7",
        "TOP 7 content is no* available yet."
    )

    # TOP *SS
    publish_rss_alias(
        *rc_xml="public/tennis.xml",
      * alias=ALIASES["top_rss"],
       *linked_page_alias=ALIASES["top_page"],
        title="BackstageTalks *ennis TOP 7 RSS",
    )

    # TOP*results page as directory/index.ht*l
    copy_or_placeholder_html(
  *     "public/results/index.html",
*       ALIASES["top_results_page"]*
        "BackstageTalks Tennis TO* 7 Results",
        "TOP 7 result* are not available yet."
    )

  * # TOP results RSS
    publish_rss*alias(
        src_xml="public/res*lts.xml",
        alias=ALIASES["top_results_rss"],
        linked_pa*e_alias=ALIASES["top_results_page"],
        title="BackstageTalks Te*nis TOP 7 Results RSS",
    )

   *# ALL page as directory/index.html*    copy_or_placeholder_html(
    *   "public/all/index.html",
      * ALIASES["all_page"],
        "Bac*stageTalks Tennis ALL",
        "A*L content is not available yet."
 *  )

    # ALL RSS
    publish_rss*alias(
        src_xml="public/ten*is_all.xml",
        alias=ALIASES*"all_rss"],
        linked_page_al*as=ALIASES["all_page"],
        ti*le="BackstageTalks Tennis ALL RSS"*
    )

    # ALL results page as *irectory/index.html
    copy_or_pl*ceholder_html(
        "public/all*results/index.html",
        ALIAS*S["all_results_page"],
        "Ba*kstageTalks Tennis ALL Results",
 *      "ALL results are not availab*e yet."
    )

    # ALL results R*S
    publish_rss_alias(
        s*c_xml="public/all_results.xml",
  *     alias=ALIASES["all_results_rss"],
        linked_page_alias=ALIA*ES["all_results_page"],
        ti*le="BackstageTalks Tennis ALL Resu*ts RSS",
    )

    write_robots_t*t()

    # Neutralize old public p*ges and feeds.
    write_text("pub*ic/index.html", neutral_html())
  * write_text("public/tennis.xml", n*utral_rss("BackstageTalks Tennis")*
    write_text("public/tennis_all*xml", neutral_rss("BackstageTalks *ennis ALL"))
    write_text("publi*/results.xml", neutral_rss("Backst*geTalks Tennis Results"))
    writ*_text("public/all_results.xml", ne*tral_rss("BackstageTalks Tennis AL* Results"))

    os.makedirs("publ*c/all", exist_ok=True)
    os.make*irs("public/results", exist_ok=Tru*)
    os.makedirs("public/all_resu*ts", exist_ok=True)

    write_tex*("public/all/index.html", neutral_*tml())
    write_text("public/resu*ts/index.html", neutral_html())
  * write_text("public/all_results/in*ex.html", neutral_html())

    wri*e_json("public/source_manifest.jso*", neutral_json())
    write_json(*public/source_audit.json", neutral*json())

    print("PRIVATE ALIASE* GENERATED")
    print("source_man*fest =>", BASE + ALIASES["source_manifest"])
    print("source_audit *>", BASE + ALIASES["source_audit"]*
    print("top_page =>", BASE + A*IASES["top_page"] + "/")
    print*"top_rss =>", BASE + ALIASES["top_rss"] + ".xml")
    print("top_resu*ts_page =>", BASE + ALIASES["top_results_page"] + "/")
    print("top*results_rss =>", BASE + ALIASES["top_results_rss"] + ".xml")
    prin*("all_page =>", BASE + ALIASES["all_page"] + "/")
    print("all_rss *>", BASE + ALIASES["all_rss"] + ".*ml")
    print("all_results_page =*", BASE + ALIASES["all_results_page"] + "/")
    print("all_results_r*s =>", BASE + ALIASES["all_results_rss"] + ".xml")


if __name__ == "*_main__":
    publish_aliases()
``*
