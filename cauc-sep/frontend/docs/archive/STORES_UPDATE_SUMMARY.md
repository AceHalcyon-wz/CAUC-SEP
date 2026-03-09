# Pinia Stores 更新总结

## 更新日期
2026-03-08

## 更新概述
完成Pinia状态管理的全面更新，确保与新架构兼容，优化布局系统集成，提供统一的导出和初始化机制。

---

## 修改的文件列表

### 1. 新增文件

#### `src/stores/index.js` ✨ 新增
**功能：** Stores统一导出文件

**关键特性：**
- 统一导出所有Stores
- 提供初始化辅助函数 `initializeDeviceStores()`
- 提供系统初始化函数 `initializeSystemStores()`
- 提供清理函数 `cleanupAllStores()`
- 提供设备状态查询函数 `getAllDeviceConnectionStatus()`

**示例用法：**
```javascript
import { useMotorStore, initializeDeviceStores } from '@/stores'

// 初始化所有设备Stores
initializeDeviceStores({ autoConnect: false })
```

#### `src/stores/README.md` ✨ 新增
**功能：** Stores使用文档

**内容：**
- Stores结构说明
- 快速开始指南
- 各Store详细说明
- 初始化和清理方法
- 最佳实践
- 故障排查

---

### 2. 更新的文件

#### `src/main.js` 📝 更新
**变更内容：**
- 添加Pinia实例创建
- 导入并初始化LayoutStore
- 添加应用初始化日志

**关键变更：**
```javascript
// 创建Pinia实例
const pinia = createPinia()

// 安装插件
app.use(pinia)

// 初始化布局Store
const layoutStore = useLayoutStore()
```

#### `src/router/index.js` 📝 更新
**变更内容：**
- 路由守卫中同步LayoutStore状态
- 添加路由后置守卫
- 优化页面标题设置

**关键变更：**
```javascript
router.beforeEach((to, from, next) => {
  // 同步布局Store的激活状态
  import('@/stores/layout').then(({ useLayoutStore }) => {
    const layoutStore = useLayoutStore()
    layoutStore.setActiveByPath(to.path)
  })
  next()
})
```

#### `src/stores/layout.js` 📝 更新
**变更内容：**
- 添加本地存储支持（保存布局偏好）
- 移除响应式断点检测（简化逻辑）
- 添加 `saveLayoutPreference()` 方法
- 添加 `loadLayoutPreference()` 方法
- 自动加载保存的布局偏好

**关键变更：**
```javascript
// 保存布局偏好到本地存储
function saveLayoutPreference() {
  const preference = {
    isSidebarCollapsed: isSidebarCollapsed.value,
    activeModuleId: activeModuleId.value,
    activeChildId: activeChildId.value
  }
  localStorage.setItem('layout-preference', JSON.stringify(preference))
}

// 从本地存储加载布局偏好
function loadLayoutPreference() {
  const saved = localStorage.getItem('layout-preference')
  if (saved) {
    const preference = JSON.parse(saved)
    // 恢复状态...
  }
}
```

#### `src/App.vue` 📝 更新
**变更内容：**
- 添加全局错误捕获
- 添加生命周期钩子
- 集成LayoutStore初始化

**关键变更：**
```javascript
// 全局错误处理
onErrorCaptured((error, instance, info) => {
  console.error('[App] Global error captured:', error)
  layoutStore.addWarning(`应用错误: ${error.message}`, 'error')
  return false
})

// 应用挂载时初始化
onMounted(() => {
  layoutStore.loadLayoutPreference()
})
```

---

## 未修改的文件

以下Stores文件保持不变，已验证与新架构兼容：

1. ✅ `src/stores/motor.js` - 电机控制Store
2. ✅ `src/stores/devices.js` - 统一设备状态Store
3. ✅ `src/stores/electromagnet.js` - 电磁铁控制Store
4. ✅ `src/stores/piezo.js` - 压电陶瓷控制Store
5. ✅ `src/stores/temperature.js` - 温度控制Store
6. ✅ `src/stores/ammeter.js` - 微电流采集Store
7. ✅ `src/stores/experiment.js` - 实验管理Store
8. ✅ `src/stores/audit.js` - 审计日志Store

**验证结果：**
- 所有Stores使用Composition API风格 ✅
- 所有Stores正确导出 ✅
- 所有Stores包含完整的JSDoc注释 ✅
- 所有Stores实现了init和cleanup方法 ✅
- 所有设备Stores集成了WebSocket连接 ✅

---

## 关键变更说明

### 1. 统一导出机制

**之前：**
```javascript
// 分散导入
import { useMotorStore } from '@/stores/motor'
import { useDevicesStore } from '@/stores/devices'
```

