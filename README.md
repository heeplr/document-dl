
----
# command line document download made easy
----

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
  * dkb.de
  * o2.de
  * kabel.vodafone.de
  * conrad.de
  * elster.de


<br><br>
## Dependencies
* [python](https://python.org)
* [click](https://github.com/pallets/click)
* [click-plugins](https://github.com/click-contrib/click-plugins)
* [watchdog](https://github.com/gorakhargosh/watchdog)
* [jq](https://github.com/mwilliamson/jq.py)
* [python-dateutil](https://dateutil.readthedocs.io/en/stable/)
* [requests](https://docs.python-requests.org/en/master/)
* [selenium](https://selenium-python.readthedocs.io/) (default webdriver is "chrome")

<br><br>
## Installation
```sh
$ git clone --recursive https://github.com/heeplr/document-dl
$ cd document-dl
$ pip install .
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
                                  DOCDL_MATCH]
  -r, --regex <ATTRIBUTE REGEX>...
                                  only output documents where attribute value
                                  matches regex  [env var: DOCDL_REGEX]
  -j, --jq JQ_EXPRESSION          only output documents if json query matches
                                  document's attributes (see
                                  https://stedolan.github.io/jq/manual/ )
                                  [env var: DOCDL_JQ]
  -H, --headless BOOLEAN          show browser window if false  [env var:
                                  DOCDL_HEADLESS;default: True]
  -b, --browser [chrome|edge|firefox|ie|opera|safari|webkitgtk]
                                  webdriver to use for selenium based plugins
                                  [env var: DOCDL_BROWSER;default: chrome]
  -t, --timeout INTEGER           seconds to wait for data before terminating
                                  connection  [env var: DOCDL_TIMEOUT;default:
                                  15]
  -i, --image-loading BOOLEAN     Turn off image loading when False  [env var:
                                  DOCDL_IMAGE_LOADING;default: False]
  -a, --action [download|list]    download or just list documents  [env var:
                                  DOCDL_ACTION;default: list]
  -f, --format [list|dicts]       choose between line buffered output of json
                                  dicts or one json list  [env var:
                                  DOCDL_FORMAT;default: dicts]
  -h, --help                      Show this message and exit.

Commands:
  amazon    Amazon (invoices)
  conrad    conrad.de (invoices)
  dkb       dkb.de with chipTAN QR (postbox)
  elster    elster.de with path to .pfx certfile as username (postbox)
  ing       banking.ing.de with photoTAN (postbox)
  o2        o2online.de (invoices/postbox)
  vodafone  kabel.vodafone.de (postbox, invoices)
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
$ document-dl --headless=false vodafone
```

Download all documents from conrad.de, pass credentials as commandline arguments:
```sh
$ document-dl --username mylogin --password mypass --action download conrad
```

Download all documents from conrad.de, pass credentials as env vars:
```sh
$ DOCDL_USERNAME='mylogin' DOCDL_PASSWORD='mypass' document-dl --action download conrad
```

Download all documents from o2online.de where "doctype" attribute contains "BILL":
```sh
$ document-dl --match doctype BILL --action download o2
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


<br><br>
## Writing a plugin

Plugins are [click-plugins](https://github.com/click-contrib/click-plugins) which
in turn are normal @click.command's registered in setup.py

* put your plugin into *"docdl/plugins"*

* write your plugin class:
  * if you just need requests, inherit from ```docdl.WebPortal``` and use
    ```self.session``` that's initialized for you
  * if you need selenium, inherit from ```docdl.SeleniumWebPortal``` and use
    ```self.webdriver``` that's initialized for you
  * add click glue code
  * add your plugin to setup.py docdl_plugins registry

```python
import docdl
import docdl.util

class MyPlugin(docdl.WebPortal):

    URL_LOGIN = "https://myservice.com/login"

    def login(self):
        request = self.session.get(self.URL_LOGIN)
        # ... authenticate ...
        if not_logged_in:
            return False
        return True

    def logout(self):
        # ... logout ...

    def documents(self):
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

and in setup.py:

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
## Security
Beware that your login credentials are most probably saved in your shell
history when you pass them as commandline arguments.
You can use the input prompt to avoid that or set environment variables
safely.


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
