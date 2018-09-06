import logging
import os
import time
import glob
import re
import datetime
from itertools import groupby
from urllib.parse import quote
from dateutil.tz import gettz
from datetime import timezone

from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.extra import ExtraExtension

from mysite.core import Module, Resource
from mysite.content import strip_frontmatter, get_frontmatter
from mysite.content import render_markdown, render_template
from mysite.content import replace_emojis_html

logger = logging.getLogger(__name__)

UTC = timezone.utc

"""
Blog support
"""

TZ = gettz("Europe/Paris")
MARKDOWN_EXTENSIONS = [
    CodeHiliteExtension(guess_lang=False),
    ExtraExtension()
]

POST_RE = re.compile("([0-9]{4}-[0-9]{2}-[0-9]{2})-([^\.]*)")

class BlogPost(Resource):
    content_type = "text/html"

    def __init__(self, blog, filename):
        super().__init__()

        self.blog = blog
        self.filename = filename

        source = self.read()
        self.data = get_frontmatter(source)

        match = POST_RE.search(self.filename)

        date = datetime.datetime.strptime(match.group(1), "%Y-%m-%d").date()

        self.timestamp = datetime.datetime.combine(date, datetime.time(0),
                                                   tzinfo=TZ)

        self.slug = match.group(2)
        self.title = self.data["title"]
        if "tags" in self.data:
            self.tags = [tag.strip() for tag in self.data["tags"].split(",")]
        else:
            self.tags = []

        if "published" in self.data:
            self.published = self.data["published"]
        else:
            self.published = True

        lines = source.splitlines()
        lines = lines[lines.index("---") + 1:]
        lines = lines[lines.index("---") + 1:]

        summary = "\n".join(lines[:lines.index("READMORE")])
        self._summary = replace_emojis_html(summary)

        content = "\n".join(lines[:lines.index("READMORE")] +
                            lines[lines.index("READMORE") + 1:])
        self._content = replace_emojis_html(content)

    def read(self):
        with open(self.filename, "rt") as f:
            return f.read()

    def __repr__(self):
        return self.slug

    def summary(self):
        return render_markdown(self._summary)

    def content(self):
        return render_markdown(self._content)

    def render(self):
        return render_template('post.html', page=self, post=self,
                               site=self.blog.site)

    def _resolve_link(self, href):
        if href is None:
            return None
        res = self.blog.get_resource(href)
        if res is None:
            raise Exception("link not found")
        return res

    @property
    def subtitle(self):
        return self.data.get("subtitle", None)

    @property
    def next(self):
        return self._resolve_link(self.data.get("next", None))

    @property
    def prev(self):
        return self._resolve_link(self.data.get("prev", None))

    @property
    def enabled(self):
        return self.data.get("published", True)

    @property
    def href(self):
        return self.timestamp.date().strftime("/%Y/%m/%d/") + self.slug + "/"

    @property
    def updated(self):
        if "updated" not in self.data:
            return self.timestamp
        else:
            return self.data["updated"].replace(tzinfo=UTC).astimezone(TZ)

class Index:

    def __init__(self, blog, title, href, posts, per_page=10):
        self.blog = blog
        self.title = title
        self.href = href
        self.posts = posts
        self.per_page = per_page

    @property
    def num_pages(self):
        res = len(self.posts) // self.per_page
        if len(self.posts) % self.per_page != 0:
            res = res + 1
        return res

    def page_content(self, page_number):
        start = (page_number - 1) * self.per_page
        stop = start + self.per_page
        return self.posts[start:stop]

    def page_href(self, page_number):
        if page_number == 1:
            return self.href
        else:
            return self.href + "page/" + str(page_number) + "/"

    def page(self, page_number):
        return IndexPage(self, page_number)

    @property
    def pages(self):
        return [self.page(page_number)
                for page_number in range(1, self.num_pages + 1)]

    @property
    def atom(self):
        return IndexAtom(self)

    @property
    def resources(self):
        for pageno in range(1, self.num_pages + 1):
            yield self.page(pageno)
        # TODO, pagination for Atom
        yield self.atom

class IndexPage(Resource):
    content_type = "text/html"

    def __init__(self, index, page_number):
        super().__init__()
        self.index = index
        self.page_number = page_number

    @property
    def href(self):
        return self.index.page_href(self.page_number)

    @property
    def posts(self):
        return self.index.page_content(self.page_number)

    @property
    def next(self):
        if self.page_number < self.index.num_pages:
            return self.index.page(self.page_number + 1)
        else:
            return None

    @property
    def prev(self):
        if self.page_number == 1:
            return None
        else:
            return self.index.page(self.page_number - 1)

    def content(self):
        source = strip_frontmatter(self.read())
        return render_markdown(source)

    def render(self):
        return render_template('index.html', site=self.index.blog.site,
                               page=self)

    @property
    def num_pages(self):
        return self.index.num_pages

    @property
    def title(self):
        if self.page_number == 1:
            return self.index.title
        else:
            return self.index.title + ", page " + str(self.page_number)


