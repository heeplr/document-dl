"""some handy helpers"""

import platform
import shutil
import sys
import os

from .dateparser import parse as parse_date  # noqa: F401 (import as shortcut)


def parse_decimal(decimal):
    """massage string with decimal number"""
    decimal = decimal.split()[0]
    decimal = decimal.replace(",", ".")
    return decimal


def show_image(filename, name="image"):
    """attempt to show image"""
    # always print image filename
    print(f'{{"{name}": "{filename}"}}', file=sys.stderr)
    # linux
    if platform.system() == "Linux":
        if shutil.which("xdg-open") and os.environ["DISPLAY"]:
            os.system(f"xdg-open {filename} >/dev/null &")

    # macintosh
    elif platform.system() == "Darwin":
        if shutil.which("open"):
            os.system(f"open {filename} >/dev/null &")

    # windows
    elif platform.system() == "Windows":
        os.system(f"start {filename}")
