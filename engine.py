"""Clean CORQ runtime entrypoint.

This is the new production entrypoint for the clean runtime:
THINQ -> CORQ -> TOP7 -> web.

Run:
    python engine.py
"""
from corq.engine import main

if __name__ == "__main__":
    main()
