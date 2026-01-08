"""
SlideRefactor: Convert NotebookLLM flattened slide PDFs into editable PPTX.

A prompt-driven pipeline that uses SOTA extraction (Datalab) + LLM-powered
layout reconstruction + deterministic PPTX rendering.
"""

__version__ = "0.1.0"
__author__ = "SlideRefactor Team"

from sliderefactor.models import SlideGraph, Slide, Block, Element
from sliderefactor.pipeline import SlideRefactorPipeline

__all__ = [
    "SlideGraph",
    "Slide",
    "Block",
    "Element",
    "SlideRefactorPipeline",
]
