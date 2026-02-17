# 字幕校对编辑器 技术架构文档

## 目录

1. [功能概述](#功能概述)
2. [系统架构](#系统架构)
3. [前端组件架构](#前端组件架构)
4. [状态管理](#状态管理)
5. [数据持久化](#数据持久化)
6. [核心交互设计](#核心交互设计)
7. [后端服务](#后端服务)
8. [API 接口](#api-接口)
9. [时序图](#时序图)
10. [技术细节](#技术细节)

---

## 功能概述

字幕校对编辑器（SubtitleEditor）是 VideoLingo 的专业字幕编辑模块，提供 **Aegisub 风格**的字幕编辑体验。用户可以在视频处理流水线完成后，对生成的双语字幕进行校对、时间轴调整，并最终将字幕烧录到视频中。

### 核心能力

| 能力 | 说明 |
|------|------|
| 双语字幕编辑 | 同时编辑原文和译文，实时预览效果 |
| 波形时间轴 | 基于 WaveSurfer.js 的音频波形可视化，拖拽调整时间轴 |
| 视频字幕叠加 | 视频播放器实时渲染字幕叠加预览 |
| 草稿自动保存 | IndexedDB 本地存储，30 秒自动保存 |
| 字幕还原 | 一键还原到原始生成的字幕 |
| 多种合并模式 | 支持 5 种字幕格式烧录到视频 |
| 字幕样式配置 | 字体大小、颜色、布局可自定义 |

---

## 系统架构

```mermaid
flowchart TB
    subgraph Frontend["前端 (React)"]
        Page["SubtitleEditor Page<br/>页面布局 + 快捷键"]
        Hook["useSubtitleEditor<br/>状态管理 Hook"]
        
        subgraph Components["UI 组件"]
            VS["VideoSync<br/>视频同步播放"]
            SL["SubtitleList<br/>字幕列表编辑"]
            TL["Timeline<br/>波形时间轴"]
            SM["SubtitleStyleModal<br/>样式配置弹窗"]
        end
        
        subgraph Services["服务层"]
            API["subtitleApi.ts<br/>API 客户端"]
            IDB["indexeddb.ts<br/>IndexedDB 草稿存储"]
            ES["editorSettings.ts<br/>编辑器设置"]
        end
    end
    
    subgraph Backend["后端 (FastAPI)"]
        Routes["subtitles.py<br/>API 路由"]
        Service["SubtitleService<br/>字幕业务逻辑"]
    end
    
    subgraph Storage["存储"]
        SRT["SRT 文件<br/>src.srt / trans.srt<br/>src_trans.srt / trans_src.srt"]
        Backup["backup/<br/>原始字幕备份"]
        Audio["audio/<br/>raw.mp3 / vocal.mp3"]
        Video["video.mp4<br/>源视频"]
    end
    
    Page --> Hook
    Page --> Components
    Hook --> Services
    Components --> Hook
    API --> Routes
    Routes --> Service
    Service --> SRT
    Service --> Backup
    Service --> Audio
    
    VS -->|视频流| Video
    TL -->|音频流| Audio
```

---

## 前端组件架构

### 页面布局

```mermaid
flowchart TD
    subgraph Layout["SubtitleEditor 页面布局"]
        Header["Header (64px)<br/>返回 | 标题 | 未保存标记 | 操作按钮"]
        
        subgraph Main["主内容区 (calc(100vh - 180px))"]
            subgraph TopRow["上部 (flex)"]
                VideoArea["VideoSync (40%)<br/>视频播放 + 字幕叠加"]
                ListArea["SubtitleList (60%)<br/>可编辑字幕列表"]
            end
            
            TimelineArea["Timeline (180px)<br/>WaveSurfer 波形 + 区域"]
        end
    end
    
    Header --> Main
    TopRow --> TimelineArea
```

### 组件职责

```mermaid
classDiagram
    class SubtitleEditorPage {
        -videoRef: VideoSyncRef
        -timelineRef: TimelineRef
        -editorSettings: EditorSettings
        -subtitleStyle: SubtitleDisplayStyle
        +handleSeekTo(time) void
        +handleBack() void
        +handleSave() void
        +handleMergeClick() void
        +handleRestore() void
        +Space键: 播放选中片段
    }
    
    class VideoSync {
        <<forwardRef>>
        -videoRef: HTMLVideoElement
        -isSeekingRef: boolean
        -durationRef: number
        +seekTo(time) void
        +activeSubtitle: SubtitleEntry
        +字幕叠加渲染
        +播放/暂停控制
        +进度条
    }
    
    class SubtitleList {
        -listRef: HTMLDivElement
        +parseTimeString(str) number
        +formatSrtTime(seconds) string
        +findActiveIndex(entries, time) number
        +自动滚动到当前字幕
        +时间码编辑 (HH:MM:SS,mmm)
        +双语文本编辑
        +删除字幕条目
    }
    
    class Timeline {
        <<forwardRef>>
        -wavesurferRef: WaveSurfer
        -regionsRef: RegionsPlugin
        -regionMapRef: Map~string,number~
        +seekTo(time) void
        +updateRegions() void
        +色块拖拽调整时间
        +空白区域拖拽创建字幕
        +滚轮缩放
    }
    
    class SubtitleStyleModal {
        -form: Form
        +loadStyleConfig() void
        +handleSave() void
        +译文样式配置
        +原文样式配置
        +布局配置
    }
    
    SubtitleEditorPage --> VideoSync
    SubtitleEditorPage --> SubtitleList
    SubtitleEditorPage --> Timeline
    SubtitleEditorPage --> SubtitleStyleModal
```

### 组件通信

```mermaid
flowchart LR
    subgraph Page["SubtitleEditor Page"]
        State["共享状态<br/>entries, currentTime,<br/>isPlaying, selectedIndex"]
    end
    
    VS["VideoSync"] -->|onTimeUpdate| State
    VS -->|onPlayingChange| State
    
    SL["SubtitleList"] -->|onSelectEntry| State
    SL -->|onUpdateEntry| State
    SL -->|onSeekTo| State
    
    TL["Timeline"] -->|onSeek| State
    TL -->|onUpdateEntry| State
    TL -->|onAddEntry| State
    TL -->|onSelectEntry| State
    TL -->|onPlayingChange| State
    
    State -->|currentTime| VS
    State -->|isPlaying| VS
    State -->|entries| VS
    
    State -->|currentTime| SL
    State -->|entries| SL
    State -->|selectedIndex| SL
    
    State -->|currentTime| TL
    State -->|isPlaying| TL
    State -->|entries| TL
    State -->|selectedIndex| TL
```

---

## 状态管理

### useSubtitleEditor Hook

```mermaid
stateDiagram-v2
    [*] --> Loading: 组件挂载
    
    Loading --> Loaded: loadSubtitles()
    Loading --> DraftRestored: 发现有效草稿
    
    state Loaded {
        [*] --> Clean
        Clean --> Dirty: updateEntry / addEntry / deleteEntry
        Dirty --> Clean: saveToServer()
        Dirty --> Dirty: 自动保存草稿 (30s)
        Dirty --> Clean: restoreToOriginal()
    }
    
    DraftRestored --> Dirty: 草稿已恢复
    
    state "自动保存循环" as AutoSave {
        [*] --> 检查isDirty
        检查isDirty --> 保存到IndexedDB: isDirty = true
        检查isDirty --> 跳过: isDirty = false
        保存到IndexedDB --> 等待30秒
        跳过 --> 等待30秒
        等待30秒 --> 检查isDirty
    }
```

### 状态字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `entries` | `SubtitleEntry[]` | 字幕条目列表 |
| `currentTime` | `number` | 当前播放时间（秒） |
| `isPlaying` | `boolean` | 是否正在播放 |
| `selectedIndex` | `number \| null` | 当前选中的字幕索引 |
| `isDirty` | `boolean` | 是否有未保存的更改 |
| `isLoading` | `boolean` | 是否正在加载 |
| `isSaving` | `boolean` | 是否正在保存到服务器 |
| `isMerging` | `boolean` | 是否正在合并到视频 |
| `isRestoring` | `boolean` | 是否正在还原 |
| `hasBackup` | `boolean` | 是否存在备份 |

### SubtitleEntry 数据结构

```typescript
interface SubtitleEntry {
  index: number;        // 字幕序号
  startTime: number;    // 开始时间（秒）
  endTime: number;      // 结束时间（秒）
  text: string;         // 译文
  originalText?: string; // 原文
}
```

---

## 数据持久化

### 三层存储架构

```mermaid
flowchart TD
    subgraph Layer1["第一层: 浏览器内存"]
        React["React State<br/>entries: SubtitleEntry[]<br/>实时响应，最新数据"]
    end
    
    subgraph Layer2["第二层: IndexedDB (本地)"]
        IDB["数据库: subtitle-editor<br/>存储: drafts<br/>键: current-draft<br/>自动保存间隔: 30秒"]
    end
    
    subgraph Layer3["第三层: 服务器 API"]
        Server["4 个 SRT 文件同步写入<br/>src.srt / trans.srt<br/>src_trans.srt / trans_src.srt"]
    end
    
    React -->|"每30秒自动保存<br/>组件卸载时保存"| IDB
    React -->|"用户点击'保存字幕'"| Server
    IDB -->|"页面加载时恢复草稿"| React
    Server -->|"loadSubtitles()"| React
    
    style Layer1 fill:#e8f5e9
    style Layer2 fill:#fff3e0
    style Layer3 fill:#e3f2fd
```

### IndexedDB 存储结构

```typescript
// 数据库配置
const DB_NAME = 'subtitle-editor';
const DB_VERSION = 1;
const STORE_NAME = 'drafts';
const DRAFT_KEY = 'current-draft';

// 存储格式
interface DraftRecord {
  id: string;                    // 固定为 'current-draft'
  entries: SubtitleEntry[];      // 字幕数据
  updatedAt: string;             // ISO 时间戳
}
```

### 草稿恢复策略

```mermaid
flowchart TD
    A[页面加载] --> B[获取服务器数据]
    B --> C{IndexedDB 有草稿?}
    
    C -->|否| D[使用服务器数据]
    C -->|是| E[加载草稿数据]
    
    E --> F{比较草稿与服务器}
    F -->|"条目数不同<br/>或首条内容不同"| G[服务器数据更新<br/>清除草稿<br/>使用服务器数据]
    F -->|数据一致| H[恢复草稿<br/>标记 isDirty=true<br/>显示'已恢复草稿']
    
    D --> I[创建备份（首次）]
    G --> I
    H --> I
```

---

## 核心交互设计

### Aegisub 风格快捷键播放

```mermaid
sequenceDiagram
    participant User as 用户
    participant Page as SubtitleEditor
    participant Video as VideoSync
    participant Timeline as Timeline
    
    User->>Page: 点击字幕条目
    Page->>Page: setSelectedIndex(index)
    Page->>Video: seekTo(entry.startTime)
    Page->>Timeline: seekTo(entry.startTime)
    
    User->>Page: 按空格键
    Page->>Page: 停止当前播放
    
    alt 自动停止开启
        Page->>Page: 设置 playUntilRef = entry.endTime
    end
    
    Page->>Video: seekTo(entry.startTime)
    Page->>Page: 延迟 50ms
    Page->>Page: setIsPlaying(true)
    Video->>Video: 开始播放
    
    loop 播放中
        Video->>Page: onTimeUpdate(currentTime)
        Page->>Page: 检查 currentTime >= endTime - 0.05
    end
    
    alt 到达结束时间
        Page->>Page: setIsPlaying(false)
        Page->>Video: seekTo(endTime - 0.01)
        Page->>Timeline: seekTo(endTime - 0.01)
    end
```

### 三方同步机制

视频播放器、波形时间轴、字幕列表三个组件通过共享状态实现同步：

```mermaid
flowchart LR
    subgraph Sync["三方同步"]
        Video["VideoSync<br/>视频播放器"]
        Timeline["Timeline<br/>波形时间轴"]
        List["SubtitleList<br/>字幕列表"]
    end
    
    CentralState["共享状态<br/>currentTime<br/>isPlaying<br/>selectedIndex"]
    
    Video <-->|"timeUpdate / seekTo"| CentralState
    Timeline <-->|"seeking / seekTo"| CentralState
    List <-->|"click / autoScroll"| CentralState
```

| 操作 | 触发源 | 同步目标 |
|------|--------|---------|
| 点击字幕条目 | SubtitleList | Video seekTo + Timeline seekTo |
| 拖拽波形游标 | Timeline | Video seekTo + List autoScroll |
| 视频播放 timeUpdate | VideoSync | Timeline position + List autoScroll |
| 空格键播放 | Page keydown | Video play + Timeline play |
| 拖拽区域边缘 | Timeline | entries 更新 → 三方刷新 |

### WaveSurfer 波形时间轴

```mermaid
flowchart TD
    subgraph WaveSurfer["WaveSurfer.js 实例"]
        WS["WaveSurfer.create()<br/>waveColor: #e0e0e0<br/>progressColor: #667eea<br/>cursorColor: #764ba2"]
        
        RP["RegionsPlugin<br/>字幕区域可视化"]
        TP["TimelinePlugin<br/>时间刻度标记"]
    end
    
    subgraph Regions["区域操作"]
        R1["拖拽区域边缘<br/>→ 调整字幕时间"]
        R2["拖拽空白区域<br/>→ 创建新字幕"]
        R3["点击区域<br/>→ 选中字幕"]
        R4["滚轮缩放<br/>→ 调整时间精度"]
    end
    
    WS --> RP
    WS --> TP
    RP --> Regions
    
    subgraph Colors["区域颜色"]
        C1["选中: rgba(102,126,234,0.5)"]
        C2["紫色: rgba(102,126,234,0.3)"]
        C3["绿色: rgba(76,175,80,0.3)"]
        C4["橙色: rgba(255,152,0,0.3)"]
        C5["粉色: rgba(233,30,99,0.3)"]
        C6["青色: rgba(0,188,212,0.3)"]
    end
```

---

## 后端服务

### SubtitleService 类图

```mermaid
classDiagram
    class SubtitleService {
        -output_dir: Path
        +parse_srt_file(filepath) List~SubtitleEntry~
        +parse_srt_content(content) List~SubtitleEntry~
        +write_srt_file(entries, filepath, include_original)
        +entries_to_srt_content(entries, include_original) str
        +get_all_subtitles() dict
        +save_all_subtitles(entries) dict
        +merge_subtitles_to_video(subtitle_type) dict
        +get_audio_path() Path
        +backup_original_subtitles() dict
        +has_backup() bool
        +restore_original_subtitles() dict
        -_merge_with_single_subtitle(srt_filename, is_translation)
        -_merge_with_bilingual_file(srt_filename)
        -_escape_ffmpeg_path(path) str
    }
    
    class SubtitleEntry {
        +index: int
        +start_time: float
        +end_time: float
        +text: str
        +original_text: str?
        +to_srt_time(seconds) str
        +to_srt_block(include_original) str
    }
    
    SubtitleService --> SubtitleEntry : 解析/写入
```

### 四文件同步写入

保存字幕时，`save_all_subtitles()` 同步更新 4 个 SRT 文件：

```mermaid
flowchart LR
    Input["entries<br/>(译文 + 原文)"] --> Proc["save_all_subtitles()"]
    
    Proc --> F1["src.srt<br/>仅原文"]
    Proc --> F2["trans.srt<br/>仅译文"]
    Proc --> F3["trans_src.srt<br/>译文 + 原文<br/>(每条两行)"]
    Proc --> F4["src_trans.srt<br/>原文 + 译文<br/>(每条两行)"]
```

### 合并到视频

支持 5 种字幕格式烧录：

| 模式 | 参数值 | 说明 | FFmpeg 处理方式 |
|------|--------|------|----------------|
| 双语分层 | `dual` | 默认，原文和译文分别渲染 | 调用 core `merge_subtitles_to_video()` |
| 译文在上 | `trans_src` | 单文件双语，译文上原文下 | 使用 trans_src.srt 单文件 |
| 原文在上 | `src_trans` | 单文件双语，原文上译文下 | 使用 src_trans.srt 单文件 |
| 仅译文 | `trans_only` | 只显示译文 | 使用 trans.srt 单文件 |
| 仅原文 | `src_only` | 只显示原文 | 使用 src.srt 单文件 |

### 备份与还原

```mermaid
flowchart TD
    subgraph Backup["备份流程"]
        B1[首次进入编辑器] --> B2{备份存在?}
        B2 -->|否| B3[复制 4 个 SRT 到 backup/]
        B2 -->|是| B4[跳过，保留原始备份]
    end
    
    subgraph Restore["还原流程"]
        R1[用户点击'还原'] --> R2[确认弹窗]
        R2 --> R3[复制 backup/ 文件回 output/]
        R3 --> R4[清除 IndexedDB 草稿]
        R4 --> R5[重新加载字幕]
    end
```

---

## API 接口

### 接口总览

```mermaid
flowchart LR
    subgraph Endpoints["字幕 API (/api/subtitles)"]
        E1["GET /api/subtitles<br/>获取所有字幕"]
        E2["PUT /api/subtitles<br/>保存编辑后的字幕"]
        E3["POST /api/subtitles/merge-video<br/>烧录字幕到视频"]
        E4["GET /api/subtitles/audio<br/>获取音频流"]
        E5["POST /api/subtitles/backup<br/>备份原始字幕"]
        E6["GET /api/subtitles/has-backup<br/>检查备份是否存在"]
        E7["POST /api/subtitles/restore<br/>还原到原始字幕"]
    end
```

### 接口详情

| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | `/api/subtitles` | - | `{ entries, files, totalCount }` | 获取字幕（优先读取 trans_src.srt） |
| PUT | `/api/subtitles` | `{ entries: SubtitleEntry[] }` | `{ success, savedFiles, entryCount }` | 同步保存到 4 个 SRT 文件 |
| POST | `/api/subtitles/merge-video` | `{ subtitleType }` | `{ success, outputVideo, exists }` | FFmpeg 烧录字幕到视频 |
| GET | `/api/subtitles/audio` | - | `audio/mpeg` (FileResponse) | 获取音频文件（raw.mp3 或 vocal.mp3） |
| POST | `/api/subtitles/backup` | - | `{ success, backedUp, skipped }` | 备份 SRT 文件到 backup/ 目录 |
| GET | `/api/subtitles/has-backup` | - | `{ hasBackup }` | 检查是否已有备份 |
| POST | `/api/subtitles/restore` | - | `{ success, restored, message }` | 从 backup/ 还原 SRT 文件 |

### 字幕读取优先级

```mermaid
flowchart TD
    A[get_all_subtitles] --> B{trans_src.srt 存在?}
    B -->|是| C[解析 trans_src.srt<br/>每条含译文+原文]
    B -->|否| D{src.srt 和 trans.srt 都存在?}
    D -->|是| E[分别解析后按 index 合并]
    D -->|否| F{src.srt 存在?}
    F -->|是| G[仅加载原文]
    F -->|否| H[返回空列表]
```

---

## 时序图

### 完整编辑流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Page as SubtitleEditor
    participant Hook as useSubtitleEditor
    participant IDB as IndexedDB
    participant API as subtitleApi
    participant Server as FastAPI
    participant Service as SubtitleService
    participant Files as SRT 文件
    
    Note over User,Files: 页面加载
    User->>Page: 进入编辑器
    Page->>Hook: loadSubtitles()
    Hook->>Server: GET /api/subtitles/has-backup
    Server-->>Hook: { hasBackup }
    Hook->>Server: GET /api/subtitles
    Server->>Service: get_all_subtitles()
    Service->>Files: 读取 trans_src.srt
    Files-->>Service: SRT 内容
    Service-->>Server: { entries, files }
    Server-->>Hook: SubtitleDataResponse
    
    Hook->>IDB: hasDraft()
    
    alt 有草稿且与服务器数据一致
        IDB-->>Hook: draftEntries
        Hook->>Hook: 恢复草稿, isDirty=true
    else 无草稿或服务器已更新
        Hook->>Hook: 使用服务器数据
    end
    
    Hook->>Server: POST /api/subtitles/backup (首次)
    
    Note over User,Files: 编辑过程
    User->>Page: 编辑字幕文本/时间
    Page->>Hook: updateEntry(index, changes)
    Hook->>Hook: isDirty = true
    
    loop 每 30 秒
        Hook->>IDB: saveDraft(entries)
    end
    
    Note over User,Files: 保存到服务器
    User->>Page: 点击"保存字幕"
    Page->>Hook: saveToServer()
    Hook->>Server: PUT /api/subtitles
    Server->>Service: save_all_subtitles(entries)
    Service->>Files: 写入 src.srt
    Service->>Files: 写入 trans.srt
    Service->>Files: 写入 trans_src.srt
    Service->>Files: 写入 src_trans.srt
    Files-->>Service: 写入完成
    Service-->>Server: { success, savedFiles }
    Server-->>Hook: SaveSubtitlesResponse
    Hook->>IDB: clearDraft()
    Hook->>Hook: isDirty = false
    
    Note over User,Files: 合并到视频
    User->>Page: 点击"合并到视频"
    Page->>Page: 显示格式选择弹窗
    User->>Page: 选择"双语分层" + 确认
    Page->>Hook: mergeVideo('dual')
    Hook->>Server: POST /api/subtitles/merge-video
    Server->>Service: merge_subtitles_to_video('dual')
    Service->>Service: 调用 core._7_sub_into_vid
    Service-->>Server: { success, outputVideo }
    Server-->>Hook: MergeVideoResponse
    Page->>Page: 显示成功弹窗
    Page->>Page: 返回首页
```

### 还原流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Hook as useSubtitleEditor
    participant IDB as IndexedDB
    participant Server as FastAPI
    participant Service as SubtitleService
    
    User->>Hook: restoreToOriginal()
    Hook->>Server: POST /api/subtitles/restore
    Server->>Service: restore_original_subtitles()
    Service->>Service: 复制 backup/*.srt → output/
    Service-->>Server: { success, restored }
    Server-->>Hook: RestoreResponse
    Hook->>IDB: clearDraft()
    Hook->>Server: GET /api/subtitles
    Server-->>Hook: 最新数据（已还原）
    Hook->>Hook: isDirty = false
```

---

## 技术细节

### VideoSync 字幕渲染

VideoSync 使用 CSS 定位在视频上叠加渲染字幕预览：

| 元素 | 样式属性 |
|------|---------|
| 译文（主字幕） | `fontSize`, `fontColor`, `bgColor`, `outlineWidth`, `outlineColor` |
| 原文（副字幕） | 相同属性，默认较小字号和较浅颜色 |
| 布局 | `marginBottom`（底部边距）, `lineSpacing`（行间距） |

默认样式：

| 属性 | 译文 | 原文 |
|------|------|------|
| 字体大小 | 18px | 14px |
| 字体颜色 | #FFFFFF | #CCCCCC |
| 背景色 | rgba(0,0,0,0.75) | rgba(0,0,0,0.6) |
| 描边 | 1px #000000 | 1px #000000 |
| 底部边距 | 40px | - |
| 行间距 | 8px | - |

### SubtitleList 时间格式解析

支持多种时间格式输入：

| 格式 | 示例 | 说明 |
|------|------|------|
| `HH:MM:SS,mmm` | `00:01:23,456` | 标准 SRT 格式 |
| `HH:MM:SS.mmm` | `00:01:23.456` | 点号分隔毫秒 |
| `MM:SS.mmm` | `1:23.456` | 省略小时 |
| `MM:SS` | `1:23` | 省略毫秒 |

### Timeline 区域管理

Timeline 组件维护两个 Map 来管理字幕条目与 WaveSurfer 区域的映射：

```
regionMapRef: Map<regionId, entryIndex>   // 区域ID → 字幕索引
indexToRegionRef: Map<entryIndex, regionId> // 字幕索引 → 区域ID
```

更新策略：当 `entries` 或 `selectedIndex` 变化时，清除所有区域并重新创建。使用 `isUpdatingRegionsRef` 标志防止重建过程中触发 `region-created` 事件。

### FFmpeg 路径转义

Windows 环境下 FFmpeg 字幕滤镜的路径需要特殊转义：

```python
def _escape_ffmpeg_path(self, path: str) -> str:
    # 反斜杠 → 正斜杠
    escaped = str(path).replace("\\", "/")
    # 盘符冒号转义: D: → D\:
    if len(escaped) >= 2 and escaped[1] == ":":
        escaped = escaped[0] + "\\:" + escaped[2:]
    return escaped
```

### 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 视频播放 | HTML5 `<video>` | 视频流播放、时间同步 |
| 波形渲染 | WaveSurfer.js | 音频可视化 |
| 区域管理 | WaveSurfer RegionsPlugin | 字幕时间段拖拽 |
| 时间刻度 | WaveSurfer TimelinePlugin | 时间标记 |
| 本地存储 | IndexedDB (`idb` 库) | 草稿自动保存 |
| UI 组件 | Ant Design 5.x | 表单、弹窗、按钮 |
| 样式 | TailwindCSS 3.4 | 布局和视觉效果 |
| 国际化 | react-i18next | 多语言支持 |
| 视频处理 | FFmpeg + OpenCV | 字幕烧录 |
| API 框架 | FastAPI | 后端路由 |
