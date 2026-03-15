import argparse
import platform
import subprocess
import sys

import revvlink

parser = argparse.ArgumentParser(prog="revvlink")
parser.add_argument(
    "--version", action="store_true", help="Get version and debug information for revvlink."
)


args = parser.parse_args()


def get_debug_info() -> None:
    python_info = "\n".join(sys.version.split("\n"))
    java_version = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT)
    java_version = f"\n{' ' * 8}- ".join(v for v in java_version.decode().split("\r\n") if v)

    info: str = f"""
    revvlink: {revvlink.__version__}

    Python:
        - {python_info}
    System:
        - {platform.platform()}
    Java:
        - {java_version or "Version Not Found"}
    """

    print(info)


if args.version:
    get_debug_info()
