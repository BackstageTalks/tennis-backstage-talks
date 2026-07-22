"""
THINQ package

THINQ is the intelligence layer for the tennis project.
It does not act as a standalone prediction model.
It prepares feature and edge data for CORQ, which remains the CORE output model.
"""

__all__ = ["ThinqService"]

try:
    from .thinq_service import ThinqService
except Exception:
    # Keeps package import safe during early development or partial deployments.
    ThinqService = None
