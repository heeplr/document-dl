"""download documents from www.vodafone.de"""

import click
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import docdl
import docdl.util


class Vodafone(docdl.SeleniumWebPortal):
    """
    download documents from https://www.vodafone.de
    """

    URL_BASE = "https://www.vodafone.de"
    URL_MYVODAFONE = f"{URL_BASE}/meinvodafone"
    URL_LOGIN = f"{URL_MYVODAFONE}/account/login"
    URL_MY_DOCUMENTS = f"{URL_MYVODAFONE}/services/notifizierung/dokumente"
    URL_LOGOUT = f"{URL_BASE}/logout"

    def login(self):
        """authenticate"""
        # load login page
        self.webdriver.get(self.URL_LOGIN)
        # fill out login form when it appears
        username = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='txtUsername']"))
        )
        password = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='txtPassword']"))
        )
        username.send_keys(self.login_id)
        password.send_keys(self.password)
        password.submit()
        # wait for page element indicating success or error
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".contract-info")),
                EC.element_to_be_clickable((By.XPATH, "//input[@id='txtUsername']")),
            )
        )
        # if there's a logout element found, login was successful
        return len(self.webdriver.find_elements(By.CSS_SELECTOR, ".contract-info")) != 0

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        """fetch list of documents"""
        # chain all document types
        docs = enumerate(self.invoices())
        for i, document in docs:
            # set an id
            document.attributes["id"] = i
            # return document
            yield document

    def invoices(self):
        """iterate "Rechnungen"""
        # go to documents site
        self.webdriver.get(self.URL_MY_DOCUMENTS)
        # wait for documents
        documents = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//ul[contains(@class, 'documents-inbox-container')]")
            )
        )
        # iterate all pages
        while next_button := WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@id='pagination']/ol/li[3]/a[1]")
            )
        ):
            # iterate all document elements
            for element in documents.find_elements(By.CSS_SELECTOR, "li"):
                # get date
                date = (
                    element.find_element(
                        By.XPATH, ".//*[@automation-id='documentsInboxes_date_tv']"
                    )
                    .get_attribute("textContent")
                    .strip()
                )
                # get title
                title = (
                    element.find_element(
                        By.XPATH, ".//*[@automation-id='documentsInboxes_type_tv']"
                    )
                    .get_attribute("textContent")
                    .strip()
                )
                # get download link
                dl_button = element.find_element(
                    By.XPATH, ".//*[@automation-id='documentsInboxes_download_btn']"
                )
                # generate document
                yield docdl.Document(
                    download_element=dl_button,
                    attributes={
                        "title": title,
                        "date": docdl.util.parse_date(date),
                        "category": "invoice",
                    },
                )
            # last page?
            if "inactive" in next_button.get_attribute("class"):
                # exit
                break
            # go to next page
            next_button.click()


@click.command()
@click.pass_context
def vodafone(ctx):
    """www.vodafone.de (invoices)"""
    docdl.cli.run(ctx, Vodafone)
