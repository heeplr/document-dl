"""download documents from web portals"""

import json
import re
import shutil
import sys
import time
import os
import platform
import requests
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import jq
import watchdog.events
import watchdog.observers

import docdl.util


# ---------------------------------------------------------------------
class AuthenticationError(Exception):
    """authentication failure"""


class DownloadError(Exception):
    """download failure"""


# ---------------------------------------------------------------------
class WebPortal:
    """base class for service portal to download documents from"""

    # default timeout (seconds)
    TIMEOUT = 15

    def __init__(self, login_id, password, useragent=None, arguments=None):
        """
        plugins inheriting from WebPortal can use self.session for scraping

        :param login_id: username/login id
        :param password: login password
        :param useragent: use this useragent
        :param arguments: extra arguments
        """
        if arguments is None:
            arguments = {}
        self.arguments = arguments
        self.login_id = login_id
        self.password = password
        self.useragent = useragent
        # initialize requests HTTP session
        self.session = requests.Session()
        # set user agent
        if useragent:
            self.session.headers["User-Agent"] = useragent

    def __enter__(self):
        # login to service
        if not self.login():
            raise AuthenticationError("login failed")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # logout
        self.logout()

    def login(self):
        """authenticate to service"""
        raise NotImplementedError(f"{ self.__class__} needs a login() method")

    def logout(self):
        """deauthenticate to service"""
        raise NotImplementedError(f"{ self.__class__} needs a logout() method")

    def documents(self):
        """
        generator that iterates all available and yields docdl.Documents()
        """
        raise NotImplementedError(f"{ self.__class__} needs a documents() generator")

    def download(self, document):
        """download document url"""
        # don't attempt download without url
        if not document.url:
            return None
        filename = self.download_with_requests(document)
        return document.rename_after_download(filename)

    def download_with_requests(self, document):
        """download a file without the browser using requests"""
        # fetch url
        req = self.session.get(
            document.url, stream=True, headers=document.request_headers
        )
        if not req.ok:
            raise DownloadError(f'"{document.url}" status code: {req.status_code}')

        # filename not already set?
        if "filename" in document.attributes:
            filename = document.attributes["filename"]
        # get filename from header
        elif "content-disposition" in req.headers:
            # @todo properly parse rfc6266
            filename = re.findall(
                "filename=([^; ]+)[;]?.*", req.headers["content-disposition"]
            )[0]
        else:
            filename = None

        # protect against empty filenames
        if not filename:
            if "title" in document.attributes:
                filename = document.attributes["title"]
            elif "id" in document.attributes:
                filename = f"document-dl.{document.attributes['id']}"
            else:
                raise RuntimeError("no suitable filename")

        # massage filename
        filename = filename.replace('"', "").strip()
        # save file
        with open(os.path.join(os.getcwd(), filename), "wb") as doc:
            for chunk in req.iter_content(chunk_size=4096):
                doc.write(chunk)

        return filename


