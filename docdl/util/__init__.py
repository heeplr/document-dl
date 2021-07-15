"""some handy helpers"""

import platform
import shutil
import os

from .dateparser import parse as parse_date


def show_image(filename, name="image"):
    """attempt to show image"""
    # always print image filename
    print(f'{{"{name}": "{filename}"}}')
    # linux
    if platform.system() == 'Linux':
        if shutil.which("xdg-open") and os.environ['DISPLAY']:
            os.system(f"xdg-open {filename} >/dev/null &")

    # macintosh
    elif platform.system() == 'Darwin':
        if shutil.which("open"):
            os.system(f"open {filename} >/dev/null &")

    # windows
    elif platform.system() == 'Windows':
        os.system(f"start {filename}")
