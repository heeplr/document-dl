"""download documents from www.vodafone.de"""

import itertools
import click
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import docdl
import docdl.util


class Vodafone(docdl.SeleniumWebPortal):
    """
    download documents from https://kabel.vodafone.de
    """

    URL_BASE = "https://kabel.vodafone.de"
    URL_MY_DOCUMENTS = f"{URL_BASE}/meinkabel/meine_kundendaten/meine_dokumente"
    URL_INVOICES = f"{URL_BASE}/meinkabel/rechnungen/rechnung"
    URL_LOGOUT = "https://www.vodafone.de/mint/saml/logout"


    def login(self):
        """authenticate"""
        # load main page
        self.webdriver.get(self.URL_BASE)
        # wait for cookie banner or login button
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "div.login-btn") or \
                      d.find_elements(By.CSS_SELECTOR, "div.red-btn")
        )
        # cookie banner?
        if cookiebutton := self.webdriver.find_elements(
            By.CSS_SELECTOR, "div.red-btn"
        ):
            # accept
            cookiebutton[0].click()
        # press login button to show login form
        loginbutton = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.login-btn"))
        )
        loginbutton.click()
        # clicking two times makes it work in firefox
        if self.WEBDRIVER == "firefox":
            loginbutton.click()
        # fill out login form when it appears
        username = self.webdriver.find_element(
            By.XPATH, "//input[@name='username']"
        )
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of(username)
        )
        password = self.webdriver.find_element(
            By.XPATH, "//input[@name='password']"
        )
        username.send_keys(self.login_id)
        password.send_keys(self.password)
        password.submit()
        # wait for page to load
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "a.logout-btn") or \
                          d.find_elements(By.CSS_SELECTOR, "div.error")
        )
        # if there's a password prompt element found, login failed
        return len(self.webdriver.find_elements(By.CSS_SELECTOR, "a.logout-btn")) != 0

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        """fetch list of documents"""
        for i, document in enumerate(itertools.chain(self.my_documents(), self.invoices())):
            # set an id
            document.attributes['id'] = i
            # return document
            yield document

    def my_documents(self):
        """iterate "Meine Dokumente"""
        # go to documents site
        self.webdriver.get(self.URL_MY_DOCUMENTS)
        # iterate all document elements
        for element in self.webdriver.find_elements(
                By.CSS_SELECTOR, "div.dataTable-row"
        ):
            # 1st cell is date
            date = element.find_element(By.CSS_SELECTOR, ":nth-child(1)") \
                   .get_attribute("textContent") \
                   .strip()
            # 2nd cell is topic
            title = element.find_element(By.CSS_SELECTOR, ":nth-child(2)") \
                    .get_attribute("textContent") \
                    .strip()
            # 4th cell contains link
            url = element.find_element(By.CSS_SELECTOR, ":nth-child(4)") \
                  .find_element(By.CSS_SELECTOR, "a") \
                  .get_attribute("href") \
                  .strip()
            # generate document
            yield docdl.Document(
                url=url,
                attributes={
                    'title': title,
                    'date': docdl.util.parse_date(date),
                    'category': "my_documents"
                }
            )


    def invoices(self):
        """iterate invoices"""
        # go to bills overview
        self.webdriver.get(self.URL_INVOICES)
        for table in self.webdriver.find_elements(By.CSS_SELECTOR, "div.dataTable"):
            rows = table.find_elements(By.CSS_SELECTOR, "div.dataTable-row")
            for i, element in enumerate(rows):
                # first row is a title row, skip it
                if i == 0:
                    continue
                cells = element.find_elements(By.XPATH, ".//div")
                # skip empty rows
                if len(cells) < 2:
                    continue
                # get type
                doctype = cells[0] \
                        .get_attribute("title") \
                        .strip()
                # get date
                date = cells[1] \
                        .get_attribute("textContent") \
                        .strip()
                # get title
                title = cells[2] \
                        .get_attribute("textContent") \
                        .strip()
                # get url
                url = cells[5] \
                      .find_element(By.CSS_SELECTOR, "a") \
                      .get_attribute("href") \
                      .strip()
                # generate document
                yield docdl.Document(
                    url=url,
                    attributes={
                        'type': doctype,
                        'title': title,
                        'date': docdl.util.parse_date(date),
                        'category': "invoice"
                    }
                )

@click.command()
@click.pass_context
def vodafone(ctx):
    """kabel.vodafone.de (postbox, invoices)"""
    docdl.cli.run(ctx, Vodafone)