class SeleniumWebPortal(WebPortal):
    """access portal using selenium"""

    WEBDRIVER = "chrome"

    def __init__(self, login_id, password, useragent=None, arguments=None):
        """
        plugins inheriting from SeleniumPortal can use self.webdriver for
        scraping

        :param login_id: username/login id
        :param password: login password
        :param useragent: use this useragent
        :param arguments: extra arguments
        """
        super().__init__(login_id, password, useragent, arguments)

        # initialize selenium
        webdriver_opts = self._init_webdriver_options()
        self._init_webdriver(webdriver_opts, arguments["webdriver"])

    def __enter__(self):
        super().__enter__()
        # copy cookies to requests session
        self.copy_to_requests_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """cleanup selenium"""
        super().__exit__(exc_type, exc_val, exc_tb)
        self.webdriver.close()
        self.webdriver.quit()

    def _init_webdriver_options(self):
        """init selenium options"""
        # choose webdriver options
        if self.WEBDRIVER == "chrome":
            # pylint: disable=C0415
            from selenium.webdriver.chrome.options import Options

        elif self.WEBDRIVER == "edge":
            # pylint: disable=C0415
            from selenium.webdriver.edge.options import Options

        elif self.WEBDRIVER == "firefox":
            # pylint: disable=C0415
            from selenium.webdriver.firefox.options import Options

        elif self.WEBDRIVER == "ie":
            # pylint: disable=C0415
            from selenium.webdriver.ie.options import Options

        elif self.WEBDRIVER == "safari":
            # pylint: disable=C0415,E0611,E0401
            from selenium.webdriver.safari.options import Options

        elif self.WEBDRIVER == "webkitgtk":
            # pylint: disable=C0415
            from selenium.webdriver.webkitgtk.options import Options

        else:
            raise AttributeError('unknown webdriver: "{self.WEBDRIVER}"')
        return Options()

    def _init_webdriver(self, webdriver_options, options):
        """init selenium"""
        # pylint: disable=C0415
        from selenium import webdriver

        def _init_chrome():
            # add prefs
            # selenium webdriver specific options
            if "headless" in options:
                # set headless mode
                webdriver_options.headless = options["headless"]
            if "load_images" in options and options["load_images"]:
                # disable image loading
                webdriver_options.add_experimental_option(
                    "prefs",
                    {
                        "profile.default_content_settings.images": 2,
                        "profile.managed_default_content_settings.images": 2,
                    },
                )
            # enable incognito mode
            webdriver_options.add_argument("--incognito")
            # set preferences
            webdriver_options.add_experimental_option(
                "prefs",
                {
                    # always save PDFs
                    "plugins.always_open_pdf_externally": True,
                    # set default download directory to CWD
                    "download.default_directory": os.getcwd(),
                },
            )
            # set user agent
            if self.useragent:
                webdriver_options.add_argument(f"user-agent='{self.useragent}'")
            # enable debugging
            if "debug" in options:
                webdriver_options.add_argument("--remote-debugging-port=9222")
            # set preference options & init webdriver
            return webdriver.Chrome(options=webdriver_options)

        def _init_edge():
            # pylint: disable=E1123
            return webdriver.Edge(options=webdriver_options)

        def _init_firefox():
            # pylint: disable=C0415
            from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

            # create custom profile
            firefox_profile = webdriver.FirefoxProfile()
            # webdriver.get_cookies() won't work in private browsing mode :(
            # ~ # always enable private browsing
            # ~ firefox_profile.set_preference(
            # ~     "browser.privatebrowsing.autostart", True
            # ~ )
            # set default download directory to CWD
            firefox_profile.set_preference("browser.download.folderList", 2)
            firefox_profile.set_preference(
                "browser.download.manager.showWhenStarting", False
            )
            firefox_profile.set_preference("browser.download.dir", os.getcwd())
            # save PDFs by default (don't preview)
            firefox_profile.set_preference(
                "browser.helperApps.neverAsk.saveToDisk", "application/pdf"
            )
            firefox_profile.set_preference("pdfjs.disabled", True)
            firefox_profile.set_preference("plugin.scan.Acrobat", "999.0")
            firefox_profile.set_preference("plugin.scan.plid.all", False)
            # turn off image loading by default
            firefox_profile.set_preference("permissions.default.image", 2)
            # headless mode
            if "headless" in options:
                # set headless mode
                webdriver_options.headless = options["headless"]
            # set user agent
            if self.useragent:
                firefox_profile.set_preference(
                    "general.useragent.override", self.useragent
                )
            # find binary
            if platform.machine() in ["x86_64", "s390x", "sparc64"]:
                moz_lib_dir = "/usr/lib64"
                secondary_lib_dir = "/usr/lib"
            else:
                moz_lib_dir = "/usr/lib"
                secondary_lib_dir = "/usr/lib64"
            # try firefox binary
            ff_path = f"{moz_lib_dir}/firefox/firefox"
            if not (os.path.isfile(ff_path) and os.access(ff_path, os.X_OK)):
                ff_path = f"{secondary_lib_dir}/firefox/firefox"
                if not (os.path.isfile(ff_path) and os.access(ff_path, os.X_OK)):
                    raise RuntimeError(
                        f"firefox binary not found in {moz_lib_dir} "
                        "or {secondary_lib_dir}"
                    )
            # get path to geckodriver executable
            gecko_path = shutil.which("geckodriver")
            # set firefox profile
            webdriver_options.profile = firefox_profile
            # set firefox binary
            webdriver_options.binary = FirefoxBinary(os.path.join(gecko_path, ff_path))
            # initialize driver
            return webdriver.Firefox(options=webdriver_options)

        def _init_ie():
            return webdriver.Ie(options=webdriver_options)

        def _init_safari():
            # pylint: disable=E1123
            return webdriver.Safari(options=webdriver_options)

        def _init_webkitgtk():
            return webdriver.WebKitGTK(options=webdriver_options)

        # webdriver registry
        webdrivers = {
            "chrome": _init_chrome,
            "edge": _init_edge,
            "firefox": _init_firefox,
            "ie": _init_ie,
            "safari": _init_safari,
            "webkitgtk": _init_webkitgtk,
        }

        # init webdriver
        self.webdriver = webdrivers[self.WEBDRIVER]()

    def documents(self):
        """
        generator that iterates all available and yields docdl.Documents()
        """
        raise NotImplementedError(f"{ self.__class__} needs a documents() generator")

    def download(self, document):
        """download a document"""
        # click download element to trigger download ?
        if document.download_element:
            filename = self.download_with_selenium(document)
        # GET url?
        elif document.url:
            # copy cookies from selenium to requests session
            self.copy_to_requests_session()
            filename = self.download_with_requests(document)
            self.copy_from_requests_session()
        # don't attempt download
        else:
            return None
        return document.rename_after_download(filename)

    def download_with_selenium(self, document):
        """download a file using the selenium webdriver"""

        class DownloadFileCreatedHandler(watchdog.events.PatternMatchingEventHandler):
            """
            directory watchdog to store filename of newly created file
            """

            filename = None

            def on_created(self, event):
                self.filename = os.path.basename(event.src_path)

        # scroll to download element
        self.scroll_to_element(document.download_element)

        # setup download directory watchdog
        # pylint: disable=C0103
        OBSERVER = watchdog.observers.Observer()
        # ignore temporary download files
        handler = DownloadFileCreatedHandler(
            ignore_patterns=["*.crdownload", "*.part", ".com.google.Chrome.*"]
        )
        OBSERVER.schedule(handler, os.getcwd(), recursive=False)

        # click element to start download
        document.download_element.click()

        # wait for download completed
        OBSERVER.start()
        try:
            while not handler.filename:
                time.sleep(0.1)
        finally:
            OBSERVER.stop()
        OBSERVER.join()

        return handler.filename

    def copy_to_requests_session(self):
        """copy current selenium session to requests session"""
        # copy cookies
        for cookie in self.webdriver.get_cookies():
            self.session.cookies.set(cookie["name"], cookie["value"])
        # copy user agent
        user_agent = self.webdriver.execute_script("return navigator.userAgent;")
        self.session.headers["User-Agent"] = user_agent

    def copy_from_requests_session(self):
        """copy current requests session to selenium session"""
        for name, value in self.session.cookies.items():
            self.webdriver.add_cookie({"name": name, "value": value})

    def captcha(self, image, entry, prompt="please enter captcha: "):
        """handle captcha"""
        # scroll to ensure captcha is visible
        self.scroll_to_element(image)
        # save screenshot
        image.screenshot("captcha.png")
        # present image to the user
        docdl.util.show_image(os.path.join(os.getcwd(), "captcha.png"), "captcha")
        # ask for interactive captcha input
        sys.stderr.write(prompt)
        sys.stderr.flush()
        captcha = input()
        # enter into field
        entry.send_keys(captcha)

    def scroll_to_element(self, element):
        """scroll WebElement into center view"""
        self.webdriver.execute_script(
            "arguments[0].scrollIntoView(true); window.scrollBy(0, -window.innerHeight/2);",
            element,
        )

    def scroll_to_bottom(self):
        """scroll to bottom of page"""
        self.webdriver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

    def wait_for_urlchange(self, current_url):
        """wait until current URL changes"""
        WebDriverWait(self.webdriver, self.TIMEOUT).until(EC.url_changes(current_url))
        # return new url
        return self.webdriver.current_url


