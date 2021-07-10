"""download bills from various online services"""

import click
import docdl
import importlib


@click.group(
    context_settings=dict(help_option_names=['-h', '--help'])
)
@click.option(
    "--username",
    prompt=True,
    envvar="DOCDL_USERNAME",
    help="login id"
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    envvar="DOCDL_PASSWORD",
    help="secret password to login"
)
@click.option(
    "--plugin",
    envvar="DOCDL_PLUGIN",
    required=True,
    help="plugin name"
)
@click.option(
    "--filter",
    type=click.Tuple([str, str]),
    metavar="<ATTRIBUTE PATTERN>...",
    multiple=True,
    envvar="DOCDL_FILTER",
    help="only process documents that match filter rule"
)
@click.option(
    "--headless",
    type=bool,
    envvar="DOCDL_HEADLESS",
    default=True,
    help="show browser window if false",
    show_default=True
)
@click.option(
    "--browser",
    type=click.Choice([
        "android", "blackberry", "chrome", "edge", "firefox",
        "ie", "opera", "phantomjs", "remote", "safari",
        "webkitgtk"
    ], case_sensitive=False),
    default="chrome",
    help="webdriver to use for selenium plugins",
    show_default=True
)
@click.option(
    "--timeout",
    type=int,
    default=15,
    help="seconds to wait for data before terminating connection",
    show_default=True
)
@click.pass_context
def documentdl(
    ctx, username, password, plugin, filter, headless, browser, timeout
):
    # set browser to use for SeleniumWebPortal class
    docdl.SeleniumWebPortal.WEBDRIVER = browser
    # set default request timeout
    docdl.WebPortal.TIMEOUT = timeout
    # create context
    ctx.obj = {}
    # load plugin
    module = importlib.import_module(f"docdl.plugins.{plugin.lower()}")
    plugin = getattr(module, plugin)
    # initialize plugin
    ctx.obj['portal'] = plugin(
        username, password, { 'headless': headless }
    )
    # store options
    ctx.obj['filter'] = filter

@documentdl.command()
@click.pass_context
def list(ctx):
    """list documents"""
    with ctx.obj['portal'] as service:
        # walk all documents found
        for document in service.documents():
            # list document if filters match
            if document.filter(ctx.obj['filter']):
                click.echo(f"{document.attributes}")

@documentdl.command()
@click.pass_context
def download(ctx):
    """download documents"""
    with ctx.obj['portal'] as service:
        # walk all documents found
        for document in service.documents():
            # list document if filters match
            if document.filter(ctx.obj['filter']):
                # download
                service.download(document)
                click.echo(f"downloaded \"{document.attributes['filename']}\"")

