# ForumLLM - Bug Report

This document lists all identified bugs in the ForumLLM application.

---

## Critical Bugs (App Breaking)

### BUG-001: Tuple Unpacking Error in `copy_last_response()` ✅ FIXED
**File:** `src/widgets/chat_panel.py:295`  
**Severity:** Critical  
**Description:** The `copy_last_response()` method attempts to unpack messages as 2-tuples, but `_messages` stores 3-tuples `(role, content, thinking)`.

**Status:** Fixed - Updated to unpack 3-tuples correctly.

---

### BUG-002: Incorrect Return Type in `get_messages()` ✅ FIXED
**File:** `src/widgets/chat_panel.py:288`  
**Severity:** Critical  
**Description:** The method signature claims to return `List[Tuple[str, str]]` but `_messages` contains 3-tuples.

**Status:** Fixed - Updated return type to `List[Tuple[str, str, str]]`.

---

### BUG-011: Thread-Unsafe `on_complete` and `on_error` Callbacks ✅ FIXED
**File:** `src/app.py:415-445`  
**Severity:** Critical  
**Description:** The `on_complete()` and `on_error()` callbacks use `QTimer.singleShot()` from a background thread. Unlike `QMetaObject.invokeMethod`, `QTimer.singleShot()` called from a non-Qt thread does NOT properly queue to the main thread and silently fails.

```python
# Broken:
def on_complete() -> None:
    QTimer.singleShot(0, finish)  # Called from background thread - FAILS SILENTLY!
```

**Impact:** After LLM response completes:
- App stays stuck in "Generating..." state
- Input remains disabled
- User cannot send new messages
- Switching conversations loses history

**Status:** Fixed - Replaced with PyQt signals (`_generation_complete`, `_generation_error`) which are inherently thread-safe.

---

### BUG-003: High DPI Policy Called After QApplication Creation ✅ FIXED
**File:** `main.py:86`  
**Severity:** Medium  
**Description:** `setHighDpiScaleFactorRoundingPolicy()` must be called BEFORE creating `QApplication`.

**Status:** Fixed - Moved to before `QApplication()` creation.

---

## Medium Bugs (Functional Issues)

### BUG-004: Missing Font "Segoe UI" on macOS ✅ FIXED
**File:** `main.py:79`  
**Severity:** Medium  
**Description:** The application sets "Segoe UI" as the default font, but this is a Windows-only font.

**Status:** Fixed - Now uses cross-platform font stack: `["Segoe UI", "SF Pro Display", "Helvetica Neue", "Ubuntu", "sans-serif"]`

---

### BUG-005: Conversation Context Not Restored When Loading History ✅ FIXED
**File:** `src/app.py:330-345`  
**Severity:** Medium  
**Description:** When loading a previous conversation, only the UI messages are restored. The `OllamaRunner._messages` list stays empty, so the LLM has no context.

**Status:** Fixed - Now populates `ollama._messages` with conversation history after loading.

---

### BUG-006: Thinking Model Content Not Properly Extracted
**File:** `src/core/ollama_runner.py:162-164`  
**Severity:** Medium  
**Description:** The code checks for `"reasoning"` field in the Ollama API response, but most thinking models (like qwen3, deepseek-r1) include thinking in `<think>...</think>` blocks within the content itself, not a separate field.

**Status:** TODO - Needs implementation to parse `<think>` tags from content.

---

## Low Priority Bugs (Minor Issues)

### BUG-007: Unused Imports in chat_panel.py
**File:** `src/widgets/chat_panel.py:6-9`  
**Severity:** Low  
**Description:** Several imported classes are not used (QScrollArea, QFrame, QLabel).

**Status:** Minor - Does not affect functionality.

---

### BUG-008: Debug Print Statements Left in Production Code
**Files:** Multiple  
**Severity:** Low  
**Description:** Debug print statements are scattered throughout the codebase.

**Status:** TODO - Should be removed or converted to proper logging.

---

### BUG-009: Error Handling Missing for Empty Response
**File:** `src/widgets/chat_panel.py:203-205`  
**Severity:** Low  
**Description:** If streaming finishes with no content, the UI shows no feedback to the user.

**Status:** Minor - Edge case.

---

## Summary

| ID | Severity | Status | Description |
|----|----------|--------|-------------|
| BUG-001 | Critical | ✅ FIXED | Tuple unpacking error in copy_last_response |
| BUG-002 | Critical | ✅ FIXED | Wrong return type in get_messages |
| BUG-011 | Critical | ✅ FIXED | Thread-unsafe on_complete/on_error callbacks |
| BUG-003 | Medium | ✅ FIXED | High DPI policy timing |
| BUG-004 | Medium | ✅ FIXED | Missing Segoe UI font |
| BUG-005 | Medium | ✅ FIXED | Conversation context not restored |
| BUG-006 | Medium | TODO | Thinking model `<think>` tag parsing |
| BUG-007 | Low | - | Unused imports |
| BUG-008 | Low | TODO | Debug print statements |
| BUG-009 | Low | - | Empty response handling |

---

## Fixed in This Session

All **critical bugs** that caused the app to get stuck after generation have been fixed:

1. **Thread-safe callbacks** - `on_complete` and `on_error` now use PyQt signals instead of `QTimer.singleShot()`
2. **Tuple unpacking** - Fixed to handle 3-tuples `(role, content, thinking)`
3. **High DPI** - Policy set before QApplication creation
4. **Fonts** - Cross-platform font stack
5. **Conversation context** - History now restored to Ollama when loading conversations
