import logging
from collections import namedtuple
from contextlib import contextmanager
from time import sleep, time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

import client.event
import client.model
import client.provider

DEFAULT_ACTIVITY_TIMEOUT = 2000

DEFAULT_VIEWPORT = (1024, 768)

WEBDRIVER_WAIT_TIMEOUT = 3
WEBDRIVER_WAIT_POLL_INTERVAL = 0.1

ORANGE_OVERLAY_WAIT = 0.5
ORANGE_OVERLAY_COLOR = (222, 100, 13)

logger = logging.getLogger(__name__)


position = namedtuple("position", "x,y")
dimension = namedtuple("dimension", "width,height")


@contextmanager
def wait_for_page_load(browser):
    old_page = browser.find_element_by_tag_name('html')

    yield

    start_time = time()
    while time() < start_time + WEBDRIVER_WAIT_TIMEOUT:
        try:
            new_page = browser.find_element_by_tag_name('html')
            state = browser.execute_script("return document.readyState;")

            if new_page.id != old_page.id and "complete" == state:
                return
        except NoSuchElementException:
            # Might not find html element in case page is loading
            pass

        sleep(WEBDRIVER_WAIT_POLL_INTERVAL)

    raise Exception('Timeout waiting for readyState')


def parse_command(line, step):
    cmd, params = line.split(" ", 1)
    if cmd == 'navigate':
        return NavigateCommand(params, step)
    elif cmd == 'clickAndWait':
        return ClickAndWaitCommand(params, step)
    else:
        print("Unknown command %s", cmd)


class NavigateCommand(object):
    is_step = True

    def __init__(self, params, step):
        self.url = step.name = params

    def execute(self, driver):
        logger.info("Executing command 'navigate %s'" % self.url)
        with wait_for_page_load(driver):
            driver.get(self.url)
        sleep(DEFAULT_ACTIVITY_TIMEOUT / 1000)


def _selector_to_xpath_lvalue(attribute):
    if attribute == 'innerText':
        return "text()"
    elif attribute == 'className':
        return "@class"
    else:
        return "@" + attribute


class ClickAndWaitCommand(object):
    is_step = True

    def __init__(self, params, step):
        self.text = step.name = params

    def execute(self, driver):
        logger.info("Executing command 'clickAndWait %s'" % self.text)

        attribute, value = self.text.split("=", 1)

        with wait_for_page_load(driver):
            xpath = '//*[%s="%s"]' % (_selector_to_xpath_lvalue(attribute), value)
            logger.debug("Find element by xpath %s" % xpath)
            driver.find_element_by_xpath(xpath).click()
        sleep(DEFAULT_ACTIVITY_TIMEOUT / 1000)


class WebDriver(client.provider.Provider):
    def __init__(self, event_bus, config):
        client.provider.Provider.__init__(self, event_bus, config, lock_on="run")
        self.driver = None

    def _init_driver(self):
        pass

    def on_setup_run(self, event):
        self._init_driver()
        self._focus_window()

    def on_tear_down_run(self, event):
        self.driver.quit()

    def on_abort(self, event):
        self.driver.quit()

    def on_setup_view(self, event):
        self.driver.set_window_size(*DEFAULT_VIEWPORT)

        window_size = self.driver.get_window_size()
        event.view.window_size = dimension(window_size[u'width'], window_size[u'height'])

        p = self.driver.get_window_position()
        event.view.window_position = position(p[u'x'], p[u'y'])

        event.view.pixel_density = self.driver.execute_script("return window.devicePixelRatio;")

    def on_start_view(self, event):
        if self.session.url:
            self.session.script = "navigate %s" % self.session.url
        self._evaluate_script(self.session.script)

    def _evaluate_script(self, script):
        step = client.model.Step(1, None)
        for line in script.split("\n"):
            logger.debug("evaluate_script - parsing command '%s'" % line)
            command = parse_command(line, step)
            if command.is_step:
                self._show_orange_overlay()

                self.event_bus.emit(client.event.SetupStepEvent(step))
                self.event_bus.emit(client.event.StartStepEvent(step))

                self._hide_orange_overlay()

                command.execute(self.driver)

                self.event_bus.emit(client.event.EndStepEvent(step))
                self.event_bus.emit(client.event.TearDownStepEvent(step))

                step = client.model.Step(step.index + 1, None)
            else:
                command.execute(self.driver)

    def _focus_window(self):
        pass

    def _show_orange_overlay(self):
        overlay_script = ("""
            var ol = document.createElement('div');
            ol.id='webpagetest_orange_overlay';
            ol.style.position='absolute';
            ol.style.top='0';
            ol.style.left='0';
            ol.style.width='100%';
            ol.style.height='100%';
            ol.style.backgroundColor='rgb({}, {}, {})';
            ol.style.zIndex='2147483647';
            ol.style.cursor='none';
            ol.style.pointerEvents='none';
            document.body.appendChild(ol);

            window.addEventListener('unload', function(event) {{
                document.getElementById('webpagetest_orange_overlay').style.backgroundColor = 'rgb(255, 255, 255)';
            }});
            window.addEventListener('beforeunload', function(event) {{
                document.getElementById('webpagetest_orange_overlay').style.backgroundColor = 'rgb(255, 255, 255)';
            }});
            window.addEventListener('pagehide', function(event) {{
                document.getElementById('webpagetest_orange_overlay').style.backgroundColor = 'rgb(255, 255, 255)';
            }});
        """)

        self.driver.execute_script(overlay_script.format(*ORANGE_OVERLAY_COLOR))
        sleep(ORANGE_OVERLAY_WAIT)

    def _hide_orange_overlay(self):
        pass


class FirefoxWebDriver(WebDriver):
    def __init__(self, event_bus, config):
        WebDriver.__init__(self, event_bus, config)
        logger.info("Creating FirefoxWebDriver")

    def _init_driver(self):
        binary = FirefoxBinary(self.config['firefox_binary'])
        self.driver = webdriver.Firefox(capabilities={"marionette":True},
                                        firefox_binary=binary,
                                        executable_path=self.config['gecko_driver'])

    def on_setup_view(self, event):
        self.driver.set_window_size(1024, 768)

        window_size = self.driver.get_window_size()
        event.view.window_size = dimension(window_size[u'width'], window_size[u'height'])

        size_arr = self.driver.execute_script("return [ window.mozInnerScreenX, window.mozInnerScreenY ]")
        event.view.window_position = position(size_arr[0], size_arr[1])
