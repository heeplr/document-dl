"""download documents from web portals"""

import inotify.adapters
import re
import requests
import os


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

    def __init__(self, login_id, password):
        self.login_id = login_id
        self.password = password
        # initialize requests HTTP session
        self.session = requests.Session()

    def __enter__(self):
        # login to service
        self.login()
        if not self.is_logged_in():
            raise AuthenticationError("login failed")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # logout
        self.logout()

    def login(self):
        """authenticate to service"""
        raise NotImplementedError(
            f"{ self.__class__} needs a login() method"
        )

    def is_logged_in(self):
        """return True if logged in successfully, False otherwise"""
        raise NotImplementedError(
            f"{self.__class__} needs a is_logged_in() method"
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



class SeleniumWebPortal(WebPortal):
    """access portal using selenium"""

    WEBDRIVER = "chrome"

    def __init__(self, login_id, password, options={}):
        """
        plugins using SeleniumPortal can use self.webdriver for scraping
        """
        super(SeleniumWebPortal, self).__init__(login_id, password)
        # initialize selenium
        from selenium import webdriver
        # choose webdriver options
        if self.WEBDRIVER == "android":
            from selenium.webdriver.android.options import Options

        elif self.WEBDRIVER == "blackberry":
            from selenium.webdriver.blackberry.options import Options

        elif self.WEBDRIVER == "chrome":
            from selenium.webdriver.chrome.options import Options

        elif self.WEBDRIVER == "edge":
            from selenium.webdriver.edge.options import Options

        elif self.WEBDRIVER == "firefox":
            from selenium.webdriver.firefox.options import Options

        elif self.WEBDRIVER == "ie":
            from selenium.webdriver.ie.options import Options

        elif self.WEBDRIVER == "opera":
            from selenium.webdriver.opera.options import Options

        elif self.WEBDRIVER == "phantomjs":
            from selenium.webdriver.phantomjs.options import Options

        elif self.WEBDRIVER == "remote":
            from selenium.webdriver.remote.options import Options

        elif self.WEBDRIVER == "safari":
            from selenium.webdriver.safari.options import Options

        elif self.WEBDRIVER == "webkitgtk":
            from selenium.webdriver.webkitgtk.options import Options

        else:
            raise AttributeError(
                "unknown webdriver: \"{self.WEBDRIVER}\""
            )
        # selenium webdriver specific options
        opts = Options()
        for opt, val in options.items():
            setattr(opts, opt, val)
        # init webdriver
        if self.WEBDRIVER == "android":
            self.webdriver = webdriver.Android(options=opts)

        elif self.WEBDRIVER == "blackberry":
            self.webdriver = webdriver.BlackBerry(options=opts)

        elif self.WEBDRIVER == "chrome":
            # enable incognito mode
            opts.add_argument("--incognito")
            # set preference options
            opts.add_experimental_option("prefs", {
                # always save PDFs
                "plugins.always_open_pdf_externally": True,
                # set default download directory to CWD
                "download.default_directory": os.getcwd()
            })
            self.webdriver = webdriver.Chrome(options=opts)

        elif self.WEBDRIVER == "edge":
            self.webdriver = webdriver.Edge(options=opts)

        elif self.WEBDRIVER == "firefox":
            # enable private browsing
            firefox_profile = webdriver.FirefoxProfile()
            firefox_profile.set_preference("browser.privatebrowsing.autostart", True)
            # set default download directory to CWD
            firefox_profile.set_preference("browser.download.dir", os.getcwd())
            # save PDFs by default (don't preview)
            firefox_profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf");
            firefox_profile.set_preference("pdfjs.disabled", True);
            firefox_profile.set_preference("plugin.scan.Acrobat", "999.0");
            firefox_profile.set_preference("plugin.scan.plid.all", False);
            self.webdriver = webdriver.Firefox(options=opts)

        elif self.WEBDRIVER == "ie":
            self.webdriver = webdriver.Ie(options=opts)

        elif self.WEBDRIVER == "opera":
            self.webdriver = webdriver.Opera(options=opts)

        elif self.WEBDRIVER == "phantomjs":
            self.webdriver = webdriver.PhantomJS(options=opts)

        elif self.WEBDRIVER == "remote":
            self.webdriver = webdriver.Remote(options=opts)

        elif self.WEBDRIVER == "safari":
            self.webdriver = webdriver.Safari(options=opts)

        elif self.WEBDRIVER == "webkitgtk":
            self.webdriver = webdriver.WebKitGTK(options=opts)

    def __exit__(self, exc_type, exc_val, exc_tb):
        super(SeleniumWebPortal, self).__exit__(exc_type, exc_val, exc_tb)
        self.webdriver.close()
        self.webdriver.quit()

    def download(self, document):
        """download a document"""
        if document.download_element:
            filename = self.download_with_selenium(document)
        elif document.url:
            filename = self.download_with_requests(document)
        else:
            raise ArgumentError(
                "Document has neither url or download_element"
            )
        # got a predefined filename?
        if "filename" in document.attributes:
            # rename file to predefined name
            os.rename(filename, document.attributes['filename'])
        else:
            # save new filename
            document.attributes['filename'] = filename

    def download_with_selenium(self, document):
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

    def download_with_requests(self, document):
        # copy cookies from selenium to requests session
        self.copy_to_requests_session()
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
                "filename=(.+);",
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

    def __init__(self, url=None, attributes={}, request_headers={}, download_element=None):
        # default custom request headers
        self.request_headers = request_headers
        # target url (if set, the url will be GET using requests)
        self.url = url
        # if download_element is set, it will be click()ed for download
        self.download_element = download_element
        # portal specific attributes
        self.attributes = attributes

    def __repr__(self):
        return f"class {self.__class__.__name__}(url=\"{self.url}\", attributes={self.attributes})"

    def filter(self, filters):
        """
        :param filters: list of (attribute_name, pattern) tuples
        :result: True if document attribute contain pattern,
                 False otherwise
        """
        # null filter match by default
        if len(filters) == 0:
            return True
        # apply filter to an attribute of a document
        _filter = lambda attribute, pattern: \
            True if attribute in self.attributes and \
                    str(pattern) in str(self.attributes[attribute]) \
                 else False
        # apply all filters to this document
        if all([ _filter(attribute, pattern) for attribute, pattern in filters ]):
            return True
        # no match
        return False
