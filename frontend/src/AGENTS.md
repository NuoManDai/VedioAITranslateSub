# AGENTS.md — frontend/src/

React 18 + TypeScript 5.3 + Vite 5 + Ant Design 5 + TailwindCSS 3。SPA 应用，懒加载页面，轮询进度，内联字幕编辑。

## 目录结构

```
src/
├── main.tsx              # ReactDOM root，Ant ConfigProvider（zhCN 语言，蓝色主题），BrowserRouter
├── App.tsx               # 路由 + lazy() 导入 + Suspense
├── pages/
│   ├── VideoList.tsx     # 网格卡片，搜索/筛选/排序，无限滚动（IntersectionObserver），上传弹窗
│   ├── Home.tsx          # 视频详情：VideoPlayer + ProcessingPanel + ConsolePanel。恢复提示
│   └── SubtitleEditor.tsx # 独立页面（无 MainLayout）。VideoSync(40%) + SubtitleList(60%) + Timeline(180px)
├── components/
│   ├── MainLayout.tsx    # Header（导航 + LanguageSwitch）+ Outlet + Footer
│   ├── VideoPlayer.tsx   # HTML5 视频播放控件
│   ├── ProcessingPanel.tsx # 标签页：字幕/校对/配音。阶段进度轮询。513 行
│   ├── ConsolePanel.tsx  # 深色主题日志查看器，通过 createPortal 全屏
│   ├── StageOutputFiles.tsx # 每阶段的流水线输出文件
│   ├── VideoUpload.tsx   # XHR 上传带进度回调
│   ├── YouTubeDownload.tsx  # URL 输入 + 下载触发
│   ├── SettingsModal.tsx # 懒加载。委托给 settings/*
│   ├── LanguageSwitch.tsx # i18n 语言选择下拉框
│   ├── settings/         # 9 个文件：LLM、字幕、配音、网络设置等
│   └── subtitle-editor/  # 见 subtitle-editor/AGENTS.md
├── hooks/
│   ├── index.ts          # 桶导出
│   ├── useSubtitleEditor.ts # 编辑器主状态。IndexedDB 每 30 秒自动保存。草稿对账
│   ├── useProcessingStatus.ts # 智能轮询器，空闲时自动停止
│   └── useConfig.ts      # 获取/更新 Configuration
├── services/
│   ├── api.ts            # fetchApi<T> 封装、XHR 上传、ApiRequestError
│   ├── subtitleApi.ts    # 字幕 CRUD、合并、备份/恢复、音频流
│   ├── indexeddb.ts      # 通过 idb 库持久化草稿
│   ├── editorSettings.ts # localStorage 编辑器偏好（字号、布局等）
│   └── polling.ts        # createPolling<T> 工厂
├── types/index.ts        # 统一导出：Video、ProcessingJob、Configuration、SubtitleEntry、常量
├── i18n/
│   ├── index.ts          # i18next：浏览器检测 → localStorage → navigator。回退：'en'
│   └── locales/          # 7 个 JSON 文件：en、zh-CN、zh-HK、ja、es、ru、fr
└── styles/globals.css    # Tailwind @apply 类、Ant Design 覆盖、自定义工具类
```

## 路由

```
BrowserRouter -> Routes
├── MainLayout（Header + Outlet + Footer）
│   ├── /              -> VideoList（懒加载）
│   └── /video/:id     -> Home（懒加载）
└── /video/:id/editor  -> SubtitleEditor（懒加载，独立页面，无 MainLayout）
```

所有页面使用 `React.lazy()` + `Suspense`。路径别名：`@/*` → `src/*`。

## 状态与数据流

- 无 Redux/Zustand/Context Provider。纯 `useState` + 自定义 Hooks + props 传递。
- IndexedDB（通过 `idb`）：字幕草稿每 30 秒自动保存，加载时草稿与服务器对账比较时间戳。
- localStorage：编辑器设置（字号、布局）、i18n 语言偏好。
- 进度轮询：`setTimeout` 递归，间隔 3000ms，非 setInterval。空闲时自动停止。

## 样式

- Tailwind 工具类（主要方式）。Preflight 已禁用以兼容 Ant Design。
- Ant Design 主题 token 在 main.tsx 中：`colorPrimary: '#3b82f6'`、`borderRadius: 8`。
- `globals.css`：自定义类（`.modern-card`、`.btn-primary`）+ 用 `!important` 覆盖 Ant Design。
- 无 CSS Modules。

## 编码规范

- 组件：PascalCase 文件名。Hooks：camelCase + `use` 前缀。
- 导入顺序：React → 第三方（antd、icons、router、i18n）→ 本地组件 → `import type` → 服务。
- 优先 `interface` 而非 `type` 别名。
- 所有 API 调用通过 `api.ts` 的 `fetchApi<T>()` 或 `subtitleApi.ts` 的函数。
- 新增 i18n 键时必须同时更新全部 7 个语言文件。

## 反模式

1. 禁止 `dangerouslySetInnerHTML`（StageOutputFiles 中有一处未消毒的使用，不要复制）
2. 禁止 `as any` / `@ts-ignore` / `@ts-expect-error`。扩展 interface 代替。
3. 禁止直接 `fetch()` 调用。使用 `fetchApi` 封装。
4. 禁止新的状态管理库。保持 useState + Hooks。
5. 禁止 CSS Modules。使用 Tailwind 类。

## 注意事项

- Ant Design 语言在 main.tsx 中硬编码 `zhCN`，不随 i18n 选择变化。
- `subtitleApi.ts` 复制了 `api.ts` 的 `API_BASE_URL` 和 `ApiRequestError`。已知技术债务。
- `SettingsModal` 在页面级懒加载之外还有单独的懒加载。
- `SubtitleEditor` 不使用 `MainLayout` 渲染。完全独立的页面。
- `VideoList.tsx`（547 行）和 `ProcessingPanel.tsx`（513 行）是最大的组件。
- Vite 代理目标是远程 `hsklw.vicp.fun:8000`，非 localhost。
- CORS 后端仅允许 `localhost:5173` 和 `127.0.0.1:5173`。
