# Pinia Stores 使用指南

## 概述

本项目使用 Pinia 进行状态管理，所有 Stores 已更新以支持新的架构和布局系统。

## Stores 结构

```
src/stores/
├── index.js              # 统一导出文件
├── motor.js              # 电机控制状态
├── devices.js            # 统一设备状态
├── electromagnet.js      # 电磁铁控制状态
├── piezo.js              # 压电陶瓷控制状态
├── temperature.js        # 温度控制状态
├── ammeter.js            # 微电流采集状态
├── experiment.js         # 实验管理状态
├── audit.js              # 审计日志状态
└── layout.js             # 布局状态
```

## 快速开始

### 1. 导入 Stores

```javascript
// 方式一：从统一导出文件导入（推荐）
import { 
  useMotorStore, 
  useDevicesStore,
  useLayoutStore 
} from '@/stores'

// 方式二：从单个文件导入
import { useMotorStore } from '@/stores/motor'
```

### 2. 在组件中使用

```vue
<script setup>
import { useMotorStore } from '@/stores'

const motorStore = useMotorStore()

// 访问状态
console.log(motorStore.isConnected)
console.log(motorStore.positionMm)

// 调用方法
motorStore.connectMotor()
motorStore.moveAbsolute(10, 5)
</script>
```

## Store 详细说明

### 1. 设备控制 Stores

#### useMotorStore - 电机控制

**状态：**
- `isConnected` - 连接状态
- `positionMm` - 当前位置（毫米）
- `positionSteps` - 当前位置（步数）
- `velocity` - 速度
- `limits` - 限位配置
- `status` - 设备状态

**主要方法：**
- `connectMotor()` - 连接电机
- `disconnectMotor()` - 断开电机
- `moveAbsolute(position, velocity)` - 绝对定位
- `jog(direction, velocity)` - JOG运动
- `emergencyStop()` - 急停
- `home()` - 回零

#### useElectromagnetStore - 电磁铁控制

**状态：**
- `currentCurrent` - 当前电流（A）
- `currentField` - 当前磁场强度（mT）
- `scanConfig` - 扫描配置
- `calibrationCurve` - 校准曲线

**主要方法：**
- `setCurrent(current)` - 设置电流
- `setField(field)` - 设置磁场强度
- `startScan()` - 开始扫描
- `uploadCalibration(points)` - 上传校准数据

#### usePiezoStore - 压电陶瓷控制

**状态：**
- `currentVoltage` - 当前电压（V）
- `currentDisplacement` - 当前位移（nm）
- `controlMode` - 控制模式
- `calibrationData` - 校准数据

**主要方法：**
- `setVoltage(voltage)` - 设置电压
- `setDisplacement(displacement)` - 设置位移
- `addCalibrationPoint(point)` - 添加校准点
- `performCalibration()` - 执行校准

#### useTemperatureStore - 温度控制

**状态：**
- `currentTemp` - 当前温度（K）
- `targetTemp` - 目标温度（K）
- `pidParams` - PID参数
- `programCurves` - 程序控温曲线

**主要方法：**
- `setTargetTemp(temperature)` - 设置目标温度
- `configurePID(params)` - 配置PID参数
- `startProgram(programId)` - 启动程序控温

#### useAmmeterStore - 微电流采集

**状态：**
- `isCollecting` - 是否正在采集
- `channelData` - 通道数据
- `bufferStatus` - 缓冲区状态

**主要方法：**
- `startCollection()` - 开始采集
- `stopCollection()` - 停止采集
- `configureChannel(channel, config)` - 配置通道

### 2. 系统管理 Stores

#### useDevicesStore - 统一设备状态

**状态：**
- `devices` - 所有设备状态映射
- `systemStatus` - 系统整体状态
- `connectedDevices` - 已连接设备列表

**主要方法：**
- `fetchAllDeviceStatus()` - 获取所有设备状态
- `refreshAll()` - 刷新所有设备状态

#### useExperimentStore - 实验管理

**状态：**
- `currentExperiment` - 当前实验信息
- `experimentStatus` - 实验状态
- `experimentProgress` - 实验进度

**主要方法：**
- `startExperiment(name, description)` - 开始实验
- `stopExperiment()` - 停止实验
- `exportExperiment(expId, format)` - 导出实验数据

#### useAuditStore - 审计日志

**状态：**
- `logList` - 日志列表
- `statistics` - 统计信息
- `filters` - 筛选条件

**主要方法：**
- `fetchLogs(params)` - 查询日志
- `fetchStatistics()` - 获取统计信息
- `exportLogs(params)` - 导出日志

#### useLayoutStore - 布局状态

