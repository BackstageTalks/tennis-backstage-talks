"""THINQ loader exports - package-safe."""
from .thinq_loader import ThinqLoader
from .h2h_loader import H2HLoader

try:
    from .h2h_loader import build_h2h_context
except Exception:
    build_h2h_context = None

__all__ = ["ThinqLoader", "H2HLoader", "build_h2h_context"]
