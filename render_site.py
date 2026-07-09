from pathlib import Path
import py_compile

path = Path('render_site.py')
text = path.read_text(encoding='utf-8')
append = ''

if 'def write_page(' not in text:
    append += '''

def write_page(predictions, title, subtitle, destination):
    html_text = render_page(predictions=predictions, title=title, subtitle=subtitle)
    directory = os.path.dirname(destination)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(destination, 'w', encoding='utf-8') as file:
        file.write(html_text)
'''

if 'def render_rss(' not in text:
    append += '''

def render_rss(predictions, title, link):
    now = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    items = []
    for prediction in predictions:
        pick = safe(prediction.get('pick'))
        opponent = safe(prediction.get('opponent'))
        probability = pct(prediction.get('probability'))
        odd = odds(prediction.get('odds'))
        description_text = f'Pick: {pick}\nOpponent: {opponent}\nWin probability: {probability}\nOdds: {odd}\n\n{HEADER_SUBTITLE}\n{FOOTER_TEXT}'
        description = html.escape(description_text)
        items.append(f'<item><title>{pick} to win vs {opponent}</title><link>{link}</link><description>{description}</description><pubDate>{now}</pubDate></item>')
    return f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{html.escape(title)}</title><link>{link}</link><description>{html.escape(HEADER_TITLE)}</description>{''.join(items)}</channel></rss>'
'''

if 'def write_rss(' not in text:
    append += '''

def write_rss(predictions, title, link, destination):
    xml = render_rss(predictions=predictions, title=title, link=link)
    directory = os.path.dirname(destination)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(destination, 'w', encoding='utf-8') as file:
        file.write(xml)
'''

if append:
    text = text.rstrip() + '\n' + append + '\n'
    path.write_text(text, encoding='utf-8')

py_compile.compile(str(path), doraise=True)
namespace = {}
exec(path.read_text(encoding='utf-8'), namespace)
missing = [name for name in ('write_page', 'write_rss') if name not in namespace]
if missing:
    raise RuntimeError('Missing exports after repair: ' + ', '.join(missing))
print('OK: render_site.py exports write_page and write_rss')
