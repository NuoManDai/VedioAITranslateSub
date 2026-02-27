# subtitle-editor/ — AGENTS.md

同步字幕编辑套件：视频播放 + 可编辑列表 + 波形时间轴，由父组件 `SubtitleEditor.tsx` 编排。

## 组件一览

| 文件 | 角色 | 关键细节 |
|------|------|----------|
| `index.ts` | 桶导出 | 重导出所有组件 |
| `VideoSync.tsx` | 静音视频 + 字幕叠层 | `forwardRef` 暴露 `seekTo(time)`。通过 `/api/video/{id}/stream` 流式播放。通过 `playUntilRef` 在字幕 `endTime` 自动暂停 |
| `SubtitleList.tsx` | 可编辑字幕行 | 内联时间编辑（HH:MM:SS.mmm），TextArea 编辑翻译。点击行 = 跳转视频 + 时间轴。自动滚动到当前行 |
| `Timeline.tsx` | WaveSurfer.js 波形 | RegionsPlugin 提供可拖拽字幕区域。`forwardRef` 暴露 `seekTo(time)`、`updateRegions(subtitles)`。鼠标滚轮缩放 |
| `SubtitleStyleModal.tsx` | Ant Design 样式控件 | 字号、颜色、描边、位置。通过 editorSettings 持久化到 localStorage |

## 组件协调

父组件 `SubtitleEditor.tsx` 持有 `currentTime`、`isPlaying`、`subtitles` 状态。

```
SubtitleList 点击行
  → videoSyncRef.seekTo(time)
  → timelineRef.seekTo(time)

空格键（document 监听器）
  → 从当前字幕 startTime 播放到 endTime
  → activeElement 检查防止与文本输入冲突

字幕编辑
  → 更新状态
  → timelineRef.updateRegions(subtitles)（手动调用，非响应式）
```

## 布局

```
┌──────────────────────────────────────────┐
│  VideoSync (40%)  │  SubtitleList (60%)  │
├──────────────────────────────────────────┤
│  Timeline（底部固定 180px）              │
└──────────────────────────────────────────┘
```

## 编码规范

- 跨组件同步使用 Ref 而非回调（`useImperativeHandle`）
- `SubtitleDisplayStyle` 类型控制叠层定位
- 时间格式：编辑器全局使用 `HH:MM:SS.mmm`
- 状态存储在 `useSubtitleEditor` Hook 中，不在这些组件内
- IndexedDB 每 30 秒自动保存。草稿对账比较时间戳与服务器版本

## 注意事项

1. **`videoFilename` 属性名具有误导性。** VideoSync 实际接收的是 videoId（UUID），不是文件名。名称是历史遗留。
2. **WaveSurfer 区域是命令式的。** 修改字幕不会自动更新区域。必须手动调用 `ref.updateRegions()`。
3. **空格键监听在 `document` 上。** 有 `activeElement` 检查保护，但新增可聚焦元素可能破坏它。
4. **时间轴鼠标滚轮缩放**可能在事件冒泡未阻止时劫持页面滚动。
5. **SubtitleStyleModal 第 113 行有 `as any` 强转。** 已知技术债务，不要新增更多。
6. **视频流 URL** 通过 `getVideoStreamUrl(videoId)` 构建。如果后端 CORS 配置变更会出问题。
