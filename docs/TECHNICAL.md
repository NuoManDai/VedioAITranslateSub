# 字幕编辑器技术方案说明

本文档详细介绍字幕编辑器页面的技术实现方案、组件架构和交互设计。

## 目录

- [功能概述](#功能概述)
- [架构设计](#架构设计)
- [组件结构](#组件结构)
- [状态管理](#状态管理)
- [核心交互](#核心交互)
- [数据流](#数据流)
- [API 接口](#api-接口)
- [技术细节](#技术细节)

---

## 功能概述

字幕编辑器是一个专业的字幕校对工具，提供类似 Aegisub 的编辑体验：

| 功能 | 说明 |
|------|------|
| **视频同步预览** | 视频播放与字幕同步显示 |
| **波形时间轴** | 音频波形可视化，可拖拽调整时间 |
| **字幕列表编辑** | 编辑翻译文本、原文、时间轴 |
| **空格键播放** | Aegisub 风格，空格播放选中片段 |
| **拖拽创建字幕** | 在波形上拖拽空白区域创建新字幕 |
| **自动保存草稿** | IndexedDB 本地草稿，30秒自动保存 |
| **还原功能** | 支持还原到原始字幕 |
| **合并到视频** | 将字幕烧录到视频中 |

---

## 架构设计

```
┌────────────────────────────────────────────────────────────────┐
│                   SubtitleEditor.tsx (页面)                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐
│  │                    useSubtitleEditor Hook                   │
│  │  (状态管理: entries, currentTime, isPlaying, isDirty...)   │
│  └─────────────────────────────────────────────────────────────┘
│                              │
│      ┌───────────────────────┼───────────────────────┐
│      │                       │                       │
│      ▼                       ▼                       ▼
│  ┌──────────┐         ┌──────────────┐        ┌──────────┐
│  │VideoSync │         │SubtitleList  │        │ Timeline │
│  │  (40%)   │         │    (60%)     │        │ (底部)   │
│  └──────────┘         └──────────────┘        └──────────┘
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 组件结构

### 文件组织

```
frontend/src/
├── pages/
│   └── SubtitleEditor.tsx           # 字幕编辑器页面
├── hooks/
│   └── useSubtitleEditor.ts         # 状态管理 Hook
├── components/subtitle-editor/
│   ├── index.ts                     # 组件导出
│   ├── VideoSync.tsx                # 视频同步组件
│   ├── SubtitleList.tsx             # 字幕列表组件
│   └── Timeline.tsx                 # 波形时间轴组件
└── services/
    ├── subtitleApi.ts               # 字幕 API 封装
    └── indexeddb.ts                 # IndexedDB 草稿存储
```

### 1. SubtitleEditor.tsx (页面组件)

**职责**: 页面布局、组件协调、键盘事件处理

```typescript
// 核心结构
export default function SubtitleEditor() {
  // Refs
  const videoRef = useRef<VideoSyncRef>(null);
  const timelineRef = useRef<TimelineRef>(null);
  const playUntilRef = useRef<number | null>(null);  // 空格键播放结束时间

  // Hook 状态
  const {
    entries, currentTime, isPlaying, selectedIndex,
    isDirty, isLoading, isSaving, isMerging,
    loadSubtitles, updateEntry, saveToServer, mergeVideo,
    setCurrentTime, setIsPlaying, setSelectedIndex,
  } = useSubtitleEditor();

  // 统一 Seek 方法 (同步视频和时间轴)
  const handleSeekTo = useCallback((time: number) => {
    setCurrentTime(time);
    videoRef.current?.seekTo(time);
    timelineRef.current?.seekTo(time);
  }, [setCurrentTime]);

  // 空格键播放选中片段 (Aegisub 风格)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && selectedIndex !== null) {
        e.preventDefault();
        const entry = entries[selectedIndex];
        if (entry) {
          setIsPlaying(false);
          playUntilRef.current = entry.endTime;
          handleSeekTo(entry.startTime);
          setTimeout(() => setIsPlaying(true), 50);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedIndex, entries, handleSeekTo, setIsPlaying]);

  // 到达结束时间自动停止
  useEffect(() => {
    if (playUntilRef.current !== null && currentTime >= playUntilRef.current) {
      setIsPlaying(false);
      playUntilRef.current = null;
    }
  }, [currentTime, setIsPlaying]);
}
```

**页面布局**:
```
┌─────────────────────────────────────────────────────────────┐
│  Header: 返回 | 标题 | 未保存标记 | 还原 | 保存 | 合并到视频  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐  ┌─────────────────────────────────┐│
│  │                   │  │                                 ││
│  │   VideoSync       │  │     SubtitleList                ││
│  │   (40% 宽度)      │  │     (60% 宽度)                  ││
│  │                   │  │                                 ││
│  └───────────────────┘  └─────────────────────────────────┘│
│                        (height: calc(100% - 180px))         │
├─────────────────────────────────────────────────────────────┤
│  Timeline (height: 180px)                                   │
│  波形时间轴 + 时间刻度                                       │
└─────────────────────────────────────────────────────────────┘
```

### 2. VideoSync.tsx (视频同步组件)

**职责**: 视频播放、字幕叠加显示、播放控制

```typescript
interface VideoSyncProps {
  videoFilename: string;
  currentTime: number;
  isPlaying: boolean;
  entries?: SubtitleEntry[];
  onTimeUpdate: (time: number) => void;
  onPlayingChange: (playing: boolean) => void;
}

export interface VideoSyncRef {
  seekTo: (time: number) => void;
}
```

**核心功能**:

| 功能 | 实现 |
|------|------|
| 视频播放 | HTML5 `<video>` 元素 |
| 时间同步 | `onTimeUpdate` 回调 |
| Seek 控制 | `forwardRef` + `useImperativeHandle` |
| 字幕叠加 | 根据 `currentTime` 查找当前字幕，绝对定位显示 |
| 双语显示 | 主字幕 (翻译) + 次字幕 (原文) |

**字幕叠加样式**:
```tsx
{activeSubtitle && (
  <div className="absolute bottom-0 left-0 right-0 p-4">
    {/* 翻译字幕 */}
    <div className="bg-black/75 text-white px-4 py-2 rounded-lg text-lg">
      {activeSubtitle.text}
    </div>
    {/* 原文字幕 (较小) */}
    {activeSubtitle.originalText && (
      <div className="bg-black/60 text-gray-300 px-3 py-1 rounded-lg text-sm mt-1">
        {activeSubtitle.originalText}
      </div>
    )}
  </div>
)}
```

### 3. SubtitleList.tsx (字幕列表组件)

**职责**: 字幕条目展示、编辑、删除、时间调整

```typescript
interface SubtitleListProps {
  entries: SubtitleEntry[];
  currentTime: number;
  selectedIndex: number | null;
  onSelectEntry: (index: number) => void;
  onUpdateEntry: (index: number, changes: Partial<SubtitleEntry>) => void;
  onDeleteEntry?: (index: number) => void;
  onSeekTo: (time: number) => void;
}
```

**核心功能**:

| 功能 | 实现 |
|------|------|
| 活跃字幕高亮 | 根据 `currentTime` 计算 `activeIndex` |
| 自动滚动 | `scrollIntoView({ behavior: 'smooth', block: 'center' })` |
| 时间编辑 | 支持 `HH:MM:SS,mmm` 和 `MM:SS.mmm` 格式 |
| 文本编辑 | `Input.TextArea` 自适应高度 |
| 选中状态 | 点击条目选中，显示 ring 高亮 |

**时间格式解析**:
```typescript
function parseTimeString(timeStr: string): number | null {
  // 支持格式:
  // - HH:MM:SS,mmm (SRT 标准)
  // - MM:SS.mmm (简化格式)
  // - MM:SS (无毫秒)
}

function formatSrtTime(seconds: number): string {
  // 输出: 00:01:23,456
}
```

**条目样式状态**:
```
┌────────────────────────────────────────────────────────┐
│ [1] ⏱ 00:00:01,234 → 00:00:03,456  [2.22s]       [🗑] │ ← Header
├────────────────────────────────────────────────────────┤
│ 翻译                                                    │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 这是翻译文本                                        │ │
│ └────────────────────────────────────────────────────┘ │
│ 原文                                                    │
│ ┌────────────────────────────────────────────────────┐ │
│ │ This is original text                              │ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

### 4. Timeline.tsx (波形时间轴组件)

**职责**: 音频波形显示、字幕区域可视化、时间轴拖拽

```typescript
interface TimelineProps {
  entries: SubtitleEntry[];
  currentTime: number;
  isPlaying: boolean;
  onSeek: (time: number) => void;
  onUpdateEntry: (index: number, changes: Partial<SubtitleEntry>) => void;
  onAddEntry?: (startTime: number, endTime: number) => void;
  onPlayingChange: (playing: boolean) => void;
  selectedIndex?: number | null;
  onSelectEntry?: (index: number) => void;
}

export interface TimelineRef {
  seekTo: (time: number) => void;
}
```

**技术栈**: [WaveSurfer.js](https://wavesurfer-js.org/)

| 插件 | 用途 |
|------|------|
| `RegionsPlugin` | 字幕区域可视化、拖拽调整、新建字幕 |
| `TimelinePlugin` | 时间刻度显示 |

**核心功能**:

```typescript
// 初始化 WaveSurfer
const ws = WaveSurfer.create({
  container: containerRef.current,
  waveColor: '#e0e0e0',
  progressColor: '#667eea',
  cursorColor: '#764ba2',
  cursorWidth: 2,
  height: 100,
  barWidth: 2,
  barGap: 1,
  barRadius: 2,
  minPxPerSec: zoomLevel,  // 缩放级别
});

// 区域插件 - 字幕可视化
const regions = ws.registerPlugin(RegionsPlugin.create());
regions.enableDragSelection({ color: 'rgba(102, 126, 234, 0.3)' });

// 事件处理
regions.on('region-updated', (region) => {
  // 拖拽/调整大小时更新字幕时间
  onUpdateEntry(entryIndex, {
    startTime: region.start,
    endTime: region.end,
  });
});

regions.on('region-created', (region) => {
  // 拖拽空白区域创建新字幕
  if (region.end - region.start >= 0.1) {
    onAddEntry(region.start, region.end);
  }
});
```

**交互特性**:

| 交互 | 行为 |
|------|------|
| 鼠标滚轮 | 缩放波形 (10-500 像素/秒) |
| 点击波形 | Seek 到点击位置 |
| 拖拽区域边缘 | 调整字幕时间 |
| 拖拽区域中心 | 移动整个字幕 |
| 拖拽空白区域 | 创建新字幕 |
| 点击区域 | 选中对应字幕 |

---

## 状态管理

### useSubtitleEditor Hook

**文件**: `frontend/src/hooks/useSubtitleEditor.ts`

```typescript
interface UseSubtitleEditorReturn {
  // 状态
  entries: SubtitleEntry[];          // 字幕列表
  currentTime: number;               // 当前播放时间
  isPlaying: boolean;                // 播放状态
  selectedIndex: number | null;      // 选中的字幕索引
  isDirty: boolean;                  // 是否有未保存更改
  isLoading: boolean;                // 加载中
  isSaving: boolean;                 // 保存中
  isMerging: boolean;                // 合并中
  isRestoring: boolean;              // 还原中
  hasBackup: boolean;                // 是否有备份
  filesInfo: SubtitleDataResponse['files'] | null;

  // 操作
  loadSubtitles: () => Promise<void>;
  updateEntry: (index: number, changes: Partial<SubtitleEntry>) => void;
  addEntry: (startTime: number, endTime: number) => void;
  deleteEntry: (index: number) => void;
  saveToServer: () => Promise<boolean>;
  saveDraftLocal: () => Promise<void>;
  mergeVideo: () => Promise<boolean>;
  restoreToOriginal: () => Promise<boolean>;
  setCurrentTime: (time: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setSelectedIndex: (index: number | null) => void;
  seekTo: (time: number) => void;
  discardDraft: () => Promise<void>;
}
```

### 自动保存机制

```typescript
const AUTO_SAVE_INTERVAL = 30000; // 30 秒

// 定时自动保存草稿
useEffect(() => {
  if (!isDirty) return;

  const interval = setInterval(() => {
    saveDraftLocal();  // 保存到 IndexedDB
  }, AUTO_SAVE_INTERVAL);

  return () => clearInterval(interval);
}, [isDirty, saveDraftLocal]);

// 组件卸载时保存草稿
useEffect(() => {
  return () => {
    if (isDirty && entries.length > 0) {
      saveDraft(entries);
    }
  };
}, [isDirty, entries]);
```

### 草稿恢复流程

```typescript
const loadSubtitles = useCallback(async () => {
  // 1. 检查备份状态
  const backupStatus = await hasSubtitleBackup();
  setHasBackup(backupStatus.hasBackup);

  // 2. 检查本地草稿
  const hasDraftData = await hasDraft();
  if (hasDraftData) {
    const draftEntries = await loadDraft();
    if (draftEntries && draftEntries.length > 0) {
      setEntries(draftEntries);
      setIsDirty(true);
      message.info('已恢复上次编辑的草稿');
      return;
    }
  }

  // 3. 从服务器加载
  const data = await getSubtitles();
  setEntries(data.entries);
  setIsDirty(false);

  // 4. 创建备份 (首次加载)
  if (!backupStatus.hasBackup && data.entries.length > 0) {
    await backupSubtitles();
    setHasBackup(true);
  }
}, []);
```

---

## 核心交互

### 1. 空格键播放片段 (Aegisub 风格)

```
用户选中字幕 #3
    ↓
按下空格键
    ↓
┌─────────────────────────────────┐
│ 1. 停止当前播放                  │
│ 2. 记录结束时间 (playUntilRef)   │
│ 3. Seek 到开始时间               │
│ 4. 延迟 50ms 后开始播放          │
└─────────────────────────────────┘
    ↓
播放进行中...
    ↓
currentTime >= playUntilRef.current
    ↓
自动停止播放
```

### 2. 视频-波形-列表三向同步

```
           ┌─────────────────────────────────────┐
           │         handleSeekTo(time)          │
           │   (统一 Seek 入口，同步三个组件)     │
           └─────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
   setCurrentTime   videoRef.seekTo   timelineRef.seekTo
        │                 │                 │
        ↓                 ↓                 ↓
   更新状态          视频 Seek          波形 Seek
```

**时间更新来源**:

| 来源 | 触发 |
|------|------|
| 视频 `onTimeUpdate` | 视频播放进度 |
| 波形 `audioprocess` | WaveSurfer 播放进度 |
| 波形 `seeking` | 用户点击波形 |
| 字幕列表点击 | 点击条目跳转 |

### 3. 字幕区域拖拽

```
用户拖拽波形上的字幕区域边缘
    ↓
RegionsPlugin 触发 'region-updated' 事件
    ↓
获取 region.id → entryIndex 映射
    ↓
调用 onUpdateEntry(entryIndex, { startTime, endTime })
    ↓
更新 entries 状态
    ↓
SubtitleList 重新渲染，显示新时间
```

---

## 数据流

### SubtitleEntry 数据结构

```typescript
interface SubtitleEntry {
  index: number;        // 字幕序号 (1-based)
  startTime: number;    // 开始时间 (秒)
  endTime: number;      // 结束时间 (秒)
  text: string;         // 翻译文本
  originalText?: string;// 原文 (可选)
}
```

### 数据持久化

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Browser    │    │  IndexedDB   │    │   Backend    │
│   Memory     │◄───│   (草稿)     │◄───│   (API)      │
└──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │
       │                   │                   │
  entries 状态         本地草稿            服务器字幕
  (实时编辑)         (30s 自动保存)       (手动保存)
```

---

## API 接口

### 字幕 API (`subtitleApi.ts`)

| 接口 | 方法 | 说明 |
|------|------|------|
| `getSubtitles()` | GET | 获取字幕列表 |
| `saveSubtitles(entries)` | PUT | 保存字幕 |
| `backupSubtitles()` | POST | 创建字幕备份 |
| `hasSubtitleBackup()` | GET | 检查是否有备份 |
| `restoreSubtitles()` | POST | 还原到原始字幕 |
| `mergeSubtitlesToVideo()` | POST | 合并字幕到视频 |
| `getAudioStreamUrl()` | - | 获取音频流 URL |

### IndexedDB 草稿存储 (`indexeddb.ts`)

```typescript
saveDraft(entries: SubtitleEntry[]): Promise<void>
loadDraft(): Promise<SubtitleEntry[] | null>
clearDraft(): Promise<void>
hasDraft(): Promise<boolean>
```

---

## 技术细节

### 1. Seek 防抖

视频和波形都有内部状态，需要防止循环 Seek：

```typescript
const isSeekingRef = useRef(false);

// Seek 时设置标记
const seekTo = (time: number) => {
  isSeekingRef.current = true;
  video.currentTime = time;
  setTimeout(() => {
    isSeekingRef.current = false;
  }, 100);
};

// 时间更新时检查标记
const handleTimeUpdate = () => {
  if (!isSeekingRef.current) {
    onTimeUpdate(currentTime);
  }
};
```

### 2. 波形区域同步

使用 Map 维护 region.id 和 entry index 的双向映射：

```typescript
const regionMapRef = useRef<Map<string, number>>(new Map());  // region.id → index
const indexToRegionRef = useRef<Map<number, string>>(new Map()); // index → region.id

// 更新区域时
entries.forEach((entry, index) => {
  const region = regions.addRegion({ ... });
  regionMapRef.current.set(region.id, index);
  indexToRegionRef.current.set(index, region.id);
});
```

### 3. 波形缩放

```typescript
const [zoomLevel, setZoomLevel] = useState(50);

// 滚轮缩放
const handleWheel = (e: WheelEvent) => {
  e.preventDefault();
  const delta = e.deltaY > 0 ? -10 : 10;
  const newZoom = Math.max(10, Math.min(500, zoomLevel + delta));
  setZoomLevel(newZoom);
  wavesurfer.zoom(newZoom);
};
```

### 4. 空格键延迟播放

解决 Seek 后立即播放时间偏移问题：

```typescript
// 问题: seek 后立即 play，视频可能还没 seek 到位
// 解决: 延迟 50ms 确保 seek 完成

setIsPlaying(false);
handleSeekTo(entry.startTime);
setTimeout(() => {
  setIsPlaying(true);
}, 50);
```

---

## 样式设计

### 配色方案

| 元素 | 颜色 |
|------|------|
| 主色调 | Indigo (#667eea) → Purple (#764ba2) 渐变 |
| 活跃状态 | Indigo-50 背景 + Indigo-500 边框 |
| 选中状态 | Indigo-400 ring |
| 波形进度 | #667eea (indigo) |
| 波形光标 | #764ba2 (purple) |

### 响应式布局

```css
/* 视频区域 40% + 字幕列表 60% */
.video-area { width: 40%; }
.subtitle-list-area { width: 60%; }

/* 时间轴固定高度 */
.timeline-area { height: 180px; }

/* 内容区域自适应 */
.content-area { height: calc(100% - 180px); }
```

---

## 扩展建议

### 待实现功能

1. **快捷键扩展**
   - `←/→` 微调时间 (±0.1s)
   - `Ctrl+S` 保存
   - `Delete` 删除选中字幕

2. **批量操作**
   - 多选字幕
   - 批量时间偏移
   - 批量删除

3. **撤销/重做**
   - 使用 useReducer 实现历史栈
   - `Ctrl+Z` / `Ctrl+Y` 快捷键

4. **字幕样式预览**
   - 字体大小调整
   - 位置调整
   - 颜色自定义
