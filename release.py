"""Release script for jupyter_rfb.

Usage:

    python release.py 1.2.3

This script will then:

    * Update all files that contain the version number.
    * Show a diff and ask for confirmation.
    * Commit the change, and tag that commit.
    * Git push main and the new tag.
    * Ask for confirmation to push to Pypi.
    * Create an sdist and bdist_wheel build.
    * Push these to Pypi.
"""

import os
import re
import sys
import shutil
import importlib
import subprocess


NAME = "jupyter_rfb"
LIBNAME = NAME.replace("-", "_")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.isdir(os.path.join(ROOT_DIR, LIBNAME)):
    sys.exit("package NAME seems to be incorrect.")


finder = re.compile(
    r"^ *((__version__)|(version)|(\"version\")|(export const version))\s*(\=|\:)\s*[\"\']([\d\.]+)[\"\']",
    re.MULTILINE,
)


def release(version):
    """Bump the version and create a release. If no version is specified, show the current version."""

    version = version.lstrip("v")
    version_info = tuple(
        int(part) if part.isnumeric() else part for part in version.split(".")
    )
    if len(version_info) == 3:
        version_info = (*version_info, "final", 0)
    if len(version_info) > 3 and version_info[3] == "final":
        tag_name = ".".join(str(part) for part in version_info[:3])
    else:
        tag_name = ".".join(str(part) for part in version_info)
    # Check that we're not missing any libraries
    for x in ["build", "hatchling", "twine"]:
        try:
            importlib.import_module(x)
        except ImportError:
            sys.exit(f"You need to ``pip install {x}`` to do a version bump")
    # Check that there are no outstanding changes
    lines = (
        subprocess.check_output(["git", "status", "--porcelain"]).decode().splitlines()
    )
    lines = [line for line in lines if not line.startswith("?? ")]
    if lines and version:
        print("Cannot bump version because there are outstanding changes:")
        print("\n".join(lines))
        return
    # Get the version definition
    only_show_version = False
    if not version.strip("x-"):
        print(__doc__)
        only_show_version = True

    for filename in [
        os.path.join(ROOT_DIR, "pyproject.toml"),
        os.path.join(ROOT_DIR, LIBNAME, "_version.py"),
        os.path.join(ROOT_DIR, "js", "package.json"),
        os.path.join(ROOT_DIR, "js", "lib", "widget.js"),
    ]:
        fname = os.path.basename(filename)
        with open(filename, "rb") as f:
            text = f.read().decode()
        m = finder.search(text)
        if not m:
            raise ValueError(f"Could not find version definition in {filename}")
        lastgroup = len(m.groups())
        if only_show_version:
            print(
                f"The current version in {fname.ljust(16)}: {m.group(lastgroup)}  -> {m.group(0)}"
            )
        else:
            # Apply changse
            i1, i2 = m.start(lastgroup), m.end(lastgroup)
            text = text[:i1] + version + text[i2:]
            with open(filename, "wb") as f:
                f.write(text.encode())
    if only_show_version:
        return
    # Ask confirmation
    subprocess.run(["git", "diff"])
    while True:
        x = input("Is this diff correct? [Y/N]: ")
        if x.lower() == "y":
            break
        elif x.lower() == "n":
            print("Cancelling (git checkout)")
            subprocess.run(["git", "checkout", filename])
            return
    # Git
    print("Git commit and tag")
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", f"Bump version to {tag_name}"])
    subprocess.run(["git", "tag", f"v{tag_name}"])
    print(f"git push origin main v{tag_name}")
    subprocess.check_call(["git", "push", "origin", "main", f"v{tag_name}"])
    # Pypi
    input("\nHit enter to upload to pypi: ")
    dist_dir = os.path.join(ROOT_DIR, "dist")
    if os.path.isdir(dist_dir):
        shutil.rmtree(dist_dir)
    subprocess.check_call([sys.executable, "-m", "build", "-n", "-w"])
    subprocess.check_call([sys.executable, "-m", "build", "-n", "-s"])

    subprocess.check_call([sys.executable, "-m", "twine", "upload", dist_dir + "/*"])
    # Bye bye
    print("Done!")
    print("Don't forget to write release notes, and check pypi!")


if __name__ == "__main__":
    version = ".".join(sys.argv[1:])
    release(version)
