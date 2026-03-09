<template>
  <div class="test-page">
    <el-card class="test-card">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Setting /></el-icon>
          <span>布局系统测试页面</span>
        </div>
      </template>
      
      <div class="test-content">
        <el-alert
          title="布局系统已成功加载"
          type="success"
          :closable="false"
          show-icon
          class="test-alert"
        />
        
        <div class="test-info">
          <h3>当前布局信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="当前模块">
              {{ layoutStore.activeModule?.name }}
            </el-descriptions-item>
            <el-descriptions-item label="当前子功能">
              {{ layoutStore.activeChild?.name }}
            </el-descriptions-item>
            <el-descriptions-item label="侧边栏状态">
              {{ layoutStore.isSidebarCollapsed ? '已折叠' : '已展开' }}
            </el-descriptions-item>
            <el-descriptions-item label="侧边栏宽度">
              {{ layoutStore.currentSidebarWidth }}px
            </el-descriptions-item>
            <el-descriptions-item label="连接状态">
              {{ layoutStore.connectionStatusText[layoutStore.connectionStatus] }}
            </el-descriptions-item>
            <el-descriptions-item label="操作提示">
              {{ layoutStore.operationTip }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
        
        <div class="test-actions">
          <h3>测试操作</h3>
          <el-space wrap>
            <el-button @click="handleToggleSidebar">
              切换侧边栏
            </el-button>
            <el-button @click="handleAddWarning">
              添加警告
            </el-button>
            <el-button type="danger" @click="handleAddError">
              添加错误
            </el-button>
            <el-button @click="handleClearWarnings">
              清空警告
            </el-button>
            <el-button @click="handleChangeConnection">
              切换连接状态
            </el-button>
          </el-space>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
/**
 * @file TestLayout.vue
 * @path src/views/
 * @description 布局系统测试页面
 * @author Agent
 * @date 2024-03-07
 */

import { useLayoutStore } from '@/stores/layout'
import { Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const layoutStore = useLayoutStore()

/**
 * 切换侧边栏
 */
function handleToggleSidebar() {
  layoutStore.toggleSidebar()
  ElMessage.success('侧边栏已切换')
}

/**
 * 添加警告
 */
function handleAddWarning() {
  layoutStore.addWarning('这是一个测试警告信息', 'warning')
  ElMessage.warning('已添加警告')
}

/**
 * 添加错误
 */
function handleAddError() {
  layoutStore.addWarning('这是一个测试错误信息', 'error')
  ElMessage.error('已添加错误')
}

/**
 * 清空警告
 */
function handleClearWarnings() {
  layoutStore.clearWarnings()
  ElMessage.success('已清空所有警告')
}

/**
 * 切换连接状态
 */
function handleChangeConnection() {
  const status = layoutStore.connectionStatus
  const statusMap = {
    disconnected: 'connecting',
    connecting: 'connected',
    connected: 'disconnected'
  }
  layoutStore.setConnectionStatus(statusMap[status])
  ElMessage.info(`连接状态已切换为: ${layoutStore.connectionStatusText[layoutStore.connectionStatus]}`)
}
</script>

<style scoped lang="scss">
.test-page {
  .test-card {
    margin-bottom: var(--spacing-6);
  }
  
  .card-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
  }
  
  .header-icon {
    font-size: var(--font-size-xl);
    color: var(--color-primary-500);
  }
  
  .test-content {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-6);
  }
  
  .test-alert {
    margin-bottom: var(--spacing-4);
  }
  
  .test-info,
  .test-actions {
    h3 {
      margin-bottom: var(--spacing-4);
      font-size: var(--font-size-base);
      font-weight: var(--font-weight-semibold);
      color: var(--color-text-primary);
    }
  }
}
</style>
