<template>
  <el-card class="experiment-panel">
    <template #header>
      <div class="card-header">
        <el-icon class="header-icon">
          <Document />
        </el-icon>
        <span class="header-title">实验记录</span>
      </div>
    </template>

    <div class="experiment-content">
      <!-- 当前实验控制 -->
      <div class="current-experiment">
        <el-form
          :model="experimentForm"
          label-width="80px"
        >
          <el-form-item label="实验名称">
            <el-input
              v-model="experimentForm.name"
              placeholder="输入实验名称"
              :disabled="isRecording"
            />
          </el-form-item>

          <el-form-item label="实验描述">
            <el-input
              v-model="experimentForm.description"
              type="textarea"
              :rows="2"
              placeholder="输入实验描述（可选）"
              :disabled="isRecording"
            />
          </el-form-item>
        </el-form>

        <div class="control-buttons">
          <el-button
            type="primary"
            size="large"
            class="control-btn control-btn--start"
            :disabled="!motorStore.isConnected || isRecording"
            :loading="isStarting"
            @click="startExperiment"
          >
            <el-icon><VideoPlay /></el-icon>
            <span>开始实验</span>
          </el-button>

          <el-button
            type="danger"
            size="large"
            class="control-btn control-btn--stop"
            :disabled="!isRecording"
            :loading="isStopping"
            @click="stopExperiment"
          >
            <el-icon><VideoPause /></el-icon>
            <span>停止实验</span>
          </el-button>
        </div>

        <!-- 实验状态 -->
        <transition name="recording-fade">
          <div
            v-if="isRecording"
            class="recording-status"
          >
            <div class="recording-indicator">
              <el-tag
                type="danger"
                effect="dark"
                size="large"
                class="recording-tag"
              >
                <el-icon class="recording-icon">
                  <VideoCamera />
                </el-icon>
                <span>正在记录实验 #{{ currentExperimentId }}</span>
              </el-tag>
            </div>
            <div class="record-time-display">
              <span class="time-label">记录时长</span>
              <span class="time-value">{{ recordTime }}</span>
            </div>
          </div>
        </transition>
      </div>

      <el-divider class="section-divider">
        <span class="divider-text">历史实验</span>
      </el-divider>

      <!-- 实验列表 -->
      <div class="experiment-list">
        <transition-group
          name="list-fade"
          tag="div"
          class="list-container"
        >
          <div
            v-for="(item, index) in experiments"
            :key="item.id"
            class="experiment-item"
            :style="{ animationDelay: `${index * 50}ms` }"
          >
            <div class="item-main">
              <div class="item-header">
                <span class="item-id">#{{ item.id }}</span>
                <el-tag
                  :type="getStatusType(item.status)"
                  size="small"
                  class="status-tag"
                >
                  {{ getStatusText(item.status) }}
                </el-tag>
              </div>
              <div class="item-name">
                {{ item.name }}
              </div>
              <div class="item-time">
                {{ formatDate(item.created_at) }}
              </div>
            </div>
            <div class="item-actions">
              <el-button
                type="primary"
                size="small"
                class="action-btn"
                @click="exportExperiment(item.id)"
              >
                <el-icon><Download /></el-icon>
                <span>导出</span>
              </el-button>
            </div>
          </div>
        </transition-group>

        <el-empty
          v-if="experiments.length === 0"
          description="暂无实验记录"
          class="empty-state"
        />
      </div>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file ExperimentPanel.vue
 * @path src/components/
 * @description 实验记录管理组件，提供实验创建、停止和历史记录查看功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, element-plus, axios
 */

import { ref, reactive, onMounted } from 'vue'
import { useMotorStore } from '@/stores/motor'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { API_BASE } from '@/config/api'

const motorStore = useMotorStore()

// 实验表单
const experimentForm = reactive({
  name: '',
  description: ''
})