**状态：**
- `isSidebarCollapsed` - 侧边栏折叠状态
- `activeModule` - 当前激活模块
- `connectionStatus` - 连接状态
- `warnings` - 警告信息列表

**主要方法：**
- `toggleSidebar()` - 切换侧边栏
- `setActiveModule(moduleId)` - 设置激活模块
- `setActiveByPath(path)` - 根据路径设置激活状态
- `addWarning(message, type)` - 添加警告

## 初始化和清理

### 应用启动时初始化

```javascript
// main.js
import { initializeDeviceStores, initializeSystemStores } from '@/stores'

// 初始化设备Stores
initializeDeviceStores({ autoConnect: false })

// 初始化系统Stores
initializeSystemStores()
```

### 应用卸载时清理

```javascript
import { cleanupAllStores } from '@/stores'

// 清理所有Stores
cleanupAllStores()
```

## 与路由系统的协调

Layout Store 会自动与路由系统同步：

```javascript
// router/index.js
router.beforeEach((to, from, next) => {
  // 自动同步激活状态
  const layoutStore = useLayoutStore()
  layoutStore.setActiveByPath(to.path)
  next()
})
```

## 本地存储

Layout Store 支持自动保存和恢复布局偏好：

- 侧边栏折叠状态
- 当前激活模块
- 当前激活子功能

```javascript
// 手动保存
layoutStore.saveLayoutPreference()

// 手动加载
layoutStore.loadLayoutPreference()
```

## WebSocket 连接管理

所有设备 Stores 都集成了 WebSocket 连接：

```javascript
// 自动连接（在设备连接成功后）
motorStore.connectMotor() // 会自动建立WebSocket连接

// 手动控制WebSocket
motorStore.connectWebSocket()
motorStore.disconnectWebSocket()
```

## 最佳实践

### 1. 使用统一导出

```javascript
// ✅ 推荐
import { useMotorStore, useDevicesStore } from '@/stores'

// ❌ 不推荐
import { useMotorStore } from '@/stores/motor'
import { useDevicesStore } from '@/stores/devices'
```

### 2. 在 setup 中使用

```vue
<script setup>
import { useMotorStore } from '@/stores'

const motorStore = useMotorStore()
</script>
```

### 3. 响应式状态访问

```vue
<template>
  <div>
    <p>位置: {{ motorStore.positionMm }} mm</p>
    <p>状态: {{ motorStore.status }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useMotorStore } from '@/stores'

const motorStore = useMotorStore()

// 使用计算属性
const formattedPosition = computed(() => {
  return `${motorStore.positionMm.toFixed(2)} mm`
})
</script>
```

### 4. 错误处理

```javascript
// Stores 内置了错误处理
const motorStore = useMotorStore()

// 错误会通过 showError 方法显示
const success = await motorStore.moveAbsolute(10, 5)
if (!success) {
  // 错误已经通过 alarmMessage 显示
  console.log(motorStore.alarmMessage)
}
```

## 更新内容

### v2.1 更新（2026-03-08）

1. **文档更新**
   - 更新所有文档日期
   - 优化文档结构
   - 补充使用示例

### v2.0 更新（2024-03-07）

1. **新增统一导出文件**
   - 创建 `stores/index.js`
   - 提供统一的 Store 导出入口
   - 添加初始化和清理辅助函数

2. **Layout Store 增强**
   - 添加本地存储支持
   - 与路由系统自动同步
   - 优化模块导航管理

3. **路由集成**
   - 路由守卫自动同步 Layout Store
   - 支持页面标题和面包屑

4. **代码规范**
   - 所有 Stores 遵循 Composition API 风格
   - 完整的 JSDoc 注释
   - 统一的错误处理机制

## 故障排查

### Store 未初始化

**问题：** 访问 Store 时提示未定义

**解决：** 确保在 `main.js` 中正确安装 Pinia

```javascript
import { createPinia } from 'pinia'

const app = createApp(App)
app.use(createPinia())
```

### WebSocket 连接失败

**问题：** WebSocket 连接失败或断开

**解决：**
1. 检查 WebSocket URL 配置
2. 确认后端服务正常运行
3. 查看浏览器控制台错误信息

### 状态不同步

**问题：** Layout Store 与路由不同步

**解决：** 确保路由守卫正确配置

```javascript
// router/index.js
router.beforeEach((to, from, next) => {
  const layoutStore = useLayoutStore()
  layoutStore.setActiveByPath(to.path)
  next()
})
```

## 相关文档

- [Pinia 官方文档](https://pinia.vuejs.org/)
- [Vue Router 官方文档](https://router.vuejs.org/)
- [项目架构文档](../docs/architecture.md)

---

**更新日期**: 2026-03-08  
**维护者**: Agent
