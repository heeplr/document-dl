"""download documents from web portals"""

import getpass
import re
import shutil
import time
import os
import platform
import requests
import jq
import watchdog.events
import watchdog.observers

from docdl import dateparser


# ---------------------------------------------------------------------
class AuthenticationError(Exception):
    """authentication failure"""


class DownloadError(Exception):
    """download failure"""


# ---------------------------------------------------------------------
class WebPortal():
    """base class for service portal to download documents from"""

    # default timeout (seconds)
    TIMEOUT = 15

    def __init__(self, login_id, password, arguments=None):
        if arguments is None:
            arguments = {}
        self.arguments = arguments
        self.login_id = login_id
        self.password = password
        # initialize requests HTTP session
        self.session = requests.Session()

    def __enter__(self):
        # login to service
        if not self.login():
            raise AuthenticationError("login failed")
        # copy cookies to requests session
        self.copy_to_requests_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # logout
        self.logout()

    def login(self):
        """authenticate to service"""
        raise NotImplementedError(
            f"{ self.__class__} needs a login() method"
        )

    def logout(self):
        """deauthenticate to service"""
        raise NotImplementedError(
            f"{ self.__class__} needs a logout() method"
        )

    def documents(self):
        """
        generate a list of documents of certain category
        (None for all categories)
        """
        raise NotImplementedError(
            f"{ self.__class__} needs a documents() generator"
        )

    def download(self, document):
        """download document url"""
        filename = self.download_with_requests(document)
        return self.rename_after_download(document, filename)

    def download_with_requests(self, document):
        """download a file without the browser using requests"""
        # fetch url
        r = self.session.get(
            document.url, stream=True, headers=document.request_headers
        )
        if not r.ok:
            raise DownloadError(f"\"{document.url}\" status code: {r.status_code}")

        # filename not already set?
        if "filename" in document.attributes:
            filename = document.attributes['filename']
        # get filename from header
        elif 'content-disposition' in r.headers:
            # @todo properly parse rfc6266
            filename = re.findall(
                "filename=([^; ]+)[;]?.*",
                r.headers['content-disposition']
            )[0]
        else:
            filename = None

        # protect against empty filenames
        if not filename:
            if 'title' in document.attributes:
                filename = document.attributes['title']
            elif 'id' in document.attributes:
                filename = f"document-dl.{document.attributes['id']}"
            else:
                raise RuntimeError("no suitable filename")

        # massage filename
        filename = filename.replace('"', '').strip()
        # save file
        with open(os.path.join(os.getcwd(), filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=4096):
                f.write(chunk)

        return filename

    def rename_after_download(self, document, filename):
        # got a predefined filename?
        if "filename" in document.attributes:
            # rename file to predefined name
            os.rename(filename, document.attributes['filename'])
        else:
            # save new filename
            document.attributes['filename'] = filename
        return filename

    def parse_date(self, datestring, date_format=None):
        """
        helper to parse generic dates
        :param date: either datetime string or datetime object
        :param date_format: datetime.strptime() format string. If none
                            is given, fuzzy matching will be used to
                            parse the date
        :result: datetime object or None
        @todo: handle timezone
        """
        return dateparser.parse(datestring, date_format)

    def prompt_password(self, prompt):
        return getpass.getpass(prompt)


class SeleniumWebPortal(WebPortal):
    """access portal using selenium"""

    WEBDRIVER = "chrome"

    def __init__(self, login_id, password, arguments=None):
        """
        plugins using SeleniumPortal can use self.webdriver for scraping
        """
        super().__init__(login_id, password, arguments)

        # initialize selenium
        webdriver_opts = self._init_webdriver_options()
        self._init_webdriver(webdriver_opts, arguments['webdriver'])


    def __exit__(self, exc_type, exc_val, exc_tb):
        """cleanup selenium"""
        super().__exit__(exc_type, exc_val, exc_tb)
        self.webdriver.close()
        self.webdriver.quit()

    def _init_webdriver_options(self):
        """init selenium options"""
        # choose webdriver options
        if self.WEBDRIVER == "chrome":
            from selenium.webdriver.chrome.options import Options

        elif self.WEBDRIVER == "edge":
            from selenium.webdriver.edge.options import Options

        elif self.WEBDRIVER == "firefox":
            from selenium.webdriver.firefox.options import Options

        elif self.WEBDRIVER == "ie":
            from selenium.webdriver.ie.options import Options

        elif self.WEBDRIVER == "opera":
            from selenium.webdriver.opera.options import Options

        elif self.WEBDRIVER == "safari":
            from selenium.webdriver.safari.options import Options

        elif self.WEBDRIVER == "webkitgtk":
            from selenium.webdriver.webkitgtk.options import Options

        else:
            raise AttributeError(
                "unknown webdriver: \"{self.WEBDRIVER}\""
            )
        return Options()

    def _init_webdriver(self, webdriver_options, options):
        """init selenium"""
        from selenium import webdriver

        # init webdriver
        if self.WEBDRIVER == "chrome":
            # add prefs
            # selenium webdriver specific options
            if 'headless' in options:
                # set headless mode
                webdriver_options.headless = options['headless']
            if 'load_images' in options and options['load_images']:
                # disable image loading
                webdriver_options.add_experimental_option(
                    'prefs',
                    {
                        'profile.default_content_settings.images': 2,
                        'profile.managed_default_content_settings.images': 2
                    }
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
                }
            )
            # ~ # debugging
            # ~ webdriver_options.add_argument("--remote-debugging-port=9222")
            # set preference options
            # init webdriver
            self.webdriver = webdriver.Chrome(options=webdriver_options)

        elif self.WEBDRIVER == "edge":
            self.webdriver = webdriver.Edge(options=webdriver_options)

        elif self.WEBDRIVER == "firefox":
            # work around "acceptInsecureCerts=true" bug
            caps = {
                'acceptInsecureCerts': False
            }
            # create custom profile
            firefox_profile = webdriver.FirefoxProfile()
            # always enable private browsing
            firefox_profile.set_preference("browser.privatebrowsing.autostart", True)
            # set default download directory to CWD
            firefox_profile.set_preference("browser.download.dir", os.getcwd())
            # save PDFs by default (don't preview)
            firefox_profile.set_preference(
                "browser.helperApps.neverAsk.saveToDisk",
                "application/pdf"
            )
            firefox_profile.set_preference("pdfjs.disabled", True)
            firefox_profile.set_preference("plugin.scan.Acrobat", "999.0")
            firefox_profile.set_preference("plugin.scan.plid.all", False)
            # turn off image loading by default
            firefox_profile.set_preference("permissions.default.image", 2)
            # initialize driver
            self.webdriver = webdriver.Firefox(
                firefox_profile=firefox_profile,
                capabilities=caps,
                options=webdriver_options
            )

        elif self.WEBDRIVER == "ie":
            self.webdriver = webdriver.Ie(options=webdriver_options)

        elif self.WEBDRIVER == "opera":
            self.webdriver = webdriver.Opera(options=webdriver_options)

        elif self.WEBDRIVER == "safari":
            self.webdriver = webdriver.Safari(options=webdriver_options)

        elif self.WEBDRIVER == "webkitgtk":
            self.webdriver = webdriver.WebKitGTK(options=webdriver_options)

    def download(self, document):
        """download a document"""
        if document.download_element:
            filename = self.download_with_selenium(document)
        elif document.url:
            # copy cookies from selenium to requests session
            self.copy_to_requests_session()
            filename = self.download_with_requests(document)
        else:
            raise RuntimeError(
                "Document has neither url or download_element"
            )
        return self.rename_after_download(document, filename)

    def download_with_selenium(self, document):
        """download a file using the selenium webdriver"""
        class DownloadFileCreatedHandler(
            watchdog.events.PatternMatchingEventHandler
        ):
            """
            directory watchdog to store filename of newly created file
            """
            filename = None

            def on_created(self, event):
                self.filename = os.path.basename(event.src_path)

        # scroll to download element
        self.scroll_to_element(document.download_element)

        # setup download directory watchdog
        OBSERVER = watchdog.observers.Observer()
        # ignore temporary download files
        handler = DownloadFileCreatedHandler(ignore_patterns=['*.crdownload'])
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
        """copy current session to requests session"""
        # copy cookies
        cookies = self.webdriver.get_cookies()
        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])
        # copy user agent
        user_agent = self.webdriver.execute_script("return navigator.userAgent;")
        self.session.headers['User-Agent'] = user_agent

    def captcha(self, image, entry, prompt="please enter captcha: "):
        """handle captcha"""
        # scroll to ensure captcha is visible
        self.scroll_to_element(image)
        # save screenshot
        image.screenshot("captcha.png")
        # present image to the user
        self.show_image(
            os.path.join(os.getcwd(), "captcha.png"),
            "captcha"
        )
        # ask for interactive captcha input
        captcha = input(prompt)
        # enter into field
        entry.send_keys(captcha)

    def show_image(self, filename, name="image"):
        """attempt to show image"""
        # always print image filename
        print(f'{{"{name}": "{filename}"}}')
        # linux
        if platform.system() == 'Linux':
            if shutil.which("xdg-open") and os.environ['DISPLAY']:
                os.system(f"xdg-open {filename} >/dev/null &")

        # macintosh
        elif platform.system() == 'Darwin':
            if shutil.which("open"):
                os.system(f"open {filename} >/dev/null &")

        # windows
        elif platform.system() == 'Windows':
            os.system(f"start {filename}")

    def scroll_to_element(self, element):
        self.webdriver.execute_script(
            "arguments[0].scrollIntoView(true);", element
        )

