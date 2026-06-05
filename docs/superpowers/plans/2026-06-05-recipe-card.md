# RecipeCard 菜谱卡片实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为AI私人厨师添加结构化菜谱卡片功能，让AI推荐的菜谱以精美卡片形式展示

**Architecture:** AI返回`recipe`代码块包裹的JSON数据，前端检测并渲染RecipeCard组件，支持收藏功能

**Tech Stack:** React + TypeScript + Tailwind CSS + Zustand

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `frontend/src/types/chat.ts` | 修改 | 增强RecipeData类型，添加收藏字段 |
| `frontend/src/components/Chat/RecipeCard.tsx` | 新建 | 菜谱卡片组件 |
| `frontend/src/components/Chat/MessageBubble.tsx` | 修改 | 检测recipe代码块并渲染卡片 |
| `frontend/src/store/useChatStore.ts` | 修改 | 添加收藏功能 |
| `app/agents/ai_chef.py` | 修改 | 更新系统提示词 |

---

### Task 1: 增强 RecipeData 类型

**Files:**
- Modify: `frontend/src/types/chat.ts:9-17`

- [ ] **Step 1: 修改 RecipeData 类型**

```typescript
export interface RecipeData {
  name: string           // 菜名
  description: string    // 简短描述
  difficulty: '简单' | '中等' | '复杂'  // 难度等级
  cookingTime: string    // 烹饪时间：30分钟
  servings: number       // 用餐人数：2
  ingredients: Array<{   // 食材列表
    name: string         // 食材名称
    amount: string       // 用量：300g
    emoji?: string       // 可选emoji图标
  }>
  steps: string[]        // 烹饪步骤
  tips?: string          // 可选小贴士
  tags?: string[]        // 可选标签：['川菜', '快手菜']
}
```

- [ ] **Step 2: 在 Conversation 类型中添加收藏字段**

```typescript
export interface Conversation {
  id: string
  title: string
  lastUpdated: number
  messages: Message[]
  pinned?: boolean
  favoriteRecipes?: string[]  // 收藏的菜谱名称列表
}
```

- [ ] **Step 3: 验证类型**

运行: `cd frontend && npx tsc --noEmit`
预期: 无错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/types/chat.ts
git commit -m "feat: 增强 RecipeData 类型，添加收藏字段"
```

---

### Task 2: 创建 RecipeCard 组件

**Files:**
- Create: `frontend/src/components/Chat/RecipeCard.tsx`

- [ ] **Step 1: 创建 RecipeCard 组件**

```tsx
import { useState } from 'react'
import { Heart, Clock, Users, ChefHat } from 'lucide-react'
import type { RecipeData } from '../../types/chat'
import { useChatStore } from '../../store/useChatStore'

interface RecipeCardProps {
  recipe: RecipeData
}

