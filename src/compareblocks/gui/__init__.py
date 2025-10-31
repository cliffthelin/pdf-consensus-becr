# src/compareblocks/gui/__init__.py
"""GUI module for the PySide6-based review interface."""

from .review_gui import ReviewGUI, ReviewDataManager, main as review_main
from .pdf_viewer import PDFViewer, BlockHighlight
from .variations_panel import VariationsPanel, VariationDisplayData
from .import_dialog import ImportDialog
from .app import BECRMainWindow, main as app_main

__all__ = [
    'ReviewGUI',
    'ReviewDataManager', 
    'PDFViewer',
    'BlockHighlight',
    'VariationsPanel',
    'VariationDisplayData',
    'ImportDialog',
    'BECRMainWindow',
    'review_main',
    'app_main'
]