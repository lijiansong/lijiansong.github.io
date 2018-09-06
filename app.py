from sys import argv
import logging
import os
import os.path
import sys
from urllib.parse import unquote

from mysite.core import Site, make_app
from mysite.file import StaticModule
from mysite.content import Page
from mysite.css import SassResource
from mysite.blog import Blog

logger = logging.getLogger(__name__)

# Wanted to used mimetypes but https://bugs.python.org/issue4963
MIME_EXTENSIONS = {
    "text/html": ".html",
    "application/atom+xml": ".atom",
}

# Static stuff
def minify_html(content, content_type):
    import htmlmin
    if content_type != "text/html":
        return content
    if type(content) == bytes:
        content = content.decode("UTF-8")
    return htmlmin.minify(content,
                          remove_comments=True,
                          reduce_boolean_attributes=True)

def minify_css(content, content_type):
    import rcssmin
    if content_type != "text/css":
        return content
    if type(content) == bytes:
        content = content.decode("UTF-8")
    return rcssmin.cssmin(content)

def minify_js(content, content_type):
    import rjsmin
    if content_type != "application/javascript":
        return content
    if type(content) == bytes:
        content = content.decode("UTF-8")
    return rjsmin.jsmin(content)

def make_site(dev=False):
    site = Site(title="/dev/posts/",
                href="http://lijiansong.github.io")

    # TODO, make a proper static module
    StaticModule(site, "static")
    Blog(site, dev=dev)

    # if not self._dev:
    if True:
        site.filters.append(minify_html)
        site.filters.append(minify_css)
        site.filters.append(minify_js)

    # TODO, make a proposer CSS module
    site.add_resource(
        SassResource("/css/main.css", "css/main.css.scss"))

    pages = [
        Page(site, "source/about/index.html.md", "/about/"),
        Page(site, "source/404.html.md", "/404.html"),
    ]
    for page in pages:
        site.add_resource(page)

    return site

# CLI
def serve(site):
    from wsgiref.simple_server import make_server
    hostname = "127.0.0.1"
    port = 4567
    httpd = make_server(hostname, port, make_app(site))
    print("http://" + hostname + ":" + str(port) + "/")
    httpd.serve_forever()
    sys.exit(0)

def update_file(filename, content, noop=True):
    if type(content) == str:
        content = content.encode("UTF-8")
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            old_content = f.read()
        if old_content == content:
            # logger.info("IDENTICAL %s", filename)
            return
        else:
            logger.info("UPDATE %s", filename)
    else:
        logger.info("CREATE %s", filename)
    dirname = os.path.dirname(filename)
    if not noop:
        os.makedirs(dirname, exist_ok=True)
        # TODO, use temporary file
        with open(filename, "w+b") as f:
            f.write(content)

def build(site, *, noop=True):
    errors = False

    build_dir = "build"
    if not noop:
        os.makedirs(build_dir, exist_ok=True)

    files = set()
    for href in site.hrefs:
        path = build_dir + unquote(href)
        if len(href) == 0 or href[0] != "/" or '\\' in href:
            errors = True
            logger.error("%s - bad href", href)
            continue
        if ".." in path:
            errors = True
            logger.error("%s - tricky href", href)
            continue

        resource = site.get_resource(href)
        if path[-1] == '/':
            ext = MIME_EXTENSIONS[resource.content_type]
            if ext is None:
                errors = True
                logger.error("%s - no extensions for MIME type %s",
                             href, resource.content_type)
                continue
            path = path + "index" + ext
        update_file(path, site.render_resource(resource), noop=noop)
        files.add(path)

    # TODO, remove useless files
    for (dirpath, dirnames, filenames) in os.walk(build_dir):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if path not in files:
                logger.info("UNLINK %s", path)
                if not noop:
                    os.unlink(path)
                    pass
        # TODO, RMDIR when necessary

    if errors:
        logger.error("Errors")
        sys.exit(1)

def main(argv):
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    if len(argv) == 1:
        action_name = "serve"
    else:
        action_name = argv[1]

    if action_name == "build":
        if len(argv) >= 3 and argv[2] == "force":
            noop = False
        else:
            noop = True
        build(make_site(dev=False), noop=noop)

    elif action_name == "serve":
        serve(make_site(dev=True))

    elif action_name == "index":
        for href in make_site(dev=True).hrefs:
            sys.stdout.write(href + "\n")

    else:
        sys.stderr("Bad CLI")
        sys.exit()

if __name__ == "__main__":
    main(argv)
