/**
 * @file DESIGN_SYSTEM.md
 * @path docs/
 * @description CAUC-SEP 设计系统完整文档
 * @author Agent
 * @date 2026-03-08
 * @version 2.0.0
 */

# CAUC-SEP 设计系统文档

## 概述

CAUC-SEP（自旋电子器件实验平台）设计系统是一套完整的UI/UX规范，旨在为科学仪器平台提供统一、专业、易用的视觉体验。

## 设计原则

### 1. 专业性
- 采用科技蓝色系，体现科学仪器的专业性
- 清晰的视觉层级，便于数据展示和操作
- 精确的数值显示，符合实验数据要求

### 2. 易用性
- 直观的交互反馈
- 一致的操作逻辑
- 清晰的状态指示

### 3. 可访问性
- 符合WCAG 2.1 AA标准
- 足够的颜色对比度
- 键盘导航支持

## 色彩系统

### 主色（Primary）

科技蓝色系，用于主要操作和重要信息。

```css
/* 使用示例 */
.primary-button {
  background-color: var(--color-primary-500); /* #1890ff */
  border-color: var(--color-primary-500);
}

.primary-button:hover {
  background-color: var(--color-primary-400); /* #40a9ff */
}

.primary-text {
  color: var(--color-primary-500);
}
```

**色阶：**
- 50: #e6f7ff - 最浅，用于背景
- 100: #bae7ff - 浅色背景
- 200: #91d5ff - 悬停状态
- 300: #69c0ff - 强调色
- 400: #40a9ff - 悬停背景
- 500: #1890ff - **主色**
- 600: #096dd9 - 激活状态
- 700: #0050b3 - 深色强调
- 800: #003a8c - 深色背景
- 900: #002766 - 最深

### 辅助色（Secondary）

青色系，与主色协调，用于次要操作和装饰。

```css
.secondary-button {
  background-color: var(--color-secondary-500); /* #14b8a6 */
}

.accent-decoration {
  border-left: 3px solid var(--color-secondary-400);
}
```

### 功能色

#### 成功色（Success）
```css
.success-message {
  color: var(--color-success); /* #52c41a */
  background-color: var(--color-success-light);
}
```

#### 警告色（Warning）
```css
.warning-alert {
  color: var(--color-warning); /* #faad14 */
  background-color: var(--color-warning-light);
}
```

#### 错误色（Error）
```css
.error-message {
  color: var(--color-error); /* #ff4d4f */
  background-color: var(--color-error-light);
}
```

#### 信息色（Info）
```css
.info-badge {
  color: var(--color-info); /* #1890ff */
  background-color: var(--color-info-light);
}
```

### 中性色

用于文字、边框、背景等基础元素。

```css
/* 文字颜色 */
.primary-text { color: var(--color-text-primary); }   /* rgba(0,0,0,0.85) */
.secondary-text { color: var(--color-text-secondary); } /* rgba(0,0,0,0.65) */
.tertiary-text { color: var(--color-text-tertiary); }   /* rgba(0,0,0,0.45) */
.disabled-text { color: var(--color-text-disabled); }   /* rgba(0,0,0,0.25) */

/* 边框颜色 */
.primary-border { border-color: var(--color-border-primary); } /* #d9d9d9 */
.secondary-border { border-color: var(--color-border-secondary); } /* #f0f0f0 */

/* 背景颜色 */
.primary-bg { background-color: var(--color-bg-primary); } /* #ffffff */
.secondary-bg { background-color: var(--color-bg-secondary); } /* #fafafa */
.tertiary-bg { background-color: var(--color-bg-tertiary); } /* #f5f5f5 */
```

## 间距系统

基于4px基准的间距系统，确保视觉一致性。

```css
/* 间距变量 */
--spacing-1: 4px;
--spacing-2: 8px;
--spacing-3: 12px;
--spacing-4: 16px;
--spacing-5: 20px;
--spacing-6: 24px;
--spacing-8: 32px;
--spacing-10: 40px;
--spacing-12: 48px;
--spacing-16: 64px;
--spacing-20: 80px;

/* 使用示例 */
.card {
  padding: var(--spacing-6); /* 24px */
  margin-bottom: var(--spacing-4); /* 16px */
  gap: var(--spacing-3); /* 12px */
}

.button-group {
  gap: var(--spacing-2); /* 8px */
}
```

### 间距使用规范

