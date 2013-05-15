import gtk
import webkit
import jswebkit
from twisted.internet import defer

from scrapy.core.downloader.handlers.http import HttpDownloadHandler
from scrapy.http import HtmlResponse
from scrapy import log

#gtk.gdk.threads_init()

class WebkitDownloadHandler(HttpDownloadHandler):

    def download_request(self, request, spider):
        if 'renderjs' in request.meta:
            d = defer.Deferred()
            d.addErrback(log.err, spider=spider)
            webview = self._get_webview()
            webview.connect('load-finished', lambda v, f: self._load_finished(d, v, f))
            win = gtk.Window()
            win.add(webview)
            win.show_all()
            webview.open(request.url)
            return d
        else:
            return super(WebkitDownloadHandler, self).download_request(request, spider)

    def _get_webview(self):
        webview = webkit.WebView()
        props = webview.get_settings()
        props.set_property('enable-java-applet', False)
        props.set_property('enable-plugins', False)
        props.set_property('enable-page-cache', False)
        #props.set_property('enable-frame-flattening', True)
        return webview

    def _load_finished(self, deferred, view, frame):
        if frame != view.get_main_frame():
            return
        ctx = jswebkit.JSContext(frame.get_global_context())
        url = ctx.EvaluateScript('window.location.href')
        html = ctx.EvaluateScript('document.documentElement.innerHTML')
        response = HtmlResponse(url, encoding='utf-8', body=html.encode('utf-8'))
        deferred.callback(response)

