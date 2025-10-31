#!/usr/bin/env python3
"""
GUI Configuration Forms for Engine Management

This module provides PySide6-based forms for:
- Viewing and editing engine configurations
- Managing PDF-specific overrides
- Reviewing and approving optimization proposals
- Historical configuration tracking
- Form-based parameter editing with validation
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QGroupBox,
    QScrollArea, QSplitter, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QDialog, QDialogButtonBox, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPalette

from typing import Dict, List, Any, Optional
from pathlib import Path
import json

from ..config.engine_config import (
    EngineConfigurationManager,
    EngineConfiguration,
    ConfigurationType,
    CLIParameter,
    OptimizationSetting
)


class ParameterWidget(QWidget):
    """Widget for editing a single configuration parameter."""
    
    valueChanged = Signal(str, object)  # parameter_name, new_value
    
    def __init__(self, parameter: CLIParameter, current_value: Any = None):
        super().__init__()
        self.parameter = parameter
        self.setup_ui()
        self.set_value(current_value if current_value is not None else parameter.default)
    
    def setup_ui(self):
        """Setup the parameter editing UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Parameter name label
        name_label = QLabel(self.parameter.name)
        name_label.setMinimumWidth(100)
        layout.addWidget(name_label)
        
        # Value editor based on parameter type
        if self.parameter.type == "bool":
            self.editor = QCheckBox()
            self.editor.stateChanged.connect(self._on_bool_changed)
        elif self.parameter.type == "int":
            self.editor = QSpinBox()
            self.editor.setRange(-999999, 999999)
            self.editor.valueChanged.connect(self._on_int_changed)
        elif self.parameter.type == "float":
            self.editor = QDoubleSpinBox()
            self.editor.setRange(-999999.0, 999999.0)
            self.editor.setDecimals(3)
            self.editor.valueChanged.connect(self._on_float_changed)
        elif self.parameter.type == "choice" and self.parameter.choices:
            self.editor = QComboBox()
            self.editor.addItems(self.parameter.choices)
            self.editor.currentTextChanged.connect(self._on_choice_changed)
        else:  # str or default
            self.editor = QLineEdit()
            self.editor.textChanged.connect(self._on_text_changed)
        
        layout.addWidget(self.editor)
        
        # Description label
        desc_label = QLabel(self.parameter.description)
        desc_label.setStyleSheet("color: gray; font-size: 10px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # CLI flag label if available
        if self.parameter.cli_flag:
            cli_label = QLabel(f"({self.parameter.cli_flag})")
            cli_label.setStyleSheet("color: blue; font-size: 9px;")
            layout.addWidget(cli_label)
    
    def set_value(self, value: Any):
        """Set the current value of the parameter."""
        if self.parameter.type == "bool":
            self.editor.setChecked(bool(value))
        elif self.parameter.type == "int":
            self.editor.setValue(int(value) if value is not None else 0)
        elif self.parameter.type == "float":
            self.editor.setValue(float(value) if value is not None else 0.0)
        elif self.parameter.type == "choice":
            if str(value) in self.parameter.choices:
                self.editor.setCurrentText(str(value))
        else:
            self.editor.setText(str(value) if value is not None else "")
    
    def get_value(self) -> Any:
        """Get the current value of the parameter."""
        if self.parameter.type == "bool":
            return self.editor.isChecked()
        elif self.parameter.type == "int":
            return self.editor.value()
        elif self.parameter.type == "float":
            return self.editor.value()
        elif self.parameter.type == "choice":
            return self.editor.currentText()
        else:
            return self.editor.text()
    
    def _on_bool_changed(self, state):
        self.valueChanged.emit(self.parameter.name, state == Qt.Checked)
    
    def _on_int_changed(self, value):
        self.valueChanged.emit(self.parameter.name, value)
    
    def _on_float_changed(self, value):
        self.valueChanged.emit(self.parameter.name, value)
    
    def _on_choice_changed(self, text):
        self.valueChanged.emit(self.parameter.name, text)
    
    def _on_text_changed(self, text):
        self.valueChanged.emit(self.parameter.name, text)


class EngineConfigurationForm(QWidget):
    """Form for editing engine configuration settings."""
    
    configurationChanged = Signal(str, dict)  # engine_name, new_settings
    
    def __init__(self, config_manager: EngineConfigurationManager, engine_name: str):
        super().__init__()
        self.config_manager = config_manager
        self.engine_name = engine_name
        self.parameter_widgets = {}
        self.current_settings = {}
        self.setup_ui()
        self.load_configuration()
    
    def setup_ui(self):
        """Setup the configuration form UI."""
        layout = QVBoxLayout(self)
        
        # Engine name header
        header = QLabel(f"Configuration for {self.engine_name}")
        header.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(header)
        
        # Scroll area for parameters
        scroll = QScrollArea()
        scroll_widget = QWidget()
        self.form_layout = QFormLayout(scroll_widget)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_button)
        
        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.apply_changes)
        button_layout.addWidget(self.apply_button)
        
        layout.addLayout(button_layout)
    
    def load_configuration(self):
        """Load current configuration for the engine."""
        config = self.config_manager.get_engine_configuration(self.engine_name)
        if not config:
            return
        
        self.current_settings = config.default_settings.copy()
        
        # Create parameter widgets
        for param in config.cli_parameters:
            current_value = self.current_settings.get(param.name, param.default)
            widget = ParameterWidget(param, current_value)
            widget.valueChanged.connect(self._on_parameter_changed)
            
            self.parameter_widgets[param.name] = widget
            self.form_layout.addRow(param.name, widget)
    
    def _on_parameter_changed(self, param_name: str, value: Any):
        """Handle parameter value change."""
        self.current_settings[param_name] = value
        self.apply_button.setEnabled(True)
    
    def reset_to_defaults(self):
        """Reset all parameters to default values."""
        config = self.config_manager.get_engine_configuration(self.engine_name)
        if not config:
            return
        
        for param in config.cli_parameters:
            if param.name in self.parameter_widgets:
                self.parameter_widgets[param.name].set_value(param.default)
                self.current_settings[param.name] = param.default
        
        self.apply_button.setEnabled(True)
    
    def apply_changes(self):
        """Apply configuration changes."""
        self.configurationChanged.emit(self.engine_name, self.current_settings.copy())
        self.apply_button.setEnabled(False)


