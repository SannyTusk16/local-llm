"""
ForumLLM - Sidebar Widget
Contains model selection, chat history list, and new chat button.
Styled like a classic forum navigation panel.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QFrame,
    QLineEdit, QSizePolicy, QMessageBox, QMenu
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QFont, QAction

from typing import List, Optional
from ..core.ollama_runner import OllamaRunner, OllamaModel
from ..core.chat_history import ChatHistory, Conversation


class Sidebar(QWidget):
    """
    Left sidebar containing:
    - Model selector dropdown
    - New Chat button
    - Search field
    - Chat history list
    """
    
    # Signals
    model_selected = pyqtSignal(str)  # Emits model name
    new_chat_requested = pyqtSignal()
    conversation_selected = pyqtSignal(int)  # Emits conversation ID
    conversation_deleted = pyqtSignal(int)  # Emits conversation ID
    settings_requested = pyqtSignal()
    
    def __init__(self, chat_history: ChatHistory, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.chat_history = chat_history
        self._models: List[OllamaModel] = []
        self._current_conversation_id: Optional[int] = None
        
        self._setup_ui()
        self._connect_signals()
        self.refresh_models()
        self.refresh_history()
    
    def _setup_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # === Header ===
        header = QLabel("ForumLLM")
        header.setObjectName("headerLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # === Model Selection Section ===
        model_section = QFrame()
        model_section.setObjectName("sidebarFrame")
        model_layout = QVBoxLayout(model_section)
        model_layout.setContentsMargins(8, 8, 8, 8)
        model_layout.setSpacing(6)
        
        model_label = QLabel("Select Model:")
        model_label.setObjectName("sectionLabel")
        model_layout.addWidget(model_label)
        
        # Model dropdown
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        self.model_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        model_layout.addWidget(self.model_combo)
        
        # Refresh models button
        refresh_btn = QPushButton("Refresh Models")
        refresh_btn.clicked.connect(self.refresh_models)
        model_layout.addWidget(refresh_btn)
        
        layout.addWidget(model_section)
        
        # === New Chat Button ===
        self.new_chat_btn = QPushButton("+ New Chat")
        self.new_chat_btn.setObjectName("newChatButton")
        self.new_chat_btn.setMinimumHeight(36)
        layout.addWidget(self.new_chat_btn)
        
        # === Chat History Section ===
        history_section = QFrame()
        history_section.setObjectName("sidebarFrame")
        history_layout = QVBoxLayout(history_section)
        history_layout.setContentsMargins(8, 8, 8, 8)
        history_layout.setSpacing(6)
        
        history_label = QLabel("Chat History:")
        history_label.setObjectName("sectionLabel")
        history_layout.addWidget(history_label)
        
        # Search field
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search conversations...")
        self.search_field.setClearButtonEnabled(True)
        history_layout.addWidget(self.search_field)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.setAlternatingRowColors(True)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        history_layout.addWidget(self.history_list)
        
        layout.addWidget(history_section, stretch=1)
        
        # === Settings Button ===
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setMinimumHeight(32)
        layout.addWidget(self.settings_btn)
        
        # Set fixed width for sidebar
        self.setMinimumWidth(240)
        self.setMaximumWidth(320)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        self.history_list.itemClicked.connect(self._on_history_item_clicked)
        self.history_list.customContextMenuRequested.connect(self._show_context_menu)
        self.search_field.textChanged.connect(self._on_search_changed)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
    
    def refresh_models(self) -> None:
        """Refresh the list of available models."""
        self.model_combo.clear()
        
        # Check if Ollama is installed
        if not OllamaRunner.is_ollama_installed():
            self.model_combo.addItem("Ollama not found!")
            self._show_ollama_error()
            return
        
        # Get models
        self._models = OllamaRunner.list_models()
        
        if not self._models:
            self.model_combo.addItem("No models installed")
            return
        
        for model in self._models:
            self.model_combo.addItem(f"{model.name} ({model.size})", model.name)
    
    def _show_ollama_error(self) -> None:
        """Show error message about Ollama not being installed."""
        QMessageBox.warning(
            self,
            "Ollama Not Found",
            "Ollama is not installed or not accessible.\n\n"
            "Please install Ollama from https://ollama.ai\n"
            "and ensure it's running before using ForumLLM.",
            QMessageBox.StandardButton.Ok
        )
    
    def refresh_history(self) -> None:
        """Refresh the chat history list."""
        self.history_list.clear()
        
        search_query = self.search_field.text().strip()
        
        if search_query:
            conversations = self.chat_history.search_conversations(search_query)
        else:
            conversations = self.chat_history.list_conversations()
        
        for conv in conversations:
            item = QListWidgetItem()
            # Truncate title if too long
            display_title = conv.title[:35] + "..." if len(conv.title) > 35 else conv.title
            item.setText(display_title)
            item.setToolTip(f"{conv.title}\nModel: {conv.model}\n{conv.updated_at.strftime('%Y-%m-%d %H:%M')}")
            item.setData(Qt.ItemDataRole.UserRole, conv.id)
            
            # Highlight current conversation
            if conv.id == self._current_conversation_id:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            
            self.history_list.addItem(item)
    
    def _on_model_changed(self, index: int) -> None:
        """Handle model selection change."""
        if index >= 0:
            model_name = self.model_combo.itemData(index)
            if model_name:
                self.model_selected.emit(model_name)
    
    def _on_history_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle chat history item click."""
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        if conv_id:
            self._current_conversation_id = conv_id
            self.conversation_selected.emit(conv_id)
    
    def _show_context_menu(self, position) -> None:
        """Show context menu for history items."""
        item = self.history_list.itemAt(position)
        if not item:
            return
        
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        
        delete_action = QAction("Delete Conversation", self)
        delete_action.triggered.connect(lambda: self._delete_conversation(conv_id))
        menu.addAction(delete_action)
        
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(lambda: self._rename_conversation(conv_id, item))
        menu.addAction(rename_action)
        
        menu.exec(self.history_list.mapToGlobal(position))
    
    def _delete_conversation(self, conv_id: int) -> None:
        """Delete a conversation after confirmation."""
        reply = QMessageBox.question(
            self,
            "Delete Conversation",
            "Are you sure you want to delete this conversation?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.chat_history.delete_conversation(conv_id)
            if conv_id == self._current_conversation_id:
                self._current_conversation_id = None
            self.conversation_deleted.emit(conv_id)
            self.refresh_history()
    
    def _rename_conversation(self, conv_id: int, item: QListWidgetItem) -> None:
        """Rename a conversation (inline editing)."""
        # For simplicity, use a dialog
        from PyQt6.QtWidgets import QInputDialog
        
        current_title = item.text()
        new_title, ok = QInputDialog.getText(
            self,
            "Rename Conversation",
            "New title:",
            text=current_title
        )
        
        if ok and new_title.strip():
            self.chat_history.update_conversation_title(conv_id, new_title.strip())
            self.refresh_history()
    
    def _on_search_changed(self, text: str) -> None:
        """Handle search field text change."""
        self.refresh_history()
    
    def get_selected_model(self) -> Optional[str]:
        """Get the currently selected model name."""
        index = self.model_combo.currentIndex()
        if index >= 0:
            return self.model_combo.itemData(index)
        return None
    
    def set_selected_model(self, model_name: str) -> None:
        """Set the selected model by name."""
        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == model_name:
                self.model_combo.setCurrentIndex(i)
                return
    
    def set_current_conversation(self, conv_id: Optional[int]) -> None:
        """Set the current conversation ID for highlighting."""
        self._current_conversation_id = conv_id
        self.refresh_history()
