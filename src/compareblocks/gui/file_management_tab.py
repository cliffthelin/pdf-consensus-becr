# src/compareblocks/gui/file_management_tab.py
"""
File Management Tab for Association Library Interface.

Provides comprehensive file management interface for:
- Root PDF list display with associated NDJSON files
- Extract associations with influence percentage calculations
- Consensus output file tracking and export file management
- Association management options (new associations, edit existing)
- MCP communication layer for all association data requests
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QGroupBox, QSplitter, QTextEdit, QMessageBox,
    QProgressBar, QMenu, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QIcon

from ..mcp.client import MCPClient, MCPConnectionError
from ..association.manager import AssociationManager
from ..config.file_manager import file_manager


class MCPWorker(QThread):
    """Worker thread for MCP communication to avoid blocking UI."""
    
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, operation: str, params: Dict[str, Any]):
        super().__init__()
        self.operation = operation
        self.params = params
        self.mcp_client = None
    
    def run(self):
        """Execute MCP operation in background thread."""
        try:
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Initialize MCP client
            self.mcp_client = MCPClient()
            
            # Execute operation
            if self.operation == "get_associations":
                result = loop.run_until_complete(self._get_associations())
            elif self.operation == "calculate_influence":
                result = loop.run_until_complete(self._calculate_influence())
            elif self.operation == "get_consensus_outputs":
                result = loop.run_until_complete(self._get_consensus_outputs())
            elif self.operation == "refresh_associations":
                result = loop.run_until_complete(self._refresh_associations())
            else:
                result = {"error": f"Unknown operation: {self.operation}"}
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self.mcp_client:
                try:
                    loop.run_until_complete(self.mcp_client.disconnect())
                except:
                    pass
            loop.close()
    
    async def _get_associations(self) -> Dict[str, Any]:
        """Get associations for PDF via MCP."""
        pdf_path = self.params.get("pdf_path")
        
        # For now, use local association manager
        # In production, this would communicate with MCP server
        manager = AssociationManager()
        associations = manager.load_associations_for_pdf(pdf_path)
        
        return {
            "pdf_path": pdf_path,
            "associations": {
                path: {
                    "format_type": content.format_type,
                    "text_length": len(content.text_content),
                    "blocks": len(content.blocks) if hasattr(content, 'blocks') else 0
                }
                for path, content in associations.associations.items()
            },
            "metadata": {
                path: {
                    "file_size": meta.file_size,
                    "last_modified": meta.last_modified.isoformat(),
                    "parsing_success": meta.parsing_success
                }
                for path, meta in associations.metadata.items()
            }
        }
    
    async def _calculate_influence(self) -> Dict[str, Any]:
        """Calculate influence percentages via MCP."""
        pdf_path = self.params.get("pdf_path")
        
        # Placeholder implementation
        # In production, this would communicate with compareblocks.analytics via MCP
        return {
            "pdf_path": pdf_path,
            "influence_percentages": {
                "tesseract": 45.5,
                "pymupdf": 35.2,
                "paddleocr": 19.3
            },
            "total_blocks": 150,
            "consensus_blocks": 145
        }
    
    async def _get_consensus_outputs(self) -> Dict[str, Any]:
        """Get consensus outputs via MCP."""
        pdf_path = self.params.get("pdf_path")
        
        # Placeholder implementation
        # In production, this would communicate with compareblocks.io.writer via MCP
        return {
            "pdf_path": pdf_path,
            "consensus_file": None,
            "export_files": []
        }
    
    async def _refresh_associations(self) -> Dict[str, Any]:
        """Refresh associations via MCP."""
        pdf_path = self.params.get("pdf_path")
        
        # Use local association manager
        manager = AssociationManager()
        associations = manager.refresh_associations(pdf_path)
        
        return {
            "pdf_path": pdf_path,
            "refreshed": True,
            "association_count": len(associations.associations)
        }


class FileManagementTab(QWidget):
    """
    File Management Tab - Primary interface for Association Library.
    
    Displays:
    - Root PDF list with associated NDJSON files
    - Extract associations with influence percentages
    - Consensus output files and exports
    - Association management options
    """
    
    association_selected = Signal(str)  # Emitted when association is selected
    pdf_selected = Signal(str)  # Emitted when PDF is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pdf_path = None
        self.association_data = {}
        self.influence_data = {}
        self.consensus_data = {}
        self.mcp_worker = None
        
        self.setup_ui()
        self.load_initial_data()
    
    def setup_ui(self):
        """Setup the file management UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("📁 Association Library")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.refresh_associations)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Progress bar for MCP operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: PDF tree
        left_panel = self.create_pdf_tree_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: Details
        right_panel = self.create_details_panel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.new_association_button = QPushButton("➕ New Association")
        self.new_association_button.clicked.connect(self.create_new_association)
        actions_layout.addWidget(self.new_association_button)
        
        self.edit_association_button = QPushButton("✏️ Edit Association")
        self.edit_association_button.clicked.connect(self.edit_association)
        self.edit_association_button.setEnabled(False)
        actions_layout.addWidget(self.edit_association_button)
        
        self.delete_association_button = QPushButton("🗑️ Delete Association")
        self.delete_association_button.clicked.connect(self.delete_association)
        self.delete_association_button.setEnabled(False)
        actions_layout.addWidget(self.delete_association_button)
        
        actions_layout.addStretch()
        
        self.export_button = QPushButton("📤 Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        actions_layout.addWidget(self.export_button)
        
        layout.addLayout(actions_layout)
    
    def create_pdf_tree_panel(self) -> QWidget:
        """Create the PDF tree panel showing root PDFs and associations."""
        panel = QGroupBox("Root PDFs and Associations")
        layout = QVBoxLayout(panel)
        
        # Tree widget
        self.pdf_tree = QTreeWidget()
        self.pdf_tree.setHeaderLabels(["Name", "Type", "Status"])
        self.pdf_tree.setColumnWidth(0, 300)
        self.pdf_tree.setColumnWidth(1, 100)
        self.pdf_tree.itemSelectionChanged.connect(self.on_tree_selection_changed)
        self.pdf_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pdf_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        layout.addWidget(self.pdf_tree)
        
        return panel
    
    def create_details_panel(self) -> QWidget:
        """Create the details panel showing association information."""
        panel = QGroupBox("Association Details")
        layout = QVBoxLayout(panel)
        
        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.details_text)
        
        # Influence percentages group
        influence_group = QGroupBox("Influence Percentages")
        influence_layout = QVBoxLayout(influence_group)
        
        self.influence_text = QTextEdit()
        self.influence_text.setReadOnly(True)
        self.influence_text.setMaximumHeight(150)
        self.influence_text.setFont(QFont("Consolas", 9))
        influence_layout.addWidget(self.influence_text)
        
        layout.addWidget(influence_group)
        
        # Consensus outputs group
        consensus_group = QGroupBox("Consensus Outputs")
        consensus_layout = QVBoxLayout(consensus_group)
        
        self.consensus_text = QTextEdit()
        self.consensus_text.setReadOnly(True)
        self.consensus_text.setMaximumHeight(100)
        self.consensus_text.setFont(QFont("Consolas", 9))
        consensus_layout.addWidget(self.consensus_text)
        
        layout.addWidget(consensus_group)
        
        return panel
    
    def load_initial_data(self):
        """Load initial data from configuration."""
        try:
            # Try to load default PDF
            pdf_path = file_manager.get_target_pdf_path()
            if pdf_path and Path(pdf_path).exists():
                self.load_pdf_associations(pdf_path)
        except Exception as e:
            self.details_text.setPlainText(f"Error loading initial data: {e}")
    
    def load_pdf_associations(self, pdf_path: str):
        """Load associations for a PDF via MCP."""
        self.current_pdf_path = pdf_path
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.refresh_button.setEnabled(False)
        
        # Start MCP worker
        self.mcp_worker = MCPWorker("get_associations", {"pdf_path": pdf_path})
        self.mcp_worker.finished.connect(self.on_associations_loaded)
        self.mcp_worker.error.connect(self.on_mcp_error)
        self.mcp_worker.start()
    
    def on_associations_loaded(self, result: Dict[str, Any]):
        """Handle associations loaded from MCP."""
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)
        
        if "error" in result:
            self.details_text.setPlainText(f"Error: {result['error']}")
            return
        
        self.association_data = result
        self.update_pdf_tree()
        self.load_influence_data()
    
    def update_pdf_tree(self):
        """Update the PDF tree with association data."""
        self.pdf_tree.clear()
        
        if not self.association_data:
            return
        
        pdf_path = self.association_data.get("pdf_path")
        if not pdf_path:
            return
        
        # Create root PDF item
        pdf_item = QTreeWidgetItem(self.pdf_tree)
        pdf_item.setText(0, Path(pdf_path).name)
        pdf_item.setText(1, "PDF")
        pdf_item.setText(2, "✅ Loaded")
        pdf_item.setData(0, Qt.UserRole, {"type": "pdf", "path": pdf_path})
        
        # Add NDJSON files section
        associations = self.association_data.get("associations", {})
        if associations:
            ndjson_item = QTreeWidgetItem(pdf_item)
            ndjson_item.setText(0, f"📊 NDJSON Files ({len(associations)})")
            ndjson_item.setText(1, "Section")
            
            for assoc_path, assoc_data in associations.items():
                assoc_item = QTreeWidgetItem(ndjson_item)
                assoc_item.setText(0, Path(assoc_path).name)
                assoc_item.setText(1, assoc_data.get("format_type", "unknown"))
                assoc_item.setText(2, f"{assoc_data.get('blocks', 0)} blocks")
                assoc_item.setData(0, Qt.UserRole, {
                    "type": "association",
                    "path": assoc_path,
                    "data": assoc_data
                })
        
        # Add extract associations section (placeholder)
        extract_item = QTreeWidgetItem(pdf_item)
        extract_item.setText(0, "🔗 Extract Associations")
        extract_item.setText(1, "Section")
        extract_item.setText(2, "Loading...")
        
        # Add consensus outputs section (placeholder)
        consensus_item = QTreeWidgetItem(pdf_item)
        consensus_item.setText(0, "✅ Consensus Output")
        consensus_item.setText(1, "Section")
        consensus_item.setText(2, "Loading...")
        
        # Add exports section (placeholder)
        exports_item = QTreeWidgetItem(pdf_item)
        exports_item.setText(0, "📤 Exports")
        exports_item.setText(1, "Section")
        exports_item.setText(2, "None")
        
        # Expand root item
        pdf_item.setExpanded(True)
    
    def load_influence_data(self):
        """Load influence percentage data via MCP."""
        if not self.current_pdf_path:
            return
        
        # Start MCP worker for influence calculation
        self.mcp_worker = MCPWorker("calculate_influence", {"pdf_path": self.current_pdf_path})
        self.mcp_worker.finished.connect(self.on_influence_loaded)
        self.mcp_worker.error.connect(self.on_mcp_error)
        self.mcp_worker.start()
    
    def on_influence_loaded(self, result: Dict[str, Any]):
        """Handle influence data loaded from MCP."""
        if "error" in result:
            self.influence_text.setPlainText(f"Error: {result['error']}")
            return
        
        self.influence_data = result
        self.update_influence_display()
        self.load_consensus_data()
    
    def update_influence_display(self):
        """Update the influence percentage display."""
        if not self.influence_data:
            self.influence_text.setPlainText("No influence data available")
            return
        
        percentages = self.influence_data.get("influence_percentages", {})
        total_blocks = self.influence_data.get("total_blocks", 0)
        consensus_blocks = self.influence_data.get("consensus_blocks", 0)
        
        text = f"Total Blocks: {total_blocks}\n"
        text += f"Consensus Blocks: {consensus_blocks}\n\n"
        text += "Engine Influence:\n"
        
        for engine, percentage in sorted(percentages.items(), key=lambda x: x[1], reverse=True):
            text += f"  {engine:15s}: {percentage:5.1f}%\n"
        
        self.influence_text.setPlainText(text)
    
    def load_consensus_data(self):
        """Load consensus output data via MCP."""
        if not self.current_pdf_path:
            return
        
        # Start MCP worker for consensus outputs
        self.mcp_worker = MCPWorker("get_consensus_outputs", {"pdf_path": self.current_pdf_path})
        self.mcp_worker.finished.connect(self.on_consensus_loaded)
        self.mcp_worker.error.connect(self.on_mcp_error)
        self.mcp_worker.start()
    
    def on_consensus_loaded(self, result: Dict[str, Any]):
        """Handle consensus data loaded from MCP."""
        if "error" in result:
            self.consensus_text.setPlainText(f"Error: {result['error']}")
            return
        
        self.consensus_data = result
        self.update_consensus_display()
    
    def update_consensus_display(self):
        """Update the consensus outputs display."""
        if not self.consensus_data:
            self.consensus_text.setPlainText("No consensus data available")
            return
        
        consensus_file = self.consensus_data.get("consensus_file")
        export_files = self.consensus_data.get("export_files", [])
        
        text = ""
        if consensus_file:
            text += f"Consensus File: {Path(consensus_file).name}\n"
        else:
            text += "Consensus File: Not generated\n"
        
        text += f"\nExport Files: {len(export_files)}\n"
        for export_file in export_files:
            text += f"  - {Path(export_file).name}\n"
        
        self.consensus_text.setPlainText(text)
    
    def on_tree_selection_changed(self):
        """Handle tree selection change."""
        selected_items = self.pdf_tree.selectedItems()
        if not selected_items:
            self.edit_association_button.setEnabled(False)
            self.delete_association_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.details_text.clear()
            return
        
        item = selected_items[0]
        item_data = item.data(0, Qt.UserRole)
        
        if not item_data:
            return
        
        item_type = item_data.get("type")
        
        if item_type == "pdf":
            self.show_pdf_details(item_data)
            self.edit_association_button.setEnabled(False)
            self.delete_association_button.setEnabled(False)
            self.export_button.setEnabled(True)
        elif item_type == "association":
            self.show_association_details(item_data)
            self.edit_association_button.setEnabled(True)
            self.delete_association_button.setEnabled(True)
            self.export_button.setEnabled(False)
    
    def show_pdf_details(self, item_data: Dict[str, Any]):
        """Show details for selected PDF."""
        pdf_path = item_data.get("path")
        if not pdf_path:
            return
        
        text = f"PDF File: {Path(pdf_path).name}\n"
        text += f"Path: {pdf_path}\n\n"
        
        if Path(pdf_path).exists():
            stat = Path(pdf_path).stat()
            text += f"Size: {stat.st_size / 1024 / 1024:.2f} MB\n"
            text += f"Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        text += f"\nAssociations: {len(self.association_data.get('associations', {}))}\n"
        
        self.details_text.setPlainText(text)
    
    def show_association_details(self, item_data: Dict[str, Any]):
        """Show details for selected association."""
        assoc_path = item_data.get("path")
        assoc_data = item_data.get("data", {})
        
        if not assoc_path:
            return
        
        text = f"Association File: {Path(assoc_path).name}\n"
        text += f"Path: {assoc_path}\n"
        text += f"Format: {assoc_data.get('format_type', 'unknown')}\n"
        text += f"Text Length: {assoc_data.get('text_length', 0):,} characters\n"
        text += f"Blocks: {assoc_data.get('blocks', 0)}\n\n"
        
        # Get metadata if available
        metadata = self.association_data.get("metadata", {}).get(assoc_path)
        if metadata:
            text += f"File Size: {metadata.get('file_size', 0) / 1024:.2f} KB\n"
            text += f"Last Modified: {metadata.get('last_modified', 'unknown')}\n"
            text += f"Parsing: {'✅ Success' if metadata.get('parsing_success') else '❌ Failed'}\n"
        
        self.details_text.setPlainText(text)
    
    def show_tree_context_menu(self, position):
        """Show context menu for tree items."""
        item = self.pdf_tree.itemAt(position)
        if not item:
            return
        
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return
        
        menu = QMenu(self)
        
        item_type = item_data.get("type")
        
        if item_type == "pdf":
            menu.addAction("🔄 Refresh Associations", lambda: self.refresh_associations())
            menu.addAction("📊 View Statistics", lambda: self.view_statistics())
            menu.addAction("📤 Export All", lambda: self.export_results())
        elif item_type == "association":
            menu.addAction("👁️ View Content", lambda: self.view_association_content(item_data))
            menu.addAction("✏️ Edit", lambda: self.edit_association())
            menu.addAction("🗑️ Delete", lambda: self.delete_association())
        
        menu.exec(self.pdf_tree.viewport().mapToGlobal(position))
    
    def refresh_associations(self):
        """Refresh associations for current PDF."""
        if not self.current_pdf_path:
            QMessageBox.warning(self, "No PDF", "No PDF selected to refresh")
            return
        
        self.load_pdf_associations(self.current_pdf_path)
    
    def create_new_association(self):
        """Create a new association."""
        # Open file dialog to select association file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Association File",
            "",
            "All Supported Files (*.json *.csv *.txt *.md *.html);;JSON Files (*.json);;CSV Files (*.csv);;Text Files (*.txt);;Markdown Files (*.md);;HTML Files (*.html)"
        )
        
        if file_path:
            QMessageBox.information(
                self,
                "Association Created",
                f"New association created:\n{Path(file_path).name}\n\nRefresh to see changes."
            )
    
    def edit_association(self):
        """Edit selected association."""
        selected_items = self.pdf_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        item_data = item.data(0, Qt.UserRole)
        
        if item_data and item_data.get("type") == "association":
            assoc_path = item_data.get("path")
            QMessageBox.information(
                self,
                "Edit Association",
                f"Edit association:\n{Path(assoc_path).name}\n\n(Edit functionality to be implemented)"
            )
    
    def delete_association(self):
        """Delete selected association."""
        selected_items = self.pdf_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        item_data = item.data(0, Qt.UserRole)
        
        if item_data and item_data.get("type") == "association":
            assoc_path = item_data.get("path")
            reply = QMessageBox.question(
                self,
                "Delete Association",
                f"Delete association:\n{Path(assoc_path).name}\n\nAre you sure?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                QMessageBox.information(
                    self,
                    "Deleted",
                    f"Association deleted:\n{Path(assoc_path).name}\n\n(Delete functionality to be implemented)"
                )
    
    def export_results(self):
        """Export results for current PDF."""
        if not self.current_pdf_path:
            QMessageBox.warning(self, "No PDF", "No PDF selected to export")
            return
        
        # Open directory dialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            ""
        )
        
        if directory:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Results exported to:\n{directory}\n\n(Export functionality to be implemented)"
            )
    
    def view_statistics(self):
        """View statistics for current PDF."""
        if not self.current_pdf_path:
            return
        
        stats_text = "PDF Statistics\n"
        stats_text += "=" * 50 + "\n\n"
        stats_text += f"PDF: {Path(self.current_pdf_path).name}\n\n"
        
        if self.association_data:
            stats_text += f"Associations: {len(self.association_data.get('associations', {}))}\n"
        
        if self.influence_data:
            stats_text += f"Total Blocks: {self.influence_data.get('total_blocks', 0)}\n"
            stats_text += f"Consensus Blocks: {self.influence_data.get('consensus_blocks', 0)}\n"
        
        QMessageBox.information(self, "Statistics", stats_text)
    
    def view_association_content(self, item_data: Dict[str, Any]):
        """View content of association file."""
        assoc_path = item_data.get("path")
        if not assoc_path or not Path(assoc_path).exists():
            QMessageBox.warning(self, "Error", "Association file not found")
            return
        
        try:
            with open(assoc_path, 'r', encoding='utf-8') as f:
                content = f.read(1000)  # Read first 1000 characters
            
            if len(content) == 1000:
                content += "\n\n... (truncated)"
            
            QMessageBox.information(
                self,
                f"Content: {Path(assoc_path).name}",
                content
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read file: {e}")
    
    def on_mcp_error(self, error_message: str):
        """Handle MCP communication error."""
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)
        
        QMessageBox.critical(
            self,
            "MCP Communication Error",
            f"Failed to communicate with MCP server:\n\n{error_message}\n\nOperating in offline mode."
        )
        
        # Show offline mode message in details
        self.details_text.setPlainText(
            f"MCP Communication Error:\n{error_message}\n\n"
            "Operating in offline mode. Some features may be unavailable."
        )
    
    def set_current_pdf(self, pdf_path: str):
        """Set the current PDF and load its associations."""
        if pdf_path and Path(pdf_path).exists():
            self.load_pdf_associations(pdf_path)
    
    def get_current_pdf(self) -> Optional[str]:
        """Get the current PDF path."""
        return self.current_pdf_path
