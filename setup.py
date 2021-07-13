import sys
import fastentrypoints
from setuptools import setup, find_packages


setup(
    name='document-dl',
    version='0.1.1',
    description='download documents from web portals',
    long_description=open("README.md").read(),
    url='',
    author='Daniel Hiepler',
    author_email='d-docdl@coderdu.de',
    license='unlicense',
    keywords='scrape office documents bills',
    py_modules=['docdl'],
    install_requires=[
        'click',
        'jq',
        'python-dateutil',
        'requests',
        'selenium',
        'watchdog'
    ],
    packages=find_packages(exclude=['tests*']),
    entry_points={
        'console_scripts': [
            'document-dl=docdl.cli:documentdl',
        ]
    }
)
