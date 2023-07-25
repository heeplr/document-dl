"""download documents from believebackstage.com"""

import itertools
import click
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import docdl


class BelieveBackstage(docdl.SeleniumWebPortal):
    """download documents from believebackstage.com"""

    URL_ROOT = "https://believebackstage.com"
    URL_LOGOUT = f"{URL_ROOT}/?logout=1"
    URL_REPORTS = f"{URL_ROOT}/royalties/reportmanager"

    def login(self):
        """authenticate with username + password"""
        # load login page
        self.webdriver.get(self.URL_ROOT)
        # wait for page to load
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@id='signInName']"))
        )
        # wait form to become interactive
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='signInName']"))
        )
        # find input fields
        username = self.webdriver.find_element(By.XPATH, "//input[@id='signInName']")
        password = self.webdriver.find_element(By.XPATH, "//input[@id='password']")
        # move mouse over username input
        ActionChains(self.webdriver).move_to_element(username).perform()
        # fill in form
        username.send_keys(self.login_id)
        password.send_keys(self.password)

        # click login button
        loginbutton = self.webdriver.find_element(By.XPATH, "//button[@id='next']")
        # move mouse over login button
        ActionChains(self.webdriver).move_to_element(loginbutton).perform()
        password.submit()
        loginbutton.click()
        loginbutton.click()

        # wait for either login error message box or success message
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//p[contains(text(),'The username or password provided "
                    "in the request are invalid')] | "
                    "//*[contains(text(), 'Kundennummer')]",
                )
            )
        )
        # login successful
        return self.webdriver.find_element(
            By.XPATH, "//*[contains(text(), 'Kundennummer')]"
        )

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        return itertools.chain(self.financial_reports(), self.catalog())

    def catalog(self):
        """catalog CSV export"""
        yield docdl.Document(
            url="https://believebackstage.com/catalog/manager/catalogExport",
            attributes={"id": "catalog", "category": "catalog export"},
        )

    def financial_reports(self):
        """quarterly/monthly financial reports"""
        # fetch report overview
        self.webdriver.get(self.URL_REPORTS)
        # wait for modal
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(@class,'modal-footer')]/a[@data-dismiss='modal']",
                )
            )
        )
        # close modal
        closebutton = self.webdriver.find_element(
            By.XPATH, "//div[contains(@class,'modal-footer')]/a[@data-dismiss='modal']"
        )
        if closebutton.is_displayed():
            closebutton.click()
        # wait for a download button
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//a[contains(@class, 'fa-download')]")
            )
        )

        # walk all pages
        while True:
            # get table
            tbody = self.webdriver.find_element(
                By.XPATH, "//table[contains(@class,'table')]"
            ).find_element(By.XPATH, ".//tbody")
            # iterate all rows
            for row in tbody.find_elements(By.XPATH, ".//tr"):
                elements = list(row.find_elements(By.XPATH, ".//td"))
                ident = elements[0].text
                report_type = elements[1].text
                amount = elements[2].text
                date = elements[3].text.replace("\n", " ")
                url = (
                    elements[5]
                    .find_element(By.XPATH, ".//a[contains(@class, 'fa-download')]")
                    .get_attribute("href")
                )

                yield docdl.Document(
                    url=url,
                    attributes={
                        "date": docdl.util.parse_date(date),
                        "category": report_type,
                        "id": ident,
                        "amount": amount,
                    },
                )

            # next page
            pagination = self.webdriver.find_element(
                By.XPATH, "//ul[contains(@class,'pagination')]"
            )
            nextbutton = pagination.find_elements(
                By.XPATH, ".//li[contains(@class, 'active')]/following-sibling::li/a"
            )
            # last page
            if not nextbutton:
                break
            # go to next page
            nextbutton[0].click()
            # wait until we become stale (page loaded then)
            WebDriverWait(self.webdriver, self.TIMEOUT).until(
                EC.staleness_of(nextbutton[0])
            )


@click.command()
@click.pass_context
# pylint: disable=W0613
def believe(ctx, *args, **kwargs):
    """believebackstage.com (financial reports + catalog export)"""
    docdl.cli.run(ctx, BelieveBackstage)
