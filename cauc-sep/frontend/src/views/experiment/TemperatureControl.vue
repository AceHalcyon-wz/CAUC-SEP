<template>
  <div class="temperature-control-page">
    <!-- 页面标题 - 状态指示器位于顶部 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon">
          <Thermometer />
        </el-icon>
        <div class="header-text">
          <h1 class="page-title">
            温度控制
          </h1>
          <p class="page-description">
            精密恒温控制与程序升温
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-tag
          type="success"
          effect="dark"
          size="large"
          class="status-indicator"
        >
          <el-icon><Thermometer /></el-icon>
          恒温控制
        </el-tag>
      </div>
    </div>

    <!-- 主内容区域 - 标签页布局 -->
    <div class="content-wrapper">
      <el-tabs
        v-model="activeTab"
        type="border-card"
        class="main-tabs"
      >
        <!-- 温度控制面板 -->
        <el-tab-pane
          label="温度控制"
          name="control"
        >
          <TemperatureControl class="main-card" />
        </el-tab-pane>

        <!-- 温度曲线监控 -->
        <el-tab-pane
          label="实时曲线"
          name="curve"
        >
          <TemperatureCurve class="main-card" />
        </el-tab-pane>

        <!-- 程序升温配置 -->
        <el-tab-pane
          label="程序升温"
          name="program"
        >
          <TemperatureProgram class="main-card" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
/**
 * @file TemperatureControl.vue
 * @path src/views/experiment/
 * @description 温度控制页面，提供目标温度设置、PID参数配置、程序控温和实时曲线监控功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref } from 'vue'
import TemperatureControl from '@/components/TemperatureControl.vue'
import TemperatureCurve from '@/components/TemperatureCurve.vue'
import TemperatureProgram from '@/components/TemperatureProgram.vue'

/** 当前激活的标签页 */
const activeTab = ref('control')
</script>

<style scoped lang="scss">
.temperature-control-page {
  max-width: 1600px;
  margin: 0 auto;
  padding: var(--spacing-6);
  min-height: 100%;
  background-color: var(--color-bg-secondary);
}

/* ==================== 页面头部 ==================== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-6);
  padding-bottom: var(--spacing-4);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border-bottom: 2px solid var(--color-border-primary);
  box-shadow: var(--shadow-sm);
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.header-icon {
  font-size: 32px;
  color: var(--color-success);
  padding: var(--spacing-3);
  background-color: var(--color-success-light);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.header-icon:hover {
  background-color: var(--color-success-lighter);
  transform: scale(1.05);
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: -0.02em;
}

.page-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

/* 状态指示器 */
.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-full);
  transition: var(--transition-all);
}

.status-indicator:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
}

/* ==================== 内容区域 ==================== */
.content-wrapper {
  width: 100%;
}

.main-tabs {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  border: none;
}

.main-tabs :deep(.el-tabs__header) {
  background: var(--color-surface-secondary);
  border-bottom: 2px solid var(--color-border-primary);
}

.main-tabs :deep(.el-tabs__item) {
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-base);
  padding: 0 var(--spacing-6);
  height: 48px;
  line-height: 48px;
  color: var(--color-text-secondary);
  transition: var(--transition-all);
}

.main-tabs :deep(.el-tabs__item:hover) {
  color: var(--color-primary-500);
  background-color: var(--color-bg-tertiary);
}

.main-tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary-500);
  font-weight: var(--font-weight-semibold);
  background: var(--color-surface-primary);
  border-bottom: 2px solid var(--color-primary-500);
}

.main-tabs :deep(.el-tabs__content) {
  padding: 0;
}

.main-card {
  border-radius: 0;
  box-shadow: none;
  border: none;
  background: var(--color-surface-primary);
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1024px) {
  .temperature-control-page {
    padding: var(--spacing-4);
  }

  .page-header {
    flex-direction: column;
    gap: var(--spacing-3);
    padding: var(--spacing-5);
  }

  .header-right {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 768px) {
  .temperature-control-page {
    padding: var(--spacing-3);
  }

  .page-header {
    padding: var(--spacing-4);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .main-tabs :deep(.el-tabs__item) {
    padding: 0 var(--spacing-4);
    font-size: var(--font-size-sm);
  }
  
  .status-indicator {
    padding: var(--spacing-1) var(--spacing-3);
    font-size: var(--font-size-xs);
  }
}
</style>
