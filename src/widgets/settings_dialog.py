"""
ForumLLM - Settings Dialog
LLM fine-tuning options and application settings.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QPushButton, QGroupBox, QTabWidget,
    QWidget, QFrame, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from typing import Optional
from ..core.config import Config, LLMSettings


class SettingsDialog(QDialog):
    """
    Settings dialog with tabs for:
    - LLM Parameters (temperature, top_p, etc.)
    - System Message
    - Application Settings
    """
    
    # Signals
    settings_changed = pyqtSignal()
    
    def __init__(self, config: Config, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config = config
        
        self.setWindowTitle("ForumLLM Settings")
        self.setMinimumSize(500, 500)
        self.setModal(True)
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # === LLM Parameters Tab ===
        llm_tab = QWidget()
        llm_layout = QVBoxLayout(llm_tab)
        llm_layout.setContentsMargins(12, 12, 12, 12)
        llm_layout.setSpacing(16)
        
        # Temperature
        temp_group = QGroupBox("Temperature")
        temp_layout = QGridLayout(temp_group)
        
        temp_layout.addWidget(QLabel("Controls randomness (0 = deterministic, 2 = very random):"), 0, 0, 1, 2)
        
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 200)
        self.temp_slider.setSingleStep(5)
        temp_layout.addWidget(self.temp_slider, 1, 0)
        
        self.temp_value = QLabel("0.7")
        self.temp_value.setMinimumWidth(40)
        self.temp_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        temp_layout.addWidget(self.temp_value, 1, 1)
        
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_value.setText(f"{v/100:.2f}")
        )
        
        llm_layout.addWidget(temp_group)
        
        # Top-P
        topp_group = QGroupBox("Top-P (Nucleus Sampling)")
        topp_layout = QGridLayout(topp_group)
        
        topp_layout.addWidget(QLabel("Consider tokens with cumulative probability (0.1 = focused, 1.0 = all):"), 0, 0, 1, 2)
        
        self.topp_slider = QSlider(Qt.Orientation.Horizontal)
        self.topp_slider.setRange(10, 100)
        self.topp_slider.setSingleStep(5)
        topp_layout.addWidget(self.topp_slider, 1, 0)
        
        self.topp_value = QLabel("0.9")
        self.topp_value.setMinimumWidth(40)
        self.topp_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        topp_layout.addWidget(self.topp_value, 1, 1)
        
        self.topp_slider.valueChanged.connect(
            lambda v: self.topp_value.setText(f"{v/100:.2f}")
        )
        
        llm_layout.addWidget(topp_group)
        
        # Top-K
        topk_group = QGroupBox("Top-K")
        topk_layout = QHBoxLayout(topk_group)
        
        topk_layout.addWidget(QLabel("Number of tokens to consider:"))
        
        self.topk_spin = QSpinBox()
        self.topk_spin.setRange(1, 100)
        self.topk_spin.setValue(40)
        topk_layout.addWidget(self.topk_spin)
        
        topk_layout.addStretch()
        
        llm_layout.addWidget(topk_group)
        
        # Repeat Penalty
        repeat_group = QGroupBox("Repeat Penalty")
        repeat_layout = QGridLayout(repeat_group)
        
        repeat_layout.addWidget(QLabel("Penalize repetition (1.0 = no penalty, 2.0 = strong):"), 0, 0, 1, 2)
        
        self.repeat_slider = QSlider(Qt.Orientation.Horizontal)
        self.repeat_slider.setRange(100, 200)
        self.repeat_slider.setSingleStep(5)
        repeat_layout.addWidget(self.repeat_slider, 1, 0)
        
        self.repeat_value = QLabel("1.1")
        self.repeat_value.setMinimumWidth(40)
        self.repeat_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        repeat_layout.addWidget(self.repeat_value, 1, 1)
        
        self.repeat_slider.valueChanged.connect(
            lambda v: self.repeat_value.setText(f"{v/100:.2f}")
        )
        
        llm_layout.addWidget(repeat_group)
        
        # Context Length
        ctx_group = QGroupBox("Context Length")
        ctx_layout = QHBoxLayout(ctx_group)
        
        ctx_layout.addWidget(QLabel("Maximum context window:"))
        
        self.ctx_combo = QComboBox()
        self.ctx_combo.addItems(["2048", "4096", "8192", "16384", "32768"])
        ctx_layout.addWidget(self.ctx_combo)
        
        ctx_layout.addStretch()
        
        llm_layout.addWidget(ctx_group)
        
        llm_layout.addStretch()
        
        self.tabs.addTab(llm_tab, "LLM Parameters")
        
        # === System Message Tab ===
        system_tab = QWidget()
        system_layout = QVBoxLayout(system_tab)
        system_layout.setContentsMargins(12, 12, 12, 12)
        system_layout.setSpacing(12)
        
        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Presets:"))
        
        self.preset_combo = QComboBox()
        self.preset_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        presets_layout.addWidget(self.preset_combo)
        
        apply_preset_btn = QPushButton("Apply")
        apply_preset_btn.clicked.connect(self._apply_preset)
        presets_layout.addWidget(apply_preset_btn)
        
        system_layout.addLayout(presets_layout)
        
        # System message editor
        system_layout.addWidget(QLabel("System Message:"))
        
        self.system_edit = QTextEdit()
        self.system_edit.setPlaceholderText(
            "Enter the system message that defines the assistant's behavior..."
        )
        system_layout.addWidget(self.system_edit)
        
        # Save as preset
        save_preset_layout = QHBoxLayout()
        save_preset_layout.addStretch()
        
        save_preset_btn = QPushButton("Save as Preset")
        save_preset_btn.clicked.connect(self._save_preset)
        save_preset_layout.addWidget(save_preset_btn)
        
        system_layout.addLayout(save_preset_layout)
        
        self.tabs.addTab(system_tab, "System Message")
        
        # === About Tab ===
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)
        about_layout.setContentsMargins(20, 20, 20, 20)
        about_layout.setSpacing(16)
        
        title = QLabel("ForumLLM")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #4A6785;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(title)
        
        subtitle = QLabel("A nostalgic local LLM chat client")
        subtitle.setStyleSheet("font-size: 13px; color: #666666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(subtitle)
        
        about_layout.addSpacing(20)
        
        info_text = QLabel(
            "ForumLLM provides a clean interface for interacting with local LLMs via Ollama.\n\n"
            "Features:\n"
            "  - Chat history saved locally\n"
            "  - Customizable LLM parameters\n"
            "  - Markdown and code syntax highlighting\n"
            "  - Classic forum-inspired aesthetic\n\n"
            "All conversations stay on your machine.\n"
            "No data is sent to external servers."
        )
        info_text.setStyleSheet("font-size: 12px; line-height: 1.5;")
        info_text.setWordWrap(True)
        about_layout.addWidget(info_text)
        
        about_layout.addStretch()
        
        credits = QLabel("Built with PyQt6 and Ollama")
        credits.setStyleSheet("font-size: 10px; color: #AAAAAA;")
        credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(credits)
        
        self.tabs.addTab(about_tab, "About")
        
        layout.addWidget(self.tabs)
        
        # === Button Row ===
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        
        button_row.addStretch()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        button_row.addWidget(reset_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_and_close)
        button_row.addWidget(save_btn)
        
        layout.addLayout(button_row)
    
    def _load_settings(self) -> None:
        """Load current settings into the UI."""
        llm = self.config.llm
        
        # LLM parameters
        self.temp_slider.setValue(int(llm.temperature * 100))
        self.topp_slider.setValue(int(llm.top_p * 100))
        self.topk_spin.setValue(llm.top_k)
        self.repeat_slider.setValue(int(llm.repeat_penalty * 100))
        
        # Context length
        ctx_index = self.ctx_combo.findText(str(llm.context_length))
        if ctx_index >= 0:
            self.ctx_combo.setCurrentIndex(ctx_index)
        
        # System message
        self.system_edit.setPlainText(llm.system_message)
        
        # Presets
        self._load_presets()
    
    def _load_presets(self) -> None:
        """Load system message presets into combo box."""
        self.preset_combo.clear()
        for name in self.config.system_presets.keys():
            self.preset_combo.addItem(name)
    
    def _apply_preset(self) -> None:
        """Apply selected preset to system message."""
        preset_name = self.preset_combo.currentText()
        if preset_name in self.config.system_presets:
            self.system_edit.setPlainText(self.config.system_presets[preset_name])
    
    def _save_preset(self) -> None:
        """Save current system message as a new preset."""
        from PyQt6.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(
            self,
            "Save Preset",
            "Preset name:",
            text=""
        )
        
        if ok and name.strip():
            message = self.system_edit.toPlainText()
            self.config.add_system_preset(name.strip(), message)
            self._load_presets()
            
            # Select the new preset
            index = self.preset_combo.findText(name.strip())
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
    
    def _reset_defaults(self) -> None:
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            defaults = LLMSettings()
            self.temp_slider.setValue(int(defaults.temperature * 100))
            self.topp_slider.setValue(int(defaults.top_p * 100))
            self.topk_spin.setValue(defaults.top_k)
            self.repeat_slider.setValue(int(defaults.repeat_penalty * 100))
            self.ctx_combo.setCurrentIndex(
                self.ctx_combo.findText(str(defaults.context_length))
            )
            self.system_edit.setPlainText(defaults.system_message)
    
    def _save_and_close(self) -> None:
        """Save settings and close dialog."""
        # Update config
        self.config.update_llm_settings(
            temperature=self.temp_slider.value() / 100,
            top_p=self.topp_slider.value() / 100,
            top_k=self.topk_spin.value(),
            repeat_penalty=self.repeat_slider.value() / 100,
            context_length=int(self.ctx_combo.currentText()),
            system_message=self.system_edit.toPlainText()
        )
        
        # Save to file
        self.config.save()
        
        self.settings_changed.emit()
        self.accept()
    
    def get_settings(self) -> dict:
        """Get current settings as a dictionary."""
        return {
            'temperature': self.temp_slider.value() / 100,
            'top_p': self.topp_slider.value() / 100,
            'top_k': self.topk_spin.value(),
            'repeat_penalty': self.repeat_slider.value() / 100,
            'context_length': int(self.ctx_combo.currentText()),
            'system_message': self.system_edit.toPlainText()
        }
