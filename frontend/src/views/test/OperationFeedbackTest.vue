<!--
  @file OperationFeedbackTest.vue
  @path src/views/test/
  @description 操作反馈系统测试页面，演示各种操作反馈功能
  @author Agent
  @date 2024-03-07
-->

<script setup>
/**
 * 操作反馈系统测试页面
 * 
 * 演示进度指示器、成功/失败提示、撤销功能等
 */

import { ref } from 'vue'
import { 
  useOperationFeedback, 
  createStepProgress, 
  delay 
} from '@/composables/useOperationFeedback'
import { OPERATION_TYPE, ERROR_TYPE } from '@/stores/operation'

// ==================== 组合式函数调用 ====================

const {
  execute,
  executeBatch,
  executeWithUndo,
  showSuccess,
  showError,
  showWarning,
  isOperating,
  progress,
  operationStore
} = useOperationFeedback()

// ==================== 响应式状态 ====================

const testResults = ref([])
const _undoCountdown = ref(0)

// ==================== 测试方法 ====================

/**
 * 测试1: 基本操作
 */
async function testBasicOperation() {
  const result = await execute({
    type: OPERATION_TYPE.DEVICE_CONNECT,
    title: '连接电机设备',
    steps: ['初始化连接', '验证设备', '加载配置'],
    action: async (updateProgress) => {
      updateProgress(0, 0, '正在初始化连接...')
      await delay(800)
      
      updateProgress(33, 1, '正在验证设备身份...')
      await delay(800)
      
      updateProgress(66, 2, '正在加载设备配置...')
      await delay(800)
      
      updateProgress(100, 2, '连接成功')
      
      return { deviceId: 'motor-001', status: 'connected' }
    }
  })
  
  testResults.value.unshift({
    name: '基本操作',
    success: result.success,
    time: new Date().toLocaleTimeString()
  })
}

/**
 * 测试2: 带撤销的操作
 */
async function testUndoableOperation() {
  const result = await executeWithUndo({
    title: '删除配置文件',
    action: async () => {
      await delay(500)
      return { deletedFile: 'config.json' }
    },
    undo: async (metadata) => {
      console.log('撤销删除:', metadata)
      await delay(500)
      showSuccess({
        title: '撤销成功',
        message: '文件已恢复'
      })
      return { restoredFile: 'config.json' }
    },
    undoWindow: 10000
  })
  
  testResults.value.unshift({
    name: '可撤销操作',
    success: result.success,
    time: new Date().toLocaleTimeString()
  })
}

/**
 * 测试3: 批量操作
 */
async function testBatchOperation() {
  const devices = [
    { id: 'motor-001', name: '电机1' },
    { id: 'motor-002', name: '电机2' },
    { id: 'motor-003', name: '电机3' },
    { id: 'motor-004', name: '电机4' },
    { id: 'motor-005', name: '电机5' }
  ]
  
  const result = await executeBatch({
    title: '批量连接设备',
    items: devices,
    processItem: async (device, index) => {
      await delay(600)
      // 模拟第三个设备失败
      if (index === 2) {
        throw new Error('连接超时')
      }
      return { connected: true, deviceId: device.id }
    },
    continueOnError: true
  })
  
  testResults.value.unshift({
    name: '批量操作',
    success: result.succeeded === result.total,
    details: `成功 ${result.succeeded}/${result.total}`,
    time: new Date().toLocaleTimeString()
  })
}

/**
 * 测试4: 错误处理
 */
async function testErrorHandling() {
  const result = await execute({
    title: '上传数据',
    steps: ['准备数据', '上传'],
    action: async (updateProgress) => {
      updateProgress(0, 0, '正在准备数据...')
      await delay(500)
      
      updateProgress(50, 1, '正在上传...')
      await delay(500)
      
      // 模拟网络错误
      const error = new Error('网络连接超时')
      error.code = 'NETWORK_ERROR'
      throw error
    }
  })
  
  testResults.value.unshift({
    name: '错误处理',
    success: false,
    details: result.error?.message,
    time: new Date().toLocaleTimeString()
  })
}

/**
 * 测试5: 手动通知
 */
