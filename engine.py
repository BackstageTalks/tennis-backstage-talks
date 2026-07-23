"""Clean production entrypoint for CORQ Daily Predictions.

Architecture:
- THINQ = intelligence layer / brain
- CORQ = CORE output model + ranking
- TOP7 = first 7 from CORQ ranking

Run:
    python engine.py
"""
from corq.engine import main

if __name__ == "__main__":
    main()