class PDFOverrideForm(QWidget):
    """Form for managing PDF-specific configuration overrides."""
    
    overrideCreated = Signal(str, str, dict)  # engine_name, pdf_path, overrides
    
    def __init__(self, config_manager: EngineConfigurationManager, engine_name: str, pdf_path: str):
        super().__init__()
        self.config_manager = config_manager
        self.engine_name = engine_name
        self.pdf_path = pdf_path
        self.override_widgets = {}
        self.setup_ui()
        self.load_current_overrides()
    
    def setup_ui(self):
        """Setup the PDF override form UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"PDF Overrides: {Path(self.pdf_path).name}")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header)
        
        # Engine and PDF info
        info_layout = QFormLayout()
        info_layout.addRow("Engine:", QLabel(self.engine_name))
        info_layout.addRow("PDF Path:", QLabel(self.pdf_path))
        layout.addLayout(info_layout)
        
        # Current effective configuration
        self.effective_config_text = QTextEdit()
        self.effective_config_text.setMaximumHeight(100)
        self.effective_config_text.setReadOnly(True)
        layout.addWidget(QLabel("Current Effective Configuration:"))
        layout.addWidget(self.effective_config_text)
        
        # Override parameters
        override_group = QGroupBox("Override Parameters")
        self.override_layout = QFormLayout(override_group)
        layout.addWidget(override_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_override_button = QPushButton("Add Override Parameter")
        self.add_override_button.clicked.connect(self.add_override_parameter)
        button_layout.addWidget(self.add_override_button)
        
        self.save_overrides_button = QPushButton("Save Overrides")
        self.save_overrides_button.clicked.connect(self.save_overrides)
        button_layout.addWidget(self.save_overrides_button)
        
        layout.addLayout(button_layout)
        
        self.update_effective_config_display()
    
    def load_current_overrides(self):
        """Load current PDF-specific overrides."""
        # Get current effective configuration
        effective_config = self.config_manager.get_effective_configuration(self.engine_name, self.pdf_path)
        base_config = self.config_manager.get_effective_configuration(self.engine_name)
        
        # Find overrides (differences between effective and base)
        overrides = {}
        for key, value in effective_config.items():
            if key not in base_config or base_config[key] != value:
                overrides[key] = value
        
        # Create widgets for existing overrides
        for param_name, value in overrides.items():
            self.add_override_widget(param_name, value)
    
    def add_override_parameter(self):
        """Add a new override parameter."""
        # Simple dialog to get parameter name and value
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Override Parameter")
        layout = QFormLayout(dialog)
        
        name_edit = QLineEdit()
        value_edit = QLineEdit()
        
        layout.addRow("Parameter Name:", name_edit)
        layout.addRow("Value:", value_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            param_name = name_edit.text().strip()
            value_text = value_edit.text().strip()
            
            if param_name and value_text:
                # Try to convert value to appropriate type
                try:
                    if value_text.lower() in ('true', 'false'):
                        value = value_text.lower() == 'true'
                    elif value_text.isdigit():
                        value = int(value_text)
                    elif '.' in value_text and value_text.replace('.', '').isdigit():
                        value = float(value_text)
                    else:
                        value = value_text
                    
                    self.add_override_widget(param_name, value)
                except ValueError:
                    QMessageBox.warning(self, "Invalid Value", f"Could not parse value: {value_text}")
    
    def add_override_widget(self, param_name: str, value: Any):
        """Add widget for override parameter."""
        if param_name in self.override_widgets:
            return  # Already exists
        
        widget_layout = QHBoxLayout()
        
        # Parameter name
        name_label = QLabel(param_name)
        name_label.setMinimumWidth(100)
        widget_layout.addWidget(name_label)
        
        # Value editor
        if isinstance(value, bool):
            value_widget = QCheckBox()
            value_widget.setChecked(value)
        elif isinstance(value, int):
            value_widget = QSpinBox()
            value_widget.setRange(-999999, 999999)
            value_widget.setValue(value)
        elif isinstance(value, float):
            value_widget = QDoubleSpinBox()
            value_widget.setRange(-999999.0, 999999.0)
            value_widget.setDecimals(3)
            value_widget.setValue(value)
        else:
            value_widget = QLineEdit(str(value))
        
        widget_layout.addWidget(value_widget)
        
        # Remove button
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(lambda: self.remove_override_widget(param_name))
        widget_layout.addWidget(remove_button)
        
        container = QWidget()
        container.setLayout(widget_layout)
        
        self.override_widgets[param_name] = {
            'container': container,
            'value_widget': value_widget
        }
        
        self.override_layout.addWidget(container)
    
    def remove_override_widget(self, param_name: str):
        """Remove override parameter widget."""
        if param_name in self.override_widgets:
            widget_info = self.override_widgets[param_name]
            widget_info['container'].setParent(None)
            del self.override_widgets[param_name]
    
    def get_override_values(self) -> Dict[str, Any]:
        """Get current override values from widgets."""
        overrides = {}
        
        for param_name, widget_info in self.override_widgets.items():
            value_widget = widget_info['value_widget']
            
            if isinstance(value_widget, QCheckBox):
                overrides[param_name] = value_widget.isChecked()
            elif isinstance(value_widget, QSpinBox):
                overrides[param_name] = value_widget.value()
            elif isinstance(value_widget, QDoubleSpinBox):
                overrides[param_name] = value_widget.value()
            elif isinstance(value_widget, QLineEdit):
                text = value_widget.text()
                # Try to convert to appropriate type
                try:
                    if text.lower() in ('true', 'false'):
                        overrides[param_name] = text.lower() == 'true'
                    elif text.isdigit():
                        overrides[param_name] = int(text)
                    elif '.' in text and text.replace('.', '').isdigit():
                        overrides[param_name] = float(text)
                    else:
                        overrides[param_name] = text
                except ValueError:
                    overrides[param_name] = text
        
        return overrides
    
    def save_overrides(self):
        """Save PDF-specific overrides."""
        overrides = self.get_override_values()
        
        if overrides:
            try:
                override_id = self.config_manager.add_pdf_override(
                    self.engine_name, self.pdf_path, overrides
                )
                QMessageBox.information(self, "Success", f"Overrides saved with ID: {override_id}")
                self.overrideCreated.emit(self.engine_name, self.pdf_path, overrides)
                self.update_effective_config_display()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save overrides: {str(e)}")
        else:
            QMessageBox.warning(self, "No Overrides", "No override parameters specified.")
    
    def update_effective_config_display(self):
        """Update the effective configuration display."""
        effective_config = self.config_manager.get_effective_configuration(self.engine_name, self.pdf_path)
        config_text = json.dumps(effective_config, indent=2)
        self.effective_config_text.setPlainText(config_text)


class OptimizationProposalWidget(QWidget):
    """Widget for reviewing and approving optimization proposals."""
    
    proposalApproved = Signal(str)  # proposal_id
    proposalRejected = Signal(str)  # proposal_id
    
    def __init__(self, config_manager: EngineConfigurationManager):
        super().__init__()
        self.config_manager = config_manager
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the optimization proposal UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Optimization Proposals")
        header.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(header)
        
        # Proposals table
        self.proposals_table = QTableWidget()
        self.proposals_table.setColumnCount(6)
        self.proposals_table.setHorizontalHeaderLabels([
            "Engine", "PDF", "Parameter", "Proposed Value", "Confidence", "Actions"
        ])
        layout.addWidget(self.proposals_table)
        
        # Refresh button
        refresh_button = QPushButton("Refresh Proposals")
        refresh_button.clicked.connect(self.load_proposals)
        layout.addWidget(refresh_button)
        
        self.load_proposals()
    
    def load_proposals(self):
        """Load optimization proposals from configuration."""
        self.proposals_table.setRowCount(0)
        
        # Load pending proposals
        proposals = self.config_manager.get_pending_optimization_proposals()
        
        if not proposals:
            return
        
        # Flatten optimization settings for display
        proposal_rows = []
        for proposal in proposals:
            for opt_setting in proposal.optimization_settings:
                proposal_rows.append({
                    'id': proposal.config_id,
                    'engine': proposal.engine_name,
                    'pdf': f"PDF Hash: {proposal.pdf_hash[:8]}..." if proposal.pdf_hash else "Unknown",
                    'parameter': opt_setting.parameter_name,
                    'value': opt_setting.value,
                    'confidence': opt_setting.confidence,
                    'reasoning': opt_setting.reasoning,
                    'performance_impact': opt_setting.performance_impact
                })
        
        self.proposals_table.setRowCount(len(proposal_rows))
        
        for row, proposal in enumerate(proposal_rows):
            self.proposals_table.setItem(row, 0, QTableWidgetItem(proposal['engine']))
            self.proposals_table.setItem(row, 1, QTableWidgetItem(proposal['pdf']))
            self.proposals_table.setItem(row, 2, QTableWidgetItem(proposal['parameter']))
            self.proposals_table.setItem(row, 3, QTableWidgetItem(str(proposal['value'])))
            self.proposals_table.setItem(row, 4, QTableWidgetItem(f"{proposal['confidence']:.2f}"))
            
            # Action buttons
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(0, 0, 0, 0)
            
            approve_button = QPushButton("Approve")
            approve_button.clicked.connect(lambda checked, pid=proposal['id']: self.approve_proposal(pid))
            button_layout.addWidget(approve_button)
            
            reject_button = QPushButton("Reject")
            reject_button.clicked.connect(lambda checked, pid=proposal['id']: self.reject_proposal(pid))
            button_layout.addWidget(reject_button)
            
            # Details button for reasoning and impact
            details_button = QPushButton("Details")
            details_button.clicked.connect(lambda checked, p=proposal: self.show_proposal_details(p))
            button_layout.addWidget(details_button)
            
            self.proposals_table.setCellWidget(row, 5, button_widget)
    
    def approve_proposal(self, proposal_id: str):
        """Approve an optimization proposal."""
        try:
            override_id = self.config_manager.approve_optimization_proposal(proposal_id)
            QMessageBox.information(self, "Success", f"Proposal approved. Override created: {override_id}")
            self.proposalApproved.emit(proposal_id)
            self.load_proposals()  # Refresh
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to approve proposal: {str(e)}")
    
    def reject_proposal(self, proposal_id: str):
        """Reject an optimization proposal."""
        # Mark proposal as inactive without creating override
        try:
            self.config_manager._update_configuration_status(proposal_id, active=False)
            QMessageBox.information(self, "Success", "Proposal rejected.")
            self.proposalRejected.emit(proposal_id)
            self.load_proposals()  # Refresh
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reject proposal: {str(e)}")
    
    def show_proposal_details(self, proposal: Dict[str, Any]):
        """Show detailed information about a proposal."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Proposal Details")
        dialog.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Details text
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        details = f"""
Engine: {proposal['engine']}
PDF: {proposal['pdf']}
Parameter: {proposal['parameter']}
Proposed Value: {proposal['value']}
Confidence: {proposal['confidence']:.2f}

Reasoning:
{proposal['reasoning']}

Performance Impact: {proposal['performance_impact']}
        """.strip()
        
        details_text.setPlainText(details)
        layout.addWidget(details_text)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.exec()


