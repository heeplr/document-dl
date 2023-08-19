"""download documents from ing.de"""

import itertools
import click
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import docdl
import docdl.util


class ING(docdl.SeleniumWebPortal):
    """download documents from ing.de"""

    URL_LOGIN = "https://banking.ing.de"
    URL_LOGOUT = "https://banking.ing.de/app/logout"
    URL_POSTBOX = "https://banking.ing.de/app/obligo/postbox"
    URL_TRANSACTIONS = "https://banking.ing.de/app/obligo/umsatzanzeige"

    def __init__(self, login_id, password, useragent=None, arguments=None):
        # don't use headless user agent to avoid ing.de mistaking us for a bot
        super().__init__(
            login_id=login_id,
            password=password,
            arguments=arguments,
            useragent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) "
            "Gecko/20100101 Firefox/91.0",
        )

    def login(self):
        # load login page
        self.webdriver.get(self.URL_LOGIN)
        # wait for cookie accept button
        dialog = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.XPATH, ".//*[@data-tag-name='ing-cc-dialog-level0']")
            )
        )
        cookie_button = dialog.shadow_root.find_element(
            By.CSS_SELECTOR, ".cc-l0__button__more"
        )
        cookie_button.click()
        # sign in
        username = self.webdriver.find_element(
            By.XPATH, "//input[contains(@name, 'zugangskennung')]"
        )
        username.send_keys(self.login_id)
        password = self.webdriver.find_element(
            By.XPATH, "//input[contains(@name, 'pin')]"
        )
        password.send_keys(self.password)
        nextbutton = self.webdriver.find_element(
            By.XPATH, "//button[@name='view:next-inline']"
        )
        nextbutton.click()

        # handle photoTAN
        if qrcode := self.webdriver.find_element(
            By.CSS_SELECTOR, "img.thumbnail__image"
        ):
            tan_entry = self.webdriver.find_element(
                By.CSS_SELECTOR, "input.input-field"
            )

            self.captcha(qrcode, tan_entry, "please enter photoTAN: ")
            # submit photoTAN
            nextbutton = self.webdriver.find_element(
                By.XPATH, "//button[@name='buttons:next']"
            )
            nextbutton.click()

        # wait for logout button (success) or tan input (failure) or
        # some ad modal (success)
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            lambda d: d.find_elements(
                By.XPATH, "//button[@class='session-button__logout-button']"
            )
            or d.find_elements(By.CSS_SELECTOR, "input.input-field")
            or d.find_elements(By.CSS_SELECTOR, "section.insight-modal")
        )
        # login successful ?
        return self.webdriver.find_elements(
            By.XPATH, "//button[@class='session-button__logout-button']"
        )

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        # chain all document types
        docs = itertools.chain(self.postbox(), self.csv())
        for i, document in enumerate(docs):
            # set an id
            document.attributes["id"] = i
            # return document
            yield document

    def csv(self):
        """scrape transaction csv as document"""
        self.webdriver.get(self.URL_TRANSACTIONS)
        # open filter menu
        filterbutton = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//button[contains(@class, 'filters')]")
            )
        )
        filterbutton.click()
        # find button to select whole year
        yearbutton = self.webdriver.find_element(
            By.XPATH, "//span[contains(text(), '1 Jahr')]"
        )
        self.scroll_to_element(yearbutton)
        yearbutton.click()
        # find button to apply filter
        applybutton = self.webdriver.find_element(
            By.XPATH, "//button[contains(@name, 'ergebnisseAnzeigen')]"
        )
        self.scroll_to_element(applybutton)
        applybutton.click()
        self.scroll_to_bottom()
        # wait for export button
        exportbutton = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[contains(text(),'Exportieren')]")
            )
        )
        exportbutton.click()
        # wait for CSV radio button
        csvspan = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//span[contains(text(),'CSV')]")
            )
        )
        # select CSV format
        csvspan.click()
        # find download button
        downloadbutton = self.webdriver.find_element(
            By.XPATH, "//a[contains(text(),'exportieren')]"
        )
        # create document
        yield docdl.Document(
            download_element=downloadbutton,
            attributes={
                "category": "csv_export",
            },
        )

    def postbox(self):
        """scrape documents in postbox"""
        # open postbox
        self.webdriver.get(self.URL_POSTBOX)
        # wait for table
        table = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ibbr-table"))
        )
        # iterate rows
        for row in table.find_elements(By.CSS_SELECTOR, "div.ibbr-table-row"):
            # the next spans contain our document data
            cell = row.find_element(
                By.XPATH, ".//span[contains(@class,'ibbr-table-cell')]"
            )
            # read status
            unread = "unread" in cell.get_attribute("class")
            # get fields inside cell
            spans = cell.find_elements(By.XPATH, ".//span")
            # date
            date = spans[0].get_attribute("textContent").strip()
            # category
            category = spans[2].get_attribute("textContent").strip()
            # subject
            subject = spans[3].get_attribute("textContent").strip()
            # download button
            download = row.find_element(By.XPATH, ".//a[contains(text(),'Download')]")
            url = download.get_attribute("href")
            # create document
            yield docdl.Document(
                url=url,
                attributes={
                    "date": docdl.util.parse_date(date),
                    "category": category,
                    "subject": subject,
                    "unread": unread,
                },
            )


@click.command()
@click.pass_context
# pylint: disable=W0613
def ing(ctx, *args, **kwargs):
    """banking.ing.de with photoTAN (postbox)"""
    docdl.cli.run(ctx, ING)
