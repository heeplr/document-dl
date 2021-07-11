"""download documents from web portals"""

import re
import os
import requests
import inotify.adapters
import jq

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
                "filename=(.+)(?:;)?",
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

    def parse_date(self, datestring, format=None):
        """
        helper to parse generic dates
        :param date: either datetime string or datetime object
        :param format: datetime.strptime() format string. If none is given,
                       brute force will be used to parse the date
        :result: datetime object or None
        @todo: handle timezone
        """
        return dateparser.parse(datestring, format)

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
        super().__exit__(exc_type, exc_val, exc_tb)
        self.webdriver.close()
        self.webdriver.quit()

    def _init_webdriver_options(self):
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
        from selenium import webdriver
        # selenium webdriver specific options
        for opt, val in options.items():
            setattr(webdriver_options, opt, val)

        # init webdriver
        if self.WEBDRIVER == "chrome":
            # enable incognito mode
            webdriver_options.add_argument("--incognito")
            # set preference options
            webdriver_options.add_experimental_option("prefs", {
                # always save PDFs
                "plugins.always_open_pdf_externally": True,
                # set default download directory to CWD
                "download.default_directory": os.getcwd()
            })
            self.webdriver = webdriver.Chrome(options=webdriver_options)

        elif self.WEBDRIVER == "edge":
            self.webdriver = webdriver.Edge(options=webdriver_options)

        elif self.WEBDRIVER == "firefox":
            # enable private browsing
            firefox_profile = webdriver.FirefoxProfile()
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
            self.webdriver = webdriver.Firefox(options=webdriver_options)

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
        # scroll to download element
        self.webdriver.execute_script(
            "arguments[0].scrollIntoView(true);",
            document.download_element
        )
        # setup inotify monitor to watch download
        # directory for new files
        notify = inotify.adapters.Inotify()
        notify.add_watch(os.getcwd())

        # click element to start download
        document.download_element.click()

        # wait for download completed
        for event in notify.event_gen(yield_nones=False):
            # unpack event
            (_, type_names, path, filename) = event
            # is this a chrome download file?
            if filename.endswith(".crdownload"):
                new_filename = filename.removesuffix(".crdownload")
            # is this our finished download ?
            if filename == new_filename:
                # we're done
                break

        # remove inotify monitor
        notify.remove_watch(os.getcwd())

        return filename

    def copy_to_requests_session(self):
        """copy current session to requests session"""
        # copy cookies
        cookies = self.webdriver.get_cookies()
        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])
        # copy user agent
        user_agent = self.webdriver.execute_script("return navigator.userAgent;")
        self.session.headers['User-Agent'] = user_agent


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
            re.match(regex, self.attributes[attribute])
        return all(
            _match(attribute, regex) for attribute, regex in regexes
        )
