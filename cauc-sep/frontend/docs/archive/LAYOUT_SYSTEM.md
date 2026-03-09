# 自旋电子实验平台 - 三栏式布局系统

## 概述

本布局系统采用类似 Cursor、Trae 等现代 IDE 应用的三栏式设计，提供专业、高效的用户界面体验。

## 文件结构

```
src/
├── stores/
│   └── layout.js              # 布局状态管理
├── components/
│   └── layout/
│       ├── index.js           # 组件统一导出
│       ├── Sidebar.vue        # 左侧导航栏
│       ├── Topbar.vue         # 顶部工具栏
│       └── StatusBar.vue      # 底部状态栏
└── views/
    ├── Layout.vue             # 主布局容器
    └── TestLayout.vue         # 布局测试页面
```

## 布局结构

### 1. 左侧导航栏（Sidebar）

**位置**：固定在左侧，高度 100vh

**尺寸**：
- 折叠状态：64px
- 展开状态：240px

**功能**：
- 显示 4 个主要功能模块图标
- 支持折叠/展开状态切换
- 高亮当前激活模块
- 深蓝色渐变背景，科学仪器专业风格

**模块列表**：
1. 实验控制
2. 设备管理
3. 数据分析
4. 系统设置

### 2. 顶部工具栏（Topbar）

**位置**：固定在顶部，高度 48px

**布局**：
- 左侧：当前模块标题和子功能名称
- 中间：子功能标签页（动态切换）
- 右侧：操作按钮和用户信息

**功能**：
- 显示当前模块标题
- 显示子功能标签页
- 快速操作按钮（刷新、导出、全屏）
- 用户菜单

### 3. 底部状态栏（StatusBar）

**位置**：固定在底部，高度 32px

**布局**：
- 左侧：连接状态指示器
- 中间：操作提示和警告信息
- 右侧：时间戳显示

**功能**：
- 显示设备连接状态（未连接/连接中/已连接）
- 显示当前操作提示
- 显示警告和错误信息
- 实时时间戳

### 4. 主内容区域

**位置**：自适应，位于侧边栏右侧、顶栏下方、状态栏上方

**功能**：
- 显示路由页面内容
- 支持页面切换动画
- 支持组件缓存（keep-alive）

## 使用方法

### 1. 基本使用

布局系统已集成到 `Layout.vue` 中，只需在路由配置中使用即可：

```javascript
{
  path: '/experiment',
  component: () => import('@/views/Layout.vue'),
  children: [
    // 子路由配置
  ]
}
```

### 2. 状态管理

使用 `useLayoutStore` 管理布局状态：

```javascript
import { useLayoutStore } from '@/stores/layout'

const layoutStore = useLayoutStore()

// 切换侧边栏
layoutStore.toggleSidebar()

// 设置连接状态
layoutStore.setConnectionStatus('connected')

// 添加警告信息
layoutStore.addWarning('设备温度过高', 'warning')

// 设置操作提示
layoutStore.setOperationTip('正在执行测量...')
```

### 3. 响应式状态

```javascript
// 侧边栏状态
const isCollapsed = computed(() => layoutStore.isSidebarCollapsed)
const currentWidth = computed(() => layoutStore.currentSidebarWidth)

// 模块导航
const activeModule = computed(() => layoutStore.activeModule)
const activeChild = computed(() => layoutStore.activeChild)

// 状态栏信息
const connectionStatus = computed(() => layoutStore.connectionStatus)
const operationTip = computed(() => layoutStore.operationTip)
const warnings = computed(() => layoutStore.warnings)
```

## 设计特点

### 1. 科学仪器风格

- **配色方案**：深蓝色主色调（#1e3a5f ~ #081328）
- **强调色**：青色系（#14b8a6）
- **专业感**：渐变背景、发光效果、阴影层次

### 2. 交互体验

- **平滑过渡**：所有状态变化都有流畅的过渡动画
- **视觉反馈**：hover、active、selected 状态清晰
- **响应式设计**：适配不同屏幕尺寸

### 3. 性能优化

- **组件懒加载**：路由组件按需加载
- **状态管理**：使用 Pinia 进行高效状态管理
- **CSS 变量**：使用设计令牌系统，便于主题定制

## 测试页面

访问 `/test` 路由查看布局测试页面，可以测试：

- 侧边栏折叠/展开
- 连接状态切换
- 警告信息添加
- 布局状态查看

## 开发服务器

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 技术栈

- **Vue 3**：Composition API
- **Vue Router 4**：路由管理
- **Pinia**：状态管理
- **Element Plus**：UI 组件库
- **SCSS**：样式预处理

## 设计令牌

布局系统使用 CSS 变量实现设计令牌系统，详见 `src/styles/design-tokens.css`。

主要变量包括：
- 颜色系统（主色、强调色、中性色）
- 间距系统（基于 4px）
- 阴影层级
- 字体系统
- 过渡动画
- 圆角
- Z-Index 层级

## 注意事项

1. **Sass 依赖**：项目需要安装 `sass` 开发依赖
2. **图标注册**：Element Plus 图标已在 `main.js` 中全局注册
3. **路由配置**：确保路由 meta 包含 `title` 和 `breadcrumb` 字段
4. **响应式**：布局会根据侧边栏状态自动调整内容区域

## 后续优化

- [x] 添加暗色主题支持
- [ ] 实现侧边栏拖拽调整宽度
- [ ] 添加标签页持久化功能
- [ ] 优化移动端适配
- [x] 添加键盘快捷键支持

---

**更新日期**: 2026-03-08  
**维护者**: Agent
