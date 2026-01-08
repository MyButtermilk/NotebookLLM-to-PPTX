"""
LLM prompt system for converting SlideGraph blocks into PPTX elements.

Uses Claude (Anthropic) to intelligently merge blocks, infer structure,
and produce a PPTX-ready element plan.
"""

from sliderefactor.prompt.block_to_element import BlockToElementConverter

__all__ = ["BlockToElementConverter"]
