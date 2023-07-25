"""download documents from service.handyvertrag.de"""

import click
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import docdl
import docdl.util


class Handyvertrag(docdl.SeleniumWebPortal):
    """download documents from service.handyvertrag.de"""

    URL_LOGIN = "https://service.handyvertrag.de/"
    URL_LOGOUT = "https://service.handyvertrag.de/public/prelogout"
    URL_INVOICES = "https://service.handyvertrag.de/mytariff/invoice/showAll"

    def login(self):
        """authenticate"""
        self.webdriver.get(self.URL_LOGIN)

        # find entry field
        username = self.webdriver.find_element(
            By.XPATH, "//input[@id='UserLoginType_alias']"
        )
        # wait for entry field
        WebDriverWait(self.webdriver, self.TIMEOUT).until(EC.visibility_of(username))
        # send username
        username.send_keys(self.login_id)
        # save current URL
        current_url = self.webdriver.current_url
        # find entry field
        password = self.webdriver.find_element(
            By.XPATH, "//input[@id='UserLoginType_password']"
        )
        # wait for entry field
        WebDriverWait(self.webdriver, self.TIMEOUT).until(EC.visibility_of(password))
        # send password
        password.send_keys(self.password)
        # submit form
        password.submit()
        # wait for page to load
        current_url = self.wait_for_urlchange(current_url)
        # wait for either login success, failure or "accept" button
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//img[contains(@alt, 'LOGOUT')] | "
                    "//div[contains(@data-test-id, 'unified-login-error')]",
                )
            )
        )
        # click "confirm" button for cookies if there is one
        cookiebutton = self.webdriver.find_element(
            By.XPATH, '//*[@id="consent_wall_optin"]'
        )
        if cookiebutton:
            cookiebutton.click()

        # Login failed
        return self.webdriver.find_elements(By.XPATH, "//img[contains(@alt, 'LOGOUT')]")

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        """fetch invoices"""
        self.webdriver.get(self.URL_INVOICES)

        invoice_collapser = self.webdriver.find_elements(
            By.XPATH, '//*[contains(@id, "heading-rechnungen-")]/button'
        )

        for row in invoice_collapser:
            row.click()
            description = row.text
            date = description.split()[-1]

            # type invoice
            link = row.parent.find_elements(By.LINK_TEXT, "Rechnung")
            if len(link) == 1:
                url = link[0].get_attribute("href")
                idn = url.split("/")[-1]
                yield docdl.Document(
                    url=url,
                    attributes={
                        "id": idn,
                        "date": docdl.util.parse_date(date),
                        "category": "invoice",
                        "subject": description,
                    },
                )

            # type call log
            link = row.parent.find_elements(By.LINK_TEXT, "Einzelverbindungsnachweis")
            if len(link) == 1:
                url = link[0].get_attribute("href")
                idn = url.split("/")[-1]
                yield docdl.Document(
                    url=url,
                    attributes={
                        "id": idn,
                        "date": docdl.util.parse_date(date),
                        "category": "call_log",
                        "subject": description,
                    },
                )


@click.command()
@click.pass_context
# pylint: disable=C0103
def handyvertrag(ctx):
    """service.handyvertrag.de (invoices, call record)"""
    docdl.cli.run(ctx, Handyvertrag)
