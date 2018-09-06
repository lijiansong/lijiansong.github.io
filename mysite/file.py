import os.path
import glob

import mimetypes
from mysite.core import Module, Resource

"""
Static files
"""
def irelglob(start, *patterns, recursive=False):
    for pattern in patterns:
        for path in glob.glob(os.path.join(glob.escape(start), pattern)):
            yield os.path.relpath(path, start=start)

def relglob(start, *patterns, recursive=False):
    return list(irelglob(start, *patterns, recursive=recursive))

class StaticResource(Resource):

    def __init__(self, href, filename, content_type=None):
        super().__init__()
        self.filename = filename
        if content_type is None:
            (content_type, encoding) = mimetypes.guess_type(filename)
            if content_type is None:
                content_type = "application/octet-stream"
            self.content_type = content_type
        else:
            self.content_type = content_type

    def render(self):
        with open(self.filename, "rb") as f:
            return f.read()

blacklist = ('~', '.', '#')

class StaticModule(Module):
    def __init__(self, site, path):
        site.modules.append(self)
        self.mappings = {}
        self.path = path
        self.refresh()

    def _list_sources(self):
        for (dirpath, dirnames, filenames) in os.walk(self.path):
            for filename in filenames:
                if filename[0] in blacklist or filename[-1] in blacklist:
                    continue
                path = os.path.join(dirpath, filename)
                if not os.path.isfile(path):
                    continue
                href = path[len(self.path):]
                yield (href, path)

    # TODO, avoid this
    def refresh(self):
        for (href, filename) in self._list_sources():
            self.mappings[href] = filename

    @property
    def hrefs(self):
        return self.mappings.keys()

    def get_resource(self, href):
        filename = self.mappings.get(href)
        if filename is not None:
            return StaticResource(href, filename)
        else:
            return None
