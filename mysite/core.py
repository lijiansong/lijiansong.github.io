from mysite.util import to_bytes
import logging

"""
Core classes
"""

logger = logging.getLogger(__name__)


class Resource:
    """
    Base (web) resource
    """

    content_type = "application/octet-stream"
    title = None
    href = None
    next = None
    prev = None

    def render(self):
        return None

    @property
    def headers(self):
        return [("Content-Type", self.content_type)]


class Module:
    """
    Base site module
    """

    @property
    def hrefs(self):
        return []

    def get_resource(self, href):
        return None


class Site(Module):
    """
    A site
    """

    def __init__(self, *, title="", href=""):
        super().__init__()
        self.title = title
        self.href = href
        self._resources = {}
        self.modules = []
        self.filters = []

    @property
    def hrefs(self):
        yield from self._resources.keys()
        for module in self.modules:
            yield from module.hrefs

    def get_resource(self, href):
        resource = self._resources.get(href)
        if resource is not None:
            return resource
        for module in self.modules:
            resource = module.get_resource(href)
            if resource is not None:
                return resource
        return None

    def add_resource(self, resource):
        self._resources[resource.href] = resource

    def render_resource(self, resource):
        content = to_bytes(resource.render())
        for filter in self.filters:
            content = filter(content, resource.content_type)
        return to_bytes(content)


def make_app(site):
    """
    Create a WSGI application for the site

    This is not meant to be used in production.
    """

    def app(environ, start_response):
        try:
            href = environ["PATH_INFO"]
            method = environ["REQUEST_METHOD"]
            if method != "GET" and method != "HEAD":
                start_response('405 Method Not Allowed', [])
                return
            resource = site.get_resource(href)
            if resource is None:
                start_response('404 Page Not Found',
                               [("Content-Type", "text/plain")])
                yield b"Not found\n"
                return

            content = site.render_resource(resource)
        except Exception:
            # start_response('500 Internal Server Error',
            #                [("Content-Type", "text/plain")])
            # yield b"Something wront happened"
            raise

        start_response('200 OK', [("Content-Type", resource.content_type)])
        if method == "HEAD":
            return
        yield content

    return app
