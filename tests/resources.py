# -*- coding: utf-8 -*-
import os
from six.moves.urllib.parse import urlparse

from twisted.web.resource import Resource
from zope.interface import implementer
from twisted.web import resource, guard, proxy
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse

from scrapy_splash.utils import to_bytes


class HtmlResource(Resource):
    isLeaf = True
    content_type = 'text/html'
    html = ''
    extra_headers = {}
    status_code = 200

    def render_GET(self, request):
        request.setHeader(b'content-type', to_bytes(self.content_type))
        for name, value in self.extra_headers.items():
            request.setHeader(to_bytes(name), to_bytes(value))
        request.setResponseCode(self.status_code)
        return to_bytes(self.html)


class HelloWorld(HtmlResource):
    html = """
    <html><body><script>document.write('hello world!');</script></body></html>
    """
    extra_headers = {'X-MyHeader': 'my value', 'Set-Cookie': 'sessionid=ABCD'}


class HelloWorldDisallowByRobots(HelloWorld):
    """ Disallow itself via robots.txt """
    isLeaf = False

    def getChild(self, name, request):
        if name == b"robots.txt":
            return self.RobotsTxt()
        return self

    class RobotsTxt(Resource):
        isLeaf = True
        def render_GET(self, request):
            return b'User-Agent: *\nDisallow: /\n'


class HelloWorldDisallowAuth(HelloWorldDisallowByRobots):
    """ Disallow itself via robots.txt if a request to robots.txt
    contains basic auth header. """
    class RobotsTxt(HelloWorldDisallowByRobots.RobotsTxt):
        def render_GET(self, request):
            if request.requestHeaders.hasHeader('Authorization'):
                return super(HelloWorldDisallowAuth.RobotsTxt, self).render_GET(request)
            request.setResponseCode(404)
            return b''


class Http400Resource(HtmlResource):
    status_code = 400
    html = "Website returns HTTP 400 error"


class ManyCookies(Resource, object):
    class SetMyCookie(HtmlResource):
        html = "hello!"
        extra_headers = {'Set-Cookie': 'login=1'}

    def __init__(self):
        super(ManyCookies, self).__init__()
        self.putChild(b'', HelloWorld())
        self.putChild(b'login', self.SetMyCookie())


def splash_proxy():
    splash_url = os.environ.get('SPLASH_URL')
    p = urlparse(splash_url)
    return lambda: proxy.ReverseProxyResource(p.hostname, int(p.port), b'')


def password_protected(resource_cls, username, password):
    # Sorry, but this is nuts. A zillion of classes, arbitrary
    # unicode / bytes requirements at random places. Is there a simpler
    # way to get HTTP Basic Auth working in Twisted?
    @implementer(IRealm)
    class SimpleRealm(object):
        def requestAvatar(self, avatarId, mind, *interfaces):
            if resource.IResource in interfaces:
                return resource.IResource, resource_cls(), lambda: None
            raise NotImplementedError()

    creds = {username: password}
    checkers = [InMemoryUsernamePasswordDatabaseDontUse(**creds)]
    return lambda: guard.HTTPAuthSessionWrapper(
        Portal(SimpleRealm(), checkers),
        [guard.BasicCredentialFactory(b'example.com')])


HelloWorldProtected = password_protected(HelloWorld, 'user', b'userpass')
HelloWorldProtected.__name__ = 'HelloWorldProtected'
HelloWorldProtected.__module__ = __name__

SplashProtected = password_protected(splash_proxy(), 'user', b'userpass')
SplashProtected.__name__ = 'SplashProtected'
SplashProtected.__module__ = __name__
