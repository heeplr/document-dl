"""download documents from o2online.de"""

import itertools
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import docdl


class O2online_DE(docdl.SeleniumWebPortal):

    URL_LOGIN="https://login.o2online.de/auth/login"
    URL_LOGOUT="https://login.o2online.de/auth/logout"
    URL_MY_MESSAGES="https://www.o2online.de/ecareng/my-messages"
    URL_INVOICES="https://www.o2online.de/vt-billing/api/invoiceinfo"
    URL_INVOICE="https://www.o2online.de/vt-billing/api/billdocument"
    URL_INVOICE_OVERVIEW="https://www.o2online.de/vt-billing/api/invoiceoverview"
    URL_VALUE_ADDED_INVOICE="https://www.o2online.de/vt-billing/api/value-added-services-invoices"

    def login(self):
        """authenticate"""
        self.webdriver.get(self.URL_LOGIN)
        # find entry field
        username = self.webdriver.find_element(
            By.XPATH,
            "//input[@name='IDToken1']"
        )
        # wait for entry field
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of(username)
        )
        # send username
        username.send_keys(self.login_id)
        username.submit()
        # find entry field
        password = self.webdriver.find_element(
            By.XPATH,
            "//input[@name='IDToken1']"
        )
        # wait for entry field
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            EC.visibility_of(password)
        )
        password.send_keys(self.password)
        password.submit()


    def is_logged_in(self):
        """return True if logged in successfully, False otherwise"""
        # wait for either login success or failure
        WebDriverWait(self.webdriver, self.TIMEOUT).until(
            lambda d: "Mein o2" in d.title or "Login" in d.title
        )
        # Login failed
        if "Login" in self.webdriver.title:
            return False
        # copy cookies to requests session
        self.copy_to_requests_session()
        return True

    def logout(self):
        self.webdriver.get(self.URL_LOGOUT)

    def documents(self):
        """fetch list of documents"""
        for n, d in enumerate(
            itertools.chain(self.invoices(), self.invoice_overview())
        ):
            # set an id
            d.attributes['id'] = n
            # return document
            yield d

    def invoice_overview(self):
        """fetch invoice overview"""
        r = self.session.get(self.URL_INVOICE_OVERVIEW)
        invoiceoverview = r.json()
        years = invoiceoverview['invoices'].keys()
        for year in years:
            yield docdl.Document(
                url=f"{self.URL_INVOICE_OVERVIEW}?statementYear={year}",
                request_headers={ "Accept": "application/pdf" },
                attributes={
                    'category': "invoice_overview",
                    'year': year,
                    'filename': f"o2-{year}-rechnungsübersicht.pdf"
                }
            )

    def invoices(self):
        """fetch list of invoices"""
        # fetch normal invoices
        r = self.session.get(self.URL_INVOICES)
        for d in self.parse_invoices_json(r.json()):
            d.attributes['category'] = "invoice"
            yield d
        # fetch value added invoices
        r = self.session.get(self.URL_VALUE_ADDED_INVOICE)
        for d in self.parse_invoices_json(r.json()):
            d.attributes['category'] = "value_added_invoice"
            yield d

    def parse_invoices_json(self, invoices):
        """parse all documents in invoiceinfo json"""
        # iterate all invoices
        for invoice in invoices['invoices']:
            year = invoice['date'][0]
            month = invoice['date'][1]
            day = invoice['date'][2]
            amount = invoice['total']['amount']
            # ~ currency = invoice['total']['currency']
            # collect attributes
            attributes = {
                'amount': f"{amount}",
                'date': f"{year}-{month}-{day}"
            }
            # iterate documents in this invoice
            for d in invoice['billDocuments']:
                yield docdl.Document(
                    url=f"{self.URL_INVOICE}?" \
                        f"billNumber={d['billNumber']}&" \
                        f"documentType={d['documentType']}",
                    attributes={
                        **attributes,
                        'number': d['billNumber'],
                        'doctype': d['documentType'],
                        'filename': f"o2-{year}-{month}-{day}-{d['documentType'].lower()}.pdf"
                    }
                )
