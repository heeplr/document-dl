"""download documents from strato.de"""

import re
import click
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import docdl
import docdl.util


class Strato(docdl.SeleniumWebPortal):
    """
    download documents from strat
    """

    def login(self):
        # load homepage
        self.webdriver.get("https://www.strato.de/apps/CustomerService")
        # accept cookies
        accept_cookies = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located((By.XPATH, "//button[@id='consentAgree']"))
        )
        accept_cookies.click()
        # find fields
        username = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//input[@autocomplete='username']")
            )
        )
        password = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input#jss_ksb_password"))
        )
        # enter credentials
        username.send_keys(self.login_id)
        password.send_keys(self.password)

        # submit form
        submit = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='submit']"))
        )
        submit.click()
        # wait for either login success or failure
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//p[contains(@class,'err-login')] | "
                    "//*[contains(text(), 'Service-PIN')]",
                )
            )
        )
        # login successful
        return re.match(r".*(Ü|ü)bersicht.*", self.webdriver.title)

    def logout(self):
        logoutbutton = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Abmelden')]")
            )
        )
        logoutbutton.click()

    def documents(self):
        # count all documents
        i = 0
        # load invoices overview
        invoices_link = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.invisibility_of_element_located(
                (By.XPATH, "//a[contains(@href,'OnlineInvoice')]")
            )
        )
        self.webdriver.get(invoices_link.get_attribute("href"))

        # iterate all pages
        while True:
            # wait for table of invoices
            invoice_table = WebDriverWait(self.webdriver, self.TIMEOUT).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//table[@id='invoice_table']")
                )
            )
            # iterate all invoices
            for invoice in invoice_table.find_elements(By.XPATH, ".//tr"):
                # hidden row ?
                if "hidden" in invoice.get_attribute("class"):
                    # skip
                    continue
                columns = invoice.find_elements(By.CSS_SELECTOR, "td")
                # got header?
                if len(columns) == 0:
                    # skip
                    continue
                # get attributes
                date = columns[1].get_attribute("data-sortvalue").strip()
                status = columns[2].get_attribute("textContent").lower().strip()
                invoice_link = columns[3].find_element(
                    By.XPATH, ".//a[contains(@href,'action=pdf')]"
                )
                title = invoice_link.get_attribute("textContent").strip()
                amount = (
                    columns[4]
                    .find_element(By.XPATH, ".//span[@class='jss_price']")
                    .get_attribute("textContent")
                    .strip()
                )

                # create document
                yield docdl.Document(
                    download_element=invoice_link,
                    attributes={
                        "date": docdl.util.parse_date(date),
                        "doctype": "invoice",
                        "status": status,
                        "amount": amount,
                        "id": i,
                        "filename": f"strato-{title}.pdf",
                    },
                )
                # increment counter
                i += 1

            # load next page
            nextbutton = WebDriverWait(self.webdriver, self.TIMEOUT).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//a[contains(@class,'next')]")
                )
            )
            # last page?
            if "disabled" in nextbutton.get_attribute("class"):
                break
            # go to next page
            nextbutton.click()


@click.command()
@click.pass_context
# pylint: disable=W0613
def strato(ctx, *args, **kwargs):
    """strato.de (invoices)"""
    docdl.cli.run(ctx, Strato)
