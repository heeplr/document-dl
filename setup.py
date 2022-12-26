import fastentrypoints  # noqa: F401 (fastentrypoint does it's magic on import)
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
        'click-plugins',
        'jq',
        'python-dateutil',
        'requests',
        'selenium<4.3.0',
        'watchdog'
    ],
    packages=find_packages(exclude=['tests*']),
    entry_points={
        'docdl_plugins': [
            'amazon=docdl.plugins.amazon:amazon',
            'conrad=docdl.plugins.conrad:conrad',
            'dkb=docdl.plugins.dkb:dkb',
            'elster=docdl.plugins.elster:elster',
            'handyvertrag=docdl.plugins.handyvertrag:handyvertrag',
            'ing=docdl.plugins.ing:ing',
            'o2=docdl.plugins.o2:o2',
            'strato=docdl.plugins.strato:strato',
            'vodafone=docdl.plugins.vodafone:vodafone'
        ],
        'console_scripts': [
            'document-dl=docdl.cli:documentdl',
        ]
    }
)
