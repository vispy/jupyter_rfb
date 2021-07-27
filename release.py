import os
import sys
import importlib
import subprocess


NAME = "jupyter_rfb"
LIBNAME = NAME.replace("-", "_")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.isdir(os.path.join(ROOT_DIR, LIBNAME)):
    sys.exit("package NAME seems to be incorrect.")


def main():
    """Bump the version. If no version is specified, show the current version."""
    version = ".".join(sys.argv[1:])
    release(version)


def release(version):
    version = version.lstrip("v")
    version_info = tuple(
        int(part) if part.isnumeric() else part for part in version.split(".")
    )
    if len(version_info) == 3:
        version_info = version_info + ("final", 0)
    if len(version_info) > 3 and version_info[3] == "final":
        tag_name = ".".join(str(part) for part in version_info[:3])
    else:
        tag_name = ".".join(str(part) for part in version_info)
    # Check that we're not missing any libraries
    for x in ("setuptools", "twine", "jupyter_packaging"):
        try:
            importlib.import_module(x)
        except ImportError:
            sys.exit(f"You need to ``pip install {x}`` to do a version bump")
    # Check that there are no outstanding changes
    lines = (
        subprocess.check_output(["git", "status", "--porcelain"]).decode().splitlines()
    )
    lines = [line for line in lines if not line.startswith("?? ")]
    if lines:
        print("Cannot bump version because there are outstanding changes:")
        print("\n".join(lines))
        return
    # Get the version definition
    filename = os.path.join(ROOT_DIR, LIBNAME, "_version.py")
    with open(filename, "rb") as f:
        lines = f.read().decode().splitlines()
    for line_index, line in enumerate(lines):
        if line.startswith("version_info = "):
            break
    else:
        raise ValueError("Could not find version definition")
    # Only show the version?
    if not version.strip("x-"):
        print(f"Release script for {NAME}.\n")
        print("Usage:\n")
        print("    python release.py 1.2.3\n")
        print("The current version is:\n")
        print("    " + lines[line_index])
        return
    # Apply change
    version_info_repr = repr(version_info).replace("'", '"')
    lines[line_index] = lines[line_index].split("=")[0] + "= " + version_info_repr
    with open(filename, "wb") as f:
        f.write(("\n".join(lines).strip() + "\n").encode())
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
    subprocess.run(["git", "add", filename])
    subprocess.run(["git", "commit", "-m", f"Bump version to {tag_name}"])
    subprocess.run(["git", "tag", f"v{tag_name}"])
    print(f"git push origin main v{tag_name}")
    subprocess.run(["git", "push", "origin", "main", f"v{tag_name}"])
    # Pypi
    input("\nHit enter to upload to pypi: ")
    dist_dir = os.path.join(ROOT_DIR, "dist")
    if os.path.isdir(dist_dir):
        shutil.rmtree(dist_dir)
    subprocess.run([sys.executable, "setup.py", "sdist", "bdist_wheel"])
    1 / 0
    subprocess.run([sys.executable, "-m", "twine", "upload", dist_dir + "/*"])
    # Bye bye
    print("Success!")
    print("Don't forget to write release notes!")


if __name__ == "__main__":
    main()
