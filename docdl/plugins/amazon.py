"""
download documents from Amazon

@todo handle "add mobile phone number?" dialog after login
"""

import re
import click
from slugify import slugify
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

import docdl
import docdl.util


class Amazon(docdl.SeleniumWebPortal):
    """
    download documents from Amazon
    note: you will probably need to enter a captcha when in headless
          mode for the first times. For me it went away after some
          runs.
    """

    def login(self):
        # use this toplevel domain
        tld = self.arguments["tld"]
        # load homepage
        self.webdriver.get(f"https://amazon.{tld}")
        # wait for account-link or captcha request
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//a[@id='nav-link-accountList'] | "
                    "//input[@id='captchacharacters']",
                )
            )
        )
        # captcha entry ?
        if captcha_entry := self.webdriver.find_elements(
            By.XPATH, "//input[@id='captchacharacters']"
        ):
            self._handle_captcha(captcha_entry)

        # get loginbutton
        loginbutton = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//a[@id='nav-link-accountList'] | //a[@data-nav-role='signin']",
                )
            )
        )
        # click "login"
        loginbutton.click()
        # handle username dialog
        self._send_username()
        # wait for password entry or error
        if not self._wait_for_result(
            By.CSS_SELECTOR,
            "input#ap_password",
            By.CSS_SELECTOR,
            "div#auth-error-message-box",
        ):
            return False
        # handle password dialog
        self._send_password()
        # wait for signout link or error
        if not self._wait_for_result(
            By.CSS_SELECTOR,
            "a#nav-item-signout",
            By.CSS_SELECTOR,
            "div#auth-error-message-box",
        ):
            # mobile phone entry?
            if skipbutton := self.webdriver.find_elements(
                By.CSS_SELECTOR, "a#ap-account-fixup-phone-skip-link"
            ):
                skipbutton.click()
                # wait for signout link or error
                if not self._wait_for_result(
                    By.CSS_SELECTOR,
                    "a#nav-item-signout",
                    By.CSS_SELECTOR,
                    "div#auth-error-message-box",
                ):
                    return False
            # no mobile phone entry
            else:
                return False
        return True

    def logout(self):
        tld = self.arguments["tld"]
        self.webdriver.get(f"https://www.amazon.{tld}/gp/flex/sign-out.html")

    def documents(self):
        # count all documents
        i = 0
        # use this toplevel domain
        tld = self.arguments["tld"]
        # load page with orders
        self.webdriver.get(f"https://www.amazon.{tld}/gp/your-account/order-history")
        # get options from orderfilter so we get all available invoices
        options = self._orderfilter_options()
        # iterate all years (+ archived orders)
        limit_year = self.arguments["limit_year"]
        for option in options:
            # skip years in limited mode
            if limit_year and option != f"year-{limit_year}":
                # debug(f"skipping option {option} due to limit_year set
                # to {limit_year}")
                continue
            # go back to order overview except if we already are on
            # the overview page
            if "order-details" in self.webdriver.current_url:
                self.webdriver.back()
            # select current orderfilter option
            self._set_orderfilter(option)
            # scroll down to load all orders
            self._load_all_orders()
            # save all order detail links
            order_detail_links = [
                e.get_attribute("href")
                for e in self.webdriver.find_elements(
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
                if not self._wait_for_result(
                    By.CSS_SELECTOR,
                    ".order-date-invoice-item",
                    By.CSS_SELECTOR,
                    ".a-alert-container",
                ):
                    # skip on alert
                    continue
                # get all invoice urls
                invoice_urls = self.webdriver.find_elements(
                    By.XPATH, "//a[contains(@href, '.pdf')]"
                )
                # remove doubles
                invoice_urls = set(e.get_attribute("href") for e in invoice_urls)
                # extract items that contain order number and order date
                date_nr = self.webdriver.find_elements(
                    By.CSS_SELECTOR, "span.order-date-invoice-item"
                )
                date = date_nr[0].get_attribute("textContent").strip()
                order_nr = date_nr[1].get_attribute("textContent").strip()
                # parse date
                date = re.match(r"[^\d]*(.+)$", date)[1]
                date = docdl.util.parse_date(date)
                # parse order number
                order_nr = re.match(r"[^\d]*(.+)$", order_nr)[1]
                # get product name
                product_name = (
                    self.webdriver.find_element(
                        By.XPATH,
                        "//div[@class='a-row']/a[contains(@href, '/product/')]",
                    )
                    .get_attribute("textContent")
                    .strip()
                )
                # some orders don't have invoices
                if len(invoice_urls) == 0:
                    # generate empty entry with warning
                    yield docdl.Document(
                        url=None,
                        attributes={
                            "date": date,
                            "order": order_nr,
                            "id": i,
                            "product": product_name,
                            "warning": "no invoice available!",
                        },
                    )
                    continue

                # generate invoices
                for url in invoice_urls:
                    filename = (
                        f"amazon-{date.strftime('%Y%m%d')}-"
                        f"{order_nr}-{slugify(product_name)}.pdf"
                    )
                    yield docdl.Document(
                        url=url,
                        attributes={
                            "date": date,
                            "order": order_nr,
                            "id": i,
                            "product": product_name,
                            "filename": filename,
                        },
                    )
                    # increment counter
                    i += 1

    def _orderfilter_options(self):
        # wait for dropdown to select orders
        # (last months, years, archived)
        orderfilter = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, ".//select[@name='orderFilter']"))
        )
        # extract values of year options
        options = [
            o.get_attribute("value")
            for o in orderfilter.find_elements(
                By.XPATH, ".//option[contains(@value, 'year')]"
            )
        ]
        # got "archived" order filter option?
        if orderfilter.find_elements(
            By.XPATH, ".//option[contains(@value, 'archived')]"
        ):
            # add "archived" option
            options += ["archived"]
        return options

    def _set_orderfilter(self, option):
        # find <select> for order filter
        orderfilter = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, ".//select[@name='orderFilter']"))
        )
        # move <select> to front
        self.webdriver.execute_script("arguments[0].style.zIndex='99'", orderfilter)
        orderfilter = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, ".//select[@name='orderFilter']"))
        )
        # select current option
        orderfilter_select = Select(orderfilter)
        orderfilter_select.select_by_value(option)

    def _load_all_orders(self):
        # scroll down to load all orders
        while True:
            # get current height
            height = self.webdriver.execute_script(
                "return document.documentElement.scrollHeight"
            )
            # scroll to bottom
            self.scroll_to_bottom()
            # wait for loader to disappear
            WebDriverWait(self.webdriver, self.TIMEOUT).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, ".rhf-loading-inner")
                )
            )
            # loop until height doesn't change
            if height == self.webdriver.execute_script(
                "return document.documentElement.scrollHeight"
            ):
                break

    def _handle_captcha(self, captcha_entry):
        # find_elements returns list, we need
        # the last (and only) entry
        captcha_entry = captcha_entry[0]
        # get image
        captcha_img = self.webdriver.find_element(
            By.XPATH, "//img[contains(@src, 'captcha')]"
        )
        # handle captcha (@todo handle failure/wrong input)
        self.captcha(captcha_img, captcha_entry)
        # submit
        captcha_entry.submit()

    def _send_username(self):
        # wait for email page
        email = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input#ap_email"))
        )
        # send username
        email.send_keys(self.login_id)
        email.submit()

    def _send_password(self):
        # send password
        password = self.webdriver.find_element(By.CSS_SELECTOR, "input#ap_password")
        password.send_keys(self.password)
        password.submit()

    def _wait_for_result(self, success_by, success_selector, error_by, error_selector):
        # wait for success element or error dialog
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            lambda d: d.find_elements(success_by, success_selector)
            or d.find_elements(error_by, error_selector)
        )
        # error ?
        if self.webdriver.find_elements(error_by, error_selector):
            return False

        return True


@click.command()
@click.option(
    "-t",
    "--tld",
    default="de",
    show_default=True,
    show_envvar=True,
    help="toplevel domain to use",
)
@click.option(
    "-y",
    "--limit-year",
    type=int,
    show_envvar=True,
    default=None,
    help="limit handling to documents of the given year",
    show_default=True,
)
@click.pass_context
# pylint: disable=W0613
def amazon(ctx, *args, **kwargs):
    """amazon.com (invoices)"""
    docdl.cli.run(ctx, Amazon)
