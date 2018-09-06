import sass

from mysite.core import Resource

"""
Compile CSCC into CSS
"""
class SassResource(Resource):
    content_type = "text/css"

    def __init__(self, href, filename):
        super().__init__()
        self.href = href
        self.filename = filename

    def render(self):
        return sass.compile(filename=self.filename)
