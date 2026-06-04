# AI Personal Chef — React Frontend Design

## Overview

Replace the current Streamlit frontend with a production-grade React + TypeScript + Tailwind CSS chat interface. Add a FastAPI backend to expose the LangGraph agent as a streaming HTTP API.

## Architecture

```
┌─────────────────────┐     SSE      ┌──────────────────────┐
│   React Frontend    │ ──────────►  │   FastAPI Backend     │
│   (Vite + TS +      │   /api/chat  │   (Python)            │
│    Tailwind CSS)    │ ◄──────────  │                       │
│                     │   stream     │   LangGraph Agent     │
│   Port: 5173        │              │   Port: 8000          │
└─────────────────────┘              └──────────────────────┘
```

- **Frontend**: Vite dev server on port 5173, proxies `/api` to backend
- **Backend**: FastAPI on port 8000, wraps `chat_stream()` with SSE
- **Data flow**: User input → POST /api/chat → FastAPI converts to LangGraph format → streams chunks back via SSE

## Backend (FastAPI)

### Endpoint: `POST /api/chat`

Request body:
```json
{
  "messages": [
    {"role": "user", "content": "我有番茄和鸡蛋"},
    {"role": "assistant", "content": "好的，我来帮你..."}
  ]
}
```

Response: SSE stream (`text/event-stream`)
```
data: {"type": "chunk", "content": "根据你提供的食材"}
data: {"type": "chunk", "content": "，我推荐..."}
data: {"type": "done"}
```

### Implementation

Wrap existing `chat_stream()` from `app.agents.ai_chef.py`. Use `StreamingResponse` with `media_type="text/event-stream"`.

### CORS

Allow `http://localhost:5173` for development.

## Frontend (React)

### Tech Stack

- Vite + React 18 + TypeScript
- Tailwind CSS (CSS variables for theming)
- Zustand (state management)
- react-markdown + remark-gfm + rehype-highlight (Markdown rendering)
- lucide-react (icons)
- date-fns (date formatting)

### File Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── MainArea.tsx
│   │   ├── Chat/
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── InputArea.tsx
│   │   │   └── TypingIndicator.tsx
│   │   ├── RecipeCard/
│   │   │   └── RecipeCard.tsx
│   │   └── common/
│   │       ├── ThemeToggle.tsx
│   │       └── IconButton.tsx
│   ├── store/
│   │   └── useChatStore.ts
│   ├── hooks/
│   │   └── useAutoScroll.ts
│   ├── utils/
│   │   ├── cn.ts
│   │   └── api.ts
│   ├── types/
│   │   └── chat.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
└── index.html
```

### Design System (CSS Variables)

Light mode:
- `--bg-primary: #ffffff`
- `--bg-secondary: #f7f8fa`
- `--bg-sidebar: #f0f2f5`
- `--text-primary: #1a1a2e`
- `--accent: #4f6ef7`
- `--bubble-user: #e8f0fe`
- `--bubble-ai: #ffffff`

Dark mode:
- `--bg-primary: #1e1e2e`
- `--bg-secondary: #2a2a3c`
- `--bg-sidebar: #252537`
- `--text-primary: #eaeaea`
- `--accent: #7b8cff`
- `--bubble-user: #2e3b4e`
- `--bubble-ai: #2a2a3c`

### Key Components

1. **Sidebar** (260px fixed): New chat button, conversation list with search, theme toggle at bottom
2. **MainArea**: flex-col container with MessageList + InputArea
3. **MessageList**: Scrollable, auto-scroll to bottom, empty state welcome screen
4. **MessageBubble**: User right-aligned, AI left-aligned, Markdown rendering for AI
5. **InputArea**: Auto-height textarea, Enter to send, Shift+Enter for newline
6. **RecipeCard**: Structured card for recipe data (title, ingredients, steps, times)
7. **TypingIndicator**: Three bouncing dots during streaming

### State Management (Zustand)

```typescript
interface ChatStore {
  conversations: Conversation[];
  currentConversationId: string | null;
  darkMode: boolean;
  searchTerm: string;
  isStreaming: boolean;

  // Actions
  createNewChat: () => void;
  switchConversation: (id: string) => void;
  sendMessage: (content: string) => Promise<void>;
  deleteConversation: (id: string) => void;
  toggleDarkMode: () => void;
  setSearchTerm: (term: string) => void;
}
```

### Streaming Flow

1. User types message → `sendMessage()` called
2. Add user message + empty assistant message to store
3. `fetch('/api/chat', { method: 'POST', body: { messages } })`
4. Read SSE stream with `ReadableStream`
5. Parse each `data:` line, append content to assistant message
6. On `[DONE]`, mark message status as `done`

### Responsive Design

- Desktop: Sidebar visible (260px) + MainArea
- Mobile (<768px): Sidebar hidden, hamburger menu to toggle overlay
- Bubble max-width: 80% desktop, 90% mobile

### Animations

- New messages: slide-up fade-in
- Typing indicator: bouncing dots
- Theme toggle: smooth color transition (0.3s)

## Directory Structure (Full Project)

```
AI-Personal-Chef/
├── app/                    # Existing Python backend
│   └── agents/
│       └── ai_chef.py
├── api/                    # NEW: FastAPI server
│   └── server.py
├── frontend/               # NEW: React app
│   └── src/
├── resources/              # SQLite DB
├── main.py                 # Existing CLI
├── streamlit_app.py        # Existing Streamlit (kept as fallback)
├── pyproject.toml
└── .env
```

## Scope

- Build FastAPI SSE endpoint wrapping existing `chat_stream()`
- Build complete React frontend per user's specification
- Keep existing Streamlit app as fallback (no modifications)
- Keep existing CLI entry point (no modifications)

## Out of Scope

- User authentication
- Recipe data persistence beyond existing SQLite
- Deployment/Docker configuration
- Unit tests (can be added later)
  C:\Users\成耀辉\Desktop\AI-Personal-Chef\images\185498e1-bedd-4e67-a51d-15c6e8dabe24.jpg