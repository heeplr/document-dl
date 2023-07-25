"""download documents from dkb.de"""

import itertools
import re
import sys
import click
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import docdl
import docdl.util


class DKB(docdl.SeleniumWebPortal):
    """download documents from dkb.de"""

    URL_LOGIN = "https://www.dkb.de/banking"
    URL_LOGOUT = "https://www.dkb.de/DkbTransactionBanking/banner.xhtml?$event=logout"
    URL_INBOX = "https://www.dkb.de/banking/postfach"

    def __init__(self, login_id, password, useragent=None, arguments=None):
        """use custom init to force image loading (for photoTAN)"""
        if arguments and "load_images" in arguments and not arguments["load_images"]:
            arguments["load_images"] = True
        super().__init__(login_id, password, useragent, arguments)

    def login(self):
        # load login page
        self.webdriver.get(self.URL_LOGIN)
        # wait for username entry
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            lambda d: d.find_elements(By.XPATH, "//input[@id='loginInputSelector']")
            or d.find_elements(By.XPATH, "//button[contains(text(), 'annehmen')]")
        )
        # cookiebanner?
        if cookiebutton := self.webdriver.find_elements(
            By.XPATH, "//button[contains(text(), 'annehmen')]"
        ):
            cookiebutton[0].click()
        # get username entry
        username = self.webdriver.find_element(
            By.XPATH, "//input[@id='loginInputSelector']"
        )
        # password entry
        password = self.webdriver.find_element(
            By.XPATH, "//input[@id='pinInputSelector']"
        )
        # enter credentials
        username.send_keys(self.login_id)
        password.send_keys(self.password)
        password.submit()
        # wait for photoTAN or "confirm with TAN" button
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//img[@alt='QR-Code'] | "
                    "//button[@id='next'] | "
                    "//div[contains(@class, 'errorMessage')]",
                )
            )
        )
        # wrong password?
        if self.webdriver.find_elements(
            By.XPATH, "//div[contains(@class, 'errorMessage')]"
        ):
            # login failed
            return False
        # sometimes QR code is not displayed instantly but one has
        # to press the next-button first
        if not (
            qrcode := self.webdriver.find_elements(By.XPATH, "//img[@alt='QR-Code']")
        ):
            nextbutton = self.webdriver.find_element(By.XPATH, "//button[@id='next']")
            nextbutton.click()
            # get qrcode
            qrcode = WebDriverWait(self.webdriver, self.TIMEOUT).until(
                EC.visibility_of_element_located((By.XPATH, "//img[@alt='QR-Code']"))
            )
        # got qrcode
        else:
            qrcode = qrcode[0]
        # wait for QR code to be fully loaded
        WebDriverWait(self.webdriver, self.TIMEOUT).until(EC.visibility_of(qrcode))
        # save current url
        current_url = self.webdriver.current_url
        # startcode
        startcode = (
            self.webdriver.find_element(By.XPATH, "//b[contains(text(), 'Startcode')]")
            .get_attribute("textContent")
            .strip()
        )
        startcode = re.match(r"[^\d]*(\d+)[^\d]*", startcode)[1]
        # tan entry
        tan = self.webdriver.find_element(By.XPATH, "//input[@id='tanInputSelector']")
        # treat QR code as captcha
        print(
            f"Überprüfen Sie den Startcode {startcode} "
            f"bestätigen Sie mit der Taste OK.",
            file=sys.stderr,
        )
        self.captcha(qrcode, tan, prompt="please enter chipTAN: ")
        tan.submit()
        # wait for page to load
        self.wait_for_urlchange(current_url)
        # wait for logout button
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            lambda d: "financialstatus" in d.current_url
            or "LoginWithTan" in d.current_url
            or d.current_url.endswith("banking")
        )
        # login successful?
        return "financialstatus" in self.webdriver.current_url

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        for i, document in enumerate(itertools.chain(self._inbox())):
            # set an id
            document.attributes["id"] = i
            # return document
            yield document

    # ~ def accounts_csv(self):
    # ~ """get transactions of each account as csv"""
    # ~ # @todo
    # ~ pass

    def _inbox(self):
        def get_catlinks(table):
            """get links of all categories and return them as list of tuples"""
            catlinks = []
            for row in table.find_elements(
                By.XPATH, "//table[@id='welcomeMboTable']/tbody/tr"
            ):
                # get category
                category = row.get_attribute("id").lower()
                # get link to open category
                subject = row.find_element(By.CSS_SELECTOR, "td.subject")
                catlink = subject.find_element(By.CSS_SELECTOR, "a")
                url = catlink.get_attribute("href")
                catlinks += [(category, url)]
            return catlinks

        # load inbox
        self.webdriver.get(self.URL_INBOX)
        # wait for table
        table = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//table[@id='welcomeMboTable']")
            )
        )
        # iterate all category rows and collect links to categories
        catlinks = get_catlinks(table)

        # iterate all categories
        for category, catlink in catlinks:
            self.webdriver.get(catlink)
            # iterate all pages
            while True:
                # iterate all documents
                for row in self.webdriver.find_elements(
                    By.CSS_SELECTOR, "table tbody tr.mbo-folderview-message"
                ):
                    # get read state
                    classes = row.get_attribute("class")
                    unread = "mbo-messageState-read" not in classes

                    # get date
                    date = (
                        row.find_element(By.CSS_SELECTOR, "div.show-for-small-down")
                        .get_attribute("textContent")
                        .strip()
                    )

                    # get link to document
                    link = row.find_element(
                        By.XPATH, ".//td/a[@tid='getMailboxAttachment']"
                    )
                    url = link.get_attribute("href")
                    topic = link.get_attribute("textContent").strip()
                    # create document
                    yield docdl.Document(
                        url=url,
                        attributes={
                            "date": docdl.util.parse_date(date),
                            "category": category,
                            "subject": topic,
                            "unread": unread,
                        },
                    )

                # is there a next-button for pagination?
                if not self._nextbutton():
                    # quit
                    break

    def _nextbutton(self):
        """
        find next-button on paginated page and return true/false
        accordingly. Load next page if true.
        """
        if nextspan := self.webdriver.find_elements(
            By.CSS_SELECTOR, "span.pager-navigator-next"
        ):
            # click next button
            nextbutton = nextspan[0].find_element(By.XPATH, "a")
            self.webdriver.get(nextbutton.get_attribute("href"))
            # wait for new folderview
            WebDriverWait(self.webdriver, self.TIMEOUT).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "table.expandableTable tbody")
                )
            )
            return True
        return False


@click.command()
@click.pass_context
def dkb(ctx):
    """dkb.de with chipTAN QR (postbox)"""
    docdl.cli.run(ctx, DKB)
