# Ollama Desktop Client - Implementation Plan

## Project Codename: **ForumLLM**

A PyQt6-based Ollama chat client with a nostalgic pre-2015 aesthetic, combining skeuomorphic textures with neomorphic depth.

---

## 1. Design Philosophy

### Visual Direction
- **Primary Aesthetic**: Forum-style interface (think phpBB, vBulletin circa 2008-2012)
- **Secondary Influences**: Neomorphism for buttons/inputs, subtle skeuomorphic textures
- **Color Palette**:
  - Background: `#E8E4DE` (warm paper-like off-white)
  - Primary: `#4A6785` (slate blue - classic forum header)
  - Secondary: `#8B4513` (saddle brown - woody accent)
  - Text: `#333333` (soft black)
  - Borders: `#CCCCCC` with subtle 1px inset shadows
  - Code blocks: `#F5F5F0` with monospace fonts

### Typography
- Headers: Georgia, serif fallback
- Body: Verdana, Tahoma, sans-serif (the classics)
- Code/Output: Consolas, "Courier New", monospace

### UI Elements
- Beveled buttons with slight gradients (not flat, not glossy)
- Inset text areas with subtle inner shadows
- Table-based layouts (spiritually) with clear cell padding
- Proper fieldsets with legends for grouping options
- Status bars at bottom (like real applications used to have)

---

## 2. Architecture Overview

```
forumllm/
├── main.py                 # Application entry point
├── requirements.txt        # Dependencies
├── assets/
│   └── styles/
│       └── forum.qss       # Qt stylesheet (our CSS equivalent)
├── src/
│   ├── __init__.py
│   ├── app.py              # Main application window
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── chat_panel.py   # Chat display area
│   │   ├── input_area.py   # Message input with send button
│   │   ├── sidebar.py      # Model selection & chat history
│   │   ├── settings_dialog.py  # LLM tuning options
│   │   └── math_renderer.py    # LaTeX/math rendering
│   ├── core/
│   │   ├── __init__.py
│   │   ├── ollama_runner.py    # Subprocess wrapper for "ollama run"
│   │   ├── chat_history.py     # SQLite-based local storage
│   │   └── config.py           # Application settings
│   └── utils/
│       ├── __init__.py
│       ├── markdown_parser.py  # Custom MD rendering
│       └── table_formatter.py  # ASCII/Unicode table handling
└── data/
    └── chat_history.db    # SQLite database (created at runtime)
```

---

## 3. Core Features Breakdown

### Feature 1: Ollama Integration
- **Method**: Use `subprocess.Popen` to run `ollama run <model>` 
- **Communication**: stdin/stdout pipe for real-time streaming
- **Model Listing**: Parse output of `ollama list` command
- **Error Handling**: Graceful fallback if Ollama not installed/running

### Feature 2: Chat History (Local Storage)
- **Database**: SQLite3 (no external dependencies)
- **Schema**:
  ```sql
  CREATE TABLE conversations (
      id INTEGER PRIMARY KEY,
      title TEXT,
      model TEXT,
      system_message TEXT,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  );
  
  CREATE TABLE messages (
      id INTEGER PRIMARY KEY,
      conversation_id INTEGER,
      role TEXT,  -- 'user' or 'assistant'
      content TEXT,
      created_at TIMESTAMP,
      FOREIGN KEY(conversation_id) REFERENCES conversations(id)
  );
  
  CREATE TABLE settings (
      key TEXT PRIMARY KEY,
      value TEXT
  );
  ```

### Feature 3: LLM Fine-tuning Options
- **Temperature**: Slider 0.0 - 2.0
- **Top-P**: Slider 0.0 - 1.0
- **Top-K**: Spinbox 1 - 100
- **Repeat Penalty**: Slider 0.0 - 2.0
- **Context Length**: Dropdown (2048, 4096, 8192, 16384)
- **System Message**: Multi-line text area with presets

### Feature 4: Model Selection
- Parse `ollama list` output
- Display in dropdown with model size info
- Remember last used model per-session
- Validate model exists before starting chat

### Feature 5: Rich Content Rendering
- **Math**: Use `matplotlib` for LaTeX rendering to QPixmap
- **Tables**: Parse markdown tables, render with QTableWidget or custom HTML
- **Code Blocks**: Syntax highlighting with Pygments
- **Markdown**: Convert to HTML, display in QTextBrowser

