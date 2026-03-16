"""
ForumLLM - Chat Panel Widget  
Displays conversation messages in a scrollable, styled view.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, QLabel,
    QTextBrowser, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtGui import QFont, QTextCursor, QDesktopServices

from typing import List, Tuple, Optional
from ..utils.markdown_parser import MarkdownParser
from ..core.chat_history import Message


class ChatPanel(QWidget):
    """
    Main chat display panel showing the conversation history.
    Uses QTextBrowser for rich HTML rendering.
    """
    
    # Signals
    copy_code_requested = pyqtSignal(str)  # Code block content
    link_clicked = pyqtSignal(str)  # URL
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._messages: List[Tuple[str, str, str]] = []  # (role, content, thinking)
        self._parser = MarkdownParser()
        self._streaming_content = ""
        self._is_streaming = False
        self._thinking_content = ""  # Thinking/reasoning text
        
        # Token counter for batched rendering
        self._token_count = 0
        self._render_every_n_tokens = 5  # Render every N tokens
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main text browser for displaying messages
        self.text_browser = QTextBrowser()
        self.text_browser.setObjectName("chatBrowser")
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.setOpenLinks(False)
        self.text_browser.anchorClicked.connect(self._on_link_clicked)
        
        # Set default content
        self._show_welcome_message()
        
        layout.addWidget(self.text_browser)
        
        # Styling
        self.setMinimumWidth(400)
    
    def _show_welcome_message(self) -> None:
        """Show welcome message when no chat is active."""
        welcome_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    font-family: Verdana, Tahoma, sans-serif;
                    background-color: #FAFAFA;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100%;
                    margin: 0;
                    padding: 40px;
                }
                .welcome-container {
                    text-align: center;
                    max-width: 500px;
                }
                h1 {
                    font-family: Georgia, "Times New Roman", serif;
                    color: #4A6785;
                    font-size: 28px;
                    margin-bottom: 16px;
                }
                .subtitle {
                    color: #666666;
                    font-size: 14px;
                    margin-bottom: 24px;
                }
                .instructions {
                    background-color: #F5F3F0;
                    border: 1px solid #DDDDDD;
                    border-radius: 6px;
                    padding: 16px;
                    text-align: left;
                    font-size: 13px;
                    line-height: 1.6;
                }
                .instructions ol {
                    margin: 8px 0;
                    padding-left: 20px;
                }
                .instructions li {
                    margin: 6px 0;
                }
                .footer {
                    margin-top: 24px;
                    font-size: 11px;
                    color: #999999;
                }
            </style>
        </head>
        <body>
            <div class="welcome-container">
                <h1>Welcome to ForumLLM</h1>
                <p class="subtitle">A local LLM chat client with a nostalgic aesthetic</p>
                
                <div class="instructions">
                    <strong>Getting Started:</strong>
                    <ol>
                        <li>Select a model from the dropdown on the left</li>
                        <li>Click "New Chat" to start a conversation</li>
                        <li>Type your message and press Ctrl+Enter to send</li>
                    </ol>
                    <p>Your conversations are saved locally and can be accessed from the history panel.</p>
                </div>
                
                <p class="footer">
                    Powered by Ollama | No data leaves your machine
                </p>
            </div>
        </body>
        </html>
        """
        self.text_browser.setHtml(welcome_html)
    
    def clear(self) -> None:
        """Clear all messages and show welcome."""
        self._messages.clear()
        self._streaming_content = ""
        self._thinking_content = ""
        self._is_streaming = False
        self._show_welcome_message()
    
    def clear_for_chat(self) -> None:
        """Clear for a new chat without showing welcome."""
        self._messages.clear()
        self._streaming_content = ""
        self._thinking_content = ""
        self._is_streaming = False
        self.text_browser.clear()
    
    def add_message(self, role: str, content: str, thinking: str = '') -> None:
        """
        Add a complete message to the display.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content (markdown)
            thinking: Optional thinking/reasoning text
        """
        self._messages.append((role, content, thinking))
        self._render_messages()
    
    def start_streaming(self, role: str) -> None:
        """Start streaming a new message."""
        print(f"\n[Assistant]: ", end="", flush=True)
        self._streaming_content = ""
        self._thinking_content = ""
        self._is_streaming = True
        self._token_count = 0
        self._render_messages()
    
    @pyqtSlot(str)
    def append_streaming_token(self, token: str) -> None:
        """Append a token to the streaming message."""
        if self._is_streaming and token:
            self._streaming_content += token
            self._token_count += 1
            # Render every N tokens for performance
            if self._token_count % self._render_every_n_tokens == 0:
                self._render_messages()
    
    @pyqtSlot(str)
    def append_thinking_token(self, token: str) -> None:
        """Append a token to the thinking/reasoning section."""
        if self._is_streaming and token:
            self._thinking_content += token
            self._token_count += 1
            if self._token_count % self._render_every_n_tokens == 0:
                self._render_messages()
    
    def finish_streaming(self) -> str:
        """
        Finish streaming and return the complete content.
        
        Returns:
            The complete streamed content
        """
        print("")  # Newline after response
        content = self._streaming_content
        if content.strip():
            # Include thinking content if present
            if self._thinking_content.strip():
                self._messages.append(('assistant', content, self._thinking_content))
            else:
                self._messages.append(('assistant', content, ''))
        self._streaming_content = ""
        self._thinking_content = ""
        self._is_streaming = False
        self._token_count = 0
        self._render_messages()
        return content
    
    def _render_messages(self) -> None:
        """Render all messages to the text browser."""
        if not self._messages and not self._streaming_content:
            self._show_welcome_message()
            return
        
        # Build message content
        message_parts = []
        
        for msg_data in self._messages:
            if len(msg_data) == 3:
                role, content, thinking = msg_data
            else:
                role, content = msg_data
                thinking = ''
            message_parts.append(self._parser.format_message(content, role, thinking))
        
        # Add streaming content if active
        if self._is_streaming and (self._streaming_content or self._thinking_content):
            message_parts.append(self._parser.format_message(
                self._streaming_content + "...",
                'assistant',
                self._thinking_content
            ))
        elif self._is_streaming:
            message_parts.append("""
            <div class="assistant-message">
                <div class="message-header">Assistant</div>
                <div class="message-content thinking">Thinking...</div>
            </div>
            """)
        
        # Wrap in HTML
        full_html = self._parser._wrap_html('\n'.join(message_parts))
        
        # Preserve scroll position if near bottom
        scrollbar = self.text_browser.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 50
        
        self.text_browser.setHtml(full_html)
        
        # Scroll to bottom if was at bottom
        if was_at_bottom or self._is_streaming:
            scrollbar.setValue(scrollbar.maximum())
    
    def load_conversation(self, messages: List[Message]) -> None:
        """
        Load a conversation from the database.
        
        Args:
            messages: List of Message objects
        """
        self._messages = [(msg.role, msg.content, '') for msg in messages]
        self._streaming_content = ""
        self._thinking_content = ""
        self._is_streaming = False
        self._render_messages()
    
    def _on_link_clicked(self, url: QUrl) -> None:
        """Handle link clicks."""
        url_string = url.toString()
        
        # Check if it's an external link
        if url_string.startswith(('http://', 'https://')):
            QDesktopServices.openUrl(url)
        else:
            self.link_clicked.emit(url_string)
    
    def get_messages(self) -> List[Tuple[str, str, str]]:
        """Get all messages as (role, content, thinking) tuples."""
        return self._messages.copy()
    
    def copy_last_response(self) -> None:
        """Copy the last assistant response to clipboard."""
        for msg in reversed(self._messages):
            role, content, thinking = msg
            if role == 'assistant':
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
                break
    
    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the chat."""
        scrollbar = self.text_browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