// 状态
const isRecording = ref(false)
const isStarting = ref(false)
const isStopping = ref(false)
const currentExperimentId = ref(null)
const recordStartTime = ref(null)
const recordTime = ref('00:00:00')
const experiments = ref([])

let recordTimer = null

/**
 * 格式化日期显示
 * @param {string} isoString - ISO格式时间字符串
 * @returns {string} 格式化后的时间
 */
function formatDate(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * 获取状态标签类型
 * @param {string} status - 实验状态
 * @returns {string} Element Plus Tag 类型
 */
function getStatusType(status) {
  const typeMap = {
    'running': 'primary',
    'completed': 'success',
    'aborted': 'danger'
  }
  return typeMap[status] || 'info'
}

/**
 * 获取状态文本
 * @param {string} status - 实验状态
 * @returns {string} 中文状态文本
 */
function getStatusText(status) {
  const textMap = {
    'running': '进行中',
    'completed': '已完成',
    'aborted': '已中止'
  }
  return textMap[status] || status
}

/**
 * 更新记录时间显示
 */
function updateRecordTime() {
  if (!recordStartTime.value) return
  
  const elapsed = Math.floor((Date.now() - recordStartTime.value) / 1000)
  const hours = Math.floor(elapsed / 3600).toString().padStart(2, '0')
  const minutes = Math.floor((elapsed % 3600) / 60).toString().padStart(2, '0')
  const seconds = (elapsed % 60).toString().padStart(2, '0')
  recordTime.value = `${hours}:${minutes}:${seconds}`
}

/**
 * 开始实验
 */
async function startExperiment() {
  if (!experimentForm.name.trim()) {
    ElMessage.warning('请输入实验名称')
    return
  }

  isStarting.value = true
  try {
    const response = await axios.post(`${API_BASE}/api/experiments/start`, {
      name: experimentForm.name,
      description: experimentForm.description
    })

    if (response.data.success) {
      currentExperimentId.value = response.data.experiment_id
      isRecording.value = true
      recordStartTime.value = Date.now()
      recordTimer = setInterval(updateRecordTime, 1000)
      ElMessage.success('实验已开始')
      await loadExperiments()
    }
  } catch (error) {
    ElMessage.error('开始实验失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isStarting.value = false
  }
}

/**
 * 停止实验
 */
async function stopExperiment() {
  if (!currentExperimentId.value) return

  isStopping.value = true
  try {
    const response = await axios.post(`${API_BASE}/api/experiments/${currentExperimentId.value}/stop`)

    if (response.data.success) {
      isRecording.value = false
      clearInterval(recordTimer)
      recordTime.value = '00:00:00'
      currentExperimentId.value = null
      ElMessage.success('实验已停止')
      await loadExperiments()
    }
  } catch (error) {
    ElMessage.error('停止实验失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isStopping.value = false
  }
}

/**
 * 导出实验数据
 * @param {number} id - 实验ID
 */
async function exportExperiment(id) {
  try {
    const response = await axios.get(`${API_BASE}/api/experiments/${id}/export`)
    
    if (response.data.success) {
      ElMessage.success(`实验数据已导出到: ${response.data.filepath}`)
    }
  } catch (error) {
    ElMessage.error('导出失败: ' + (error.response?.data?.detail || error.message))
  }
}

/**
 * 加载实验列表
 */
async function loadExperiments() {
  try {
    const response = await axios.get(`${API_BASE}/api/experiments?limit=20`)
    experiments.value = response.data.experiments || []
  } catch (error) {
    console.error('加载实验列表失败:', error)
  }
}

onMounted(() => {
  loadExperiments()
})
</script>

<style scoped>
.experiment-panel {
  margin-bottom: var(--spacing-5);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
}

.experiment-panel:hover {
  box-shadow: var(--shadow-lg);
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
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.experiment-content {
  padding: var(--spacing-2) 0;
}

.current-experiment {
  margin-bottom: var(--spacing-5);
}

/* 控制按钮样式 */
.control-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-4);
  margin-top: var(--spacing-5);
}

.control-btn {
  height: 48px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
}

.control-btn--start {
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-primary-600));
  border: none;
  box-shadow: var(--shadow-sm);
}

