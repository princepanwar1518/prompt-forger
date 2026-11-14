"""Prompt Forger engine: turns a form into ready-to-use prompt files."""

from .forge import forge
from .schema import DEFAULT_FORM

__all__ = ["forge", "DEFAULT_FORM", "__version__"]
__version__ = "1.2.0"
