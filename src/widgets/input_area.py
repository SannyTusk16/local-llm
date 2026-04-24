"""
ForumLLM - Input Area Widget
Text input field with send button and keyboard shortcuts.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTextEdit,
    QPushButton, QLabel, QSizePolicy, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QKeyEvent, QFont, QShortcut, QKeySequence

from typing import Optional, List


class MessageInput(QTextEdit):
    """
    Custom text input that handles Ctrl+Enter for sending.
    """
    
    send_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setPlaceholderText("Type your message here... (Ctrl+Enter to send)")
        self.setAcceptRichText(False)
        
        # Set reasonable size
        self.setMinimumHeight(60)
        self.setMaximumHeight(200)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        # Ctrl+Enter to send
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.send_requested.emit()
            return
        
        # Shift+Enter for newline (default behavior)
        super().keyPressEvent(event)


class InputArea(QWidget):
    """
    Input area widget containing:
    - Multi-line text input
    - Send button
    - Character count
    - Status indicators
    """
    
    # Signals
    message_sent = pyqtSignal(str, list)  # Emits message content + attachment paths
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._is_enabled = True
        self._attachments: List[str] = []
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Initialize the UI components."""
        # Main frame with inset styling
        frame = QFrame()
        frame.setObjectName("inputFrame")
        
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(12, 8, 12, 8)
        frame_layout.setSpacing(8)
        
        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        
        # Text input
        self.text_input = MessageInput()
        self.text_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        input_row.addWidget(self.text_input)
        
        # Button column
        button_col = QVBoxLayout()
        button_col.setSpacing(4)
        
        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.setMinimumHeight(40)
        self.send_btn.setMinimumWidth(80)
        button_col.addWidget(self.send_btn)

        # Attach button
        self.attach_btn = QPushButton("Attach")
        self.attach_btn.setMinimumHeight(30)
        button_col.addWidget(self.attach_btn)
        
        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMinimumHeight(30)
        button_col.addWidget(self.clear_btn)
        
        button_col.addStretch()
        input_row.addLayout(button_col)
        
        frame_layout.addLayout(input_row)
        
        # Status row
        status_row = QHBoxLayout()
        status_row.setSpacing(16)
        
        # Character count
        self.char_count = QLabel("0 characters")
        self.char_count.setStyleSheet("color: #888888; font-size: 11px;")
        status_row.addWidget(self.char_count)

        # Attachment summary
        self.attachments_label = QLabel("No attachments")
        self.attachments_label.setStyleSheet("color: #888888; font-size: 11px;")
        status_row.addWidget(self.attachments_label)
        
        status_row.addStretch()
        
        # Hint text
        hint = QLabel("Ctrl+Enter to send | Shift+Enter for new line")
        hint.setStyleSheet("color: #AAAAAA; font-size: 10px;")
        status_row.addWidget(hint)
        
        frame_layout.addLayout(status_row)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(frame)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.text_input.send_requested.connect(self._on_send)
        self.text_input.textChanged.connect(self._on_text_changed)
        self.send_btn.clicked.connect(self._on_send)
        self.attach_btn.clicked.connect(self._on_attach)
        self.clear_btn.clicked.connect(self.clear)
    
    def _on_send(self) -> None:
        """Handle send action."""
        if not self._is_enabled:
            return
        
        text = self.text_input.toPlainText().strip()
        if text or self._attachments:
            self.message_sent.emit(text, self._attachments.copy())
            self.text_input.clear()
            self._attachments.clear()
            self._update_attachments_label()
            self._refresh_send_enabled()

    def _on_attach(self) -> None:
        """Open file picker for image/document/audio attachments."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach files",
            "",
            "Supported files (*.png *.jpg *.jpeg *.webp *.gif *.bmp *.txt *.md *.pdf *.doc *.docx *.json *.csv *.yaml *.yml *.xml *.wav *.mp3 *.ogg *.m4a *.flac);;All files (*.*)"
        )

        if files:
            self._attachments.extend(files)
            # De-duplicate while preserving order
            self._attachments = list(dict.fromkeys(self._attachments))
            self._update_attachments_label()
            self._refresh_send_enabled()

    def _update_attachments_label(self) -> None:
        """Update the attachment status text."""
        count = len(self._attachments)
        if count == 0:
            self.attachments_label.setText("No attachments")
        elif count == 1:
            self.attachments_label.setText("1 attachment")
        else:
            self.attachments_label.setText(f"{count} attachments")
    
    def _on_text_changed(self) -> None:
        """Handle text change."""
        text = self.text_input.toPlainText()
        char_count = len(text)
        self.char_count.setText(f"{char_count} character{'s' if char_count != 1 else ''}")

        self._refresh_send_enabled()

    def _refresh_send_enabled(self) -> None:
        """Enable send when there is text or at least one attachment."""
        has_text = bool(self.text_input.toPlainText().strip())
        has_attachments = bool(self._attachments)
        self.send_btn.setEnabled(self._is_enabled and (has_text or has_attachments))
    
    def clear(self) -> None:
        """Clear the input field."""
        self.text_input.clear()
        self._attachments.clear()
        self._update_attachments_label()
        self._refresh_send_enabled()
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the input area."""
        self._is_enabled = enabled
        self.text_input.setEnabled(enabled)
        self.attach_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self._refresh_send_enabled()
        
        if not enabled:
            self.text_input.setPlaceholderText("Waiting for response...")
        else:
            self.text_input.setPlaceholderText("Type your message here... (Ctrl+Enter to send)")
    
    def focus_input(self) -> None:
        """Set focus to the text input."""
        self.text_input.setFocus()
    
    def get_text(self) -> str:
        """Get the current input text."""
        return self.text_input.toPlainText()
    
    def set_text(self, text: str) -> None:
        """Set the input text."""
        self.text_input.setPlainText(text)
