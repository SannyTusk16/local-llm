"""
ForumLLM - Chat History Management
SQLite-based local storage for conversations.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass


@dataclass
class Message:
    """Represents a single chat message."""
    id: Optional[int]
    conversation_id: int
    role: str  # 'user' or 'assistant'
    content: str
    created_at: datetime
    
    @classmethod
    def from_row(cls, row: tuple) -> 'Message':
        return cls(
            id=row[0],
            conversation_id=row[1],
            role=row[2],
            content=row[3],
            created_at=datetime.fromisoformat(row[4])
        )


@dataclass
class Attachment:
    """Represents a persisted attachment linked to a message."""
    id: Optional[int]
    message_id: int
    conversation_id: int
    file_name: str
    file_path: str
    kind: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> 'Attachment':
        return cls(
            id=row[0],
            message_id=row[1],
            conversation_id=row[2],
            file_name=row[3],
            file_path=row[4],
            kind=row[5],
            created_at=datetime.fromisoformat(row[6])
        )


@dataclass
class Conversation:
    """Represents a conversation with metadata."""
    id: Optional[int]
    title: str
    model: str
    system_message: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = None
    
    def __post_init__(self):
        if self.messages is None:
            self.messages = []
    
    @classmethod
    def from_row(cls, row: tuple) -> 'Conversation':
        return cls(
            id=row[0],
            title=row[1],
            model=row[2],
            system_message=row[3],
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5])
        )


class ChatHistory:
    """SQLite-based chat history manager."""
    
    SCHEMA_VERSION = 2

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".forumllm" / "data" / "chat_history.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute('PRAGMA foreign_keys = ON')
        return self._conn
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Create tables
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            );
            
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                model TEXT NOT NULL,
                system_message TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                conversation_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                kind TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id);

            CREATE INDEX IF NOT EXISTS idx_attachments_message
                ON attachments(message_id);
            
            CREATE INDEX IF NOT EXISTS idx_conversations_updated 
                ON conversations(updated_at DESC);
        ''')
        
        # Check and set schema version
        cursor.execute('SELECT version FROM schema_version LIMIT 1')
        row = cursor.fetchone()
        if row is None:
            cursor.execute('INSERT INTO schema_version (version) VALUES (?)', 
                         (self.SCHEMA_VERSION,))
        elif row[0] < self.SCHEMA_VERSION:
            self._migrate_schema(row[0])
        
        conn.commit()

    def _migrate_schema(self, current_version: int) -> None:
        """Apply schema migrations to latest version."""
        conn = self._get_conn()
        cursor = conn.cursor()

        if current_version < 2:
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    conversation_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_attachments_message
                    ON attachments(message_id);
            ''')

            cursor.execute(
                'UPDATE schema_version SET version = ? WHERE version = ?',
                (2, current_version)
            )

        conn.commit()

    def _guess_attachment_kind(self, file_path: str) -> str:
        """Infer attachment kind from extension."""
        suffix = Path(file_path).suffix.lower()
        if suffix in self.IMAGE_EXTENSIONS:
            return 'image'
        if suffix in self.VIDEO_EXTENSIONS:
            return 'video'
        if suffix in self.AUDIO_EXTENSIONS:
            return 'audio'
        return 'document'

    def add_attachments(self, message_id: int, conversation_id: int, file_paths: List[str]) -> None:
        """Persist attachment metadata for a message."""
        if not file_paths:
            return

        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        rows = []
        for raw in file_paths:
            path = Path(raw)
            rows.append(
                (
                    message_id,
                    conversation_id,
                    path.name,
                    str(path),
                    self._guess_attachment_kind(str(path)),
                    now,
                )
            )

        cursor.executemany('''
            INSERT INTO attachments (message_id, conversation_id, file_name, file_path, kind, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', rows)

        conn.commit()

    def get_conversation_attachments(self, conversation_id: int) -> Dict[int, List[Attachment]]:
        """Return attachments grouped by message_id for a conversation."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, message_id, conversation_id, file_name, file_path, kind, created_at
            FROM attachments
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        ''', (conversation_id,))

        by_message: Dict[int, List[Attachment]] = {}
        for row in cursor.fetchall():
            attachment = Attachment.from_row(tuple(row))
            by_message.setdefault(attachment.message_id, []).append(attachment)

        return by_message
    
    def create_conversation(
        self,
        title: str,
        model: str,
        system_message: str = ""
    ) -> Conversation:
        """Create a new conversation."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO conversations (title, model, system_message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, model, system_message, now, now))
        
        conn.commit()
        
        return Conversation(
            id=cursor.lastrowid,
            title=title,
            model=model,
            system_message=system_message,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now)
        )
    
    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID with all messages."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, model, system_message, created_at, updated_at
            FROM conversations WHERE id = ?
        ''', (conversation_id,))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        conversation = Conversation.from_row(tuple(row))
        
        # Load messages
        cursor.execute('''
            SELECT id, conversation_id, role, content, created_at
            FROM messages WHERE conversation_id = ?
            ORDER BY created_at ASC
        ''', (conversation_id,))
        
        conversation.messages = [Message.from_row(tuple(r)) for r in cursor.fetchall()]
        
        return conversation
    
    def list_conversations(self, limit: int = 50, offset: int = 0) -> List[Conversation]:
        """List conversations ordered by most recent update."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, model, system_message, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        return [Conversation.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str
    ) -> Message:
        """Add a message to a conversation."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO messages (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
        ''', (conversation_id, role, content, now))
        
        # Update conversation timestamp
        cursor.execute('''
            UPDATE conversations SET updated_at = ? WHERE id = ?
        ''', (now, conversation_id))
        
        conn.commit()
        
        return Message(
            id=cursor.lastrowid,
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=datetime.fromisoformat(now)
        )
    
    def update_conversation_title(self, conversation_id: int, title: str) -> None:
        """Update conversation title."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE conversations SET title = ?, updated_at = ?
            WHERE id = ?
        ''', (title, datetime.now().isoformat(), conversation_id))
        
        conn.commit()
    
    def delete_conversation(self, conversation_id: int) -> None:
        """Delete a conversation and all its messages."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM attachments WHERE conversation_id = ?', (conversation_id,))
        
        # Messages will be deleted via CASCADE
        cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
        conn.commit()
    
    def search_conversations(self, query: str, limit: int = 20) -> List[Conversation]:
        """Search conversations by title or message content."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        search_pattern = f'%{query}%'
        
        cursor.execute('''
            SELECT DISTINCT c.id, c.title, c.model, c.system_message, 
                   c.created_at, c.updated_at
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.title LIKE ? OR m.content LIKE ?
            ORDER BY c.updated_at DESC
            LIMIT ?
        ''', (search_pattern, search_pattern, limit))
        
        return [Conversation.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def get_conversation_preview(self, conversation_id: int, max_length: int = 100) -> str:
        """Get a preview of the conversation's first message."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT content FROM messages 
            WHERE conversation_id = ? AND role = 'user'
            ORDER BY created_at ASC LIMIT 1
        ''', (conversation_id,))
        
        row = cursor.fetchone()
        if row is None:
            return ""
        
        content = row[0]
        if len(content) > max_length:
            return content[:max_length-3] + "..."
        return content
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
