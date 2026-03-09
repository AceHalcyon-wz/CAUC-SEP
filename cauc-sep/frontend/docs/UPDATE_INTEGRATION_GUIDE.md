# 自动更新前端集成指南

## 概述

本文档说明如何在 CAUC-SEP 前端应用中集成自动更新功能。

## 文件结构

```
frontend/src/
├── api/
│   └── update.js              # 更新API接口封装
├── components/
│   └── UpdateNotification.vue # 更新通知组件
├── stores/
│   └── update.js              # 更新状态管理Store
├── components/__tests__/
│   └── UpdateNotification.test.js # 组件单元测试
└── examples/
    └── update-integration-example.js # 集成示例
```

## 快速开始

### 1. 在 App.vue 中添加更新通知组件

```vue
<template>
  <div id="app">
    <router-view />
    
    <!-- 添加更新通知组件 -->
    <UpdateNotification
      :auto-check="true"
      :check-interval="3600000"
      :background-download="true"
      channel="stable"
    />
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import UpdateNotification from '@/components/UpdateNotification.vue';
import { useUpdateStore } from '@/stores/update';

const updateStore = useUpdateStore();

onMounted(() => {
  updateStore.init();
});
</script>
```

### 2. 在 main.js 中初始化

```javascript
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

// 初始化更新系统
import { useUpdateStore } from '@/stores/update';
const updateStore = useUpdateStore();
updateStore.init();

app.mount('#app');
```

## 组件功能

### UpdateNotification 组件

**Props:**

- `autoCheck` (Boolean): 是否启用自动检查更新，默认 `true`
- `checkInterval` (Number): 自动检查间隔（毫秒），默认 `3600000`（1小时）
- `backgroundDownload` (Boolean): 是否启用后台下载，默认 `true`
- `channel` (String): 更新通道，可选 `stable`、`beta`、`dev`，默认 `stable`

**Events:**

- `update-available`: 发现新版本时触发
- `update-progress`: 下载进度更新时触发
- `update-complete`: 更新完成时触发
- `update-error`: 更新失败时触发
- `close`: 关闭通知时触发

**示例:**

```vue
<UpdateNotification
  :auto-check="true"
  :check-interval="3600000"
  :background-download="true"
  channel="stable"
  @update-available="handleUpdateAvailable"
  @update-complete="handleUpdateComplete"
/>
```

## Store 使用

### useUpdateStore

**State:**

- `currentVersion`: 当前版本信息
- `updateInfo`: 可用更新信息
- `status`: 更新状态
- `downloadProgress`: 下载进度
- `installProgress`: 安装进度
- `backups`: 备份列表
- `updateHistory`: 更新历史

**Getters:**

- `hasUpdate`: 是否有可用更新
- `isUpdating`: 是否正在更新
- `priorityText`: 更新优先级文本
- `updateTypeText`: 更新类型文本
- `canRollback`: 是否可回滚

**Actions:**

- `init()`: 初始化Store
- `checkUpdate()`: 检查更新
- `applyUpdate()`: 应用更新
- `createBackup(description)`: 创建备份
- `removeBackup(backupId)`: 删除备份
- `cleanupBackups(maxCount)`: 清理旧备份
- `setChannel(channel)`: 设置更新通道
- `setAutoCheckEnabled(enabled)`: 启用/禁用自动检查

**示例:**

```javascript
import { useUpdateStore } from '@/stores/update';

const updateStore = useUpdateStore();

// 检查更新
await updateStore.checkUpdate();

// 应用更新
if (updateStore.hasUpdate) {
  await updateStore.applyUpdate();
}

// 创建备份
await updateStore.createBackup('手动备份');

// 查看更新历史
console.log(updateStore.updateHistory);
```

## API 接口

### update.js

**可用方法:**

- `getCurrentVersion()`: 获取当前版本信息
- `checkForUpdate(params)`: 检查更新
- `getUpdateProgress()`: 获取更新进度
- `applyUpdate(params)`: 应用更新
- `uploadUpdatePackage(file, onProgress)`: 上传更新包
- `verifyUpdatePackage(packagePath, checksum)`: 验证更新包
- `performRollback(params)`: 执行回滚
- `getBackupList()`: 获取备份列表
- `createManualBackup(description)`: 创建手动备份
- `deleteBackup(backupId)`: 删除备份
- `getUpdateHistory()`: 获取更新历史
- `cleanupOldBackups(maxCount)`: 清理旧备份

**示例:**

```javascript
import {
  checkForUpdate,
  applyUpdate,
  getBackupList
} from '@/api/update';

// 检查更新
const result = await checkForUpdate({
  current_version: '0.3.0',
  current_build: 30000,
  channel: 'stable'
});

if (result.has_update) {
  console.log('发现新版本:', result.update_info.latest_version);
}

// 获取备份列表
const backups = await getBackupList();
console.log('备份列表:', backups.backups);
```

