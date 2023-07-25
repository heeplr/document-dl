"""download documents from web portals"""

import pkg_resources
import click
import click_plugins
import docdl


@click_plugins.with_plugins(pkg_resources.iter_entry_points("docdl_plugins"))
@click.group(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "auto_envvar_prefix": "DOCDL",
    }
)
@click.option("-u", "--username", prompt=True, show_envvar=True, help="login id")
@click.option(
    "-p",
    "--password",
    prompt=True,
    hide_input=True,
    show_envvar=True,
    help="secret password",
)
@click.option(
    "-m",
    "--match",
    "string_matches",
    type=click.Tuple([str, str]),
    metavar="<ATTRIBUTE PATTERN>...",
    multiple=True,
    show_envvar=True,
    help="only output documents where attribute contains pattern string",
)
@click.option(
    "-r",
    "--regex",
    "regex_matches",
    type=click.Tuple([str, str]),
    metavar="<ATTRIBUTE REGEX>...",
    multiple=True,
    show_envvar=True,
    help="only output documents where attribute value matches regex",
)
@click.option(
    "-j",
    "--jq",
    "jq_matches",
    metavar="JQ_EXPRESSION",
    multiple=True,
    show_envvar=True,
    help="only output documents if json query matches document's "
    "attributes (see https://stedolan.github.io/jq/manual/ )",
)
@click.option(
    "--headless/--show",
    "-H/ ",
    type=bool,
    show_envvar=True,
    default=True,
    help="show/hide browser window",
    show_default=True,
)
@click.option(
    "-b",
    "--browser",
    type=click.Choice(
        ["chrome", "edge", "firefox", "ie", "safari", "webkitgtk"], case_sensitive=False
    ),
    show_envvar=True,
    default="chrome",
    help="webdriver to use for selenium based plugins",
    show_default=True,
)
@click.option(
    "-t",
    "--timeout",
    type=int,
    default=25,
    show_envvar=True,
    help="seconds to wait for data before terminating connection",
    show_default=True,
)
@click.option(
    "-i",
    "--image-loading",
    type=bool,
    default=False,
    show_envvar=True,
    help="Turn off image loading when False",
    show_default=True,
)
@click.option(
    "-l",
    "--list",
    "action",
    flag_value="list",
    default=True,
    show_envvar=True,
    help="list documents",
    show_default=True,
)
@click.option(
    "-d",
    "--download",
    "action",
    flag_value="download",
    show_envvar=True,
    help="download documents",
    show_default=True,
)
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["list", "dicts"], case_sensitive=False),
    show_envvar=True,
    default="dicts",
    help="choose between line buffered output " "of json dicts or single json list",
    show_default=True,
)
@click.option(
    "-D",
    "--debug",
    type=bool,
    is_flag=True,
    default=False,
    show_envvar=True,
    help="use selenium remote debugging on port 9222",
    show_default=True,
)
@click.pass_context
# pylint: disable=W0613,C0103,R0913
def documentdl(
    ctx,
    username,
    password,
    string_matches,
    regex_matches,
    jq_matches,
    headless,
    browser,
    timeout,
    image_loading,
    action,
    output_format,
    debug,
):
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
        login_id=root_params["username"],
        password=root_params["password"],
        arguments={
            # set webdriver specific params
            "webdriver": {
                "headless": root_params["headless"],
                "load_images": root_params["image_loading"],
            },
            # pass plugin params directly to plugin
            **params,
        },
    )

    # let's go
    with plugin as portal:
        # list of documents
        result = []
        # walk all documents found
        for document in portal.documents():
            # filter document
            filtered = (
                document.match_string(root_params["string_matches"])
                and document.match_regex(root_params["regex_matches"])
                and document.match_jq(root_params["jq_matches"])
            )
            # skip filtered documents
            if not filtered:
                continue
            # download ?
            if root_params["action"] == "download":
                portal.download(document)
            # line buffered dict output?
            if root_params["output_format"] == "dicts":
                # always output as json dict
                click.echo(document.toJSON())
            # just store result for later
            else:
                result += [document.toJSON()]

        # output json list?
        if root_params["output_format"] == "list":
            click.echo(f"[ {','.join(result)} ]")
