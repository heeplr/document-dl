"""parse any possible date/time string to datetime object"""

import datetime
import json
import re
import dateutil.parser


class DateEncoder(json.JSONEncoder):
    """
    custom json encoder that converts datetime
    objects to ISO format string
    """

    def default(self, o):
        # treat datetime objects specially
        if isinstance(o, datetime.datetime):
            # https://xkcd.com/1179/
            # we add the Z to prevent:
            # >>jq: error date ... does not match format "%Y-%m-%dT%H:%M:%SZ"<<
            return o.isoformat() + "Z"
        # pass everything else to default encoder
        return json.JSONEncoder.default(self, o)


def check_for_keywords(date):
    """check for shorthands"""
    result = None
    if date == "now":
        result = datetime.datetime.now()
    elif date == "today":
        result = datetime.datetime.today()
    elif date == "yesterday":
        result = datetime.datetime.today() - datetime.timedelta(1)
    elif date == "tomorrow":
        result = datetime.datetime.today() + datetime.timedelta(1)
    elif date in ("last week", "lastweek"):
        result = datetime.datetime.today() - datetime.timedelta(7)
    elif date in ("last month", "lastmonth"):
        result = datetime.datetime.today() - datetime.timedelta(30)
    return result


# pylint: disable=R0911,R0912,R0915
def parse(date, date_format=None):
    """convert input to datetime object
    :param date: either datetime string or datetime object
    :param date_format: datetime.strptime() format string.
                        If none is given, fuzzy matching will be used
                        to parse the date
    :result: datetime object or input date upon parsing failure
    @todo: handle timezone"""
    # remember input
    input_date = date
    # got nothing?
    if date is None:
        return None

    # already got a datetime object?
    if isinstance(date, datetime.datetime):
        # remove timezone info
        return date.replace(tzinfo=None)

    # got a string?
    if isinstance(date, str):
        # empty string ?
        if date == "":
            return input_date

        # massage string
        date = date.lower().strip()
        # replace month names
        date = replace_months(date)
        # remove whitespace before and after .
        date = re.sub(r"\s*\.\s", ".", date)
        # check for keywords
        if result := check_for_keywords(date):
            return result
        # got a pattern?
        if date_format:
            # use it to interpret date string
            return datetime.datetime.strptime(date, date_format)

        # try american date format MM/DD/YYYY
        try:
            result = datetime.datetime.strptime(date, "%m/%d/%Y")
            # remove timezone info
            return result.replace(tzinfo=None)
        except ValueError:
            pass

        # MM/DD/YYYY HH:MM:ss
        try:
            result = datetime.datetime.strptime(date, "%m/%d/%Y %H:%M:%S")
            # remove timezone info
            return result.replace(tzinfo=None)
        except ValueError:
            pass

        # try german date format DD.MM.YYYY
        try:
            result = datetime.datetime.strptime(date, "%d.%m.%Y")
            # remove timezone info
            return result.replace(tzinfo=None)
        except ValueError:
            pass

        # try german date format DD.MM.YY
        try:
            result = datetime.datetime.strptime(date, "%d.%m.%y")
            # remove timezone info
            return result.replace(tzinfo=None)
        except ValueError:
            pass

        # try fuzzy parser
        try:
            result = dateutil.parser.parse(date, fuzzy=True)
            # parse() could return a tuple
            if isinstance(result, tuple):
                result = result[0]
            # remove timezone info
            return result.replace(tzinfo=None)
        except (ValueError, TypeError, OverflowError):
            pass

        # try YYYYDDMM
        try:
            result = datetime.datetime.strptime(date, "%Y%d%m")
            return result.replace(tzinfo=None)
        except ValueError:
            pass

        # try to split off timezone
        if "+" in date:
            split_date = date.split("+")
            # ~ tz = split_date[1]
            date = split_date[0]
        if "z" in date:
            split_date = date.split("z")
            date = split_date[0]
        if "." in date:
            split_date = date.split(".")
            date = split_date[0]

        # will raise ValueError on problems
        try:
            result = dateutil.parser.parse(date, fuzzy=True)
            # parse() could return a tuple
            if isinstance(result, tuple):
                result = result[0]
            return result.replace(tzinfo=None)
        except (ValueError, TypeError, OverflowError):
            pass

        # try timestamp
        try:
            result = datetime.datetime.fromtimestamp(int(date))
            return result.replace(tzinfo=None)
        except ValueError:
            pass

        # 2015-jan-thut05:01:39akdt
        try:
            result = datetime.datetime.strptime(date, "%Y-%b-%at%H:%M:%Sakdt")
            return result.replace(tzinfo=None)
        except ValueError:
            pass

    return input_date


def replace_months(date):
    """replace literal month names with numbers"""
    months = {
        1: ["jan", "januray", "januar"],
        2: ["feb", "february", "februar"],
        3: ["mar", "march", "märz"],
        4: ["apr", "april"],
        5: ["may", "mai"],
        6: ["jun", "june", "juni"],
        7: ["jul", "july", "juli"],
        8: ["aug", "august"],
        9: ["sep", "september"],
        10: ["oct", "october", "oktober"],
        11: ["nov", "november"],
        12: ["dec", "december", "dezember"],
    }

    # walk all months
    for month, names in months.items():
        # check for all names (sorted by length, longest first)
        for name in reversed(sorted(names, key=len)):
            # replace on occurence
            if name in date:
                return date.replace(name, f"{month}.")
    return date
