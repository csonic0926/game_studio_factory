"""Evidence-only Godot automation platform used by Game Studio Factory.

The package owns technical execution and immutable evidence.  It deliberately
does not own gameplay interpretation, a human playtest verdict, or baseline
promotion.
"""

from .api import GodotSession
from .common import GodotAutomationError, OperationResult

__all__ = ["GodotAutomationError", "GodotSession", "OperationResult"]