class Document():
    """a document"""

    def __init__(self, url=None, attributes=None, request_headers=None, download_element=None):
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
        return f"class {self.__class__.__name__}(url=\"{self.url}\", attributes={self.attributes})"

    def match(self, filters):
        """
        :param filters: list of (attribute_name, pattern) tuples
        :result: True if all document attributes contain the pattern,
                 False otherwise
        """
        # null filter match by default
        if len(filters) == 0:
            return True
        # apply filter to an attribute of a document
        _filter = lambda attribute, pattern: \
            str(pattern) in str(self.attributes[attribute])
        # apply all filters to this document
        return all(_filter(attribute, pattern) for attribute, pattern in filters)

    def jq(self, jq_string):
        """
        :param jq_string: jq expression
        :result: True if jq expression produces any True result,
                 False otherwise
        """
        # null expression matches by default
        if not jq_string:
            return True
        # compile jq expression
        exp = jq.compile(jq_string)
        # feed attributes to jq
        return any(exp.input(self.attributes).all())

    def regex(self, regexes):
        """
        :param regexes: list of (attribute, regex) tuples
        :result: True if all attributes match their regex, False
                 otherwise.
        """
        # always match if there are no regexes
        if not regexes:
            return True
        _match = lambda attribute, regex: \
            re.match(regex, str(self.attributes[attribute]))
        return all(
            _match(attribute, regex) for attribute, regex in regexes
        )
