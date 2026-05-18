import os
import json
import logging
import aiosqlite
from typing import List, Dict, Any, Callable, Awaitable

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "sessions.db")
MAX_WINDOW = int(os.getenv("MAX_WINDOW", "5"))
COMPRESSION_TRIGGER = int(os.getenv("COMPRESSION_TRIGGER", "10"))

COMPRESSION_PROMPT = """Summarize this conversation in under 100 words.
Keep: user's goal, technical terms used, key decisions made, errors seen, and exact function names.
Remove: greetings, filler, repeated questions. Be factual only.
CRITICAL: Do not generalize specific technical constraints. If a specific framework or parameter is mentioned, retain it."""

async def _init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                summary TEXT,
                generation_counter INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        ''')
        await db.commit()

async def add_message(session_id: str, role: str, content: str) -> None:
    """
    Adds a message to the session's short-term memory.
    
    WHAT IT DOES:
    Inserts a new message (user or assistant) into the SQLite messages table for the given session.
    Also ensures the session exists in the sessions table.
    
    WHY IT DOES IT:
    Maintains the exact verbatim conversation history for short-term context window.
    """
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH) as db:
            # Ensure session exists
            await db.execute(
                'INSERT OR IGNORE INTO sessions (session_id, generation_counter) VALUES (?, 0)', 
                (session_id,)
            )
            # Add message
            await db.execute(
                'INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)',
                (session_id, role, content)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to add message for session {session_id}: {e}")

async def get_context(session_id: str) -> List[Dict[str, str]]:
    """
    Retrieves the current context window for an LLM prompt.
    
    WHAT IT DOES:
    Fetches the rolling summary (if it exists) and appends the last MAX_WINDOW messages.
    
    WHY IT DOES IT:
    Prevents context window bloat and excessive token costs. By prepending a rolling summary, 
    we maintain long-term goal awareness without the token penalty of the full history.
    """
    context = []
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH) as db:
            # Get summary
            async with db.execute('SELECT summary FROM sessions WHERE session_id = ?', (session_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    context.append({"role": "system", "content": f"Previous conversation summary: {row[0]}"})
            
            # Get recent messages
            async with db.execute(
                '''SELECT role, content FROM messages 
                   WHERE session_id = ? 
                   ORDER BY timestamp DESC LIMIT ?''', 
                (session_id, MAX_WINDOW)
            ) as cursor:
                rows = await cursor.fetchall()
                # Reverse to get chronological order
                for role, content in reversed(rows):
                    context.append({"role": role, "content": content})
                    
    except Exception as e:
        logger.error(f"Failed to get context for session {session_id}: {e}")
        
    return context

async def should_compress(session_id: str) -> bool:
    """
    Checks if the session is eligible for compression.
    
    WHAT IT DOES:
    Returns True if the session has reached the COMPRESSION_TRIGGER threshold
    beyond the currently summarized messages.
    """
    try:
        await _init_db()
        async with aiosqlite.connect(DB_PATH) as db:
            # Check message count
            async with db.execute('SELECT COUNT(*) FROM messages WHERE session_id = ?', (session_id,)) as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0
            
            # Check generation counter to correctly trigger rolling compression
            async with db.execute('SELECT generation_counter FROM sessions WHERE session_id = ?', (session_id,)) as cursor:
                row = await cursor.fetchone()
                generation = row[0] if row else 0
                
            return count >= (generation + 1) * COMPRESSION_TRIGGER
    except Exception as e:
        logger.error(f"Failed to check compression status for {session_id}: {e}")
        return False

async def compress_session(session_id: str, local_call_fn: Callable[[str], Awaitable[str]]) -> str:
    """
    Executes a rolling summarization of the session using a local LLM.
    
    WHAT IT DOES:
    Gathers unsummarized messages + previous summary, formatting them to creating a rolling summary
    Updates the session with the new summary and increments the generation counter
    """
    if not await should_compress(session_id):
        return ""
        
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get current summary
            async with db.execute('SELECT summary FROM sessions WHERE session_id = ?', (session_id,)) as cursor:
                row = await cursor.fetchone()
                current_summary = row[0] if row and row[0] else ""

            # Get new messages to compress
            async with db.execute(
                'SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC', 
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                
            conversation_text = "\n".join([f"{role.upper()}: {content}" for role, content in rows])
            prompt = f"{COMPRESSION_PROMPT}\n\nPREVIOUS SUMMARY:\n{current_summary}\n\nNEW CONVERSATION:\n{conversation_text}"
            
            # Call local model (injected dependency)
            summary = await local_call_fn(prompt)
            
            # Save and update generation counter
            await db.execute(
                'UPDATE sessions SET summary = ?, generation_counter = generation_counter + 1 WHERE session_id = ?',
                (summary, session_id)
            )
            await db.commit()
            return summary
            
    except Exception as e:
        logger.error(f"Failed to compress session {session_id}: {e}")
        return ""
