import Queue
import json
import logging
import re

import thread

import sys
import urllib2

import websocket
from selenium.common.exceptions import NoSuchElementException

from client.browser.webdriver.webdriver import WebDriver
from selenium.webdriver import Remote
from argparse import ArgumentParser


logger = logging.getLogger(__name__)


class Response:
    def __init__(self, msg):
        self.result = msg[u'result']
        self.id = msg[u'id']
        self.msg = msg


class Error:
    def __init__(self, msg):
        self.error = msg[u'error']
        self.id = msg[u'id']
        self.msg = msg


class Event:
    def __init__(self, msg):
        self.params = msg[u'params'] if u'params' in msg else {}
        self.method = msg[u'method']
        self.msg = msg


class RemoteDebugError(Exception):
    def __init__(self, msg, code):
        super(RemoteDebugError, self).__init__(msg)
        self.code = code


def _to_snake_case(k):
    return re.sub("([A-Z])", "_\\1", k).lower()


class RemoteDebugConnectionThread(websocket.threading.Thread):
    QUIT = {"method": "quit"}

    def __init__(self, url):
        super(RemoteDebugConnectionThread, self).__init__()

        self.logger = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))

        self.inbox = Queue.Queue()
        self.outbox = Queue.Queue()
        self.id = 1

        def on_message(ws, message):
            try:
                decoded_message = json.loads(message)
                if u'result' in decoded_message:
                    self.inbox.put(Response(decoded_message))
                elif u'error' in decoded_message:
                    self.inbox.put(Error(decoded_message))
                else:
                    self.inbox.put(Event(decoded_message))
            except:
                print "Unexpected error:", sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2], message
                raise

        def on_error(ws, error):
            self.logger.error(error)

        def on_close(ws):
            self.logger.info("Connection closed")

        def on_open(ws):
            def run():
                while True:
                    msg = self.outbox.get()
                    if msg == self.QUIT:
                        ws.close()
                    else:
                        self.logger.debug(">> %s" % msg)
                        ws.send(msg)

            thread.start_new_thread(run, ())

        self.ws = websocket.WebSocketApp(url, on_message=on_message, on_error=on_error, on_close=on_close)
        self.ws.on_open = on_open

    def run(self):
        self.ws.run_forever()

    def close(self):
        self.outbox.put(self.QUIT)

    def send(self, method, params={}):
        payload = '{"id": %d, "method": "%s", "params": %s}' % (self.id, method, json.dumps(params))
        self.outbox.put(payload)
        resp = self.wait_for_response(self.id)
        self.id += 1
        return resp

    def wait_for_response(self, id):
        while True:
            item = self.inbox.get(block=True, timeout=5)
            if (isinstance(item, Response) or isinstance(item, Error)) and item.id == id:
                self.logger.debug("<< %r" % item.msg)
                if isinstance(item, Error):
                    raise RemoteDebugError(item.error[u'message'], item.error[u'code'])
                return item

    def wait_for_frame_event(self, method, frameId):
        return self.wait_for_event(method, lambda i: i.params[u'frameId'] == frameId)

    def wait_for_event(self, method, condition=lambda i: True):
        while True:
            item = self.inbox.get(block=True, timeout=5)
            if isinstance(item, Event) and item.method == method and condition(item):
                self.logger.debug(" < %r" % item.msg)
                return item


