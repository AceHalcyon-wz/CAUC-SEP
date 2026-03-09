/**
 * @file DESIGN_QUICK_REFERENCE.md
 * @path docs/
 * @description CAUC-SEP 设计系统快速参考卡片
 * @author Agent
 * @date 2026-03-08
 */

# CAUC-SEP 设计系统快速参考

## 色彩变量速查

### 主色
```css
--color-primary-50: #e6f7ff
--color-primary-100: #bae7ff
--color-primary-200: #91d5ff
--color-primary-300: #69c0ff
--color-primary-400: #40a9ff
--color-primary-500: #1890ff  /* 主色 */
--color-primary-600: #096dd9
--color-primary-700: #0050b3
--color-primary-800: #003a8c
--color-primary-900: #002766
```

### 功能色
```css
--color-success: #52c41a
--color-warning: #faad14
--color-error: #ff4d4f
--color-info: #1890ff
```

### 文字色
```css
--color-text-primary: rgba(0,0,0,0.85)
--color-text-secondary: rgba(0,0,0,0.65)
--color-text-tertiary: rgba(0,0,0,0.45)
--color-text-disabled: rgba(0,0,0,0.25)
```

### 边框色
```css
--color-border-primary: #d9d9d9
--color-border-secondary: #f0f0f0
--color-border-focus: #1890ff
```

### 背景色
```css
--color-bg-primary: #ffffff
--color-bg-secondary: #fafafa
--color-bg-tertiary: #f5f5f5
```

## 间距速查

```css
--spacing-1: 4px    /* 极小 */
--spacing-2: 8px    /* 小 */
--spacing-3: 12px   /* 中小 */
--spacing-4: 16px   /* 标准 */
--spacing-5: 20px   /* 中等 */
--spacing-6: 24px   /* 大 */
--spacing-8: 32px   /* 较大 */
--spacing-10: 40px  /* 大 */
--spacing-12: 48px  /* 很大 */
```

## 圆角速查

```css
--radius-xs: 2px
--radius-sm: 4px
--radius-base: 6px
--radius-md: 8px
--radius-lg: 12px
--radius-xl: 16px
--radius-2xl: 24px
--radius-full: 9999px
```

## 阴影速查

```css
--shadow-sm: 轻微阴影
--shadow-md: 中等阴影
--shadow-lg: 较大阴影
--shadow-xl: 大阴影
--shadow-card: 卡片阴影
--shadow-dropdown: 下拉菜单阴影
--shadow-modal: 模态框阴影
```

## 字体速查

### 字体大小
```css
--font-size-xs: 12px
--font-size-sm: 14px
--font-size-base: 16px
--font-size-lg: 18px
--font-size-xl: 20px
--font-size-2xl: 24px
--font-size-3xl: 30px
--font-size-4xl: 36px
--font-size-5xl: 48px
```

### 字重
```css
--font-weight-light: 300
--font-weight-normal: 400
--font-weight-medium: 500
--font-weight-semibold: 600
--font-weight-bold: 700
```

### 字体族
```css
--font-family-chinese: 'PingFang SC', 'Microsoft YaHei'
--font-family-english: 'Inter', 'Roboto'
--font-family-mono: 'JetBrains Mono', 'Consolas'
```

## 动画速查

```css
--transition-fast: 150ms
--transition-base: 200ms
--transition-slow: 300ms
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1)
```

## 状态色速查

```css
--color-status-online: #52c41a
--color-status-offline: #8c8c8c
--color-status-warning: #faad14
--color-status-error: #ff4d4f
--color-status-measuring: #1890ff
```

## SCSS 函数速查

```scss
spacing(4)          // var(--spacing-4)
primary-color(500)  // var(--color-primary-500)
neutral-color(600)  // var(--color-neutral-600)
font-size(lg)       // var(--font-size-lg)
radius(lg)          // var(--radius-lg)
shadow(md)          // var(--shadow-md)
transition(base)    // var(--transition-base)
```

## SCSS Mixins 速查

```scss
@include respond-to('md')        // 响应式
@include text-truncate(2)        // 文本截断
@include flex-center             // Flex 居中
@include flex-between            // Flex 两端对齐
@include card-style              // 卡片样式
@include button-hover            // 按钮悬停
@include status-indicator('online')  // 状态指示器
@include numeric-display('large')    // 数值显示
@include custom-scrollbar        // 自定义滚动条
```

## 常用组合

### 卡片样式
```css
.card {
  background-color: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
  box-shadow: var(--shadow-card);
}
```

### 按钮样式
```css
.button {
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
}
```

### 数值显示
```css
.numeric-value {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  letter-spacing: 0.05em;
}
```

### 状态徽章
```css
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}
```

## 响应式断点

```scss
@include respond-to('xs')  // max-width: 480px
@include respond-to('sm')  // max-width: 576px
@include respond-to('md')  // max-width: 768px
@include respond-to('lg')  // max-width: 992px
@include respond-to('xl')  // max-width: 1200px
@include respond-to('xxl') // max-width: 1600px
```

## Element Plus 兼容

```css
--el-color-primary: var(--color-primary-500)
--el-color-success: var(--color-success)
--el-color-warning: var(--color-warning)
--el-color-danger: var(--color-error)
--el-text-color-primary: var(--color-text-primary)
--el-border-color: var(--color-border-primary)
--el-bg-color: var(--color-bg-primary)
```

## 文件位置

```
src/styles/
├── design-tokens.css     # CSS 变量定义
├── variables.scss        # SCSS 变量和工具
├── global.css           # 全局样式
├── layout.css           # 布局样式
└── page-layout.scss     # 页面布局样式

docs/
├── DESIGN_SYSTEM.md     # 完整文档
└── DESIGN_QUICK_REFERENCE.md  # 快速参考（本文件）
```

## 使用建议

1. **优先使用语义化变量名**，避免硬编码颜色值
2. **保持一致性**，使用设计系统变量而非自定义值
3. **利用 SCSS 工具**，提高开发效率
4. **遵循间距规范**，基于4px基准
5. **注意可访问性**，确保足够的颜色对比度

## 更新日期

最后更新：2026-03-08
版本：v2.0.0