---

## 4. Implementation Phases

### Phase 1: Foundation (Core Infrastructure)
- [x] Create project structure
- [x] Set up requirements.txt
- [x] Implement config.py (settings management)
- [x] Implement ollama_runner.py (subprocess wrapper)
- [x] Implement chat_history.py (SQLite layer)

### Phase 2: UI Shell
- [x] Create main window layout (app.py)
- [x] Design and implement QSS stylesheet
- [x] Build sidebar widget (model list + history)
- [x] Build chat panel (message display)
- [x] Build input area (text input + send)

### Phase 3: Core Functionality
- [x] Wire up ollama subprocess to UI
- [x] Implement streaming response display
- [x] Connect chat history save/load
- [x] Model selection dropdown
- [x] New chat / clear chat actions

### Phase 4: Settings & Fine-tuning
- [x] Settings dialog design
- [x] All slider/spinbox controls
- [x] System message editor with presets
- [x] Settings persistence

### Phase 5: Rich Content
- [x] Markdown parsing and display
- [x] Code block syntax highlighting
- [x] Math formula rendering (LaTeX placeholders)
- [x] Table formatting
- [x] Copy last response functionality

### Phase 6: Polish & Edge Cases
- [x] Error handling and user feedback
- [x] Loading states and streaming indicators
- [x] Keyboard shortcuts
- [x] Window state persistence
- [x] Forum-style QSS styling

---

## 5. Dependencies

```
PyQt6>=6.4.0
pygments>=2.15.0       # Syntax highlighting
matplotlib>=3.7.0      # LaTeX math rendering  
markdown>=3.4.0        # Markdown to HTML
```

---

## 6. Key Technical Decisions

### Why `ollama run` via subprocess?
- Simpler than HTTP API for streaming
- No need for additional libraries
- Direct access to all Ollama features
- More "old school" approach fitting our aesthetic

### Why SQLite?
- Zero configuration
- Single file database
- Ships with Python
- Reliable and battle-tested

### Why Matplotlib for Math?
- Already handles LaTeX natively
- No need for external LaTeX installation
- Can render directly to images for embedding

### UI Scaling Strategy
- Use relative sizes where possible (em-like calculations)
- Respect system DPI settings
- Minimum window size: 800x600
- Recommended: 1200x800

---

## 7. Risk Assessment

| Risk | Mitigation |
|------|------------|
| Ollama not installed | Check on startup, show helpful error |
| Large model responses | Virtual scrolling, lazy rendering |
| Complex LaTeX | Fall back to plain text display |
| SQLite corruption | Periodic backups, corruption recovery |

---

## 8. Styling Reference (QSS Snippets)

```css
/* Forum-style button */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #F8F8F8, stop:1 #E0E0E0);
    border: 1px solid #AAAAAA;
    border-radius: 3px;
    padding: 6px 16px;
    font-family: Verdana, sans-serif;
    font-size: 12px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:1 #E8E8E8);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #D0D0D0, stop:1 #E0E0E0);
    border-style: inset;
}

/* Inset text area */
QTextEdit {
    background-color: #FFFFFF;
    border: 2px solid #CCCCCC;
    border-style: inset;
    padding: 8px;
    font-family: Verdana;
}
```

---

## 9. Execution Order

1. **Create directory structure** (`mkdir -p`)
2. **Write requirements.txt** 
3. **Implement core modules** (config, ollama_runner, chat_history)
4. **Build QSS stylesheet**
5. **Create main window shell**
6. **Implement widgets one by one**
7. **Wire everything together in app.py**
8. **Test with real Ollama models**
9. **Polish and debug**

---

## 10. Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Send Message | Ctrl+Enter |
| New Chat | Ctrl+N |
| Settings | Ctrl+, |
| Focus Input | Ctrl+L |
| Copy Last Response | Ctrl+Shift+C |
| Toggle Sidebar | Ctrl+B |

---

**Status**: IMPLEMENTATION COMPLETE  
**Tests**: Core modules verified, all imports successful  
**Run with**: `python main.py`

*"We build not for today's trends, but for the timeless elegance of properly indented HTML and tables that actually align."*