FEED_FILENAME = "feed.atom"

class IndexAtom(Resource):
    content_type = "application/atom+xml"

    def __init__(self, index):
        super().__init__()
        self.index = index

    @property
    def href(self):
        return self.index.href + FEED_FILENAME

    def render(self):
        return render_template('atom.atom', site=self.index.blog.site,
                               page=self)

    @property
    def posts(self):
        return self.index.posts

# TODO, add description for each tag from data/tags.yaml
class TagsPage(Resource):
    content_type = "text/html"

    def __init__(self, blog):
        self.blog = blog

    @property
    def href(self):
        return self.blog.href + "tags/"

    def render(self):
        return render_template('tags.html', blog=self.blog,
                               site=self.blog.site, page=self)

    @property
    def posts(self):
        return self.index.posts

class ArchivesPage(Resource):
    content_type = "text/html"

    def __init__(self, blog):
        super().__init__()
        self.blog = blog

    @property
    def href(self):
        return self.blog.href + "tags/"

    def render(self):
        return render_template('archives.html', blog=self.blog,
                               site=self.blog.site, page=self)

    @property
    def posts(self):
        return self.blog.posts


BLOG_UPDATE_DELAY = 1

class Blog(Module):

    def __init__(self, site, *, dev=False):
        self.site = site
        self._update_time = None
        self._source_mtime = None
        self._dev = dev
        site.modules.append(self)
        self.refresh(force=True)

    def _mtime(self):
        filenames = ["posts/", *glob.glob("posts/*.html.md")]
        return max(os.stat(filename).st_mtime_ns for filename in filenames)

    def refresh(self, force=False):

        # TODO, replace this mess with filesystem notify
        if self._dev:

            # Don't refresh too often:
            now = time.time()
            if self._update_time is not None and now < (self._update_time
                                                        + BLOG_UPDATE_DELAY):
                return

            mtime = self._mtime()
            if self._source_mtime is not None and self._source_mtime == mtime:
                self._update_time = now
                return

        elif not force:
            return

        posts = []
        for filename in glob.glob("posts/*.html.md"):
            post = BlogPost(self, filename)
            if post.enabled or self._dev:
                posts.append(post)
        posts = list(sorted(posts,
                            key=lambda post: post.timestamp,
                            reverse=True))
        self._posts = posts

        # Tags:
        self._tags = list(sorted({tag
                                  for post in self._posts
                                  for tag in post.tags}))
        main_index = Index(self, "Index", "/", self._posts)
        self._tag_index = {
            tag: Index(self,
                       "Tag {}".format(tag),
                       "/tags/{}/".format(quote(tag)),
                       [post for post in self._posts if tag in post.tags])
            for tag in self._tags
        }

        # Archives
        self._year_index = {
            year: Index(self,
                        "Archive for {}".format(year),
                        "/{}/".format(year),
                        list(posts))
            for (year, posts) in groupby(posts,
                                         key=lambda post: post.timestamp.year)
        }

        self._resources = {}
        for index in ([main_index] + list(self._tag_index.values())
                      + list(self._year_index.values())):
            for resource in index.resources:
                self._resources[resource.href] = resource
        for post in self._posts:
            self._resources[post.href] = post

        if self._dev:
            self._update_time = now
            self._source_mtime = mtime

    @property
    def years(self):
        self.refresh()
        return sorted(self._year_index.keys(), reverse=True)

    def year_posts(self, year):
        self.refresh()
        return self._year_index[year].posts

    def posts_by_tag(self, tag):
        self.refresh()
        return [post for post in self.posts if tag in post.tags]

    def get_resource(self, href):
        self.refresh()
        if href == "/tags/":
            return TagsPage(self)
        if href == "/archives/":
            return ArchivesPage(self)
        resource = self._resources.get(href)
        if resource is not None:
            return resource
        return None

    @property
    def posts(self):
        self.refresh()
        return self._posts

    @property
    def tags(self):
        self.refresh()
        return self._tags

    @property
    def hrefs(self):
        self.refresh()
        yield "/tags/"
        yield "/archives/"
        for resource in self._resources:
            yield resource
        # for post in self._posts:
        #    yield post.href