| 间距级别 | 像素值 | 使用场景 |
|---------|--------|---------|
| spacing-1 | 4px | 极小间距，图标与文字 |
| spacing-2 | 8px | 小间距，组件内部元素 |
| spacing-3 | 12px | 中小间距，表单项间距 |
| spacing-4 | 16px | 标准间距，卡片内边距 |
| spacing-5 | 20px | 中等间距，段落间距 |
| spacing-6 | 24px | 大间距，卡片外边距 |
| spacing-8 | 32px | 较大间距，区块间距 |
| spacing-10 | 40px | 大间距，章节间距 |
| spacing-12 | 48px | 很大间距，页面区域 |
| spacing-16 | 64px | 极大间距，页面顶部 |
| spacing-20 | 80px | 超大间距，页面底部 |

## 圆角系统

```css
/* 圆角变量 */
--radius-xs: 2px;
--radius-sm: 4px;
--radius-base: 6px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
--radius-2xl: 24px;
--radius-full: 9999px;

/* 使用示例 */
.small-badge {
  border-radius: var(--radius-sm); /* 4px */
}

.button {
  border-radius: var(--radius-base); /* 6px */
}

.card {
  border-radius: var(--radius-lg); /* 12px */
}

.modal {
  border-radius: var(--radius-xl); /* 16px */
}

.avatar {
  border-radius: var(--radius-full); /* 圆形 */
}
```

### 圆角使用规范

| 圆角级别 | 像素值 | 使用场景 |
|---------|--------|---------|
| radius-xs | 2px | 小标签、徽章 |
| radius-sm | 4px | 小按钮、输入框 |
| radius-base | 6px | 标准按钮、标签 |
| radius-md | 8px | 中等组件 |
| radius-lg | 12px | 卡片、面板 |
| radius-xl | 16px | 对话框、大卡片 |
| radius-2xl | 24px | 特殊容器 |
| radius-full | 9999px | 圆形元素 |

## 阴影系统

```css
/* 阴影变量 */
--shadow-sm: 轻微阴影;
--shadow-md: 中等阴影;
--shadow-lg: 较大阴影;
--shadow-xl: 大阴影;

/* 特殊阴影 */
--shadow-card: 卡片阴影;
--shadow-dropdown: 下拉菜单阴影;
--shadow-modal: 模态框阴影;

/* 发光效果 */
--shadow-glow-primary: 主色发光;
--shadow-glow-success: 成功色发光;
--shadow-glow-warning: 警告色发光;
--shadow-glow-error: 错误色发光;

/* 使用示例 */
.card {
  box-shadow: var(--shadow-card);
}

.card:hover {
  box-shadow: var(--shadow-lg);
}

.dropdown {
  box-shadow: var(--shadow-dropdown);
}

.active-button {
  box-shadow: var(--shadow-glow-primary);
}
```

## 字体系统

### 字体族

```css
/* 中文字体 */
--font-family-chinese: 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB';

/* 英文字体 */
--font-family-english: 'Inter', 'Roboto', -apple-system;

/* 等宽字体（代码和数据） */
--font-family-mono: 'JetBrains Mono', 'Consolas', 'Monaco';

/* 通用字体 */
--font-family-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC';
```

### 字体大小

```css
--font-size-xs: 12px;   /* 辅助文字、标签 */
--font-size-sm: 14px;   /* 次要文字、说明 */
--font-size-base: 16px; /* 正文文字 */
--font-size-lg: 18px;   /* 小标题 */
--font-size-xl: 20px;   /* 中标题 */
--font-size-2xl: 24px;  /* 大标题 */
--font-size-3xl: 30px;  /* 特大标题 */
--font-size-4xl: 36px;  /* 超大标题 */
--font-size-5xl: 48px;  /* 巨大标题 */
```

### 字重

```css
--font-weight-light: 300;     /* 细体 */
--font-weight-normal: 400;    /* 常规 */
--font-weight-medium: 500;    /* 中等 */
--font-weight-semibold: 600;  /* 半粗 */
--font-weight-bold: 700;      /* 粗体 */
```

### 行高

```css
--line-height-tight: 1.25;    /* 紧凑 */
--line-height-normal: 1.5;    /* 标准 */
--line-height-relaxed: 1.75;  /* 宽松 */
--line-height-loose: 2;       /* 很宽松 */
```

### 使用示例

