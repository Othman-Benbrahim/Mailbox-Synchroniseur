"""Entry point of the packaged build.

`mailbox_sync/__main__.py` uses relative imports, which are invalid when
PyInstaller runs a file as a top-level script. This launcher imports the package
properly instead, so the frozen build takes exactly the same code path as
`python -m mailbox_sync`.
"""
import sys

from mailbox_sync.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