export function RecipeCard({ recipe }: RecipeCardProps) {
  const [isFavorite, setIsFavorite] = useState(false)
  const { currentConversation, toggleFavoriteRecipe } = useChatStore()

  const difficultyColor = {
    '简单': 'text-green-500',
    '中等': 'text-yellow-500',
    '复杂': 'text-red-500'
  }

  const handleFavorite = () => {
    setIsFavorite(!isFavorite)
    toggleFavoriteRecipe(recipe.name)
  }

  return (
    <div
      className="rounded-2xl border overflow-hidden my-4"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-color)',
      }}
    >
      {/* 头部：菜名和描述 */}
      <div className="px-5 pt-5 pb-3">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
              🍳 {recipe.name}
            </h3>
            <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
              {recipe.description}
            </p>
          </div>
          <button
            onClick={handleFavorite}
            className="p-2 rounded-full transition-colors"
            style={{ color: isFavorite ? '#ef4444' : 'var(--text-secondary)' }}
          >
            <Heart size={20} fill={isFavorite ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>

      {/* 信息栏：难度、时间、人数 */}
      <div
        className="px-5 py-3 flex items-center gap-4 text-sm"
        style={{
          borderTop: '1px solid var(--border-color)',
          borderBottom: '1px solid var(--border-color)',
        }}
      >
        <span className={`flex items-center gap-1 ${difficultyColor[recipe.difficulty]}`}>
          <ChefHat size={14} />
          {recipe.difficulty}
        </span>
        <span className="flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
          <Clock size={14} />
          {recipe.cookingTime}
        </span>
        <span className="flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
          <Users size={14} />
          {recipe.servings}人份
        </span>
        {recipe.tags && recipe.tags.length > 0 && (
          <div className="flex gap-1 ml-auto">
            {recipe.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 rounded-full text-xs"
                style={{
                  backgroundColor: 'var(--accent)',
                  color: '#fff',
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 食材列表 */}
      <div className="px-5 py-4">
        <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
          📋 食材
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {recipe.ingredients.map((ing, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm"
              style={{ backgroundColor: 'var(--bg-primary)' }}
            >
              <span>{ing.emoji || '•'}</span>
              <span style={{ color: 'var(--text-primary)' }}>{ing.name}</span>
              <span className="ml-auto" style={{ color: 'var(--text-secondary)' }}>
                {ing.amount}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 步骤列表 */}
      <div className="px-5 py-4" style={{ borderTop: '1px solid var(--border-color)' }}>
        <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
          👨‍🍳 步骤
        </h4>
        <ol className="space-y-3">
          {recipe.steps.map((step, idx) => (
            <li key={idx} className="flex gap-3 text-sm">
              <span
                className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
              >
                {idx + 1}
              </span>
              <span className="pt-0.5" style={{ color: 'var(--text-primary)' }}>
                {step}
              </span>
            </li>
          ))}
        </ol>
      </div>

      {/* 小贴士 */}
      {recipe.tips && (
        <div
          className="px-5 py-4"
          style={{
            borderTop: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-primary)',
          }}
        >
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            💡 {recipe.tips}
          </p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 验证组件**

运行: `cd frontend && npx tsc --noEmit`
预期: 无错误（可能有未使用的导入警告，暂时忽略）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/Chat/RecipeCard.tsx
git commit -m "feat: 创建 RecipeCard 菜谱卡片组件"
```

---

### Task 3: 在 useChatStore 中添加收藏功能

**Files:**
- Modify: `frontend/src/store/useChatStore.ts:14-33`
- Modify: `frontend/src/store/useChatStore.ts:35-236`

- [ ] **Step 1: 在 ChatState 接口中添加 toggleFavoriteRecipe**

```typescript
interface ChatState {
  conversations: Conversation[]
  currentConversationId: string | null
  darkMode: boolean
  searchTerm: string
  isStreaming: boolean

  createNewChat: () => void
  switchConversation: (id: string) => void
  deleteConversation: (id: string) => void
  renameConversation: (id: string, title: string) => void
  togglePinConversation: (id: string) => void
  toggleFavoriteRecipe: (recipeName: string) => void  // 新增
  setSearchTerm: (term: string) => void
  toggleDarkMode: () => void
  sendMessage: (content: string) => Promise<void>

  currentConversation: () => Conversation | undefined
  currentMessages: () => Message[]
  filteredConversations: () => Conversation[]
}
```

- [ ] **Step 2: 在 createNewChat 中添加 favoriteRecipes 字段**

```typescript
createNewChat: () => {
  const id = uuid()
  const newConv: Conversation = {
    id,
    title: '新对话',
    lastUpdated: Date.now(),
    messages: [],
    favoriteRecipes: [],  // 新增
  }
  set((state) => ({
    conversations: [newConv, ...state.conversations],
    currentConversationId: id,
  }))
},
```

- [ ] **Step 3: 添加 toggleFavoriteRecipe 函数**

在 `togglePinConversation` 函数后面添加：

```typescript
toggleFavoriteRecipe: (recipeName) => {
  const state = get()
  const convId = state.currentConversationId
  if (!convId) return

  set((state) => ({
    conversations: state.conversations.map((c) => {
      if (c.id !== convId) return c
      const favorites = c.favoriteRecipes || []
      const isFavorited = favorites.includes(recipeName)
      return {
        ...c,
        favoriteRecipes: isFavorited
          ? favorites.filter((name) => name !== recipeName)
          : [...favorites, recipeName],
      }
    }),
  }))
},
```

- [ ] **Step 4: 更新 partialize 以保存收藏数据**

```typescript
partialize: (state) => ({
  conversations: state.conversations,
  currentConversationId: state.currentConversationId,
  darkMode: state.darkMode,
}),
```

注意：`favoriteRecipes` 已经在 `conversations` 中，会被自动保存。

- [ ] **Step 5: 验证类型**

运行: `cd frontend && npx tsc --noEmit`
预期: 无错误

- [ ] **Step 6: 提交**

```bash
git add frontend/src/store/useChatStore.ts
git commit -m "feat: 添加菜谱收藏功能"
```

---

### Task 4: 修改 MessageBubble 检测 recipe 代码块

**Files:**
- Modify: `frontend/src/components/Chat/MessageBubble.tsx:1-37`

- [ ] **Step 1: 修改 MessageBubble 组件**

```tsx
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import type { Message, RecipeData } from '../../types/chat'
import { RecipeCard } from './RecipeCard'

interface MessageBubbleProps {
  message: Message
}

function parseRecipeContent(content: string): { before: string; recipe: RecipeData | null; after: string } {
  const recipeRegex = /```recipe\n([\s\S]*?)\n```/
  const match = content.match(recipeRegex)

  if (!match) {
    return { before: content, recipe: null, after: '' }
  }

  const before = content.slice(0, match.index).trim()
  const after = content.slice(match.index! + match[0].length).trim()

  try {
    const recipe = JSON.parse(match[1]) as RecipeData
    return { before, recipe, after }
  } catch {
    return { before: content, recipe: null, after: '' }
  }
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[80%] px-5 py-3.5 bg-[var(--bubble-user)] rounded-2xl rounded-br-md"
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    )
  }

  const { before, recipe, after } = parseRecipeContent(message.content)

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        {before && (
          <div
            className="px-5 py-3.5 bg-[var(--bubble-ai)] rounded-2xl rounded-bl-md shadow-[var(--shadow)]"
          >
            <div className="markdown-body">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              >
                {before}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {recipe && <RecipeCard recipe={recipe} />}

        {after && (
          <div
            className="px-5 py-3.5 bg-[var(--bubble-ai)] rounded-2xl rounded-bl-md shadow-[var(--shadow)]"
          >
            <div className="markdown-body">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              >
                {after}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 验证类型**

运行: `cd frontend && npx tsc --noEmit`
预期: 无错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/Chat/MessageBubble.tsx
git commit -m "feat: MessageBubble 支持渲染 RecipeCard"
```

---

### Task 5: 更新后端 AI 提示词

**Files:**
- Modify: `app/agents/ai_chef.py:22-28`

- [ ] **Step 1: 修改系统提示词**

```python
system_prompt = """
你是一名私人厨师。根据用户提供的食材，推荐合适的菜谱。
优先调用 search_recipe 工具搜索菜谱，再搜索不到的情况下才能自己发挥。

## 菜谱返回格式

当你推荐菜谱时，请使用以下JSON格式返回结构化数据：

```recipe
{
  "name": "菜名",
  "description": "简短描述",
  "difficulty": "简单/中等/复杂",
  "cookingTime": "时间",
  "servings": 人数,
  "ingredients": [{"name": "食材", "amount": "用量", "emoji": "可选图标"}],
  "steps": ["步骤1", "步骤2"],
  "tips": "可选小贴士",
  "tags": ["标签1", "标签2"]
}
```

这样前端可以渲染精美的菜谱卡片。在JSON前后可以添加说明文字。

## 其他说明

- 如果用户说"收藏这个菜谱"，请回复"已收藏"并提取菜谱名称。
- 如果用户说"我的偏好是..."或"我忌口..."，请记住并回复"已记住你的偏好"。
"""
```

- [ ] **Step 2: 提交**

```bash
git add app/agents/ai_chef.py
git commit -m "feat: 更新AI提示词，支持返回结构化菜谱JSON"
```

---

### Task 6: 手动测试

- [ ] **Step 1: 启动后端服务**

```bash
cd C:\Users\成耀辉\Desktop\AI-Personal-Chef
python api/server.py
```

- [ ] **Step 2: 启动前端开发服务器**

```bash
cd C:\Users\成耀辉\Desktop\AI-Personal-Chef\frontend
npm run dev
```

- [ ] **Step 3: 测试菜谱卡片**

在浏览器打开 http://localhost:5173，输入：
- "推荐一个简单的晚餐"
- "我有一些鸡胸肉，能做什么菜？"

预期：AI返回带有 `recipe` 代码块的内容，前端渲染精美卡片

- [ ] **Step 4: 测试收藏功能**

点击菜谱卡片上的收藏按钮（心形图标）
预期：图标变红，刷新页面后收藏状态保持

- [ ] **Step 5: 最终提交**

```bash
git add .
git commit -m "feat: 完成 RecipeCard 菜谱卡片功能"
```

---

## 完成检查

- [ ] RecipeData 类型已增强
- [ ] RecipeCard 组件已创建并渲染精美卡片
- [ ] MessageBubble 能检测并渲染 recipe 代码块
- [ ] 收藏功能正常工作
- [ ] 后端提示词已更新
- [ ] 所有测试通过
- [ ] 代码已提交
