"""download documents from amazon.de"""

import re
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

import docdl


class Amazon(docdl.SeleniumWebPortal):
    """
    download documents from amazon.de
    note: you will probably need to enter a captcha when in headless mode
    """

    URL_BASE="https://amazon.de"
    URL_LOGOUT="https://www.amazon.de/gp/flex/sign-out.html"
    URL_ORDERS="https://www.amazon.de/gp/your-account/order-history"

    def login(self):
        # load homepage
        self.webdriver.get(self.URL_BASE)
        # wait for account-link or captcha request
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((
                By.XPATH, "//a[@id='nav-link-accountList'] | //input[@id='captchacharacters']"
            ))
        )
        # captcha entry ?
        captcha_entry = self.webdriver.find_elements(
            By.XPATH, "//input[@id='captchacharacters']"
        )
        if captcha_entry:
            # find_elements returns list
            captcha_entry = captcha_entry[0]
            # take screenshot
            self.webdriver.get_screenshot_as_file("screenshot.png")
            print(f"captcha saved to \"{os.path.join(os.getcwd(), 'screenshot.png')}\" ...")
            captcha = input("please enter captcha: ")
            captcha_entry.send_keys(captcha)
            captcha_entry.submit()

        # get loginbutton
        loginbutton = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((
                By.XPATH, "//a[@id='nav-link-accountList'] | //a[@data-nav-role='signin']"
            ))
        )
        # click "login"
        loginbutton.click()
        # wait for email page
        email = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, "input#ap_email"
            ))
        )
        # send username
        email.send_keys(self.login_id)
        email.submit()
        # wait for password page
        password = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, "input#ap_password"
            ))
        )
        # send password
        password.send_keys(self.password)
        password.submit()
        # wait for either login success or failure
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            lambda d: "Anmelden" in d.title or \
                      "Amazon.de" in d.title
        )
        # Login failed
        if "Anmelden" in self.webdriver.title:
            return False
        return True

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        # count all documents
        count = 0
        # load page with orders
        self.webdriver.get(self.URL_ORDERS)

        orderfilter = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, "select#orderFilter"
            ))
        )
        # extract values of year options
        options = [
            o.get_attribute("value") for o in orderfilter.find_elements(
                By.XPATH, ".//option[contains(@value, 'year')]"
            )
        ]
        # add "archived" option
        options += [ "archived" ]

        # collect all "order-details" links
        order_detail_links = []
        # iterate all years + archived orders
        for option in options:
            # go back to order overview except if we already are on
            # the overview page
            if "order-details" in self.webdriver.current_url:
                self.webdriver.back()
            # find <select> for order filter
            orderfilter = WebDriverWait(self.webdriver, self.TIMEOUT).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, "select#orderFilter"
                ))
            )
            orderfilter_select = Select(orderfilter)
            orderfilter_select.select_by_value(option)

            # scroll down to load all orders
            while True:
                # get current height
                height = self.webdriver.execute_script(
                    "return document.documentElement.scrollHeight"
                )
                # scroll to bottom
                self.webdriver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                # wait for loader to disappear
                WebDriverWait(self.webdriver, self.TIMEOUT).until(
                    EC.invisibility_of_element_located((
                        By.CSS_SELECTOR, ".rhf-loading-inner"
                    ))
                )
                # loop until height doesn't change
                if height != self.webdriver.execute_script(
                    "return document.documentElement.scrollHeight"
                ):
                    break

            # append links
            order_detail_links = [
                e.get_attribute("href") for e in self.webdriver.find_elements(
                    By.XPATH, "//a[contains(@href, 'order-details')]"
                )
            ]

            # iterate order-detail pages
            for order_link in order_detail_links:
                # go back to order overview except if we already are on
                # the overview page
                if "order-details" in self.webdriver.current_url:
                    self.webdriver.back()
                # load order details page
                self.webdriver.get(order_link)
                # wait for invoice links or alert
                WebDriverWait(self.webdriver, self.TIMEOUT).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, ".order-date-invoice-item,.a-alert-container"
                    ))
                )
                # alert visible?
                alert = self.webdriver.find_elements(By.CSS_SELECTOR, ".a-alert-container")
                if alert and alert[0].is_displayed():
                    # skip
                    continue
                # get all invoice urls
                invoice_urls = self.webdriver.find_elements(
                    By.XPATH, "//a[contains(@href, '.pdf')]"
                )
                invoice_urls = set(
                    e.get_attribute("href") for e in invoice_urls
                )
                # some orders don't have invoices
                if len(invoice_urls) == 0:
                    # skip this order
                    continue
                # extract items that contain order number and order date
                date_nr = self.webdriver.find_elements(
                    By.CSS_SELECTOR, "span.order-date-invoice-item"
                )
                date = date_nr[0].get_attribute("textContent").strip()
                nr = date_nr[1].get_attribute("textContent").strip()
                # parse date
                date = re.match(r"[^\d]*(.+)$", date)[1]
                # parse order number
                nr = re.match(r"[^\d]*(.+)$", nr)[1]

                # generate invoices
                for url in invoice_urls:
                    yield docdl.Document(
                        url=url,
                        attributes={
                            'date': self.parse_date(date),
                            'nr': nr,
                            'id': count,
                            'filename': f"amazon-invoice-{nr}.pdf"
                        }
                    )
                    # increment counter
                    count += 1
