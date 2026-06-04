# AI Personal Chef — React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade React chat UI with FastAPI SSE backend, replacing Streamlit.

**Architecture:** FastAPI wraps the existing LangGraph `chat_stream()` as an SSE endpoint. React frontend consumes it via `fetch` with streaming. Two independent subsystems: backend API and frontend UI.

**Tech Stack:** FastAPI, React 18, TypeScript, Tailwind CSS, Zustand, react-markdown, lucide-react, Vite

---

## File Structure

### Backend (new)
- `api/server.py` — FastAPI app with SSE endpoint, CORS, static file serving

### Frontend (new directory: `frontend/`)
- `frontend/package.json` — dependencies
- `frontend/vite.config.ts` — Vite config with proxy
- `frontend/tailwind.config.js` — Tailwind config
- `frontend/tsconfig.json` — TypeScript config
- `frontend/index.html` — entry HTML
- `frontend/src/main.tsx` — React entry point
- `frontend/src/App.tsx` — root component
- `frontend/src/index.css` — global styles + CSS variables + Tailwind
- `frontend/src/types/chat.ts` — type definitions
- `frontend/src/utils/cn.ts` — className helper
- `frontend/src/utils/api.ts` — API client (SSE streaming)
- `frontend/src/store/useChatStore.ts` — Zustand state
- `frontend/src/hooks/useAutoScroll.ts` — auto-scroll hook
- `frontend/src/components/Layout/Sidebar.tsx` — sidebar
- `frontend/src/components/Layout/MainArea.tsx` — main chat area
- `frontend/src/components/Chat/MessageList.tsx` — message list
- `frontend/src/components/Chat/MessageBubble.tsx` — message bubble
- `frontend/src/components/Chat/InputArea.tsx` — input area
- `frontend/src/components/Chat/TypingIndicator.tsx` — typing dots
- `frontend/src/components/RecipeCard/RecipeCard.tsx` — recipe card
- `frontend/src/components/common/ThemeToggle.tsx` — theme toggle
- `frontend/src/components/common/IconButton.tsx` — icon button

---

## Task 1: FastAPI SSE Backend

**Files:**
- Create: `api/server.py`

- [ ] **Step 1: Install FastAPI dependencies**

```bash
cd "C:\Users\成耀辉\Desktop\AI-Personal-Chef"
uv add fastapi uvicorn
```

- [ ] **Step 2: Create the FastAPI server**

Create `api/server.py`:

```python
# api/server.py
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.ai_chef import chat_stream

app = FastAPI(title="AI Personal Chef API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: Any


class ChatRequest(BaseModel):
    messages: List[Message]


@app.post("/api/chat")
async def chat(request: ChatRequest):
    messages = [msg.model_dump() for msg in request.messages]

    def event_stream():
        try:
            for chunk in chat_stream(messages):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 3: Test the server starts**

```bash
cd "C:\Users\成耀辉\Desktop\AI-Personal-Chef"
python -m api.server
```

Expected: Server starts on port 8000 without errors. Ctrl+C to stop.

- [ ] **Step 4: Test health endpoint**

Open browser to `http://localhost:8000/api/health`

Expected: `{"status": "ok"}`

- [ ] **Step 5: Commit**

```bash
git add api/
git commit -m "feat: add FastAPI SSE backend for LangGraph agent"
```

---

## Task 2: Initialize React Project

**Files:**
- Create: `frontend/` (entire directory via Vite scaffold)

- [ ] **Step 1: Scaffold Vite + React + TypeScript project**

```bash
cd "C:\Users\成耀辉\Desktop\AI-Personal-Chef"
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install
npm install zustand react-markdown remark-gfm rehype-highlight lucide-react date-fns highlight.js
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: Configure Vite proxy**

Replace `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: Verify project runs**

```bash
cd frontend
npm run dev
```

Expected: Opens on http://localhost:5173, shows Vite + React default page.

- [ ] **Step 5: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: scaffold React + Vite + TypeScript frontend"
```

---

## Task 3: Global Styles & Design System

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Replace index.css with design system**

Replace `frontend/src/index.css`:

```css
@import "tailwindcss";

:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f7f8fa;
  --bg-sidebar: #f0f2f5;
  --text-primary: #1a1a2e;
  --text-secondary: #6b7280;
  --bubble-user: #e8f0fe;
  --bubble-ai: #ffffff;
  --border-color: #e5e7eb;
  --accent: #4f6ef7;
  --radius: 16px;
  --shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.dark {
  --bg-primary: #1e1e2e;
  --bg-secondary: #2a2a3c;
  --bg-sidebar: #252537;
  --text-primary: #eaeaea;
  --text-secondary: #a0a0b0;
  --bubble-user: #2e3b4e;
  --bubble-ai: #2a2a3c;
  --border-color: #3f3f5a;
  --accent: #7b8cff;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.3s, color 0.3s;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--text-secondary); border-radius: 3px; }

/* Markdown body styles */
.markdown-body h1, .markdown-body h2, .markdown-body h3 {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
}
.markdown-body p { margin-bottom: 0.75em; line-height: 1.7; }
.markdown-body ul, .markdown-body ol { padding-left: 1.5em; margin-bottom: 0.75em; }
.markdown-body li { margin-bottom: 0.25em; }
.markdown-body code {
  background: var(--bg-secondary);
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
}
.markdown-body pre {
  background: var(--bg-secondary);
  padding: 1em;
  border-radius: 8px;
  overflow-x: auto;
  margin-bottom: 1em;
}
.markdown-body pre code {
  background: none;
  padding: 0;
}
.markdown-body table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}
.markdown-body th, .markdown-body td {
  border: 1px solid var(--border-color);
  padding: 0.5em 0.75em;
  text-align: left;
}
.markdown-body blockquote {
  border-left: 3px solid var(--accent);
  padding-left: 1em;
  color: var(--text-secondary);
  margin-bottom: 0.75em;
}

/* Slide-up animation */
@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-slide-up {
  animation: slideUp 0.3s ease-out;
}
```

- [ ] **Step 2: Replace App.tsx with minimal shell**

Replace `frontend/src/App.tsx`:

```tsx
function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden" style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      <div className="flex-1 flex items-center justify-center">
        <p style={{ color: 'var(--text-secondary)' }}>AI Chef — Coming soon</p>
      </div>
    </div>
  )
}

export default App
```

- [ ] **Step 3: Clean up main.tsx**

Replace `frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 4: Delete default assets**

```bash
cd frontend
rm -f src/App.css src/assets/react.svg public/vite.svg
```

- [ ] **Step 5: Verify it renders**

```bash
npm run dev
```

Expected: Clean page with "AI Chef — Coming soon" text, correct colors.

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: add design system CSS variables and global styles"
```

---

## Task 4: Type Definitions & Utilities

**Files:**
- Create: `frontend/src/types/chat.ts`
- Create: `frontend/src/utils/cn.ts`
- Create: `frontend/src/utils/api.ts`

- [ ] **Step 1: Create type definitions**

Create `frontend/src/types/chat.ts`:

```typescript
export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  status?: 'sending' | 'streaming' | 'done' | 'error'
}

export interface RecipeData {
  title: string
  description: string
  imageUrl?: string
  ingredients: string[]
  steps: string[]
  prepTime: string
  cookTime: string
}

export interface Conversation {
  id: string
  title: string
  lastUpdated: number
  messages: Message[]
}
```

- [ ] **Step 2: Create cn utility**

Create `frontend/src/utils/cn.ts`:

```typescript
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}
```

- [ ] **Step 3: Create API client**

Create `frontend/src/utils/api.ts`:

```typescript
import { Message } from '../types/chat'

interface StreamChunk {
  type: 'chunk' | 'done' | 'error'
  content?: string
}