.control-btn--start:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-500));
  box-shadow: var(--shadow-glow-primary);
  transform: translateY(-2px);
}

.control-btn--stop {
  background: linear-gradient(135deg, var(--color-error), var(--color-error-dark));
  border: none;
  box-shadow: var(--shadow-sm);
}

.control-btn--stop:hover:not(:disabled) {
  background: linear-gradient(135deg, #f56565, var(--color-error));
  box-shadow: var(--shadow-glow-error);
  transform: translateY(-2px);
}

.control-btn:disabled {
  opacity: 0.5;
  transform: none;
  box-shadow: none;
}

/* 录制状态样式 */
.recording-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--spacing-5);
  padding: var(--spacing-4);
  background: linear-gradient(135deg, var(--color-error-light), rgba(254, 215, 215, 0.5));
  border-radius: var(--radius-md);
  border: 1px solid rgba(229, 62, 62, 0.2);
}

.recording-indicator {
  display: flex;
  align-items: center;
}

.recording-tag {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  font-weight: var(--font-weight-medium);
}

.recording-icon {
  animation: pulse-recording 1.5s ease-in-out infinite;
  font-size: var(--font-size-lg);
}

@keyframes pulse-recording {
  0%, 100% { 
    opacity: 1;
    transform: scale(1);
  }
  50% { 
    opacity: 0.5;
    transform: scale(0.95);
  }
}

.record-time-display {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--spacing-1);
}

.time-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.time-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-error);
  font-family: var(--font-family-mono);
  letter-spacing: 2px;
}

/* 分隔线样式 */
.section-divider {
  margin: var(--spacing-6) 0;
}

.divider-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

/* 实验列表样式 */
.experiment-list {
  margin-top: var(--spacing-4);
}

.list-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
  max-height: 400px;
  overflow-y: auto;
  padding-right: var(--spacing-2);
}

/* 自定义滚动条 */
.list-container::-webkit-scrollbar {
  width: 6px;
}

.list-container::-webkit-scrollbar-track {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
}

.list-container::-webkit-scrollbar-thumb {
  background: var(--color-neutral-300);
  border-radius: var(--radius-full);
}

.list-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-neutral-400);
}

/* 列表项样式 */
.experiment-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-4);
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
  animation: slide-in-up 0.3s ease-out forwards;
  opacity: 0;
}

@keyframes slide-in-up {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.experiment-item:hover {
  background: var(--color-interactive-hover);
  border-color: var(--color-primary-300);
  box-shadow: var(--shadow-sm);
  transform: translateX(4px);
}

.item-main {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-1);
}

.item-id {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary-500);
  font-family: var(--font-family-mono);
}

.status-tag {
  font-size: var(--font-size-xs);
}

.item-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: var(--spacing-1);
}

.item-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

.item-actions {
  display: flex;
  gap: var(--spacing-2);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  border-radius: var(--radius-sm);
  transition: var(--transition-all);
}

.action-btn:hover {
  transform: scale(1.05);
}

/* 空状态 */
.empty-state {
  padding: var(--spacing-8) 0;
}

/* 过渡动画 */
.recording-fade-enter-active,
.recording-fade-leave-active {
  transition: all 0.3s ease;
}

.recording-fade-enter-from,
.recording-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.list-fade-enter-active,
.list-fade-leave-active {
  transition: all 0.3s ease;
}

.list-fade-enter-from,
.list-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.list-fade-move {
  transition: transform 0.3s ease;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .control-buttons {
    grid-template-columns: 1fr;
  }
  
  .recording-status {
    flex-direction: column;
    gap: var(--spacing-3);
    text-align: center;
  }
  
  .record-time-display {
    align-items: center;
  }
  
  .experiment-item {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-3);
  }
  
  .item-actions {
    justify-content: flex-end;
  }
}
</style>
