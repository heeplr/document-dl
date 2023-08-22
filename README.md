
----
# command line document download made easy
[![Pylint](https://github.com/heeplr/document-dl/actions/workflows/pylint.yml/badge.svg)](https://github.com/heeplr/document-dl/actions/workflows/pylint.yml)
[![flake8](https://github.com/heeplr/document-dl/actions/workflows/flake8.yml/badge.svg)](https://github.com/heeplr/document-dl/actions/workflows/flake8.yml)
----

Like [youtube-dl](https://youtube-dl.org/) can download videos from various
websites, document-dl can download documents like invoices, messages, reports, etc.

It can save you from regularly logging into your account to download new
documents.

Websites that don't require any form of 2FA can be polled without interaction
regularly using a cron job so documents are downloaded automatically.

<br>

## Highlights

* list available documents in json format or download them
* filter documents using
  * **string matching**
  * **regular expressions** or
  * **[jq queries](https://stedolan.github.io/jq/manual/)**
* display captcha or QR codes for interactive input
* writing new plugins is easy
* existing plugins (some of them even work):
  * amazon
  * ing.de
  * handyvertrag.de
  * dkb.de
  * o2.de
  * www.vodafone.de
  * conrad.de
  * elster.de
  * strato.de


<br><br>
## Dependencies
* [python](https://python.org)
* [click](https://github.com/pallets/click)
* [click-plugins](https://github.com/click-contrib/click-plugins)
* [jq](https://github.com/mwilliamson/jq.py)
* [python-dateutil](https://dateutil.readthedocs.io/en/stable/)
* [requests](https://docs.python-requests.org/en/master/)
* [selenium](https://selenium-python.readthedocs.io/) (default webdriver is "chrome")
* [slugify](https://github.com/un33k/python-slugify)
* [watchdog](https://github.com/gorakhargosh/watchdog)

<br><br>
## Installation (for debian bullseye)

```sh
$ apt install git python3-dev python3-pip python3-selenium chromium-chromedriver
$ pip3 install --user git+https://github.com/heeplr/document-dl.git
```

or for developers:

```sh
$ git clone --recursive https://github.com/heeplr/document-dl
$ cd document-dl
$ pip install --user --editable .
```

<br><br>
## Usage

Display Help:

```sh
$ document-dl -h
Usage: document-dl [OPTIONS] COMMAND [ARGS]...

  download documents from web portals

Options:
  -u, --username TEXT             login id  [env var: DOCDL_USERNAME]
  -p, --password TEXT             secret password  [env var: DOCDL_PASSWORD]
  -m, --match <ATTRIBUTE PATTERN>...
                                  only output documents where attribute
                                  contains pattern string  [env var:
                                  DOCDL_STRING_MATCHES]
  -r, --regex <ATTRIBUTE REGEX>...
                                  only output documents where attribute value
                                  matches regex  [env var:
                                  DOCDL_REGEX_MATCHES]
  -j, --jq JQ_EXPRESSION          only output documents if json query matches
                                  document's attributes (see
                                  https://stedolan.github.io/jq/manual/ )
                                  [env var: DOCDL_JQ_MATCHES]
  -H, --headless / --show         show/hide browser window  [env var:
                                  DOCDL_HEADLESS; default: headless]
  -b, --browser [chrome|edge|firefox|ie|safari|webkitgtk]
                                  webdriver to use for selenium based plugins
                                  [env var: DOCDL_BROWSER; default: chrome]
  -t, --timeout INTEGER           seconds to wait for data before terminating
                                  connection  [env var: DOCDL_TIMEOUT;
                                  default: 25]
  -i, --image-loading BOOLEAN     Turn off image loading when False  [env var:
                                  DOCDL_IMAGE_LOADING; default: False]
  -l, --list                      list documents  [env var: DOCDL_ACTION;
                                  default: list]
  -d, --download                  download documents  [env var: DOCDL_ACTION;
                                  default: list]
  -f, --format [list|dicts]       choose between line buffered output of json
                                  dicts or single json list  [env var:
                                  DOCDL_OUTPUT_FORMAT; default: dicts]
  -D, --debug                     use selenium remote debugging on port 9222
                                  [env var: DOCDL_DEBUG]
  -h, --help                      Show this message and exit.

Commands:
  amazon        amazon.com (invoices)
  believe       believebackstage.com (financial reports + catalog export)
  conrad        conrad.de (invoices)
  dkb           dkb.de with chipTAN QR (postbox)
  elster        elster.de with path to .pfx certfile as username (postbox)
  handyvertrag  service.handyvertrag.de (invoices, call record)
  ing           banking.ing.de with photoTAN (postbox)
  o2            o2online.de (invoices, call record, postbox)
  strato        strato.de (invoices)
  vodafone      www.vodafone.de (invoices)
```

Display plugin-specific help:
(**currently there is a [bug in click](https://github.com/pallets/click/issues/1369)
that prompts for username and password before displaying the help**)

```
$ document-dl ing --help
Usage: document-dl ing [OPTIONS]

  banking.ing.de with photoTAN (postbox)

Options:
  -k, --diba-key TEXT  DiBa Key  [env var: DOCDL_DIBA_KEY]
  -h, --help           Show this message and exit.
```

<br><br>
## Examples

List all documents from vodafone.de, prompt for username/password:
```sh
$ document-dl vodafone
```

Same, but show browser window this time:
```sh
$ document-dl --show vodafone
```

Download all documents from conrad.de, pass credentials as commandline arguments:
```sh
$ document-dl --username mylogin --password mypass --action download conrad
```

Download all documents from conrad.de, pass credentials as env vars:
```sh
$ DOCDL_USERNAME='mylogin' DOCDL_PASSWORD='mypass' document-dl --action download conrad
```

Download all documents from o2online.de where "category" attribute contains "BILL":
```sh
$ document-dl --match category BILL --action download o2
```

You can also use regular expressions to filter documents:
```sh
$ document-dl --regex date '^(2021-04|2021-05).*$' o2
```

List all documents from o2online.de where year >= 2019:
```sh
$ document-dl --jq 'select(.year >= 2019)' o2
```

Download document from elster.de with id == 15:
```sh
$ document-dl --jq 'contains({id: 15})' --action download elster
```

You can create a config file ```.o2_documentdlrc``` like so:
```sh
DOCDL_PLUGIN="o2"
DOCDL_USERNAME="01771234567"
DOCDL_PASSWORD="super-secret-password"
DOCDL_ACTION="download"
DOCDL_DSTPATH="${HOME}/Documents/o2"
DOCDL_TIMEOUT="30"
```

then invoke document-dl in a script like so:

```sh
#!/bin/bash

CONFIG="${HOME}/.config/.o2_documentdlrc"

# load config
set -a
. "${CONFIG}" || error "parsing config ${CONFIG}"
set +a
# cd to target dir
cd "${DOCDL_DSTPATH}"
# download documents
/usr/bin/document-dl "${DOCDL_PLUGIN}"
```


<br><br>
## Security
BEWARE that your login credentials are most probably **saved in your shell
history when you pass them as commandline arguments**.
You can use the input prompt to avoid that or set environment variables
securely.
Make sure to set secure permissions when saving credentials on a trusted system (e.g. ```chmod 0600 <file>```)

<br><br>
## Writing a plugin

Plugins are [click-plugins](https://github.com/click-contrib/click-plugins) which
in turn are normal @click.command's that are registered in setup.py

Roughly, you have to:

* put your plugin into *"docdl/plugins/myplugin.py"*
* write your plugin class, e.g. MyPlugin():
  * if you just need python requests, inherit from ```docdl.WebPortal``` and use
    ```self.session``` that's initialized for you
  * if you need selenium, inherit from ```docdl.SeleniumWebPortal``` and use
    ```self.webdriver``` that's initialized for you
  * add a
    * login() method,
    * logout() method and
    * documents() generator that yields ```docdl.Document()``` instances
    * optional: download() method if you need to do more fancy stuff than downloading an URLs and saving it to a file
* add click glue code
* add your plugin to setup.py docdl_plugins registry

Checkout other plugins as example.

### requests plugin example

```python
import docdl
import docdl.util

class MyPlugin(docdl.WebPortal):

    URL_LOGIN = "https://myservice.com/login"
    URL_LOGOUT = "https://myservice.com/logout"

    def login(self):
        # maybe load some session cookie
        request = self.session.get(self.URL_LOGIN)
        # authenticate
        request = self.session.post(
            self.URL_LOGIN,
            data={ 'username': self.username, 'password': self.password }
        )
        # return false if login failed, true otherwise
        if not request.ok:
            return False
        return True

    def logout(self):
        request = self.session.get(self.URL_LOGOUT)

    def documents(self):
        # acquire list of documents
        # ...

        # iterate over all available documents
        for count, document in enumerate(all_documents):

            # scrape:
            #  * document attributes
            #    * it's recommended to assign an incremental "id"
            #      attribute to every document
            #    * if you set a "filename" attribute, it will be used to
            #      rename the downloaded file
            #    * dates should be parsed to datetime.datetime objects
            #      docdl.util.parse_date() should parse the most common strings
            #
            # also you must scrape either:
            #  * the download URL
            #
            # or (for SeleniumWebPortal plugins):
            #  * the DOM element that triggers download. It is expected
            #    that the download starts immediately after click() on
            #    the DOM element
            # or implement a custom download() method

            yield docdl.Document(
                url = this_documents_url,
                # download_element = <some selenium element to click>
                attributes = {
                    "id": count,
                    "category": "invoices",
                    "title": this_documents_title,
                    "filename": this_documents_target_filename,
                    "date": docdl.util.parse_date(some_date_string)
                }
            )


    def download(self, document):
        """you shouldn't need this for most web portals"""
        # ... save file to os.getcwd() ...
        return self.rename_after_download(document, filename)


@click.command()
@click.pass_context
def myplugin(ctx):
    """plugin description (what, documents, are, scraped)"""
    docdl.cli.run(ctx, MyPlugin)

```

### selenium plugin example

TBD


### register plugin

...in setup.py:

```
# ...
setup(
    # ...
    packages=find_packages(
        # ...
        entry_points={
            'docdl_plugins': [
                # ...
                'myplugin=docdl.plugins.myplugin:myplugin',
                # ...
            ],
            # ...
        }
)
```


<br><br>
## Bugs
document-dl is still in a very early state of development and a lot of
things don't work, yet. Especially a ton of edge cases need to be
covered.
If you find a bug, please [open an issue](https://github.com/heeplr/document-dl/issues)
or send a pull request.

* --browser settings beside **chrome** probably don't work unless you help to test them
* some services offer more documents/data than currently scraped


<br><br>
## TODO
* logging
* better documentation
* properly parse rfc6266
* delete action
