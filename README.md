# 五子棋 (Gomoku)

双人对战五子棋，支持 **AI 模式** 和 **在线对战模式**，纯 Python Flask 后端 + Canvas 前端，零框架依赖。

在线体验：https://gomoku-xai.onrender.com

---

## 目录结构

```
gomoku/
├── README.md              # 本文件
├── requirements.txt       # Python 依赖
├── Procfile               # Render 部署配置
├── server.py              # Flask HTTP 服务（路由层）
├── index.html             # 前端 SPA（Canvas + 浏览器 JS）
├── game/                  # 游戏核心逻辑包
│   ├── __init__.py
│   ├── board.py           # 棋盘数据结构
│   ├── ai.py              # AI 评分引擎
│   └── game.py            # 游戏状态机
├── room/                  # 房间管理包
│   ├── __init__.py
│   └── room_manager.py    # 房间 + 事件队列
└── .gitignore
```

## 运行方式

```bash
pip install -r requirements.txt
python server.py
# 浏览器打开 http://127.0.0.1:5000
```

## 项目架构

### 架构总览

```
┌─────────────────────────────────────────┐
│            浏览器 (index.html)            │
│   Canvas 渲染 + 鼠标事件 + fetch API 调用 │
│   AI 模式: fetch /api/{state,move,undo}  │
│   PvP 模式: fetch /api/pvp/{*,...} + 轮询 │
└──────────────┬──────────────────────────┘
               │ HTTP JSON
               ▼
┌─────────────────────────────────────────┐
│          server.py (Flask)               │
│  路由分发 / API 层 + cookie/Session 管理   │
└──────┬────────────────────┬─────────────┘
       │                    │
       ▼                    ▼
┌──────────────┐   ┌──────────────────────┐
│  game/game.py │   │ room/room_manager.py │
│  AI + PvP 双  │   │ 房间创建/加入 + 事件   │
│  模式状态机     │   │ 队列（polling 驱动）   │
└──────┬───────┘   └──────────────────────┘
       │
       ▼
┌──────────────┐
│  game/board   │←── game/ai.py (评分)
│  棋盘数据结构  │
└──────────────┘
```

**核心设计理念：** 后端无状态 API + 前端单页应用。AI 模式和 PvP 模式共享同一套 `Game` 状态机，只在路由层分派不同的 API 端点。

---

## 模块详解

### 1. `game/board.py` — 棋盘数据结构

```python
SIZE = 15              # 棋盘尺寸 15×15
EMPTY, BLACK, WHITE = 0, 1, 2

class Board:
    grid: list[list[int]]   # 二维数组，0=空，1=黑，2=白

    reset()                 # 清空棋盘
    get(x, y)               # 读取坐标
    set(x, y, player)       # 写入坐标
    is_valid(x, y)          # 合法性校验（界内 + 空位）
    is_full()               # 棋盘满（平局判定）
    to_list()               # 导出深拷贝，用于序列化传给前端
```

最底层的数据容器，存储 15×15 的整数矩阵。`to_list()` 做深拷贝是因为前端会消费这些数据，不能引用内部的 grid。

### 2. `game/ai.py` — AI 评分引擎

**算法原理：** 基于模式加权评分的启发式搜索。扫描全盘 225 个空位，对每个位置分别计算进攻分和防守分，选最高分。

**评分函数 `_score_position(x, y, player, board)`：**

对一个位置的四个方向（→ ↘ ↓ ↙）分别统计连续同色棋子数 + 开放端数，按模式加权求和。

| 模式 | 示例 | 分值 | 说明 |
|------|------|------|------|
| 五连 | `●●●●●` | 100,000 | 必胜，最高优先级 |
| 活四 | `_●●●●_` | 50,000 | 两端开放，必赢 |
| 冲四 | `_●●●●` 或 `●_●●●` | 5,000 | 一端开放，有威胁 |
| 活三 | `_●●●_` | 5,000 | 两端开放的三连 |
| 眠三 | `_●●●` | 500 | 一端开放的三连 |
| 活二 | `_●●_` | 500 | 两端开放的二连 |

**综合评分 `evaluate_position(x, y, board)`：**

```python
def evaluate_position(x, y, board):
    ai_score = _score_position(x, y, WHITE, board)      # 进攻分
    human_score = _score_position(x, y, BLACK, board)    # 防守分
    if ai_score >= 100000:
        return ai_score * 10     # AI 能赢，直接取
    return ai_score + human_score * 1.1   # 否则进攻+防守，略偏进攻
```

**选择落子 `ai_move(board)`：** 遍历所有空位，`evaluate_position` 打分，取最高分位置（同分随机选）。