export async function* streamChat(
  messages: Message[]
): AsyncGenerator<string, void, unknown> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data: StreamChunk = JSON.parse(line.slice(6))
        if (data.type === 'chunk' && data.content) {
          yield data.content
        } else if (data.type === 'error') {
          throw new Error(data.content || 'Unknown error')
        } else if (data.type === 'done') {
          return
        }
      }
    }
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/ frontend/src/utils/
git commit -m "feat: add TypeScript types and API client for SSE streaming"
```

---

## Task 5: Zustand Store

**Files:**
- Create: `frontend/src/store/useChatStore.ts`

- [ ] **Step 1: Create the Zustand store**

Create `frontend/src/store/useChatStore.ts`:

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Conversation, Message } from '../types/chat'
import { streamChat } from '../utils/api'

function uuid(): string {
  return crypto.randomUUID()
}

function generateTitle(content: string): string {
  return content.slice(0, 30) + (content.length > 30 ? '...' : '')
}

interface ChatState {
  conversations: Conversation[]
  currentConversationId: string | null
  darkMode: boolean
  searchTerm: string
  isStreaming: boolean

  createNewChat: () => void
  switchConversation: (id: string) => void
  deleteConversation: (id: string) => void
  setSearchTerm: (term: string) => void
  toggleDarkMode: () => void
  sendMessage: (content: string) => Promise<void>

  // Selectors
  currentConversation: () => Conversation | undefined
  currentMessages: () => Message[]
  filteredConversations: () => Conversation[]
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      darkMode: false,
      searchTerm: '',
      isStreaming: false,

      createNewChat: () => {
        const id = uuid()
        const newConv: Conversation = {
          id,
          title: '新对话',
          lastUpdated: Date.now(),
          messages: [],
        }
        set((state) => ({
          conversations: [newConv, ...state.conversations],
          currentConversationId: id,
        }))
      },

      switchConversation: (id) => {
        set({ currentConversationId: id })
      },

      deleteConversation: (id) => {
        set((state) => {
          const remaining = state.conversations.filter((c) => c.id !== id)
          const newCurrentId =
            state.currentConversationId === id
              ? remaining[0]?.id ?? null
              : state.currentConversationId
          return {
            conversations: remaining,
            currentConversationId: newCurrentId,
          }
        })
      },

      setSearchTerm: (term) => set({ searchTerm: term }),

      toggleDarkMode: () =>
        set((state) => ({ darkMode: !state.darkMode })),

      sendMessage: async (content) => {
        const state = get()
        let convId = state.currentConversationId

        // Auto-create conversation if none selected
        if (!convId) {
          get().createNewChat()
          convId = get().currentConversationId
        }

        const userMsg: Message = {
          id: uuid(),
          role: 'user',
          content,
          timestamp: Date.now(),
          status: 'done',
        }

        const assistantMsg: Message = {
          id: uuid(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          status: 'streaming',
        }

        // Add messages to conversation
        set((state) => ({
          isStreaming: true,
          conversations: state.conversations.map((c) =>
            c.id === convId
              ? {
                  ...c,
                  title:
                    c.messages.length === 0
                      ? generateTitle(content)
                      : c.title,
                  lastUpdated: Date.now(),
                  messages: [...c.messages, userMsg, assistantMsg],
                }
              : c
          ),
        }))

        try {
          const currentMessages = get()
            .conversations.find((c) => c.id === convId)
            ?.messages.filter((m) => m.id !== assistantMsg.id) ?? []

          let accumulated = ''
          for await (const chunk of streamChat(currentMessages)) {
            accumulated += chunk
            set((state) => ({
              conversations: state.conversations.map((c) =>
                c.id === convId
                  ? {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantMsg.id
                          ? { ...m, content: accumulated }
                          : m
                      ),
                    }
                  : c
              ),
            }))
          }

          // Mark as done
          set((state) => ({
            isStreaming: false,
            conversations: state.conversations.map((c) =>
              c.id === convId
                ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === assistantMsg.id
                        ? { ...m, status: 'done' }
                        : m
                    ),
                  }
                : c
            ),
          }))
        } catch (error) {
          set((state) => ({
            isStreaming: false,
            conversations: state.conversations.map((c) =>
              c.id === convId
                ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === assistantMsg.id
                        ? {
                            ...m,
                            status: 'error',
                            content: `出错了：${error instanceof Error ? error.message : '未知错误'}`,
                          }
                        : m
                    ),
                  }
                : c
            ),
          }))
        }
      },

      currentConversation: () => {
        const state = get()
        return state.conversations.find(
          (c) => c.id === state.currentConversationId
        )
      },

      currentMessages: () => {
        return get().currentConversation()?.messages ?? []
      },

      filteredConversations: () => {
        const state = get()
        const term = state.searchTerm.toLowerCase()
        if (!term) return state.conversations
        return state.conversations.filter((c) =>
          c.title.toLowerCase().includes(term)
        )
      },
    }),
    {
      name: 'ai-chef-storage',
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
        darkMode: state.darkMode,
      }),
    }
  )
)
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/store/
git commit -m "feat: add Zustand store with conversation management and SSE streaming"
```