class Document:
    """a document"""

    def __init__(
        self, url=None, attributes=None, request_headers=None, download_element=None
    ):
        # default custom request headers
        if request_headers is None:
            request_headers = {}
        self.request_headers = request_headers
        # target url (if set, the url will be GET using requests)
        self.url = url
        # if download_element is set, it will be click()ed for download
        self.download_element = download_element
        # portal specific attributes
        if attributes is None:
            attributes = {}
        self.attributes = attributes

    def __repr__(self):
        return f'class {self.__class__.__name__}(url="{self.url}", attributes={self.attributes})'

    def rename_after_download(self, filename):
        """
        called after file was downloaded - checks if there's a filename
        the newly downloaded file should be renamed to. Rename file if
        so.
        """
        # got a predefined filename?
        if "filename" in self.attributes:
            # rename file to predefined name
            os.rename(filename, self.attributes["filename"])
        else:
            # save new filename
            self.attributes["filename"] = filename
        return filename

    def match_string(self, filters):
        """
        :param filters: list of (attribute_name, pattern) tuples
        :result: True if all document attributes contain the pattern,
                 False otherwise
        """

        def _filter_attr(attribute, pattern):
            """apply filter to an attribute of a document"""
            return str(pattern) in str(self.attributes[attribute])

        # null filter match by default
        if len(filters) == 0:
            return True

        # apply all filters to this document
        return all(_filter_attr(attribute, pattern) for attribute, pattern in filters)

    def match_jq(self, jq_strings):
        """
        :param jq_string: jq expression
        :result: True if jq expression produces any True result,
                 False otherwise
        """
        # null expression matches by default
        if len(jq_strings) == 0:
            return True

        # all jq expressions must produce output
        # false positive - pylint: disable=R1729
        return all(
            [
                any(jq.compile(jq_string).input(text=self.toJSON()).all())
                for jq_string in jq_strings
            ]
        )

    def match_regex(self, regexes):
        """
        :param regexes: list of (attribute, regex) tuples
        :result: True if all attributes match their regex, False
                 otherwise.
        """

        def _match_attr(attribute, regex):
            return re.match(regex, str(self.attributes[attribute]))

        # always match if there are no regexes
        if len(regexes) == 0:
            return True

        return all(_match_attr(attribute, regex) for attribute, regex in regexes)

    # we don't use camelCase here pylint: disable=C0103
    def toJSON(self):
        """:result: json representation of document"""
        return json.dumps(
            self.attributes, sort_keys=True, cls=docdl.util.dateparser.DateEncoder
        )