### 3. `game/game.py` — 游戏状态机

`Game` 类管理一盘游戏的完整生命周期。

| 属性 | 类型 | 说明 |
|------|------|------|
| `board` | Board | 棋盘 |
| `current_player` | int | 当前轮到谁（`BLACK=1` 或 `WHITE=2`） |
| `history` | list[dict] | 落子历史 `[{x, y, stone}]` |
| `game_over` | bool | 是否结束 |
| `winner` | str \| None | 胜方 `"black"`/`"white"`/`None` |

**核心方法：**

- **`_check_win(x, y, player)`** — 从落子点沿四个方向（水平、垂直、两条对角线）统计同色连续棋子数，≥5 则胜。

- **`human_move(x, y)`** — AI 模式的落子入口：
  1. 验证当前是黑方回合
  2. 落子
  3. 判赢 → 若人类胜则结束
  4. 切换到白方
  5. 自动调用 `ai_move()` 让 AI 响应
  6. 判赢 → 若 AI 胜则结束
  7. 切回黑方

- **`pvp_move(x, y, player)`** — PvP 模式的落子入口（与 `human_move` 的区别）：
  - 接收 `player` 参数，不写死为黑方
  - 不触发 AI，只切换 `current_player`
  - 供房间模块在收到对方落子请求后调用

- **`undo()`** — 悔棋：弹出历史栈顶 2 步（AI + 人类各一步），恢复棋盘。

- **`_state(message)` / `get_state()`** — 序列化为 JSON 字典，供路由层返回给前端。

### 4. `room/room_manager.py` — 房间管理器

管理在线对战的房间和事件队列。

```python
class Room:
    room_id: str                # 4位数字房间号
    player_black: str           # 黑方 player_id（UUID）
    player_white: str           # 白方 player_id（UUID）
    status: str                 # "waiting" | "playing"
    game: Game                  # 游戏实例
    created_at: float           # 创建时间戳（用于清理超时房间）
    events: dict                # 事件队列 { "black": [], "white": [] }
```

**RoomManager 核心逻辑：**

| 方法 | 功能 |
|------|------|
| `create_room(player_id)` | 生成不重复的 4 位房间号，创建 Room 实例 |
| `join_room(rid, player_id)` | 按房间号加入，写入 `player_white`，状态置为 `playing`，向黑方写入 `"opponent_joined"` 事件 |
| `get_room_by_player(player_id)` | 通过 player_id 查玩家所在房间 |
| `poll_events(room, color)` | **取出并清空**该颜色的事件队列（消费后即删除，保证不重复） |
| `add_move_event(room, target_color, ...)` | 落子后向对手颜色写入 `"opponent_moved"` 事件 |
| `leave(player_id)` | 玩家离开：向对手写入 `"opponent_left"` 事件，删除房间 |
| `cleanup_stale()` | 清理超过 5 分钟还在等待的房间 |

**事件队列机制：** 这是轮询模式的核心。每个房间维护两个队列（黑/白），一方操作后向对方队列写入事件。对方下一次轮询时取走并处理事件。

### 5. `server.py` — Flask 路由层

**AI 模式 API（基于 cookie 的会话管理）：**

| 方法 | 路径 | 功能 |
|------|------|------|
| `GET` | `/` | 返回 `index.html` |
| `GET` | `/api/state` | 获取当前游戏状态，通过 `game_id` cookie 关联玩家 |
| `POST` | `/api/new-game` | 重置游戏 |
| `POST` | `/api/move` | 人类落子（自动触发 AI 响应） |
| `POST` | `/api/undo` | 悔棋 |

**会话管理：** 每个浏览器首次请求 `/api/state` 时，服务端生成一个 `game_id`（UUID）写入 cookie，之后所有请求携带该 cookie 关联到对应 `Game` 实例。

**PvP 模式 API（基于 player_id 参数）：**

| 方法 | 路径 | 功能 |
|------|------|------|
| `POST` | `/api/pvp/create` | 创建房间 → `{ player_id, room_id, color: "black" }` |
| `POST` | `/api/pvp/join` | 加入房间 → `{ player_id, color: "white", board }` |
| `GET` | `/api/pvp/state` | 轮询状态 + 事件 |
| `POST` | `/api/pvp/move` | 落子（验证 + 写入对手事件） |
| `GET/POST` | `/api/pvp/leave` | 离开房间 |

**关键设计区别：** AI 模式用 cookie 关联玩家（一人一局），PvP 模式用服务端生成的 `player_id`（UUID）作为玩家身份标识，客户端保存在 `sessionStorage` 中。