---

## Task 6: Custom Hooks

**Files:**
- Create: `frontend/src/hooks/useAutoScroll.ts`

- [ ] **Step 1: Create auto-scroll hook**

Create `frontend/src/hooks/useAutoScroll.ts`:

```typescript
import { useEffect, useRef } from 'react'

export function useAutoScroll<T>(
  containerRef: React.RefObject<HTMLDivElement | null>,
  dependency: T
) {
  const isAtBottom = useRef(true)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = el
      isAtBottom.current = scrollHeight - scrollTop - clientHeight < 100
    }

    el.addEventListener('scroll', handleScroll)
    return () => el.removeEventListener('scroll', handleScroll)
  }, [containerRef])

  useEffect(() => {
    if (isAtBottom.current && containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [dependency, containerRef])
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/
git commit -m "feat: add useAutoScroll hook for chat messages"
```

---

## Task 7: Common Components

**Files:**
- Create: `frontend/src/components/common/IconButton.tsx`
- Create: `frontend/src/components/common/ThemeToggle.tsx`

- [ ] **Step 1: Create IconButton**

Create `frontend/src/components/common/IconButton.tsx`:

```tsx
import { Plus, Search, Trash2, Menu, X } from 'lucide-react'

const iconMap = {
  Plus,
  Search,
  Trash2,
  Menu,
  X,
} as const

interface IconButtonProps {
  icon: keyof typeof iconMap
  onClick: () => void
  label: string
  className?: string
}

export function IconButton({ icon, onClick, label, className = '' }: IconButtonProps) {
  const Icon = iconMap[icon]
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={`p-2 rounded-lg transition-colors hover:bg-[var(--bg-primary)] ${className}`}
      style={{ color: 'var(--text-secondary)' }}
    >
      <Icon size={18} />
    </button>
  )
}
```

- [ ] **Step 2: Create ThemeToggle**

Create `frontend/src/components/common/ThemeToggle.tsx`:

```tsx
import { Moon, Sun } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'

export function ThemeToggle() {
  const { darkMode, toggleDarkMode } = useChatStore()

  return (
    <button
      onClick={toggleDarkMode}
      aria-label="Toggle theme"
      className="p-2 rounded-lg transition-colors hover:bg-[var(--bg-primary)]"
      style={{ color: 'var(--text-secondary)' }}
    >
      {darkMode ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/common/
git commit -m "feat: add IconButton and ThemeToggle components"
```

---

## Task 8: Layout Components

**Files:**
- Create: `frontend/src/components/Layout/Sidebar.tsx`
- Create: `frontend/src/components/Layout/MainArea.tsx`

- [ ] **Step 1: Create Sidebar**

Create `frontend/src/components/Layout/Sidebar.tsx`:

```tsx
import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useChatStore } from '../../store/useChatStore'
import { IconButton } from '../common/IconButton'
import { ThemeToggle } from '../common/ThemeToggle'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const {
    createNewChat,
    switchConversation,
    deleteConversation,
    setSearchTerm,
    currentConversationId,
    filteredConversations,
  } = useChatStore()

  const conversations = filteredConversations()

  const handleNewChat = () => {
    createNewChat()
    onClose()
  }

  const handleSelect = (id: string) => {
    switchConversation(id)
    onClose()
  }

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      <div
        className={`
          fixed md:relative z-50 md:z-auto
          w-[260px] flex-shrink-0 h-full
          border-r flex flex-col
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
        style={{
          backgroundColor: 'var(--bg-sidebar)',
          borderColor: 'var(--border-color)',
        }}
      >
        {/* Header */}
        <div className="p-4 flex items-center justify-between">
          <span className="font-bold text-lg" style={{ color: 'var(--text-primary)' }}>
            AI Chef
          </span>
          <IconButton icon="Plus" onClick={handleNewChat} label="新对话" />
        </div>

        {/* Search */}
        <div className="px-3 mb-2">
          <input
            type="text"
            placeholder="搜索对话..."
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg px-3 py-2 text-sm outline-none"
            style={{
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
            }}
          />
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-2">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => handleSelect(conv.id)}
              className="w-full text-left px-3 py-2 rounded-lg mb-1 truncate transition-colors"
              style={{
                backgroundColor:
                  conv.id === currentConversationId
                    ? 'var(--bg-primary)'
                    : 'transparent',
                color: 'var(--text-primary)',
                borderLeft:
                  conv.id === currentConversationId
                    ? '2px solid var(--accent)'
                    : '2px solid transparent',
              }}
              onMouseEnter={(e) => {
                if (conv.id !== currentConversationId) {
                  e.currentTarget.style.backgroundColor = 'var(--bg-primary)'
                }
              }}
              onMouseLeave={(e) => {
                if (conv.id !== currentConversationId) {
                  e.currentTarget.style.backgroundColor = 'transparent'
                }
              }}
            >
              <div className="text-sm font-medium truncate">{conv.title}</div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                {formatDistanceToNow(conv.lastUpdated, { addSuffix: true, locale: zhCN })}
              </div>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div
          className="p-3 flex items-center justify-between"
          style={{ borderTop: '1px solid var(--border-color)' }}
        >
          <ThemeToggle />
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
            style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
          >
            U
          </div>
        </div>
      </div>
    </>
  )
}
```

- [ ] **Step 2: Create MainArea**

Create `frontend/src/components/Layout/MainArea.tsx`:

```tsx
import { MessageList } from '../Chat/MessageList'
import { InputArea } from '../Chat/InputArea'

