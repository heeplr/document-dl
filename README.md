
Plugin based command-line utility to download documents (invoices, notifications, ...)
from various web portals.


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

Download all documents from Vodafone:
```
$ DOCDL_USERNAME="mylogin" DOCDL_PASSWORD="mypass" document-dl --plugin VodafoneKabel_DE download
```

Download all invoices from o2 Online (and enter username/password at prompt):
```
$ document-dl --plugin O2online_DE --filter doctype BILL download
```


# TODO
* better filtering
* better documentation
