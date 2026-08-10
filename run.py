"""Start pAstroCORE.

A launcher rather than the application itself. The window used to live in
`pastrocore.py` beside the `pastrocore` package, where Python could import one or the
other but never both -- so nothing could import the main window, and it was the one part
of the interface no test could reach.
"""
from pastrocore.app import main

if __name__ == "__main__":
    main()
