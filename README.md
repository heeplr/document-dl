
Command line program to download documents from web portals.

Use specific plugins to download all kind of documents (invoices,
notifications, ...) or write your own scraping plugin.


# Dependencies
* python
* click
* inotify
* selenium (default webdriver is "chrome")

# Installation
```
$ pip install .
```

# Usage

Display Help:

```
$ document-dl -h
```

# Examples

List all documents from Vodafone:
```
$ document-dl --username mylogin --password mypass --plugin VodafoneKabel_DE list
```

Download all documents from Vodafone (and provide credentials using env vars):
```
$ DOCDL_USERNAME="mylogin" DOCDL_PASSWORD="mypass" document-dl --plugin VodafoneKabel_DE download
```

Download all invoices from o2 Online (and enter username/password at prompt):
```
$ document-dl --plugin O2online_DE --filter doctype BILL download
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
            #
            # also scrape either:
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
                    "filename": this_documents_target_filename
                }
            )


    def download(self, document):
        """if you really need a custom download method"""

        # ... save file to os.getcwd() ...

        return self.rename_after_download(document, filename)

```

# TODO
* better filtering
* better documentation
