"""
ForumLLM - Markdown Parser and Renderer
Converts Markdown to styled HTML for QTextBrowser display.
Includes special handling for code blocks, tables, and math.
"""

import re
import html
from typing import Optional, List, Tuple
import markdown
from markdown.extensions import fenced_code, tables, toc


class MarkdownParser:
    """
    Converts Markdown to HTML with custom styling for ForumLLM.
    Handles code syntax highlighting, tables, and LaTeX math rendering.
    """
    
    # CSS for rendered content
    INLINE_CSS = """
    <style>
        body {
            font-family: Verdana, Tahoma, sans-serif;
            font-size: 13px;
            line-height: 1.5;
            color: #333333;
            margin: 0;
            padding: 8px;
        }
        
        p {
            margin: 0 0 12px 0;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: Georgia, "Times New Roman", serif;
            color: #4A6785;
            margin: 16px 0 8px 0;
            padding-bottom: 4px;
            border-bottom: 1px solid #DDDDDD;
        }
        
        h1 { font-size: 20px; }
        h2 { font-size: 18px; }
        h3 { font-size: 16px; }
        h4 { font-size: 14px; border-bottom: none; }
        
        code {
            font-family: Consolas, "Courier New", monospace;
            background-color: #F4F4F4;
            border: 1px solid #DDDDDD;
            border-radius: 3px;
            padding: 1px 4px;
            font-size: 12px;
        }
        
        pre {
            background-color: #2D2D2D;
            color: #F8F8F2;
            border: 1px solid #1A1A1A;
            border-radius: 4px;
            padding: 12px;
            overflow-x: auto;
            font-family: Consolas, "Courier New", monospace;
            font-size: 12px;
            line-height: 1.4;
            margin: 8px 0;
        }
        
        pre code {
            background: none;
            border: none;
            padding: 0;
            color: inherit;
        }
        
        blockquote {
            margin: 8px 0;
            padding: 8px 12px;
            border-left: 4px solid #4A6785;
            background-color: #F8F6F4;
            color: #555555;
        }
        
        ul, ol {
            margin: 8px 0;
            padding-left: 24px;
        }
        
        li {
            margin: 4px 0;
        }
        
        table {
            border-collapse: collapse;
            margin: 12px 0;
            width: 100%;
            background-color: #FFFFFF;
        }
        
        th {
            background: linear-gradient(to bottom, #F0F0F0, #E0E0E0);
            border: 1px solid #BBBBBB;
            padding: 8px 12px;
            text-align: left;
            font-weight: bold;
            color: #4A6785;
        }
        
        td {
            border: 1px solid #CCCCCC;
            padding: 6px 12px;
        }
        
        tr:nth-child(even) {
            background-color: #F8F8F8;
        }
        
        tr:hover {
            background-color: #F0EDE8;
        }
        
        a {
            color: #4A6785;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        hr {
            border: none;
            border-top: 1px solid #CCCCCC;
            margin: 16px 0;
        }
        
        img {
            max-width: 100%;
            height: auto;
        }
        
        .math-block {
            text-align: center;
            margin: 12px 0;
            padding: 8px;
            background-color: #FAFAFA;
            border: 1px solid #EEEEEE;
            border-radius: 4px;
        }
        
        .math-inline {
            background-color: #FAFAFA;
            padding: 0 2px;
        }
        
        .user-message {
            background-color: #E3F2FD;
            border: 1px solid #90CAF9;
            border-radius: 6px;
            padding: 12px;
            margin: 8px 0;
        }
        
        .assistant-message {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 12px;
            margin: 8px 0;
        }
        
        .message-header {
            font-weight: bold;
            color: #4A6785;
            margin-bottom: 8px;
            padding-bottom: 4px;
            border-bottom: 1px solid #DDDDDD;
        }
        
        .thinking-section {
            margin: 12px 0 8px 0;
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            background-color: #F8F6F4;
        }
        
        .thinking-section details {
            margin: 0;
        }
        
        .thinking-section summary {
            cursor: pointer;
            padding: 8px 12px;
            background: linear-gradient(to bottom, #E8E4DE, #D8D4CE);
            border-bottom: 1px solid #C0C0C0;
            font-weight: 600;
            color: #6B7B8C;
            user-select: none;
            border-radius: 3px 3px 0 0;
        }
        
        .thinking-section summary:hover {
            background: linear-gradient(to bottom, #EAE6E0, #DAD6D0);
        }
        
        .thinking-section summary::-webkit-details-marker {
            display: none;
        }
        
        .thinking-section summary:before {
            content: '▶ ';
            display: inline-block;
            transition: transform 0.2s;
        }
        
        .thinking-section details[open] summary:before {
            transform: rotate(90deg);
        }
        
        .thinking-content {
            padding: 12px;
            color: #555555;
            font-style: italic;
            line-height: 1.6;
            background-color: #FAFAF8;
            border-radius: 0 0 3px 3px;
        }
    </style>
    """
    
    def __init__(self, enable_syntax_highlighting: bool = True):
        self.enable_syntax_highlighting = enable_syntax_highlighting
        
        # Initialize markdown processor with extensions
        self.md = markdown.Markdown(
            extensions=[
                'fenced_code',
                'tables',
                'toc',
                'nl2br',
                'sane_lists'
            ],
            extension_configs={
                'fenced_code': {
                    'lang_prefix': 'language-'
                }
            }
        )
    
    def parse(self, text: str) -> str:
        """
        Convert Markdown text to styled HTML.
        
        Args:
            text: Raw markdown text
            
        Returns:
            HTML string ready for QTextBrowser
        """
        # Reset markdown processor state
        self.md.reset()
        
        # Pre-process: handle math blocks
        text = self._process_math_blocks(text)
        
        # Convert markdown to HTML
        html_content = self.md.convert(text)
        
        # Post-process: syntax highlighting for code blocks
        if self.enable_syntax_highlighting:
            html_content = self._highlight_code_blocks(html_content)
        
        # Wrap in HTML structure with CSS
        return self._wrap_html(html_content)
    
    def _process_math_blocks(self, text: str) -> str:
        """
        Convert LaTeX math blocks to placeholders for later rendering.
        Handles both $...$ (inline) and $$...$$ (block) math.
        """
        # Block math: $$...$$
        text = re.sub(
            r'\$\$(.*?)\$\$',
            lambda m: f'<div class="math-block">{html.escape(m.group(1))}</div>',
            text,
            flags=re.DOTALL
        )
        
        # Inline math: $...$  (but not $$ which would be empty)
        text = re.sub(
            r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)',
            lambda m: f'<span class="math-inline">{html.escape(m.group(1))}</span>',
            text
        )
        
        return text
    
    def _highlight_code_blocks(self, html_content: str) -> str:
        """
        Apply syntax highlighting to code blocks using Pygments.
        """
        try:
            from pygments import highlight
            from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
            from pygments.formatters import HtmlFormatter
            
            # Custom formatter for dark theme
            formatter = HtmlFormatter(
                style='monokai',
                noclasses=True,
                nowrap=True
            )
            
            def highlight_match(match):
                lang = match.group(1) or ''
                code = html.unescape(match.group(2))
                
                try:
                    if lang:
                        lexer = get_lexer_by_name(lang, stripall=True)
                    else:
                        lexer = guess_lexer(code)
                except:
                    lexer = TextLexer()
                
                highlighted = highlight(code, lexer, formatter)
                return f'<pre style="background-color: #272822; color: #F8F8F2; padding: 12px; border-radius: 4px; overflow-x: auto;">{highlighted}</pre>'
            
            # Match code blocks with optional language
            pattern = r'<pre><code class="language-(\w+)">(.*?)</code></pre>'
            html_content = re.sub(pattern, highlight_match, html_content, flags=re.DOTALL)
            
            # Match code blocks without language
            pattern = r'<pre><code>(.*?)</code></pre>'
            html_content = re.sub(
                pattern,
                lambda m: f'<pre style="background-color: #272822; color: #F8F8F2; padding: 12px; border-radius: 4px; overflow-x: auto;">{html.unescape(m.group(1))}</pre>',
                html_content,
                flags=re.DOTALL
            )
            
        except ImportError:
            # Pygments not available, skip highlighting
            pass
        
        return html_content
    
    def _wrap_html(self, content: str) -> str:
        """Wrap content in full HTML document with styles."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {self.INLINE_CSS}
        </head>
        <body>
            {content}
        </body>
        </html>
        """
    
    def format_message(self, content: str, role: str, thinking: str = '') -> str:
        """
        Format a single message with role-specific styling.
        
        Args:
            content: Message content (markdown)
            role: 'user' or 'assistant'
            thinking: Optional thinking/reasoning content to display in collapsible section
            
        Returns:
            HTML formatted message
        """
        # Convert content to HTML (without full wrapper)
        self.md.reset()
        text = self._process_math_blocks(content)
        html_content = self.md.convert(text)
        
        if self.enable_syntax_highlighting:
            html_content = self._highlight_code_blocks(html_content)
        
        if role == 'user':
            header = 'You'
            css_class = 'user-message'
        else:
            header = 'Assistant'
            css_class = 'assistant-message'
        
        # Add thinking section if present
        thinking_html = ''
        if thinking:
            # Process thinking content as markdown too
            self.md.reset()
            thinking_processed = self._process_math_blocks(thinking)
            thinking_html_content = self.md.convert(thinking_processed)
            if self.enable_syntax_highlighting:
                thinking_html_content = self._highlight_code_blocks(thinking_html_content)
            
            thinking_html = f"""
            <div class="thinking-section">
                <details>
                    <summary>💭 Thinking & Reasoning</summary>
                    <div class="thinking-content">{thinking_html_content}</div>
                </details>
            </div>
            """
        
        return f"""
        <div class="{css_class}">
            <div class="message-header">{header}</div>
            {thinking_html}
            <div class="message-content">{html_content}</div>
        </div>
        """
    
    def format_conversation(self, messages: List[Tuple[str, str]]) -> str:
        """
        Format a full conversation with all messages.
        
        Args:
            messages: List of (role, content) tuples
            
        Returns:
            Full HTML document with all messages
        """
        message_html = '\n'.join(
            self.format_message(content, role)
            for role, content in messages
        )
        
        return self._wrap_html(message_html)
    
    @staticmethod
    def escape_for_display(text: str) -> str:
        """Escape text for safe display without markdown processing."""
        return html.escape(text)
