"""parse any possible date/time string to datetime object"""

import datetime
import re
import dateutil.parser


class Date(datetime.datetime):
    """custom datetime object wrapper represented in ISO format"""

    def __repr__(self):
        """https://xkcd.com/1179/"""
        return self.isoformat()

# monkeypatch datetime to use our ISO representation globally
datetime.datetime = Date


def parse(date, date_format=None):
    """convert input to datetime object
       :param date: either datetime string or datetime object
       :param date_format: datetime.strptime() format string.
                           If none is given, fuzzy matching will be used
                           to parse the date
       :result: datetime object or None
       @todo: handle timezone"""

    # got nothing?
    if date is None:
        return None

    # already got a datetime object?
    if isinstance(date, datetime.datetime):
        # remove timezone info
        return date.replace(tzinfo=None)

    # got a string?
    if isinstance(date, str):
        # massage string
        date = date.lower().strip()

        # empty string ?
        if date == "":
            raise ValueError("Failed to parse datetime: Empty string")

        # replace month names
        date = replace_months(date)
        # remove whitespace before and after .
        date = re.sub(r'\s*\.\s', '.', date)
        # check for keywords
        if date == "now":
            return datetime.datetime.now()
        if date == "today":
            return datetime.datetime.today()
        if date == "yesterday":
            return datetime.datetime.today() - datetime.timedelta(1)
        if date == "tomorrow":
            return datetime.datetime.today() + datetime.timedelta(1)
        if date in ("last week", "lastweek"):
            return datetime.datetime.today() - datetime.timedelta(7)
        if date in ("last month", "lastmonth"):
            return datetime.datetime.today() - datetime.timedelta(30)
        # got a pattern?
        if date_format:
            # use it to interpret date string
            return datetime.datetime.strptime(date, date_format)

        # try american date format MM/DD/YYYY
        try:
            d = datetime.datetime.strptime(date, "%m/%d/%Y")
            # remove timezone info
            return d.replace(tzinfo=None)
        except ValueError:
            pass

        # try german date format DD.MM.YYYY
        try:
            d = datetime.datetime.strptime(date, "%d.%m.%Y")
            # remove timezone info
            return d.replace(tzinfo=None)
        except ValueError:
            pass

        # try german date format DD.MM.YY
        try:
            d = datetime.datetime.strptime(date, "%d.%m.%y")
            # remove timezone info
            return d.replace(tzinfo=None)
        except ValueError:
            pass

        # try fuzzy parser
        try:
            d = dateutil.parser.parse(date, fuzzy=True)
            # parse() could return a tuple
            if isinstance(d, tuple):
                d = d[0]
            # remove timezone info
            return d.replace(tzinfo=None)
        except (ValueError, TypeError, OverflowError):
            pass

        # try YYYYDDMM
        try:
            d = datetime.datetime.strptime(date, "%Y%d%m")
            return d.replace(tzinfo=None)
        except ValueError:
            pass

        # try to split off timezone
        if "+" in date:
            t = date.split("+")
            tz = t[1]
            date = t[0]
        if "z" in date:
            t = date.split("z")
            date = t[0]
        if "." in date:
            t = date.split(".")
            date = t[0]

        # will raise ValueError on problems
        try:
            d = dateutil.parser.parse(date, fuzzy=True)
            # parse() could return a tuple
            if isinstance(d, tuple):
                d = d[0]
            return d.replace(tzinfo=None)
        except (ValueError, TypeError, OverflowError):
            pass

        # try timestamp
        try:
            d = datetime.datetime.fromtimestamp(int(date))
            return d.replace(tzinfo=None)
        except ValueError:
            pass

        # 2015-jan-thut05:01:39akdt
        try:
            d = datetime.datetime.strptime(date, "%Y-%b-%at%H:%M:%Sakdt")
            return d.replace(tzinfo=None)
        except ValueError:
            pass

        raise ValueError(f"Failed to parse date: {date}")

    # unknown type
    raise TypeError(
        "Need <type 'datetime'>, <type 'str'> or <type 'unicode'>. "
        f"Got {type(i)}"
    )


def replace_months(date):
    """replace literal month names with numbers"""
    MONTHS = {
        1:  [ "jan", "januray", "januar" ],
        2:  [ "feb", "february", "februar" ],
        3:  [ "mar", "march", "märz" ],
        4:  [ "apr", "april" ],
        5:  [ "may", "mai" ],
        6:  [ "jun", "june", "juni" ],
        7:  [ "jul", "july", "juli" ],
        8:  [ "aug", "august" ],
        9:  [ "sep", "september" ],
        10: [ "oct", "october", "oktober" ],
        11: [ "nov", "november" ],
        12: [ "dec", "december", "dezember" ],
    }

    # walk all months
    for month, names in MONTHS.items():
        # check for all names (sorted by length, longest first)
        for name in reversed(sorted(names, key=lambda n: len(n))):
            # replace on occurence
            if name in date:
                return date.replace(name, f"{month}.")
    return date
