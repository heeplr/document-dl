"""download documents from conrad.de"""

import re
import click
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

import docdl
import docdl.util


class Conrad(docdl.SeleniumWebPortal):
    """download documents from conrad.de"""

    URL_LOGIN = "https://www.conrad.de/de/account.html"
    URL_LOGOUT = "https://api.conrad.de/session/1/logout"
    URL_INVOICES = "https://www.conrad.de/de/account.html#/invoices"

    def login(self):
        # load login page
        self.webdriver.get(self.URL_LOGIN)
        # find fields
        username = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input#username"))
        )
        password = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input#password"))
        )
        # enter credentials
        username.send_keys(self.login_id)
        password.send_keys(self.password)
        # save current URL
        current_url = self.webdriver.current_url
        # submit form
        password.submit()
        # wait for page to load
        current_url = self.wait_for_urlchange(current_url)
        # wait for either login success or failure
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            lambda d: "Mein Konto" in d.title or "Conrad" in d.title
        )
        # Login failed
        if "Conrad" in self.webdriver.title:
            return False
        # close cookie notification
        cookie_button = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Ablehnen')]")
            )
        )
        cookie_button.click()
        return True

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        # wait for loader icon to disappear
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.vld-icon"))
        )
        # load list of invoices
        self.webdriver.get(self.URL_INVOICES)
        # wait for time period selection
        time_period = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//select[@name='timePeriodProperty']")
            )
        )
        time_period_select = Select(time_period)
        # show all invoices
        time_period_select.select_by_visible_text("Alle Rechnungen")
        # wait for loader icon to disappear
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.vld-icon"))
        )
        # iterate all invoices
        for i, invoice in enumerate(
            self.webdriver.find_elements(By.XPATH, "//a[@data-e2e='invoiceList-item']")
        ):
            # get attributes
            title = (
                invoice.find_element(
                    By.XPATH, ".//div[@data-e2e='invoiceListItem-title']"
                )
                .get_attribute("textContent")
                .strip()
            )
            date = re.match(r".*(\d{2}\.\d{2}\.\d{4})", title)[1]
            number = (
                invoice.find_element(
                    By.XPATH, ".//div[@data-e2e='invoiceListItem-invoiceNumber']"
                )
                .get_attribute("textContent")
                .strip()
            )
            doctype = (
                invoice.find_element(
                    By.XPATH, ".//div[@data-e2e='invoiceListItem-type']"
                )
                .get_attribute("textContent")
                .strip()
                .lower()
            )
            amount = (
                invoice.find_element(
                    By.XPATH, ".//div[@data-e2e='invoiceListItem-amount']"
                )
                .get_attribute("textContent")
                .strip()
            )
            # strip currency symbol
            amount = re.match(r"[^\d]*(\d+,\d+).*", amount)[1]
            # create filename
            filename = f"conrad-{date.replace('.','-')}-{doctype}-{number}.pdf"
            # create document
            yield docdl.Document(
                download_element=invoice,
                attributes={
                    "date": docdl.util.parse_date(date),
                    "number": number,
                    "doctype": doctype,
                    "amount": amount,
                    "id": i,
                    "filename": filename,
                    "category": "invoice",
                },
            )


@click.command()
@click.pass_context
def conrad(ctx):
    """conrad.de (invoices)"""
    docdl.cli.run(ctx, Conrad)
