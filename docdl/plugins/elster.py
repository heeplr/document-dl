"""download documents from elster.de using certificate file + password"""

import docdl
import re
import requests
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



class Elster(docdl.SeleniumWebPortal):
    """login_id must be the path to the .pfx file"""

    URL_LOGIN="https://www.elster.de/eportal/login"
    URL_LOGOUT="https://www.elster.de/eportal/logout"
    URL_INBOX="https://www.elster.de/eportal/meinelster/meinposteingang"

    def login(self):
        """authenticate using certfile + password"""
        self.webdriver.get(self.URL_LOGIN)
        # find input fields
        certfile = self.webdriver.find_element(
            By.XPATH, "//input[@id='loginBox.file_cert']"
        )
        password = self.webdriver.find_element(
            By.XPATH, "//input[@id='password']"
        )
        # wait for entry field
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of(password)
        )
        # fill in form
        certfile.send_keys(self.login_id)
        password.send_keys(self.password)
        # click login button
        loginbutton = self.webdriver.find_element(
            By.XPATH, "//button[@title='Login']"
        )
        loginbutton.click()

    def is_logged_in(self):
        """return True if logged in successfully, False otherwise"""
        # wait for either login error message box or success message
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located((
                By.XPATH, "//div[contains(@class,'messageBox--error')] | //*[contains(text(), 'Erfolgreich eingeloggt')]"
            ))
            # ~ lambda d: d.find_element(By.CSS_SELECTOR, "div.messageBox--error").is_displayed() or \
                      # ~ d.find_element(By.XPATH, "//*[contains(text(), 'Erfolgreich eingeloggt')]").is_displayed()
        )
        # login successful
        if "Mein ELSTER" in self.webdriver.title:
            return True
        # login failed
        return False

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        # fetch inbox
        self.webdriver.get(self.URL_INBOX)
        # count all extracted documents
        n = 0
        # iterate all pages
        while True:
            # count elements on this page
            n_page = 0
            # iterate all rows of table
            while True:
                # wait for table
                posteingang = WebDriverWait(self.webdriver, self.TIMEOUT).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, "#posteingangModel tbody"
                    ))
                )
                # find all rows on this page
                rows = posteingang.find_elements(By.CSS_SELECTOR, "tr")
                # last row?
                if n_page >= len(rows):
                    # done
                    break
                # get current row
                row = rows[n_page]
                # get columns
                downloadbutton = WebDriverWait(row, self.TIMEOUT).until(
                    EC.presence_of_element_located((
                        By.XPATH, ".//td[@data-rwd='Betreff']/*/button"
                    ))
                )
                betreff = downloadbutton \
                            .get_attribute("textContent") \
                            .strip()

                ordnungskriterium = row.find_element(
                    By.XPATH, ".//td[@data-rwd='Ordnungskriterium']"
                ).get_attribute("textContent").strip()

                profil = row.find_element(
                    By.XPATH, ".//td[@data-rwd='Profil']"
                ).get_attribute("textContent").strip()

                absender = row.find_element(
                    By.XPATH, ".//td[@data-rwd='Absender']"
                ).get_attribute("textContent").strip()

                datum = row.find_element(
                    By.XPATH, ".//td[@data-rwd='Datum']"
                ).get_attribute("textContent").strip()
                datum = re.sub(r"[\n\r\t]+", " ", datum)

                yield docdl.Document(
                    download_element = downloadbutton,
                    attributes = {
                        'betreff': betreff,
                        'ordnungskriterium': ordnungskriterium,
                        'profil': profil,
                        'absender': absender,
                        'datum': datum,
                        'id': n
                    }
                )
                # increase counter
                n += 1
                n_page += 1

            # last page?
            next_button = self.webdriver.find_element(
                By.ID,
                "MeinPosteingangTable_pagination_next_page"
            )
            if not next_button.is_enabled():
                # quit
                break
            else:
                # load next page
                next_button.click()

    def download(self, document):
        """
        custom download function since ELSTER needs the cert password
        for every document
        """
        # click to open download dialog
        document.download_element.click()
        # wait for "save as PDF" button
        savebutton = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located((
                By.XPATH, "//button[@id='alsPDFSpeichern']"
            ))
        )
        # click savebutton
        savebutton.click()
        # wait for password dialog
        password = WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of_element_located((
                By.XPATH, "//input[@id='passwortEingeben']"
            ))
        )
        # enter password
        password.send_keys(self.password)
        # get new save button
        savebutton = self.webdriver.find_element(
            By.XPATH, "//button[@id='openButton']"
        )
        # store "save" button as new download_element
        document.download_element = savebutton
        # download file
        super(Elster, self).download(document)
        try:
            # try to get button to close dialog
            # (that sometimes disappears on itself)
            closebutton = self.webdriver.find_element(
                By.XPATH, "//a[@id='closeButton_modal.message']"
            )
            # close dialog
            closebutton.click()
        except NoSuchElementException:
            pass