### 6. `index.html` — 前端 SPA

纯 Canvas 渲染 + 原生 JS 的单页应用，零框架依赖。

**渲染引擎：**

```
Canvas 尺寸 = PAD(28)*2 + CELL(38)*(SIZE-1)
网格线: 15×15 交叉点
星位点: (3,3) (3,7) (3,11) (7,3) (7,7) (7,11) (11,3) (11,7) (11,11)
棋子: 径向渐变（黑: #555→#000, 白: #fff→#ccc）
悬停预览: 半透明灰点（alpha 0.4）
最后一步: 金色(#ffd700) / 橙色(#ff4500) 圆环标记
```

**前端架构：**

```
全局状态:
  boardState[][]  — 15×15 数组（来自后端）
  currentStone    — "black" | "white" 当前回合
  gameOver        — 是否结束
  myColor         — 玩家颜色（PvP 模式下）
  playerId        — 玩家身份（PvP 模式下）
  gameMode        — "ai" | "pvp"
  pollTimer       — 轮询定时器

UI 状态机:
  mode-select (主菜单)
    ├─→ AI 模式: showOverlay(null) → 棋盘
    └─→ PvP 模式:
          ├─ room-menu (创建/加入)
          │    ├─ createRoom() → 创建房间 → waiting (显示房间号, 开始轮询)
          │    └─ joinRoom() → 加入房间 → 棋盘 (开始轮询)
          └─ 游戏中对局:
                ├─ 点击 → POST /api/pvp/move
                ├─ 轮询 → GET /api/pvp/state → 处理 events
                └─ 退出 → POST /api/pvp/leave → 返回主菜单
```

**轮询机制：**

```javascript
// 每 1 秒执行一次
setInterval(async () => {
    const data = await fetch(`/api/pvp/state?player_id=${playerId}`);
    // 1. 更新 board、current_player、game_over
    // 2. 处理 events:
    //    - "opponent_joined": 关闭等待界面，显示棋盘
    //    - "opponent_moved": 对手刚落子（board 已包含最新状态）
    //    - "opponent_left": 显示"对手已离开"，停止轮询
    // 3. 更新状态文字
}, 1000);
```

**断线重连：** `player_id` 和 `room_id` 存储在 `sessionStorage` 中。页面加载时 `init()` 函数检查 `sessionStorage`，如果有保存的 `player_id`，则向后端查询房间状态，若房间仍在则自动恢复游戏。

**`navigator.sendBeacon()`：** 页面关闭或刷新时，通过 `beforeunload` 事件用 `sendBeacon` 发送离开请求（比 `fetch` 更可靠，浏览器保证在页面销毁前发送）。

---

## AI 核心技术

AI 基于模式评分 + 穷举搜索，不涉及机器学习。

**时间复杂度：** 每步遍历 225 个空位，每个位置检查 4 个方向，每个方向最多延伸 4 格 → 约 `225 × 4 × 5 ≈ 4500` 次操作，在 Python 中 < 1ms。

**局限：**
- 不会识别间隔模式（如 `●_●●` 跳活三）
- 不会做多步前瞻（没有博弈树搜索）
- 评分权重是手工调的，未经过机器学习优化

对于休闲玩家来说，AI 具备基本的攻防意识，能正确识别活四/冲四等关键棋型，足以提供有趣的对弈体验。

---

## PvP 核心技术

**纯轮询方案（区别于 WebSocket）：**

```
玩家A 落子                     玩家B 轮询
  │                             │
  ├─ POST /api/pvp/move ───────→┤
  │   服务器校验 → 写入事件      │
  │ ← { ok: true }              │
  │                             ├─ GET /api/pvp/state?player_id=B
  │                             │   服务器查询事件队列
  │                             │ ← { board, events: [opponent_moved], ... }
  │                             │   取走 events 并清空队列
  │                             │   更新棋盘渲染
```

**为什么用轮询而非 WebSocket：**
- 免费部署平台（Render 免费实例）对 WebSocket + eventlet 支持不完善，出现 `400 Invalid session`
- 五子棋是回合制游戏，1 秒轮询延迟对用户体验影响极小
- 零额外依赖，部署简单可靠

---

## 部署方式

### Render（免费）

1. 将项目推送到 GitHub 仓库
2. 在 [render.com](https://render.com) 创建 **New Web Service**
3. 连接你的 GitHub 仓库
4. 配置：

| 字段 | 值 |
|------|-----|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn server:app`（或留空由 Procfile 接管） |

5. 点击 **Deploy**

> Render 免费实例 15 分钟无访问会休眠，再次访问需等待约 30 秒唤醒。
