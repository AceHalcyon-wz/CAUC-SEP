<template>
  <div class="settings-audit-page">
    <!-- 页面头部 -->
    <el-row class="page-header">
      <el-col :span="24">
        <div class="header-content">
          <div class="header-left">
            <el-icon class="header-icon">
              <Document />
            </el-icon>
            <div class="header-text">
              <h1 class="page-title">
                审计日志
              </h1>
              <p class="page-subtitle">
                系统操作记录与审计追踪
              </p>
            </div>
          </div>
          <div class="header-right">
            <el-button
              class="action-btn"
              @click="handleRefresh"
            >
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button
              class="action-btn"
              @click="handleExport"
            >
              <el-icon><Download /></el-icon>
              导出
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 审计日志组件 -->
    <div class="audit-content">
      <AuditLog ref="auditLogRef" />
    </div>
  </div>
</template>

<script setup>
/**
 * @file Audit.vue
 * @path src/views/settings/
 * @description 审计日志页面，集成AuditLog组件进行日志查看与管理
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies element-plus, @/components/AuditLog
 */

import { ref } from 'vue'
import { Document, Refresh, Download } from '@element-plus/icons-vue'
import AuditLog from '@/components/AuditLog.vue'

// ==================== 组件引用 ====================

/** AuditLog组件引用 */
const auditLogRef = ref(null)

// ==================== 事件处理方法 ====================

/**
 * 刷新日志列表
 */
function handleRefresh() {
  // AuditLog组件内部已实现刷新逻辑
  if (auditLogRef.value) {
    // 可以通过ref调用组件方法
  }
}

/**
 * 导出日志
 */
function handleExport() {
  // AuditLog组件内部已实现导出逻辑
  if (auditLogRef.value) {
    // 可以通过ref调用组件方法
  }
}
</script>

<style scoped>
.settings-audit-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-secondary);
}

/* 页面头部 */
.page-header {
  background-color: var(--color-surface-primary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-6);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.header-icon {
  font-size: 32px;
  color: var(--color-primary-500);
  padding: var(--spacing-3);
  background-color: var(--color-primary-50);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.header-icon:hover {
  background-color: var(--color-primary-100);
  transform: scale(1.05);
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.page-title {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: var(--line-height-tight);
}

.page-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.header-right {
  display: flex;
  gap: var(--spacing-3);
}

.action-btn {
  transition: var(--transition-all);
  border: 1px solid var(--color-border-primary);
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-300);
}

.action-btn:active {
  transform: translateY(0);
}

/* 内容区域 */
.audit-content {
  flex: 1;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  padding: var(--spacing-6);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  margin-top: var(--spacing-4);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-primary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-4);
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .header-right {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .audit-content {
    padding: var(--spacing-4);
    margin-top: var(--spacing-3);
    border-radius: var(--radius-md);
  }

  .action-btn {
    flex: 1;
    min-width: 100px;
  }
}
</style>