class RemoteDebugRemoteConnection(object):
    def __init__(self, ws_url):
        self.ws_url = ws_url

        self.logger = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))

        self.connection = RemoteDebugConnectionThread(self.ws_url)
        self.connection.start()

    def execute(self, command, params):
        if command[:3] == 'w3c':
            command = command[3].lower() + command[4:]

        command = _to_snake_case(command)
        params = {_to_snake_case(k): v for k, v in params.iteritems()}

        self.logger.debug("Call %s ( %r )" % (command, params))

        if command not in self.__class__.__dict__:
            raise Exception("Unsupported command %s" % command)

        return self.__class__.__dict__[command](self, **params)

    def new_session(self, required_capabilities, desired_capabilities):
        return {"sessionId": '1', "value": {"specificationLevel": 1}}

    def set_window_size(self, session_id, window_handle, width, height):
        return self.execute_script(session_id,
                                   "window.resizeTo(%d, %d)" % (width, height))

    def get_window_size(self, session_id, window_handle):
        return self.execute_script(session_id,
                                   "return { 'width': window.innerWidth, 'height': window.innerHeight };")

    def get_window_position(self, session_id, window_handle):
        return self.execute_script(session_id,
                                   "return { 'x': window.screenX, 'y': window.screenY };")

    def quit(self, session_id):
        self.connection.close()
        return {}

    def execute_script(self, session_id, script, args=None):
        res = self.connection.send("Runtime.evaluate",
                                   {"expression": "(function(){%s})()" % script,
                                    "returnByValue": True})
        if res.result[u'result'][u'type'] == u'undefined':
            ret = {"status": 0}
        else:
            ret = {'status': 0, 'value': res.result[u'result'][u'value']}
        return ret

    def find_element(self, session_id, value, using):
        root = self.connection.send("DOM.getDocument").result[u'root'][u'nodeId']

        if using == 'link text':
            return self._find_by_xpath(root, "//a[text()='%s']" % value)
        elif using == 'xpath':
            return self._find_by_xpath(root, value)
        else:
            try:
                ret = self.connection.send("DOM.querySelector", {"nodeId": root, "selector": value})
                return {"status": 0, "value": {"ELEMENT": ret.result[u'nodeId']}}
            except RemoteDebugError as e:
                if e.code == -32000:
                    raise NoSuchElementException(e.message)
                else:
                    raise

    def click_element(self, session_id, id):
        object_id = self.connection.send("DOM.resolveNode", {"nodeId": id}).result[u'object'][u'objectId']
        self.connection.send("Runtime.callFunctionOn", {"objectId": object_id,
                                                        "functionDeclaration": "function() { this.click() }"})

        try:
            self.connection.send("Runtime.releaseObject", {"objectId": object_id })
        except RemoteDebugError:
            # No worry if release object fails, as this navigates to new page and automatically releases object
            pass

    def get(self, session_id, url):
        self.connection.send("Page.navigate", {"url": url})

    def _find_by_xpath(self, root, xpath):
        ret = self.connection.send("DOM.performSearch", {"nodeId": root, "query": xpath})

        search_id = ret.result[u'searchId']
        count = ret.result[u'resultCount']

        ret = self.connection.send("DOM.getSearchResults",
                                   {"searchId": search_id, "fromIndex": 0, "toIndex": count})

        self.connection.send("DOM.discardSearchResults", {"searchId": search_id})

        if count == 0:
            raise NoSuchElementException()
        return {"status": 0, "value": {"ELEMENT": ret.result[u'nodeIds'][0]}}

    def delete_cookies(self, cookies):
        for cookie in cookies:
            url = cookie['domain']
            if url.startswith("."):
                url = "www" + url
            url = ("https://" if cookie['secure'] else "http://") + url + cookie['path']
            self.connection.send("Page.deleteCookie", {"cookieName": cookie['name'], "url": url})

    def delete_all_cookies(self, session_id):
        self.connection.send("Network.clearBrowserCookies")

    def clear_cache(self, session_id):
        self.connection.send("Network.clearBrowserCache")

    def get_cookies(self, session_id):
        return {"status": 0,
                "value": [{"name": c['name'],
                           "value": c['value'],
                           "path": c.get('path', None),
                           "domain": c.get('domain', None),
                           "secure": c.get('secure', None),
                           "httpOnly": c.get('httpOnly', None),
                           "expiry": c.get('expires', None)}
                          for c in self.connection.send("Page.getCookies").result['cookies']]
                }

    def disable_cache(self):
        self.connection.send("Network.setCacheDisabled", {"cacheDisabled": True})

    def enable_cache(self):
        self.connection.send("Network.setCacheDisabled", {"cacheDisabled": False})

    def can_clear_cookies(self):
        try:
            return self.connection.send("Network.canClearCookies").result
        except RemoteDebugError:
            return False

    def can_clear_cache(self):
        try:
            return self.connection.send("Network.canClearCache").result
        except RemoteDebugError:
            return False


class RemoteDebugWebDriver(WebDriver):
    def __init__(self, event_bus, config, lock_on="run"):
        super(WebDriver, self).__init__(event_bus, config, lock_on)
        self.cookies = []

    @classmethod
    def argparser(cls):
        p = ArgumentParser(description=cls.__name__, prog=cls.__name__, add_help=False, parents=[WebDriver.argparser()])
        p.add_argument('--port', dest='port', required=True)
        p.add_argument('--clear-cookies', dest='clear_cookies', default='auto',
                       choices=['none', 'auto', 'all', 'post-run'])
        p.add_argument('--clear-cache', dest='clear_cache', default='auto',
                       choices=['none', 'auto', 'all', 'disable-cache'])
        return p

    def _init_driver(self):
        # Make request to http://localhost:<port>/json
        response = json.loads(urllib2.urlopen("http://localhost:%s/json" % self.config['port']).read())

        self.connection = RemoteDebugRemoteConnection(response[0][u'webSocketDebuggerUrl'])
        self.driver = Remote(command_executor=self.connection, desired_capabilities={})

    def on_setup_run(self, event):
        super(RemoteDebugWebDriver, self).on_setup_run(event)

        if self.config['clear_cookies'] == 'auto':
            self.config['clear_cookies'] = 'all' if self.connection.can_clear_cookies() else 'post-run'

        if self.config['clear_cache'] == 'auto':
            self.config['clear_cache'] = 'all' if self.connection.can_clear_cache() else 'disable-cache'

        if self.config['clear_cookies'] == 'all':
            self.driver.delete_all_cookies()
        if self.config['clear_cache'] == 'all':
            self.connection.clear_cache()

    def on_setup_view(self, event):
        super(RemoteDebugWebDriver, self).on_setup_view(event)
        if self.config['clear_cache'] == 'disable-cache':
            if event.view.is_first:
                self.connection.disable_cache()
            else:
                self.connection.enable_cache()

    # TODO: This should really be on_tear_down_run, but that clashes with closing the debug proxy
    def on_end_run(self, event):
        if self.config['clear_cookies'] == 'post-run':
            self.connection.delete_cookies(self.cookies)

    def on_tear_down_step(self, event):
        if self.config['clear_cookies'] == 'post-run':
            self.cookies.extend(self.driver.get_cookies())


class IOSRemoteDebugWebDriver(RemoteDebugWebDriver):
    def _hide_orange_overlay(self):
        self.driver.execute_script(
            "document.getElementById('webpagetest_orange_overlay').style.backgroundColor = 'rgb(255, 255, 255)';")
