"""download documents from web portals"""

import importlib
import click
import docdl


@click.group(
    context_settings=dict(help_option_names=['-h', '--help'])
)
@click.option(
    "-u",
    "--username",
    prompt=True,
    envvar="DOCDL_USERNAME",
    show_envvar=True,
    help="login id"
)
@click.option(
    "-p",
    "--password",
    prompt=True,
    hide_input=True,
    envvar="DOCDL_PASSWORD",
    show_envvar=True,
    help="secret password"
)
@click.option(
    "-P",
    "--plugin",
    envvar="DOCDL_PLUGIN",
    show_envvar=True,
    required=True,
    help="plugin name"
)
@click.option(
    "-f",
    "--filter",
    "filt",
    type=click.Tuple([str, str]),
    metavar="<ATTRIBUTE PATTERN>...",
    multiple=True,
    envvar="DOCDL_FILTER",
    show_envvar=True,
    help="only process documents that match filter rule"
)
@click.option(
    "-H",
    "--headless",
    type=bool,
    envvar="DOCDL_HEADLESS",
    show_envvar=True,
    default=True,
    help="show browser window if false",
    show_default=True
)
@click.option(
    "-b",
    "--browser",
    type=click.Choice([
        "chrome", "edge", "firefox", "ie", "opera", "safari",
        "webkitgtk"
    ], case_sensitive=False),
    envvar="DOCDL_BROWSER",
    show_envvar=True,
    default="chrome",
    help="webdriver to use for selenium plugins",
    show_default=True
)
@click.option(
    "-t",
    "--timeout",
    type=int,
    default=15,
    envvar="DOCDL_TIMEOUT",
    show_envvar=True,
    help="seconds to wait for data before terminating connection",
    show_default=True
)
@click.pass_context
def documentdl(
    ctx, username, password, plugin, filt, headless, browser, timeout
):
    """download documents from web portals"""
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
    ctx.obj['filter'] = filt

@documentdl.command(name="list")
@click.pass_context
def list_(ctx):
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
