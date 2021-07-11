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
    "-a",
    "--plugin-argument",
    "plugin_arguments",
    type=click.Tuple([str, str]),
    metavar="<KEY VALUE>...",
    multiple=True,
    envvar="DOCDL_PLUGINARG",
    show_envvar=True,
    help="key/value argument passed to the plugin"
)
@click.option(
    "-m",
    "--match",
    "matches",
    type=click.Tuple([str, str]),
    metavar="<ATTRIBUTE PATTERN>...",
    multiple=True,
    envvar="DOCDL_MATCH",
    show_envvar=True,
    help="only process documents where attribute contains pattern string"
)
@click.option(
    "-r",
    "--regex",
    "regexes",
    type=click.Tuple([str, str]),
    metavar="<ATTRIBUTE REGEX>...",
    multiple=True,
    envvar="DOCDL_REGEX",
    show_envvar=True,
    help="only process documents where attribute value matches regex"
)
@click.option(
    "-j",
    "--jq",
    metavar="JQ_EXPRESSION",
    envvar="DOCDL_JQ",
    show_envvar=True,
    help="process document only if json query matches document " \
         "attributes (see https://stedolan.github.io/jq/manual/ )"
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
    ctx, username, password, plugin, plugin_arguments, matches,
    regexes, jq, headless, browser, timeout
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
        username,
        password,
        {
            'webdriver': { 'headless': headless },
            **dict(plugin_arguments)
        }
    )
    # store options
    ctx.obj['matches'] = matches
    ctx.obj['regexes'] = regexes
    ctx.obj['jq'] = jq


@documentdl.command(name="list")
@click.pass_context
def list_(ctx):
    """list documents"""
    with ctx.obj['portal'] as service:
        # walk all documents found
        for document in service.documents():
            # list document if filters match
            if document.match(ctx.obj['matches']) and \
               document.regex(ctx.obj['regexes']) and \
               document.jq(ctx.obj['jq']):
                click.echo(f"{document.attributes}")


@documentdl.command()
@click.pass_context
def download(ctx):
    """download documents"""
    with ctx.obj['portal'] as service:
        # walk all documents found
        for document in service.documents():
            # list document if filters match
            if document.match(ctx.obj['matches']) and \
               document.regex(ctx.obj['regexes']) and \
               document.jq(ctx.obj['jq']):
                # download
                service.download(document)
                click.echo(f"downloaded \"{document.attributes['filename']}\"")
