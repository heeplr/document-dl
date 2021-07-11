
Plugin based command line utility to download documents from web portals.

List or download all kind of documents (invoices, notifications, ...) or
write your own scraping plugin.

Select specific documents using simple string search (**--filter**),
regular expressions (**--regex**) or [jq queries](https://stedolan.github.io/jq/manual/)
(**--jq**).


# Dependencies
* python
* click
* inotify
* jq
* python-dateutil
* selenium (default webdriver is "chrome")


# Installation
```
$ pip install .
```


# Usage

Display Help:

```
$ document-dl -h
Usage: document-dl [OPTIONS] COMMAND [ARGS]...

  download documents from web portals

Options:
  -u, --username TEXT             login id  [env var: DOCDL_USERNAME]
  -p, --password TEXT             secret password  [env var: DOCDL_PASSWORD]
  -P, --plugin TEXT               plugin name  [env var: DOCDL_PLUGIN;
                                  required]

  -a, --plugin-argument <KEY VALUE>...
                                  key/value argument passed to the plugin
                                  [env var: DOCDL_PLUGINARG]

  -m, --match <ATTRIBUTE PATTERN>...
                                  only process documents where attribute
                                  contains pattern string  [env var:
                                  DOCDL_MATCH]

  -r, --regex <ATTRIBUTE REGEX>...
                                  only process documents where attribute value
                                  matches regex  [env var: DOCDL_REGEX]

  -j, --jq JQ_EXPRESSION          process document only if json query matches
                                  document attributes (see
                                  https://stedolan.github.io/jq/manual/ )
                                  [env var: DOCDL_JQ]

  -H, --headless BOOLEAN          show browser window if false  [env var:
                                  DOCDL_HEADLESS; default: True]

  -b, --browser [chrome|edge|firefox|ie|opera|safari|webkitgtk]
                                  webdriver to use for selenium plugins  [env
                                  var: DOCDL_BROWSER; default: chrome]

  -t, --timeout INTEGER           seconds to wait for data before terminating
                                  connection  [env var: DOCDL_TIMEOUT;
                                  default: 15]

  -h, --help                      Show this message and exit.

Commands:
  download  download documents
  list      list documents
```


# Examples

List all documents from vodafone.de, prompt for username/password:
```
$ document-dl --plugin VodafoneKabel_DE download
```

Same, but show browser window this time:
```
$ document-dl --headless=false --plugin VodafoneKabel_DE download
```

Download all documents from conrad.de, pass credentials as commandline arguments:
```
$ document-dl --username mylogin --password mypass --plugin Conrad_DE download
```

Download all documents from conrad.de, pass credentials  env vars:
```
$ DOCDL_USERNAME="mylogin" DOCDL_PASSWORD="mypass" document-dl --plugin Conrad_DE download
```

Download all documents from o2online.de where "doctype" attribute contains "BILL":
```
$ document-dl --plugin O2online_DE --filter doctype BILL download
```

You can also use regular expressions to filter documents:
```
$ document-dl --plugin O2online_DE --regex date '^(2021-04|2021-05).*$'
```

List all documents from o2online.de where year >= 2019:
```
$ document-dl --plugin O2online_DE --jq 'select(.year >= 2020)' list
```

Download document from elster.de with id == 15:
```
$ document-dl --plugin Elster --jq 'contains({id: 15})' download
```



# Writing a plugin

* name your module the lowercase version of your class name and put it
  in *"docdl/plugins"* (e.g. "docdl/plugins/myplugin.py" for "class MyPlugin")

* write your plugin class:
  * if you just need requests, inherit from docdl.WebPortal and use
    ```self.session``` that's initialized for you
  * if you need selenium, inherit from docdl.SeleniumWebPortal and use
    ```self.webdriver``` that's initialized for you

```
import docdl

class MyPlugin(docdl.WebPortal):

    def login(self):
        """authenticate to web service with self.login_id"""

        # ... authenticate ...

        if not_logged_in:
            return False
        return True

    def logout(self):
        """sign off cleanly"""
        # ... logout ...

    def documents(self):
        """generator to iterate all available documents"""

        # do this for every available document
        for count, document in enumerate(all_documents):

            # scrape:
            #  * document attributes
            #    * it's recommended to assign an incremental "id"
            #      attribute to every document
            #    * if you set a "filename" attribute, it will be used to
            #      rename the downloaded file
            #    * dates should be parsed to datetime.datetime objects
            #      self.parse_date() should parse the most common strings
            #
            # also you must scrape either:
            #  * the download URL
            #
            # or:
            #  * the DOM element that triggers download. It is expected
            #    that the download starts immediately after click() on
            #    the DOM element
            #    (otherwise override the download() method)

            yield docdl.Document(
                url = this_documents_url,
                # download_element = <some selenium element to click>
                attributes = {
                    "id": count,
                    "category": "invoices",
                    "title": this_documents_title,
                    "filename": this_documents_target_filename,
                    "date": self.parse_date(some_date_string)
                }
            )


    def download(self, document):
        """if you really need a custom download method"""

        # ... save file to os.getcwd() ...

        return self.rename_after_download(document, filename)

```


# TODO
* regex filter
* list of available plugins
* plugin specific help
* better documentation
* properly parse rfc6266