class ConfigurationManagerWidget(QTabWidget):
    """Main widget for managing engine configurations."""
    
    def __init__(self, config_manager: EngineConfigurationManager):
        super().__init__()
        self.config_manager = config_manager
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the main configuration management UI."""
        # Engine configuration tabs
        engines = ["tesseract", "paddleocr", "pymupdf", "docling", "kreuzberg"]
        
        for engine in engines:
            # Ensure engine configuration exists
            if not self.config_manager.get_engine_configuration(engine):
                self.config_manager.add_engine_configuration(engine)
            
            # Create configuration form
            config_form = EngineConfigurationForm(self.config_manager, engine)
            config_form.configurationChanged.connect(self.on_configuration_changed)
            self.addTab(config_form, engine.title())
        
        # Optimization proposals tab
        proposals_widget = OptimizationProposalWidget(self.config_manager)
        proposals_widget.proposalApproved.connect(self.on_proposal_approved)
        proposals_widget.proposalRejected.connect(self.on_proposal_rejected)
        self.addTab(proposals_widget, "Optimization Proposals")
    
    def add_pdf_override_tab(self, engine_name: str, pdf_path: str):
        """Add a tab for PDF-specific overrides."""
        tab_name = f"{engine_name} - {Path(pdf_path).name}"
        
        # Check if tab already exists
        for i in range(self.count()):
            if self.tabText(i) == tab_name:
                self.setCurrentIndex(i)
                return
        
        # Create new PDF override form
        override_form = PDFOverrideForm(self.config_manager, engine_name, pdf_path)
        override_form.overrideCreated.connect(self.on_override_created)
        
        tab_index = self.addTab(override_form, tab_name)
        self.setCurrentIndex(tab_index)
    
    def on_configuration_changed(self, engine_name: str, settings: Dict[str, Any]):
        """Handle configuration changes."""
        # In a real implementation, you might want to save changes immediately
        # or provide a global save mechanism
        print(f"Configuration changed for {engine_name}: {settings}")
    
    def on_override_created(self, engine_name: str, pdf_path: str, overrides: Dict[str, Any]):
        """Handle PDF override creation."""
        print(f"Override created for {engine_name} on {pdf_path}: {overrides}")
    
    def on_proposal_approved(self, proposal_id: str):
        """Handle proposal approval."""
        print(f"Proposal approved: {proposal_id}")
    
    def on_proposal_rejected(self, proposal_id: str):
        """Handle proposal rejection."""
        print(f"Proposal rejected: {proposal_id}")