```css
/* 标题样式 */
.page-title {
  font-family: var(--font-family-chinese);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-tight);
  color: var(--color-text-primary);
}

/* 正文样式 */
.body-text {
  font-family: var(--font-family-sans);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-normal);
  line-height: var(--line-height-normal);
  color: var(--color-text-secondary);
}

/* 数值显示 */
.numeric-display {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  letter-spacing: 0.05em;
}
```

## 动画过渡

### 过渡时长

```css
--transition-fast: 150ms;   /* 快速 */
--transition-base: 200ms;   /* 标准 */
--transition-slow: 300ms;   /* 慢速 */
--transition-slower: 500ms; /* 很慢 */
```

### 缓动函数

```css
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);  /* 标准缓动 */
--ease-in: cubic-bezier(0.4, 0, 1, 1);        /* 缓入 */
--ease-out: cubic-bezier(0, 0, 0.2, 1);       /* 缓出 */
--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55); /* 弹跳 */
```

### 组合过渡

```css
--transition-colors: color, background-color, border-color;
--transition-transform: transform;
--transition-opacity: opacity;
--transition-shadow: box-shadow;
--transition-all: all;
```

### 使用示例

```css
/* 按钮悬停 */
.button {
  transition: var(--transition-all);
}

.button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* 颜色过渡 */
.link {
  transition: var(--transition-colors);
}

.link:hover {
  color: var(--color-primary-500);
}

/* 淡入淡出 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base) var(--ease-in-out);
}
```

## 响应式断点

```css
--breakpoint-xs: 480px;   /* 超小屏幕 */
--breakpoint-sm: 576px;   /* 小屏幕 */
--breakpoint-md: 768px;   /* 中等屏幕（平板） */
--breakpoint-lg: 992px;   /* 大屏幕（笔记本） */
--breakpoint-xl: 1200px;  /* 超大屏幕（桌面） */
--breakpoint-xxl: 1600px; /* 巨大屏幕 */
```

### 使用示例

```css
/* CSS 媒体查询 */
@media (max-width: 768px) {
  .sidebar {
    width: 100%;
  }
}

/* SCSS Mixin */
@import '@/styles/variables.scss';

.container {
  padding: var(--spacing-6);
  
  @include respond-to('md') {
    padding: var(--spacing-4);
  }
}
```

## 特殊用途变量

### 仪器状态色

```css
--color-status-online: #52c41a;      /* 在线 */
--color-status-offline: #8c8c8c;     /* 离线 */
--color-status-warning: #faad14;     /* 警告 */
--color-status-error: #ff4d4f;       /* 错误 */
--color-status-measuring: #1890ff;   /* 测量中 */
--color-status-standby: #722ed1;     /* 待机 */
--color-status-disconnected: #bfbfbf; /* 断开连接 */
```

### 信号强度色

```css
--color-signal-excellent: #52c41a;  /* 优秀 */
--color-signal-good: #73d13d;       /* 良好 */
--color-signal-fair: #faad14;       /* 一般 */
--color-signal-weak: #ff4d4f;       /* 较弱 */
--color-signal-none: #d9d9d9;       /* 无信号 */
```

### 数据可视化色

```css
--color-data-blue: #1890ff;   /* 蓝色数据 */
--color-data-cyan: #13c2c2;   /* 青色数据 */
--color-data-green: #52c41a;  /* 绿色数据 */
--color-data-yellow: #fadb14; /* 黄色数据 */
--color-data-orange: #fa8c16; /* 橙色数据 */
--color-data-red: #f5222d;    /* 红色数据 */
--color-data-purple: #722ed1; /* 紫色数据 */
--color-data-pink: #eb2f96;   /* 粉色数据 */
```

## SCSS 工具函数和 Mixins

### 函数

```scss
@import '@/styles/variables.scss';

// 获取间距
.element {
  padding: spacing(4); // var(--spacing-4)
}

// 获取主色
.primary-element {
  color: primary-color(500); // var(--color-primary-500)
}

// 获取中性色
.neutral-element {
  color: neutral-color(600); // var(--color-neutral-600)
}

// 获取字体大小
.title {
  font-size: font-size(2xl); // var(--font-size-2xl)
}

// 获取圆角
.card {
  border-radius: radius(lg); // var(--radius-lg)
}

// 获取阴影
.elevated-element {
  box-shadow: shadow(md); // var(--shadow-md)
}

// 获取过渡时间
.animated-element {
  transition: all transition(base); // var(--transition-base)
}
```