function testManualNotifications() {
  // 成功通知
  showSuccess({
    title: '保存成功',
    message: '配置已保存到本地',
    duration: 3000
  })
  
  // 延迟显示错误
  setTimeout(() => {
    showError({
      title: '连接失败',
      error: {
        type: ERROR_TYPE.NETWORK,
        message: '无法连接到服务器，请检查网络设置'
      },
      retryable: true
    })
  }, 500)
  
  // 延迟显示警告
  setTimeout(() => {
    showWarning({
      title: '设备警告',
      message: '电机温度过高，请注意散热'
    })
  }, 1000)
  
  testResults.value.unshift({
    name: '手动通知',
    success: true,
    time: new Date().toLocaleTimeString()
  })
}

/**
 * 测试6: 长时间操作
 */
async function testLongOperation() {
  const result = await execute({
    title: '数据导出',
    steps: ['查询数据', '格式转换', '生成文件', '下载'],
    action: async (updateProgress) => {
      const nextStep = createStepProgress(4, updateProgress)
      
      nextStep('正在查询数据库...')
      await delay(1000)
      
      nextStep('正在转换数据格式...')
      await delay(1000)
      
      nextStep('正在生成Excel文件...')
      await delay(1000)
      
      nextStep('正在准备下载...')
      await delay(1000)
      
      return { fileUrl: '/downloads/data.xlsx', size: '2.5MB' }
    }
  })
  
  testResults.value.unshift({
    name: '长时间操作',
    success: result.success,
    time: new Date().toLocaleTimeString()
  })
}

/**
 * 测试7: 可取消操作
 */
async function testCancellableOperation() {
  const result = await execute({
    title: '长时间任务',
    steps: ['处理中'],
    cancellable: true,
    action: async (updateProgress) => {
      for (let i = 0; i <= 100; i += 5) {
        updateProgress(i, 0, `处理进度 ${i}%`)
        await delay(200)
      }
      return { completed: true }
    }
  })
  
  testResults.value.unshift({
    name: '可取消操作',
    success: result.success,
    details: result.success ? '完成' : '已取消',
    time: new Date().toLocaleTimeString()
  })
}

/**
 * 清空测试结果
 */
function clearResults() {
  testResults.value = []
}

/**
 * 清空所有通知
 */
function clearNotifications() {
  operationStore.clearAllNotifications()
}
</script>

<template>
  <div class="operation-feedback-test">
    <header class="test-header">
      <h1>操作反馈系统测试</h1>
      <p class="test-description">
        测试操作进度指示器、成功/失败提示、撤销功能等
      </p>
    </header>

    <section class="test-section">
      <h2>测试用例</h2>
      
      <div class="test-buttons">
        <button 
          class="test-btn"
          :disabled="isOperating"
          @click="testBasicOperation"
        >
          基本操作
        </button>
        
        <button 
          class="test-btn"
          :disabled="isOperating"
          @click="testUndoableOperation"
        >
          可撤销操作
        </button>
        
        <button 
          class="test-btn"
          :disabled="isOperating"
          @click="testBatchOperation"
        >
          批量操作
        </button>
        
        <button 
          class="test-btn test-btn--danger"
          :disabled="isOperating"
          @click="testErrorHandling"
        >
          错误处理
        </button>
        
        <button 
          class="test-btn"
          @click="testManualNotifications"
        >
          手动通知
        </button>
        
        <button 
          class="test-btn"
          :disabled="isOperating"
          @click="testLongOperation"
        >
          长时间操作
        </button>
        
        <button 
          class="test-btn"
          :disabled="isOperating"
          @click="testCancellableOperation"
        >
          可取消操作
        </button>
      </div>
    </section>

    <section class="test-section">
      <h2>当前状态</h2>
      
      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">操作状态:</span>
          <span
            class="status-value"
            :class="{ 'status-active': isOperating }"
          >
            {{ isOperating ? '执行中' : '空闲' }}
          </span>
        </div>
        
        <div class="status-item">
          <span class="status-label">当前进度:</span>
          <span class="status-value">{{ progress }}%</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">活跃操作:</span>
          <span class="status-value">{{ operationStore.activeOperations.length }}</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">可撤销操作:</span>
          <span class="status-value">{{ operationStore.undoableCount }}</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">未读成功通知:</span>
          <span class="status-value">{{ operationStore.unreadSuccessCount }}</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">未读错误通知:</span>
          <span class="status-value">{{ operationStore.unreadErrorCount }}</span>
        </div>
      </div>
    </section>

    <section class="test-section">
      <div class="section-header">
        <h2>测试结果</h2>
        <div class="section-actions">
          <button
            class="action-btn"
            @click="clearResults"
          >
            清空结果
          </button>
          <button
            class="action-btn"
            @click="clearNotifications"
          >
            清空通知
          </button>
        </div>
      </div>
      
      <div class="test-results">
        <div 
          v-for="(result, index) in testResults" 
          :key="index"
          class="result-item"
          :class="{ 'result-success': result.success, 'result-fail': !result.success }"
        >
          <span class="result-icon">{{ result.success ? '✓' : '✕' }}</span>
          <span class="result-name">{{ result.name }}</span>
          <span
            v-if="result.details"
            class="result-details"
          >{{ result.details }}</span>
          <span class="result-time">{{ result.time }}</span>
        </div>
        
        <div
          v-if="testResults.length === 0"
          class="empty-state"
        >
          暂无测试结果
        </div>
      </div>
    </section>

    <section class="test-section">
      <h2>使用说明</h2>
      
      <div class="usage-guide">
        <div class="guide-item">
          <h3>基本操作</h3>
          <p>执行一个简单的操作，显示进度条和步骤信息。</p>
        </div>
        
        <div class="guide-item">
          <h3>可撤销操作</h3>
          <p>执行一个可撤销的操作，操作完成后会显示撤销按钮，10秒内可撤销。</p>
        </div>
        
        <div class="guide-item">
          <h3>批量操作</h3>
          <p>批量处理多个项目，显示整体进度，支持出错时继续处理。</p>
        </div>
        
        <div class="guide-item">
          <h3>错误处理</h3>
          <p>模拟操作失败，显示错误提示，支持重试和查看详情。</p>
        </div>
        
        <div class="guide-item">
          <h3>手动通知</h3>
          <p>手动触发成功、错误、警告通知。</p>
        </div>
        
        <div class="guide-item">
          <h3>长时间操作</h3>
          <p>执行一个较长时间的操作，测试进度更新。</p>
        </div>
        
        <div class="guide-item">
          <h3>可取消操作</h3>
          <p>执行一个可取消的操作，点击进度条上的取消按钮可中断操作。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.operation-feedback-test {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-6);
}

