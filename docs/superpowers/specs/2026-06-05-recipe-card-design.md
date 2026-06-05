# RecipeCard 菜谱卡片功能设计

## 概述

为AI私人厨师项目添加结构化菜谱卡片功能，让AI推荐的菜谱以精美的卡片形式展示，提升用户体验和项目视觉效果。

## 功能目标

1. AI返回结构化JSON格式的菜谱数据
2. 前端渲染精美的菜谱卡片组件
3. 支持收藏功能
4. 保持与现有Markdown渲染的兼容性

## 数据结构设计

### RecipeData 类型（增强版）

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
    emoji?: string       // 可选emoji图标，如 🥩🥜🌶️
  }>
  steps: string[]        // 烹饪步骤
  tips?: string          // 可选小贴士
  tags?: string[]        // 可选标签：['川菜', '快手菜']
}
```

### AI返回格式

AI在推荐菜谱时，使用特殊标记包裹JSON数据：

```
这是宫保鸡丁的做法：

```recipe
{
  "name": "宫保鸡丁",
  "description": "经典川菜，麻辣鲜香",
  "difficulty": "中等",
  "cookingTime": "30分钟",
  "servings": 2,
  "ingredients": [
    {"name": "鸡胸肉", "amount": "300g", "emoji": "🥩"},
    {"name": "花生米", "amount": "50g", "emoji": "🥜"}
  ],
  "steps": [
    "鸡胸肉切丁，加料酒腌制10分钟",
    "热锅凉油，爆香干辣椒和花椒",
    "下鸡丁翻炒至变色",
    "加入花生米翻炒均匀",
    "调味出锅"
  ],
  "tips": "花生米最后放更脆",
  "tags": ["川菜", "快手菜"]
}
```

这道菜适合配米饭食用。
```

## 组件设计

### RecipeCard.tsx

**位置：** `frontend/src/components/Chat/RecipeCard.tsx`

**功能：**
- 展示菜谱卡片，包含所有信息
- 支持收藏按钮
- 响应式设计，适配移动端

**视觉设计：**
```
┌─────────────────────────────────┐
│ 🍳 宫保鸡丁                      │
│ 经典川菜，麻辣鲜香                │
├─────────────────────────────────┤
│ ⭐ 中等难度  ⏱️ 30分钟  👥 2人份   │
├─────────────────────────────────┤
│ 📋 食材                          │
│ 🥩 鸡胸肉 300g    🥜 花生米 50g  │
│ 🌶️ 干辣椒 10个    🫚 花椒 1勺    │
├─────────────────────────────────┤
│ 👨‍🍳 步骤                          │
│ 1. 鸡胸肉切丁，加料酒腌制10分钟    │
│ 2. 热锅凉油，爆香干辣椒和花椒      │
│ 3. 下鸡丁翻炒至变色               │
│ 4. 加入花生米翻炒均匀              │
│ 5. 调味出锅                      │
├─────────────────────────────────┤
│ 💡 小贴士：花生米最后放更脆        │
│                          [收藏 ♡] │
└─────────────────────────────────┘
```

### MessageBubble.tsx 修改

**修改内容：**
1. 检测消息内容是否包含 `recipe` 代码块
2. 如果包含，解析JSON并渲染RecipeCard
3. 如果不包含，保持原有Markdown渲染

**检测逻辑：**
```typescript
const recipeMatch = content.match(/```recipe\n([\s\S]*?)\n```/)
if (recipeMatch) {
  const recipeData = JSON.parse(recipeMatch[1])
  return <RecipeCard recipe={recipeData} />
}
```

## 后端修改

### AI提示词修改

**修改文件：** `app/agents/ai_chef.py` 中的系统提示词

在系统提示词中添加菜谱返回格式说明：

```markdown
当你推荐菜谱时，请使用以下JSON格式返回结构化数据：

\`\`\`recipe
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
\`\`\`

这样前端可以渲染精美的菜谱卡片。在JSON前后可以添加说明文字。
```

## 收藏功能

### 数据结构

在Conversation中添加收藏列表：

```typescript
export interface Conversation {
  id: string
  title: string
  lastUpdated: number
  messages: Message[]
  pinned?: boolean
  favoriteRecipes?: string[]  // 收藏的菜谱名称列表，如 ['宫保鸡丁', '番茄炒蛋']
}
```

### 收藏按钮

- 点击收藏按钮，将菜谱名称添加到收藏列表
- 再次点击取消收藏
- 收藏状态持久化到localStorage
- 收藏的菜谱可以在侧边栏的"收藏"分组中查看

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/types/chat.ts` | 修改 | 增强RecipeData类型 |
| `frontend/src/components/Chat/RecipeCard.tsx` | 新建 | 菜谱卡片组件 |
| `frontend/src/components/Chat/MessageBubble.tsx` | 修改 | 检测并渲染RecipeCard |
| `frontend/src/store/useChatStore.ts` | 修改 | 添加收藏功能 |
| 后端提示词 | 修改 | 返回结构化JSON |

## 测试方案

1. **单元测试：**
   - RecipeCard组件渲染测试
   - JSON解析测试
   - 收藏功能测试

2. **集成测试：**
   - AI返回菜谱 → 前端渲染卡片
   - 收藏按钮 → 状态更新

3. **手动测试：**
   - 输入"推荐一个晚餐" → 检查卡片渲染
   - 点击收藏 → 刷新页面检查持久化

## 实现顺序

1. 修改RecipeData类型
2. 创建RecipeCard组件
3. 修改MessageBubble检测逻辑
4. 修改后端提示词
5. 添加收藏功能
6. 测试和调试