### Mixins

```scss
@import '@/styles/variables.scss';

// 响应式
.container {
  padding: var(--spacing-6);
  
  @include respond-to('md') {
    padding: var(--spacing-4);
  }
}

// 文本截断
.single-line {
  @include text-truncate(1);
}

.multi-line {
  @include text-truncate(3);
}

// Flex 居中
.centered-container {
  @include flex-center;
}

// Flex 两端对齐
.header {
  @include flex-between;
}

// 卡片样式
.my-card {
  @include card-style;
}

// 按钮悬停效果
.my-button {
  @include button-hover;
}

// 状态指示器
.status-online {
  @include status-indicator('online');
}

// 数值显示
.data-value {
  @include numeric-display('large');
}

// 自定义滚动条
.scrollable-container {
  @include custom-scrollbar;
}

// 禁用选择
.no-select-element {
  @include no-select;
}
```

## Element Plus 兼容性

设计系统已完全兼容 Element Plus，通过CSS变量覆盖实现主题定制。

```css
/* Element Plus 主色覆盖 */
--el-color-primary: var(--color-primary-500);

/* Element Plus 功能色覆盖 */
--el-color-success: var(--color-success);
--el-color-warning: var(--color-warning);
--el-color-danger: var(--color-error);
--el-color-info: var(--color-info);

/* Element Plus 文字色覆盖 */
--el-text-color-primary: var(--color-text-primary);
--el-text-color-regular: var(--color-text-secondary);

/* Element Plus 边框色覆盖 */
--el-border-color: var(--color-border-primary);

/* Element Plus 背景色覆盖 */
--el-bg-color: var(--color-bg-primary);
--el-bg-color-page: var(--color-bg-secondary);

/* Element Plus 圆角覆盖 */
--el-border-radius-base: var(--radius-base);

/* Element Plus 阴影覆盖 */
--el-box-shadow: var(--shadow-md);
```

## 最佳实践

### 1. 使用语义化变量名

```css
/* ✅ 推荐 */
.status-badge {
  color: var(--color-success);
}

/* ❌ 不推荐 */
.status-badge {
  color: #52c41a;
}
```

### 2. 保持一致性

```css
/* ✅ 推荐 - 使用设计系统变量 */
.card {
  padding: var(--spacing-4);
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

/* ❌ 不推荐 - 使用硬编码值 */
.card {
  padding: 16px;
  margin-bottom: 16px;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
```

### 3. 利用工具函数

```scss
/* ✅ 推荐 - 使用 SCSS 函数 */
.element {
  padding: spacing(4);
  color: primary-color(500);
  font-size: font-size(lg);
}

/* ❌ 不推荐 - 手动拼接变量名 */
.element {
  padding: var(--spacing-4);
  color: var(--color-primary-500);
  font-size: var(--font-size-lg);
}
```

### 4. 响应式设计

```scss
/* ✅ 推荐 - 使用 Mixin */
.container {
  padding: var(--spacing-6);
  
  @include respond-to('md') {
    padding: var(--spacing-4);
  }
  
  @include respond-to('sm') {
    padding: var(--spacing-3);
  }
}
```

## 文件结构

```
src/styles/
├── design-tokens.css     # CSS 变量定义
├── variables.scss        # SCSS 变量和工具
├── global.css           # 全局样式
├── layout.css           # 布局样式
└── page-layout.scss     # 页面布局样式
```

## 更新日志

### v2.0.0 (2026-03-08)
- 完全重构色彩系统，采用科技蓝色系
- 新增辅助色系统
- 优化功能色（成功/警告/错误/信息）
- 完善间距系统（基于4px）
- 新增圆角系统（8个级别）
- 优化阴影系统（更柔和的阴影）
- 完善字体系统（支持中英文和等宽字体）
- 新增动画过渡系统
- 新增响应式断点
- 新增 Element Plus 兼容变量
- 新增 SCSS 工具函数和 Mixins
- 新增仪器状态色和信号强度色
- 新增数据可视化色

## 贡献指南

如需修改设计系统，请遵循以下步骤：

1. 在 `design-tokens.css` 中修改 CSS 变量
2. 在 `variables.scss` 中同步更新 SCSS 变量
3. 更新本文档
4. 测试所有使用该变量的组件
5. 提交代码审查

## 联系方式

如有问题或建议，请联系前端团队。
