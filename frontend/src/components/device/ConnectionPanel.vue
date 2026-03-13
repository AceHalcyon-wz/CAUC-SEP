<template>
  <el-card class="connection-panel">
    <template #header>
      <div class="card-header">
        <el-icon class="header-icon">
          <Link />
        </el-icon>
        <span class="header-title">连接控制</span>
      </div>
    </template>

    <div class="connection-content">
      <!-- 连接状态 -->
      <div class="status-row">
        <span class="label">连接状态</span>
        <div class="status-indicator-wrapper">
          <span 
            class="status-dot"
            :class="{
              'status-dot--connected': motorStore.isConnected,
              'status-dot--connecting': motorStore.isConnecting,
              'status-dot--disconnected': !motorStore.isConnected && !motorStore.isConnecting
            }"
          />
          <el-tag 
            :type="statusType" 
            effect="dark" 
            size="large"
            class="status-tag"
          >
            {{ statusText }}
          </el-tag>
        </div>
      </div>

      <!-- WebSocket状态 -->
      <div class="status-row">
        <span class="label">实时数据</span>
        <div class="status-indicator-wrapper">
          <span 
            class="status-dot"
            :class="{
              'status-dot--connected': motorStore.wsConnected,
              'status-dot--disconnected': !motorStore.wsConnected
            }"
          />
          <el-tag 
            :type="motorStore.wsConnected ? 'success' : 'info'" 
            size="small"
          >
            {{ motorStore.wsConnected ? '已连接' : '未连接' }}
          </el-tag>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="button-row">
        <el-button
          type="primary"
          size="large"
          :loading="motorStore.isConnecting"
          :disabled="motorStore.isConnected"
          class="connect-btn"
          @click="handleConnect"
        >
          <el-icon><Link /></el-icon>
          <span>连接设备</span>
        </el-button>

        <el-button
          type="danger"
          size="large"
          :disabled="!motorStore.isConnected"
          class="disconnect-btn"
          @click="handleDisconnect"
        >
          <el-icon><CircleClose /></el-icon>
          <span>断开连接</span>
        </el-button>
      </div>

      <!-- 串口配置 -->
      <el-divider class="config-divider">
        <el-icon><Setting /></el-icon>
        <span>串口配置</span>
      </el-divider>
      
      <el-form
        :model="config"
        label-width="80px"
        size="small"
        class="config-form"
      >
        <el-form-item label="串口号">
          <el-select
            v-model="config.port"
            class="form-select"
          >
            <el-option
              label="COM1"
              value="COM1"
            />
            <el-option
              label="COM2"
              value="COM2"
            />
            <el-option
              label="COM3"
              value="COM3"
            />
            <el-option
              label="COM4"
              value="COM4"
            />
            <el-option
              label="COM5"
              value="COM5"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="波特率">
          <el-select
            v-model="config.baudrate"
            class="form-select"
          >
            <el-option
              label="9600"
              :value="9600"
            />
            <el-option
              label="19200"
              :value="19200"
            />
            <el-option
              label="38400"
              :value="38400"
            />
            <el-option
              label="57600"
              :value="57600"
            />
            <el-option
              label="115200"
              :value="115200"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="从站地址">
          <el-input-number 
            v-model="config.slaveId" 
            :min="1" 
            :max="247" 
            class="form-input-number"
          />
        </el-form-item>
      </el-form>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file ConnectionPanel.vue
 * @path src/components/
 * @description 设备连接控制面板，管理串口连接和WebSocket实时数据连接
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed } from 'vue'
import { useMotorStore } from '@/stores/motor'

const motorStore = useMotorStore()

/** 串口配置参数 */
const config = ref({
  port: 'COM3',
  baudrate: 115200,
  slaveId: 1
})

/**
 * 连接状态文本
 */
const statusText = computed(() => {
  if (motorStore.isConnecting) return '连接中...'
  if (motorStore.isConnected) return '已连接'
  return '未连接'
})

/**
 * 状态标签类型
 */
const statusType = computed(() => {
  if (motorStore.isConnecting) return 'warning'
  if (motorStore.isConnected) return 'success'
  return 'danger'
})

/**
 * 连接设备
 */
async function handleConnect() {
  await motorStore.connectMotor({
    port: config.value.port,
    baudrate: config.value.baudrate,
    slave_id: config.value.slaveId
  })
}

/**
 * 断开连接
 */
async function handleDisconnect() {
  await motorStore.disconnectMotor()
}
</script>

<style scoped>
.connection-panel {
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.connection-panel:hover {
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.header-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.connection-content {
  padding: var(--spacing-2) 0;
}

/* 状态行样式 */
.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  margin-bottom: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.status-row:hover {
  background-color: var(--color-interactive-hover);
}

.label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.status-indicator-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

/* 状态指示器发光效果 */
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  transition: var(--transition-all);
}

.status-dot--connected {
  background-color: var(--color-status-online);
  box-shadow: 0 0 12px var(--color-status-online);
  animation: pulse-glow 2s ease-in-out infinite;
}

.status-dot--connecting {
  background-color: var(--color-status-warning);
  box-shadow: 0 0 12px var(--color-status-warning);
  animation: pulse-glow 1s ease-in-out infinite;
}

.status-dot--disconnected {
  background-color: var(--color-status-offline);
}

@keyframes pulse-glow {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.2);
  }
}

.status-tag {
  font-weight: var(--font-weight-medium);
}

/* 按钮行样式 */
.button-row {
  display: flex;
  gap: var(--spacing-3);
  margin-top: var(--spacing-4);
}

.connect-btn,
.disconnect-btn {
  flex: 1;
  height: 44px;
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
}

.connect-btn:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-primary);
}

.disconnect-btn:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-error);
}

.connect-btn:active,
.disconnect-btn:active {
  transform: translateY(0);
}

/* 分割线样式 */
.config-divider {
  margin: var(--spacing-6) 0;
}

.config-divider :deep(.el-divider__text) {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  background-color: var(--color-surface-primary);
}

/* 表单样式 */
.config-form {
  margin-top: var(--spacing-4);
}

.form-select,
.form-input-number {
  width: 100%;
}

:deep(.el-form-item__label) {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .button-row {
    flex-direction: column;
  }
  
  .connect-btn,
  .disconnect-btn {
    width: 100%;
  }
}
</style>