## 更新流程

### 1. 自动检查流程

```
应用启动
  ↓
初始化 UpdateStore
  ↓
启动定时检查（默认1小时）
  ↓
调用后端 API 检查更新
  ↓
发现更新 → 显示通知 → 后台下载
  ↓
下载完成 → 提示用户安装
  ↓
用户确认 → 应用更新 → 重启服务
```

### 2. 手动更新流程

```
用户点击"检查更新"
  ↓
调用 checkUpdate()
  ↓
显示更新信息
  ↓
用户点击"立即更新"
  ↓
调用 applyUpdate()
  ↓
显示安装进度
  ↓
更新完成 → 提示重启
```

## 更新状态说明

### UPDATE_STATUS 枚举

- `IDLE`: 空闲状态
- `CHECKING`: 正在检查更新
- `AVAILABLE`: 发现可用更新
- `DOWNLOADING`: 正在下载更新
- `VERIFYING`: 正在验证更新包
- `INSTALLING`: 正在安装更新
- `COMPLETED`: 更新完成
- `FAILED`: 更新失败
- `ROLLING_BACK`: 正在回滚

### UPDATE_PRIORITY 枚举

- `LOW`: 可选更新
- `MEDIUM`: 建议更新
- `HIGH`: 重要更新
- `CRITICAL`: 关键安全更新

## 测试

### 运行单元测试

```bash
# 运行所有测试
npm run test

# 运行更新组件测试
npm run test UpdateNotification.test.js

# 运行测试并生成覆盖率报告
npm run test:coverage
```

### 测试覆盖范围

- ✅ 基础渲染测试
- ✅ 更新检查测试
- ✅ UI交互测试
- ✅ 进度显示测试
- ✅ 状态管理测试
- ✅ 事件发射测试
- ✅ 定时器测试
- ✅ 边界情况测试

## 最佳实践

### 1. 更新检查时机

- 应用启动时检查一次
- 定时检查（建议1小时）
- 用户手动检查
- 从后台切换到前台时检查

### 2. 后台下载

- 启用后台下载，减少用户等待
- 下载完成后提示用户安装
- 显示下载进度和预估时间

### 3. 用户提示

- 关键更新：强制提示，阻止操作
- 重要更新：显著提示，建议立即更新
- 普通更新：温和提示，可稍后更新

### 4. 错误处理

- 网络错误：提示用户稍后重试
- 验证失败：提示用户重新下载
- 安装失败：自动回滚到上一版本

### 5. 备份管理

- 更新前自动创建备份
- 定期清理旧备份（保留最近5个）
- 支持手动创建和删除备份

## 配置选项

### 更新通道

- `stable`: 稳定版本（推荐生产环境）
- `beta`: 测试版本（用于测试新功能）
- `dev`: 开发版本（仅用于开发环境）

### 检查间隔

- 每小时检查：`3600000`（默认）
- 每天检查：`86400000`
- 每周检查：`604800000`

## 故障排查

### 问题：检查更新失败

**可能原因:**
- 网络连接问题
- 后端服务未启动
- API接口错误

**解决方案:**
1. 检查网络连接
2. 确认后端服务运行正常
3. 查看浏览器控制台错误信息

### 问题：下载速度慢

**可能原因:**
- 网络带宽限制
- 服务器性能问题

**解决方案:**
1. 使用后台下载模式
2. 优化网络环境
3. 联系管理员优化服务器

### 问题：安装失败

**可能原因:**
- 更新包损坏
- 权限不足
- 磁盘空间不足

**解决方案:**
1. 重新下载更新包
2. 检查应用权限
3. 清理磁盘空间
4. 使用备份回滚

## 相关文档

- [后端更新API文档](../../backend/api/update.py)
- [更新系统设计文档](../../docs/update-system-design.md)
- [用户操作手册](../../docs/user-manual.md)

## 更新日志

### v0.3.1 (2026-03-08)
- 📝 更新文档日期和版本信息
- 🔧 优化更新通知组件

### v0.3.0 (2026-03-07)

- ✨ 新增自动更新前端支持
- ✨ 实现更新通知组件
- ✨ 实现更新状态管理Store
- ✨ 实现后台下载功能
- ✨ 实现更新进度显示
- ✨ 实现备份管理功能
- ✨ 添加单元测试

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/update-enhancement`)
3. 提交更改 (`git commit -m 'Add update enhancement'`)
4. 推送到分支 (`git push origin feature/update-enhancement`)
5. 创建 Pull Request

## 许可证

Copyright © 2026 CAUC-SEP Team
