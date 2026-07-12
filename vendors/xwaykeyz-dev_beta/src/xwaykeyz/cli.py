from .lib import logger
from .lib.logger import debug, error, info, log
from .version import __description__, __name__, __version__
from typing import List

CONFIG_NAMESPACE = "CFG:"

def _gen_config_header(path):
    return bytes("import re;"
        "from xwaykeyz.config_api import *;"
        f"__config__ = '{path}';"
        ,"utf-8")


def eval_config(path):
    with open(path, "rb") as file:
        header = _gen_config_header(path)
        config_code = header + file.read()
        # WARN: yes, this is potentially a security risk, but our config is
        # - python code so we're sort of stuck with this AFAIK
        # TODO: some sort of sandboxing maybe?
        exec(compile(config_code, f"{CONFIG_NAMESPACE}{path}", "exec"), globals())  # nosec


def uinput_device_exists():
    from os.path import exists

    return exists("/dev/uinput")


def has_access_to_uinput():
    from evdev.uinput import UInputError

    try:
        from xwaykeyz.output import setup_uinput  # noqa: F401

        setup_uinput()
        return True
    except UInputError:
        return False


def print_config_traceback():
    import traceback
    import sys
    cls, desc, tb = sys.exc_info()

    print("\nTraceback (while executing your config):")
    for frame in traceback.extract_tb(tb):
        if "xwaykeyz/cli" in frame.filename:
            continue
        if frame.name == "include":
            continue

        file = frame.filename.replace(CONFIG_NAMESPACE, "")
        print(f"  File \"{file}\", line {frame.lineno}, in {frame.name}")
        if (frame.line):
            print(frame.line)
    print(f"{cls.__name__}: {desc}")


def check_is_config_good(filename):
    config_good = False
    try:
        eval_config(filename)
        log("CONFIG: Looks good to me.")
        config_good = True
    except BaseException:

        error("CONFIG: No bueno, we have a problem...")
        print_config_traceback()

    return config_good


def main():
    # Parse args
    import argparse

    from appdirs import user_config_dir

    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        metavar="config.py",
        type=str,
        default=user_config_dir("xwaykeyz/config.py"),
        help="use custom configuration file",
    )
    parser.add_argument(
        "-d",
        "--devices",
        dest="devices",
        metavar="device",
        type=str,
        nargs="+",
        help="manually specify devices to remap",
    )
    parser.add_argument(
        "-w",
        "--watch",
        dest="watch",
        action="store_true",
        help="watch for new hot-plugged devices",
    )
    parser.add_argument(
        "-v", dest="verbose", action="store_true", help="increase debug logging"
    )
    parser.add_argument(
        "--flush", dest="flush", action="store_true", help="immediately flush all log output"
    )
    parser.add_argument(
        "--list-devices", dest="list_devices", action="store_true", help=""
    )
    parser.add_argument(
        "--check",
        dest="check_config",
        action="store_true",
        help="evaluate config script, check for syntax errors",
    )
    parser.add_argument(
        "--version", dest="show_version", action="store_true", help=""
    )
    parser.add_argument(
        "--very-bad-idea",
        dest="run_as_root",
        action="store_true",
        help="(deprecated: allow running as root)",
    )
    args = parser.parse_args()

    if args.show_version:
        print(f"{__name__} v{__version__}")
        exit(0)

    if args.verbose:
        logger.VERBOSE = True

    if args.flush:
        logger.FLUSH = True

    print(f"{__name__} v{__version__}")

    import os

    if os.getuid() == 0:
        if not args.run_as_root:
            log("ROOT: All your base are belong to us! ;-)")
            error(
                "Please don't run me as root.  "
                "It's a --very-bad-idea, seriously."
            )
            info(
                "Running as root is deprecated, prefer running "
                "as a semi-priveleged user."
            )
            exit(0)
        else:
            log("ROOT: Yes, I am.  --very-bad-idea acknowledged.")

    if args.list_devices:
        from .devices import Devices

        Devices.print_list()
        exit(0)

    if args.check_config:
        config_good = check_is_config_good(args.config)
        exit(0) if config_good else exit(1)

    # Make sure that the /dev/uinput device exists
    if not uinput_device_exists():
        error(
            """The '/dev/uinput' device does not exist.
Please check kernel configuration."""
        )
        import sys

        sys.exit(1)

    # Make sure that user have root privilege
    if not has_access_to_uinput():
        error(
            """Failed to open `uinput` in write mode.
Please check access permissions for /dev/uinput."""
        )
        import sys

        sys.exit(1)

    debug(f"CONFIG: {args.config}")

    # Load configuration file
    try:
        eval_config(args.config)
    except BaseException:
        print_config_traceback()
        exit(1)

    if args.watch:
        log("WATCH: Watching for new devices to hot-plug.")

    ###############################################################################################
    # Let the user pass in devices args from the config file with the `devices_api()` function,
    # instead of using `--devices` on command line.

    from xwaykeyz.config_api import _DEVICE_ARGS

    _only_devices: List[str]        = _DEVICE_ARGS['only_devices']
    # _add_devices: List[str]       = _DEVICE_ARGS['add_devices']
    _ignore_devices: List[str]      = _DEVICE_ARGS['ignore_devices']

    # Override with API input only if no CLI input
    if not args.devices and _only_devices:
        debug(f"Using device arguments from devices_api call in config...")
        print(f"\t{_only_devices}")
        args.devices = _only_devices
    elif args.devices:
        debug(f"Using device arguments from command line '--devices' option...")

    #
    ###############################################################################################

    # Enter event loop
    from xwaykeyz.input import main_loop

    main_loop(args.devices, args.watch, _ignore_devices)