export function MainArea() {
  return (
    <div className="flex-1 flex flex-col min-w-0 h-full">
      <MessageList />
      <InputArea />
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Layout/
git commit -m "feat: add Sidebar and MainArea layout components"
```

---

## Task 9: Chat Components

**Files:**
- Create: `frontend/src/components/Chat/MessageBubble.tsx`
- Create: `frontend/src/components/Chat/MessageList.tsx`
- Create: `frontend/src/components/Chat/InputArea.tsx`
- Create: `frontend/src/components/Chat/TypingIndicator.tsx`

- [ ] **Step 1: Create MessageBubble**

Create `frontend/src/components/Chat/MessageBubble.tsx`:

```tsx
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Message } from '../../types/chat'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-slide-up`}>
      <div
        className={`max-w-[80%] px-4 py-3 shadow-sm ${
          isUser
            ? 'rounded-2xl rounded-br-md'
            : 'rounded-2xl rounded-bl-md markdown-body'
        }`}
        style={{
          backgroundColor: isUser ? 'var(--bubble-user)' : 'var(--bubble-ai)',
          color: 'var(--text-primary)',
        }}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create TypingIndicator**

Create `frontend/src/components/Chat/TypingIndicator.tsx`:

```tsx
export function TypingIndicator() {
  return (
    <div className="flex justify-start animate-slide-up">
      <div
        className="px-4 py-3 rounded-2xl rounded-bl-md shadow-sm"
        style={{ backgroundColor: 'var(--bubble-ai)' }}
      >
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2 h-2 rounded-full"
              style={{
                backgroundColor: 'var(--text-secondary)',
                animation: `bounce 1.4s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>
        <style>{`
          @keyframes bounce {
            0%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-6px); }
          }
        `}</style>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create MessageList**

Create `frontend/src/components/Chat/MessageList.tsx`:

```tsx
import { useRef } from 'react'
import { ChefHat } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'
import { useAutoScroll } from '../../hooks/useAutoScroll'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'

function WelcomeScreen() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 px-4">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center"
        style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
      >
        <ChefHat size={32} />
      </div>
      <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
        AI 私人厨师
      </h2>
      <p className="text-center max-w-md" style={{ color: 'var(--text-secondary)' }}>
        告诉我你有什么食材，我来帮你想想做什么好吃的
      </p>
    </div>
  )
}

export function MessageList() {
  const messages = useChatStore((s) => s.currentMessages())
  const isStreaming = useChatStore((s) => s.isStreaming)
  const containerRef = useRef<HTMLDivElement>(null)

  useAutoScroll(containerRef, messages)

  if (messages.length === 0) {
    return <WelcomeScreen />
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-6"
    >
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isStreaming &&
          messages.length > 0 &&
          messages[messages.length - 1].role === 'assistant' &&
          messages[messages.length - 1].content === '' && (
            <TypingIndicator />
          )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create InputArea**

Create `frontend/src/components/Chat/InputArea.tsx`:

```tsx
import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'

export function InputArea() {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const isStreaming = useChatStore((s) => s.isStreaming)

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return
    const msg = input.trim()
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    await sendMessage(msg)
  }

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 150) + 'px'
    }
  }, [input])

  return (
    <div
      className="px-4 py-3"
      style={{ borderTop: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)' }}
    >
      <div className="max-w-3xl mx-auto flex items-end gap-2">
        <button
          className="shrink-0 p-3 rounded-xl transition-colors"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
          aria-label="上传图片"
        >
          <Paperclip size={20} />
        </button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="告诉 AI Chef 你想吃什么..."
          rows={1}
          className="flex-1 resize-none rounded-xl px-4 py-3 outline-none text-sm"
          style={{
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            maxHeight: '150px',
          }}
        />

        <button
          onClick={handleSend}
          disabled={!input.trim() || isStreaming}
          className="shrink-0 p-3 rounded-xl text-white transition-opacity disabled:opacity-40"
          style={{ backgroundColor: 'var(--accent)' }}
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Chat/
git commit -m "feat: add chat components (MessageBubble, MessageList, InputArea, TypingIndicator)"
```

---

## Task 10: Wire Up App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Replace App.tsx with full layout**

Replace `frontend/src/App.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { Menu } from 'lucide-react'
import { Sidebar } from './components/Layout/Sidebar'
import { MainArea } from './components/Layout/MainArea'
import { useChatStore } from './store/useChatStore'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { darkMode, createNewChat } = useChatStore()

  // Apply dark mode class
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
  }, [darkMode])

  // Create initial chat on first load
  useEffect(() => {
    const convs = useChatStore.getState().conversations
    if (convs.length === 0) {
      createNewChat()
    }
  }, [])

  return (
    <div
      className="flex h-screen w-screen overflow-hidden"
      style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)' }}
    >
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* Mobile header */}
        <div
          className="md:hidden flex items-center p-3"
          style={{ borderBottom: '1px solid var(--border-color)' }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg"
            style={{ color: 'var(--text-secondary)' }}
          >
            <Menu size={20} />
          </button>
          <span className="ml-2 font-bold" style={{ color: 'var(--text-primary)' }}>
            AI Chef
          </span>
        </div>

        <MainArea />
      </div>
    </div>
  )
}

export default App
```

- [ ] **Step 2: Verify full app renders**

```bash
cd frontend
npm run dev
```

Expected: Sidebar on left, main area with welcome screen, input at bottom.

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend/src/App.tsx
git commit -m "feat: wire up App.tsx with Sidebar and MainArea"
```

---

## Task 11: Integration Test

**Files:** None (verification only)

- [ ] **Step 1: Start backend**

```bash
cd "C:\Users\成耀辉\Desktop\AI-Personal-Chef"
python -m api.server
```

- [ ] **Step 2: Start frontend (new terminal)**

```bash
cd frontend
npm run dev
```

- [ ] **Step 3: Open browser and test**

1. Go to http://localhost:5173
2. Verify welcome screen shows
3. Type "我有番茄和鸡蛋" and press Enter
4. Verify user message appears on right
5. Verify AI response streams in on left
6. Verify sidebar shows conversation title
7. Click "新对话" and verify new conversation created
8. Switch back to first conversation, verify history preserved
9. Toggle dark mode, verify theme changes
10. Test on narrow viewport (mobile), verify sidebar hides

- [ ] **Step 4: Fix any issues found during testing**

If there are issues, fix them and re-test.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete React frontend with SSE streaming integration"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | FastAPI SSE backend | `api/server.py` |
| 2 | Vite project scaffold | `frontend/` |
| 3 | Global styles & design system | `index.css`, `App.tsx`, `main.tsx` |
| 4 | Types & utilities | `types/chat.ts`, `utils/` |
| 5 | Zustand store | `store/useChatStore.ts` |
| 6 | Auto-scroll hook | `hooks/useAutoScroll.ts` |
| 7 | Common components | `ThemeToggle`, `IconButton` |
| 8 | Layout components | `Sidebar`, `MainArea` |
| 9 | Chat components | `MessageBubble`, `MessageList`, `InputArea`, `TypingIndicator` |
| 10 | Wire up App.tsx | `App.tsx` |
| 11 | Integration test | Manual verification |
