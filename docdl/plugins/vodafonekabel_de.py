"""download documents from https://www.vodafone.de"""

import docdl
import itertools
import selenium.common.exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



class VodafoneKabel_DE(docdl.SeleniumWebPortal):
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
        # press login button to show login form
        loginbutton = self.webdriver.find_element_by_css_selector("div.login-btn")
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of(loginbutton)
        )
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.login-btn"))
        )
        loginbutton.click()
        # fill out login form when it appears
        username = self.webdriver.find_element_by_xpath("//input[@name='username']")
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of(username)
        )
        password = self.webdriver.find_element_by_xpath("//input[@name='password']")
        username.send_keys(self.login_id)
        password.send_keys(self.password)
        password.submit()

    def is_logged_in(self):
        """return True if logged in successfully, False otherwise"""
        # wait for page to load
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "a.logout-btn") or \
                          d.find_elements(By.XPATH, "//input[@type='password']")
        )
        # if there's a password prompt, login failed
        if len(self.webdriver.find_elements(By.CSS_SELECTOR, "a.logout-btn")) == 0:
            return False
        return True

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        """fetch list of documents"""
        for n, d in enumerate(itertools.chain(self.my_documents(), self.invoices())):
            # set an id
            d.attributes['id'] = n
            # return document
            yield d

    def my_documents(self):
        """iterate "Meine Dokumente"""
        # go to documents site
        self.webdriver.get(self.URL_MY_DOCUMENTS)
        # iterate all document elements
        for e in self.webdriver.find_elements_by_css_selector("div.dataTable-row"):
            # 1st cell is date
            date = e.find_element_by_css_selector(":nth-child(1)") \
                   .get_attribute("textContent") \
                   .strip()
            # 2nd cell is topic
            title = e.find_element_by_css_selector(":nth-child(2)") \
                    .get_attribute("textContent") \
                    .strip()
            # 4th cell contains link
            url = e.find_element_by_css_selector(":nth-child(4)") \
                  .find_element_by_css_selector("a") \
                  .get_attribute("href") \
                  .strip()
            # generate document
            yield docdl.Document(
                url=url,
                attributes={
                    'title': title,
                    'date': date,
                    'category': "my_documents"
                }
            )


    def invoices(self):
        # go to bills overview
        self.webdriver.get(self.URL_INVOICES)
        for table in self.webdriver.find_elements_by_css_selector("div.dataTable"):
            rows = table.find_elements_by_css_selector("div.dataTable-row")
            for i, e in enumerate(rows):
                # first row is a title row, skip it
                if i == 0:
                    continue
                cells = e.find_elements_by_tag_name("div")
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
                      .find_element_by_css_selector("a") \
                      .get_attribute("href") \
                      .strip()
                # generate document
                yield docdl.Document(
                    url=url,
                    attributes={
                        'type': doctype,
                        'title': title,
                        'date': date,
                        'category': "invoice"
                    }
                )