.test-header {
  margin-bottom: var(--spacing-8);
}

.test-header h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-2);
}

.test-description {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.test-section {
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-6);
  margin-bottom: var(--spacing-6);
  box-shadow: var(--shadow-sm);
}

.test-section h2 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-4);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
}

.section-header h2 {
  margin-bottom: 0;
}

.section-actions {
  display: flex;
  gap: var(--spacing-2);
}

.test-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--spacing-3);
}

.test-btn {
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.test-btn:hover:not(:disabled) {
  background: var(--color-primary-600);
  transform: translateY(-1px);
}

.test-btn:disabled {
  background: var(--color-neutral-300);
  cursor: not-allowed;
}

.test-btn--danger {
  background: var(--color-error);
}

.test-btn--danger:hover:not(:disabled) {
  background: var(--color-error-dark);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--spacing-4);
}

.status-item {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.status-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.status-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.status-active {
  color: var(--color-primary-500);
}

.test-results {
  max-height: 300px;
  overflow-y: auto;
}

.result-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-2);
  background: var(--color-bg-secondary);
}

.result-success {
  border-left: 3px solid var(--color-success);
}

.result-fail {
  border-left: 3px solid var(--color-error);
}

.result-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
}

.result-success .result-icon {
  background: var(--color-success-light);
  color: var(--color-success);
}

.result-fail .result-icon {
  background: var(--color-error-light);
  color: var(--color-error);
}

.result-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.result-details {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.result-time {
  margin-left: auto;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-8);
  color: var(--color-text-tertiary);
}

.action-btn {
  padding: var(--spacing-2) var(--spacing-3);
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background: var(--color-interactive-hover);
  color: var(--color-text-primary);
}

.usage-guide {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: var(--spacing-4);
}

.guide-item {
  padding: var(--spacing-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.guide-item h3 {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-2);
}

.guide-item p {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

/* 响应式 */
@media (max-width: 768px) {
  .operation-feedback-test {
    padding: var(--spacing-4);
  }

  .test-buttons {
    grid-template-columns: 1fr;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }

  .usage-guide {
    grid-template-columns: 1fr;
  }
}
</style>