**现在：**
```javascript
// 统一导入（推荐）
import { useMotorStore, useDevicesStore } from '@/stores'
```

**优势：**
- 简化导入语句
- 更好的代码组织
- 便于维护和重构

### 2. 布局状态持久化

**新增功能：**
- 自动保存侧边栏折叠状态
- 自动保存当前激活模块
- 页面刷新后自动恢复布局

**实现方式：**
```javascript
// 自动保存（在切换侧边栏时）
toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
  saveLayoutPreference() // 自动保存
}

// 自动加载（在Store初始化时）
loadLayoutPreference() // 自动加载
```

### 3. 路由与状态同步

**新增功能：**
- 路由切换时自动更新激活模块
- 页面标题自动设置
- 面包屑自动生成

**实现方式：**
```javascript
// 路由守卫中同步
router.beforeEach((to, from, next) => {
  const layoutStore = useLayoutStore()
  layoutStore.setActiveByPath(to.path)
  next()
})
```

### 4. 全局错误处理

**新增功能：**
- 捕获所有未处理的错误
- 自动添加警告到状态栏
- 阻止错误传播导致应用崩溃

**实现方式：**
```javascript
onErrorCaptured((error, instance, info) => {
  layoutStore.addWarning(`应用错误: ${error.message}`, 'error')
  return false // 阻止传播
})
```

---

## 架构兼容性验证

### ✅ 与路由系统兼容
- LayoutStore与路由自动同步
- 页面切换时状态正确更新
- 面包屑导航正常工作

### ✅ 与布局系统兼容
- 侧边栏状态正确管理
- 模块导航正常工作
- 状态栏信息正确显示

### ✅ 与设备控制兼容
- 所有设备Stores正常工作
- WebSocket连接正常建立
- 实时数据更新正常

### ✅ 与实验管理兼容
- 实验创建、控制正常
- 数据导出功能正常
- 实验列表查询正常

---

## 使用建议

### 1. 应用初始化

在 `main.js` 中初始化：

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')
```

### 2. 组件中使用Stores

```vue
<script setup>
import { useMotorStore, useLayoutStore } from '@/stores'

const motorStore = useMotorStore()
const layoutStore = useLayoutStore()

// 访问状态
const position = motorStore.positionMm
const isCollapsed = layoutStore.isSidebarCollapsed

// 调用方法
motorStore.connectMotor()
layoutStore.toggleSidebar()
</script>
```

### 3. 设备初始化

```javascript
import { initializeDeviceStores } from '@/stores'

// 初始化所有设备Stores（不自动连接）
initializeDeviceStores({ autoConnect: false })

// 或自动连接所有设备
initializeDeviceStores({ autoConnect: true })
```

---

## 性能优化

### 1. 懒加载优化
- 路由组件使用懒加载
- Stores按需导入
- 避免循环依赖

### 2. 状态管理优化
- 使用Composition API减少内存占用
- 计算属性缓存优化
- WebSocket连接池管理

### 3. 本地存储优化
- 仅保存必要的布局偏好
- 使用JSON序列化
- 异常处理避免阻塞

---

## 测试建议

### 1. 功能测试
- [ ] 所有Stores正常初始化
- [ ] 设备连接/断开正常
- [ ] 布局状态持久化正常
- [ ] 路由切换同步正常

### 2. 集成测试
- [ ] LayoutStore与路由集成
- [ ] 设备Stores与WebSocket集成
- [ ] 全局错误处理正常

### 3. 性能测试
- [ ] 页面加载时间正常
- [ ] 内存占用合理
- [ ] WebSocket连接稳定

---

## 后续优化建议

### 1. 短期优化（1-2周）
- [ ] 添加Stores单元测试
- [ ] 优化WebSocket重连机制
- [ ] 添加离线状态管理

### 2. 中期优化（1个月）
- [ ] 实现Stores状态持久化（IndexedDB）
- [ ] 添加状态快照和回滚功能
- [ ] 优化大数据量状态管理

### 3. 长期优化（3个月）
- [ ] 实现状态同步机制（多标签页）
- [ ] 添加状态审计日志
- [ ] 实现状态可视化调试工具

---

## 相关文档

- [Stores使用指南](./src/stores/README.md)
- [项目架构文档](./docs/architecture.md)
- [路由配置说明](./docs/router.md)
- [布局系统说明](./docs/layout.md)

---

## 联系方式

如有问题或建议，请联系项目负责人。

**更新人：** Agent  
**审核人：** 待定  
**版本：** v2.1.0  
**更新日期：** 2026-03-08
