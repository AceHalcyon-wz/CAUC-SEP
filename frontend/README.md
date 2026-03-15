# CAUC-SEP Frontend v3.5.1

中国民航大学科学实验平台前端应用

## 版本信息

- **版本**: v3.5.1
- **更新日期**: 2024-03-15
- **技术栈**: Vue 3 + Vite + Ant Design Vue + Pinia

## 主要更新

### v3.5.1 (2024-03-15)

- **UI/UX全面优化**: 重构Topbar和Sidebar组件，提升用户体验
- **布局优化**: 修复button位置和span元素顺序问题（汉字在左，符号在右）
- **响应式设计**: 完善移动端适配，支持侧边栏折叠/展开
- **国际化增强**: 扩充中英文翻译词条，覆盖更多场景
- **设计系统升级**: 完善design-tokens.css，新增更多CSS变量
- **性能优化**: 优化组件渲染性能，减少不必要的重渲染

### v3.5.0 (2024-03-07)

- **UI/UX全面升级**: 采用现代化设计系统，提升用户体验
- **新增设计系统**: 引入完整的design-system.css，统一视觉风格
- **组件优化**: 重构Layout、Sidebar、Topbar组件，支持响应式布局
- **API完善**: 新增device.js、user.js、websocket.js等API模块
- **WebSocket支持**: 实现实时数据推送和连接状态管理
- **国际化增强**: 完善多语言支持框架（中英文）

## 项目结构

```
src/
├── api/                    # API接口封装
│   ├── motor.js           # 电机控制API
│   ├── electromagnet.js   # 电磁铁控制API
│   ├── temperature.js     # 温控系统API
│   ├── piezo.js           # 压电陶瓷API
│   ├── ammeter.js         # 微电流采集API
│   ├── analysis.js        # 数据分析API
│   ├── device.js          # 设备管理API
│   ├── user.js            # 用户管理API
│   └── websocket.js       # WebSocket客户端
├── components/            # Vue组件
│   ├── layout/           # 布局组件
│   │   ├── Sidebar.vue   # 侧边栏组件（v3.5.1优化）
│   │   ├── Topbar.vue    # 顶部栏组件（v3.5.1优化）
│   │   └── StatusBar.vue # 状态栏组件
│   ├── common/           # 通用组件
│   ├── device/           # 设备组件
│   └── experiment/       # 实验组件
├── composables/          # 组合式函数
│   ├── useWebSocket.js   # WebSocket组合式函数
│   ├── useDeviceBase.js  # 设备基础组合式函数
│   └── ...
├── i18n/                 # 国际化配置
│   └── index.js          # 中英文翻译（v3.5.1扩充）
├── router/               # 路由配置
├── stores/               # Pinia状态管理
│   ├── devices.js        # 设备状态管理
│   ├── motor.js          # 电机状态管理
│   ├── electromagnet.js  # 电磁铁状态管理
│   └── ...
├── styles/               # 样式文件
│   ├── design-tokens.css # 设计令牌（v3.5.1扩充）
│   ├── design-system.css # 设计系统
│   ├── global.css        # 全局样式（v3.5.1优化）
│   └── layout.css        # 布局样式
├── utils/                # 工具函数
└── views/                # 页面视图
    ├── Layout.vue        # 主布局（v3.5.1优化）
    ├── device/           # 设备管理页面
    ├── experiment/       # 实验控制页面
    ├── analysis/         # 数据分析页面
    └── settings/         # 系统设置页面
```

## 设计系统

### 色彩系统

| 类别 | 颜色名称 | 色值 | 用途 |
|------|----------|------|------|
| 主色 | Primary 500 | #0077ff | 主要操作按钮、链接、高亮 |
| 主色 | Primary 600 | #2563eb | 按钮悬停态 |
| 成功色 | Success | #22c55e | 成功状态、在线指示 |
| 警告色 | Warning | #f59e0b | 警告状态、注意事项 |
| 错误色 | Error | #ef4444 | 错误状态、离线指示 |
| 背景色 | BG Primary | #ffffff | 主背景 |
| 背景色 | BG Secondary | #f8fafc | 次级背景、卡片背景 |
| 文字色 | Text Primary | #0f172a | 主要文字 |
| 文字色 | Text Secondary | #475569 | 次要文字 |

### 布局尺寸

```css
--sidebar-width: 260px;           /* 侧边栏展开宽度 */
--sidebar-collapsed-width: 80px;  /* 侧边栏折叠宽度 */
--topbar-height: 64px;            /* 顶部栏高度 */
--content-max-width: 1440px;      /* 内容最大宽度 */
```

### 间距系统（4px基准）

```css
--spacing-1: 4px;
--spacing-2: 8px;
--spacing-3: 12px;
--spacing-4: 16px;
--spacing-5: 20px;
--spacing-6: 24px;
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 代码检查

```bash
npm run lint
```

### 运行测试

```bash
npm run test
npm run test:e2e
```

## 环境变量

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000/ws
```

## 后端接口

### RESTful API

- `GET /api/v1/device/status` - 获取所有设备状态
- `GET /api/v1/device/{device_id}/status` - 获取指定设备状态
- `POST /api/v1/device/{device_id}/connect` - 连接设备
- `POST /api/v1/device/{device_id}/disconnect` - 断开设备
- `GET /api/v1/device/ports/scan` - 扫描可用串口
- `POST /api/v1/device/test_connection` - 测试设备连接

### WebSocket API

- `ws://localhost:8000/ws/devices` - 设备状态实时推送
- `ws://localhost:8000/ws/motor` - 电机数据实时推送
- `ws://localhost:8000/ws/electromagnet` - 电磁铁数据实时推送
- `ws://localhost:8000/ws/temperature` - 温度数据实时推送
- `ws://localhost:8000/ws/piezo` - 压电陶瓷数据实时推送
- `ws://localhost:8000/ws/ammeter` - 电流数据实时推送

## 浏览器支持

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 响应式断点

| 断点 | 宽度 | 说明 |
|------|------|------|
| xs | < 480px | 超小屏幕（手机） |
| sm | < 640px | 小屏幕 |
| md | < 768px | 中等屏幕（平板） |
| lg | < 1024px | 大屏幕 |
| xl | < 1280px | 超大屏幕 |
| 2xl | < 1536px | 特大屏幕 |

## 许可证

MIT License - 中国民航大学航空工程学院
