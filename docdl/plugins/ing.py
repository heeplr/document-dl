"""download documents from ing.de"""

import click
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import docdl



class ING(docdl.SeleniumWebPortal):
    """download documents from ing.de"""

    URL_LOGIN = "https://banking.ing.de"
    URL_LOGOUT = "https://banking.ing.de/app/logout"
    URL_POSTBOX = "https://banking.ing.de/app/postbox"

    def login(self):
        # load login page
        self.webdriver.get(self.URL_LOGIN)
        # wait for cookie accept button
        cookie_button = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located((
                By.XPATH, "//button[contains(text(), 'Annehmen')]"
            ))
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
        # get DiBa Key digits
        digits = self.webdriver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'diba-keypad')]/"
            "div[contains(@class, 'notification')]/"
            "p[@role='heading']/b/span"
        )
        digits = [ e.get_attribute('textContent').strip() for e in digits ]
        # click numbers on keypad
        for digit in digits:
            number = self.arguments['diba_key'][int(digit)-1]
            self.webdriver.find_element_by_link_text(number).click()
        # get "next" button
        nextbutton = self.webdriver.find_element(
            By.XPATH, "//button[@name='buttons:next']"
        )
        nextbutton.click()
        # wait for photoTAN
        qrcode = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located((
                By.CSS_SELECTOR, "img.thumbnail__image"
            ))
        )
        # handle photoTAN
        tan_entry = self.webdriver.find_element(
            By.CSS_SELECTOR, "input.input-field"
        )
        self.captcha(qrcode, tan_entry, "please enter photoTAN: ")
        # submit photoTAN
        nextbutton = self.webdriver.find_element(
            By.XPATH, "//button[@name='buttons:next']"
        )
        nextbutton.click()
        # wait for logout button (success) or tan input (failure)
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            lambda d:
                d.find_elements(
                    By.XPATH, "//a[@aria-label='Logout']"
                ) or \
                d.find_elements(
                    By.CSS_SELECTOR, "input.input-field"
                )
        )
        # login successful ?
        return self.webdriver.find_elements(
            By.XPATH, "//a[@aria-label='Logout']"
        )

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        # open postbox
        self.webdriver.get(self.URL_POSTBOX)
        # wait for table
        table = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located((
                By.CSS_SELECTOR, "div.ibbr-table"
            ))
        )
        # iterate rows
        for i, row in enumerate(table.find_elements(
            By.CSS_SELECTOR, "div.ibbr-table-row"
        )):
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
            download = row.find_element(
                By.XPATH, ".//a[contains(text(),'Download')]"
            )
            url = download.get_attribute("href")

            # create document
            yield docdl.Document(
                url = url,
                attributes = {
                    'date': self.parse_date(date),
                    'category': category,
                    'subject': subject,
                    'unread': unread,
                    'id': i
                }
            )

@click.command()
@click.option(
    "-k",
    "--diba-key",
    prompt=True,
    hide_input=True,
    envvar="DOCDL_DIBA_KEY",
    show_envvar=True,
    help="DiBa Key"
)
@click.pass_context
# pylint: disable=W0613
def ing(ctx, *args, **kwargs):
    """banking.ing.de with photoTAN (postbox)"""
    docdl.cli.run(ctx, ING)
