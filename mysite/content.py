from urllib.parse import quote
import re

import json
import yaml
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.extra import ExtraExtension
from jinja2 import Environment, FileSystemLoader, select_autoescape

from mysite.core import Resource

MARKDOWN_EXTENSIONS = [
    CodeHiliteExtension(linenums="off"),
    ExtraExtension()
    ]

with open("data/emoji.json", "rt") as f:
    emoji_data = {}
    data = json.load(f)
    for (k, emoji) in data.items():
        for shortname in (emoji["shortname"], *emoji["shortname_alternates"]):
            emoji_data[shortname] = emoji

def _replace_emojis_html(match):
    shortname = ":" + match.group(1) + ":"
    emoji = emoji_data.get(shortname)
    if emoji is None:
        return match.group(0)
    else:
        codepoints = emoji["code_points"]["base"].lower()
        path = "/img/emojione/{}.png".format(codepoints)
        real = "".join([chr(int(code, 16)) for code in codepoints.split("-")])
        return "<img class='emoji' src='{}' alt='{}' />".format(quote(path),
                                                                real)
def replace_emojis_html(source):
    return re.sub(":([0-9a-zA-Z_]{1,}):", _replace_emojis_html, source)

jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(['html', 'xml', 'atom'])
    )

def register_filter(f):
    jinja_env.fitlers[f.name] = f
    return f

def render_template(template, **kwargs):
    return jinja_env.get_template(template).render(**kwargs)

def strip_frontmatter(data):
    lines = data.splitlines()
    lines = lines[lines.index("---") + 1:]
    lines = lines[lines.index("---") + 1:]
    return "\n".join(lines)

def get_frontmatter(data):
    return next(yaml.load_all(data))

def render_markdown(source):
    return markdown.markdown(source, extensions=MARKDOWN_EXTENSIONS)

class Page(Resource):
    content_type = "text/html"

    def __init__(self, site, filename, href):
        super().__init__()
        self.site = site
        self.filename = filename
        self.href = href
        self.data = get_frontmatter(self.read())
        self.title = self.data["title"]

    @property
    def lang(self):
        return self.data.get("lang", None)

    def read(self):
        with open(self.filename, "rt") as f:
            return f.read()

    def content(self):
        source = strip_frontmatter(self.read())
        return render_markdown(replace_emojis_html(source))

    def render(self):
        return render_template('page.html', site=self.site, page=self)
