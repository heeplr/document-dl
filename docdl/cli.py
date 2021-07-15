"""download documents from web portals"""

import json
import pkg_resources
import click
import click_plugins
import docdl


@click_plugins.with_plugins(
    pkg_resources.iter_entry_points('docdl_plugins')
)
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
    "-m",
    "--match",
    "string_matches",
    type=click.Tuple([str, str]),
    metavar="<ATTRIBUTE PATTERN>...",
    multiple=True,
    envvar="DOCDL_MATCH",
    show_envvar=True,
    help="only output documents where attribute contains pattern string"
)
@click.option(
    "-r",
    "--regex",
    "regex_matches",
    type=click.Tuple([str, str]),
    metavar="<ATTRIBUTE REGEX>...",
    multiple=True,
    envvar="DOCDL_REGEX",
    show_envvar=True,
    help="only output documents where attribute value matches regex"
)
@click.option(
    "-j",
    "--jq",
    "jq_matches",
    metavar="JQ_EXPRESSION",
    envvar="DOCDL_JQ",
    show_envvar=True,
    help="only output documents if json query matches document's " \
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
    help="webdriver to use for selenium based plugins",
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
@click.option(
    "-i",
    "--image-loading",
    type=bool,
    default=False,
    envvar="DOCDL_IMAGE_LOADING",
    show_envvar=True,
    help="Turn off image loading when False",
    show_default=True
)
@click.option(
    "-a",
    "--action",
    type=click.Choice(["download", "list"]),
    default="list",
    envvar="DOCDL_ACTION",
    show_envvar=True,
    help="download or just list documents",
    show_default=True
)
@click.pass_context
def documentdl(browser, timeout, *args, **kwargs):
    """download documents from web portals"""
    # set browser that SeleniumWebPortal plugins should use
    docdl.SeleniumWebPortal.WEBDRIVER = browser
    # set default request timeout
    docdl.WebPortal.TIMEOUT = timeout


def run(ctx, plugin_class):
    """this gets called by plugins with their click context"""
    # get our root context
    root_ctx = ctx.find_root()
    root_params = root_ctx.params
    params = ctx.params

    # initialize plugin
    plugin = plugin_class(
        login_id=root_params['username'],
        password=root_params['password'],
        arguments={
            # set webdriver specific params
            'webdriver': {
                'headless': root_params['headless'],
                'load_images': root_params['image_loading']
            },
            # pass plugin params directly to plugin
            **params
        }
    )

    # let's go
    with plugin as portal:
        # walk all documents found
        for document in portal.documents():
            # filter document
            filtered = (
                document.match_string(root_params['matches']) and \
                document.match_regex(root_params['regexes']) and \
                document.match_jq(root_params['jq'])
            )
            # skip filtered documents
            if not filtered:
                continue
            # always output as json dict
            click.echo(
                json.dumps(
                    document.attributes,
                    sort_keys=True,
                    default=str
                )
            )
            # download ?
            if root_params['action'] == "download":
                portal.download(document)
