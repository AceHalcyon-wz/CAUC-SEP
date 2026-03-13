<template>
  <div class="device-status-monitor">
    <el-card class="monitor-card">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="header-icon">
              <Monitor />
            </el-icon>
            <span>设备状态监控</span>
          </div>
          <el-button 
            type="primary" 
            :loading="refreshing" 
            size="small"
            class="refresh-btn"
            @click="refreshAll"
          >
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <!-- 报警提示 -->
      <Transition name="slide-fade">
        <div
          v-if="motorStore.alarmMessage"
          class="alarm-banner"
        >
          <div class="alarm-icon">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <div class="alarm-content">
            <div class="alarm-title">
              设备报警
            </div>
            <div class="alarm-message">
              {{ motorStore.alarmMessage }}
            </div>
          </div>
          <el-button 
            type="text" 
            class="alarm-close"
            @click="motorStore.clearAlarm()"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </Transition>

      <div class="status-grid">
        <!-- 基本状态卡片 -->
        <div class="status-card glass-card">
          <div class="card-header-inner">
            <span class="card-title">基本状态</span>
            <div
              class="status-badge"
              :class="connectionBadgeClass"
            >
              <span class="badge-dot" />
              {{ motorStore.isConnected ? '在线' : '离线' }}
            </div>
          </div>
          
          <div class="status-content">
            <div class="status-row">
              <span class="status-label">连接状态</span>
              <el-tag
                :type="motorStore.isConnected ? 'success' : 'danger'"
                size="small"
              >
                {{ motorStore.isConnected ? '已连接' : '未连接' }}
              </el-tag>
            </div>
            
            <div class="status-row">
              <span class="status-label">运行状态</span>
              <el-tag
                :type="statusType"
                size="small"
              >
                {{ statusText }}
              </el-tag>
            </div>
            
            <div class="status-row status-row--highlight">
              <span class="status-label">当前位置</span>
              <div class="position-display">
                <span class="position-value mono">{{ motorStore.positionMm.toFixed(3) }}</span>
                <span class="position-unit">mm</span>
                <span class="position-steps mono">({{ motorStore.positionSteps }} 步)</span>
              </div>
            </div>
            
            <div class="status-row">
              <span class="status-label">限位状态</span>
              <el-tag
                :type="motorStore.limitStatusType"
                size="small"
              >
                {{ motorStore.limitStatus }}
              </el-tag>
            </div>
            
            <div class="status-row">
              <span class="status-label">WebSocket</span>
              <div
                class="ws-status"
                :class="motorStore.wsConnected ? 'ws-status--connected' : 'ws-status--disconnected'"
              >
                <span class="ws-dot" />
                {{ motorStore.wsConnected ? '已连接' : '未连接' }}
              </div>
            </div>
          </div>
        </div>

        <!-- 状态字卡片 -->
        <div class="status-card glass-card">
          <div class="card-header-inner">
            <span class="card-title">状态字</span>
            <el-button 
              type="text" 
              :loading="motorStore.loading.statusWord" 
              class="refresh-icon-btn"
              @click="motorStore.readStatusWord"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
          
          <div
            v-if="motorStore.statusWord"
            class="status-word-content"
          >
            <div class="status-word-display">
              <span class="status-word-value mono">0x{{ formatStatusWord(motorStore.statusWord.raw) }}</span>
            </div>
            
            <div class="status-flags">
              <div
                class="flag-item"
                :class="{ 'flag-item--active': motorStore.statusWord.ready_to_switch_on }"
              >
                <span class="flag-dot" />
                <span class="flag-label">准备就绪</span>
                <span class="flag-value">{{ motorStore.statusWord.ready_to_switch_on ? '是' : '否' }}</span>
              </div>
              
              <div
                class="flag-item"
                :class="{ 'flag-item--active': motorStore.statusWord.switched_on }"
              >
                <span class="flag-dot" />
                <span class="flag-label">开关使能</span>
                <span class="flag-value">{{ motorStore.statusWord.switched_on ? '是' : '否' }}</span>
              </div>
              
              <div
                class="flag-item"
                :class="{ 'flag-item--active': motorStore.statusWord.operation_enabled }"
              >
                <span class="flag-dot" />
                <span class="flag-label">运行使能</span>
                <span class="flag-value">{{ motorStore.statusWord.operation_enabled ? '是' : '否' }}</span>
              </div>
              
              <div
                class="flag-item"
                :class="{ 'flag-item--error': motorStore.statusWord.fault }"
              >
                <span class="flag-dot" />
                <span class="flag-label">故障</span>
                <span class="flag-value">{{ motorStore.statusWord.fault ? '是' : '否' }}</span>
              </div>
              
              <div
                class="flag-item"
                :class="{ 'flag-item--warning': motorStore.statusWord.motion }"
              >
                <span class="flag-dot" />
                <span class="flag-label">运动中</span>
                <span class="flag-value">{{ motorStore.statusWord.motion ? '是' : '否' }}</span>
              </div>
              
              <div
                class="flag-item"
                :class="{ 'flag-item--active': motorStore.statusWord.target_reached }"
              >
                <span class="flag-dot" />
                <span class="flag-label">到达目标</span>
                <span class="flag-value">{{ motorStore.statusWord.target_reached ? '是' : '否' }}</span>
              </div>
            </div>
          </div>
          
          <div
            v-else
            class="empty-state"
          >
            <el-icon class="empty-icon">
              <Document />
            </el-icon>
            <span>点击刷新获取状态字</span>
          </div>
        </div>

        <!-- 报警信息卡片 -->
        <div
          class="status-card glass-card"
          :class="{ 'status-card--alarm': motorStore.alarmCode !== null && motorStore.alarmCode !== 0 }"
        >
          <div class="card-header-inner">
            <span class="card-title">报警信息</span>
            <el-button 
              type="text" 
              :loading="motorStore.loading.alarmCode" 
              class="refresh-icon-btn"
              @click="motorStore.readAlarmCode"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
          
          <div
            v-if="motorStore.alarmCode !== null"
            class="alarm-content-inner"
          >
            <div class="alarm-code-display">
              <span class="alarm-label">报警代码</span>
              <span class="alarm-code mono">{{ motorStore.alarmCode }}</span>
            </div>
            
            <div class="alarm-description">
              <el-icon class="alarm-desc-icon">
                <InfoFilled />
              </el-icon>
              <span>{{ alarmDescription }}</span>
            </div>
            
            <el-button 
              type="warning" 
              :loading="motorStore.loading.resetAlarm" 
              class="reset-alarm-btn"
              @click="handleResetAlarm"
            >
              <el-icon><Warning /></el-icon>
              报警复位
            </el-button>
          </div>
          
          <div
            v-else
            class="empty-state"
          >
            <el-icon class="empty-icon">
              <Document />
            </el-icon>
            <span>点击刷新获取报警信息</span>
          </div>
        </div>

        <!-- 控制操作卡片 -->
        <div class="status-card glass-card">
          <div class="card-header-inner">
            <span class="card-title">控制操作</span>
          </div>
          
          <div class="control-actions">
            <el-button 
              type="primary" 
              :loading="motorStore.loading.home" 
              :disabled="!motorStore.canControl"
              class="control-btn control-btn--primary"
              @click="handleHome"
            >
              <el-icon><Position /></el-icon>
              <span>回零 (模式 0)</span>
            </el-button>
            
            <el-button 
              type="success" 
              :loading="motorStore.loading.saveParams" 
              :disabled="!motorStore.isConnected"
              class="control-btn control-btn--success"
              @click="handleSaveParams"
            >
              <el-icon><DocumentAdd /></el-icon>
              <span>保存参数到 EEPROM</span>
            </el-button>
            
            <el-button 
              type="danger" 
              :loading="motorStore.loading.factoryReset" 
              :disabled="!motorStore.isConnected"
              class="control-btn control-btn--danger"
              @click="handleFactoryReset"
            >
              <el-icon><Delete /></el-icon>
              <span>恢复出厂设置</span>
            </el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
/**
 * @file DeviceStatusMonitor.vue
 * @path src/components/
 * @description 设备状态监控组件，显示电机状态、状态字、报警信息及控制操作
 * @author Agent
 * @date 2024-03-06
 */

import { ref, computed } from 'vue'
import { useMotorStore } from '@/stores/motor'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Refresh, Warning, Position, DocumentAdd, Delete, 
  WarningFilled, Close, Document, InfoFilled, Monitor 
} from '@element-plus/icons-vue'

const motorStore = useMotorStore()

/** 刷新状态标志 */
const refreshing = ref(false)

/**
 * 报警代码中文描述映射表
 * 基于常见伺服驱动器报警代码
 */
const ALARM_CODE_MAP = {
  0: '无报警',
  1: '过流保护',
  2: '过压保护',
  3: '欠压保护',
  4: '过热保护',
  5: '编码器故障',
  6: '通信故障',
  7: '位置偏差过大',
  8: '速度偏差过大',
  9: '过载保护',
  10: '电机过热',
  11: '驱动器过热',
  12: '再生制动过载',
  13: '主电源欠压',
  14: '控制电源欠压',
  15: 'EEPROM错误',
  16: '位置限制触发',
  17: '软件限位触发',
  18: '硬限位触发',
  19: '急停触发',
  20: '伺服使能无效',
  21: '参数错误',
  22: '系统错误',
  23: '内存错误',
  24: '看门狗超时',
  25: 'CAN通信错误',
  26: '脉冲输入错误',
  27: '模拟输入错误',
  28: '编码器Z信号错误',
  29: '编码器UVW信号错误',
  30: '编码器断线',
  31: '电机识别错误',
  32: '自动调谐失败',
  33: '位置超限',
  34: '速度超限',
  35: '加速度超限',
  36: '力矩超限',
  37: '跟随误差过大',
  38: '定位超时',
  39: '回零失败',
  40: '回零超时',
  100: '用户自定义报警1',
  101: '用户自定义报警2',
  102: '用户自定义报警3',
}

/**
 * 运行状态对应的标签类型
 * 
 * @returns {string} Element Plus Tag组件的类型
 */
const statusType = computed(() => {
  if (motorStore.status === 'ready') return 'success'
  if (motorStore.status === 'moving') return 'warning'
  if (motorStore.status === 'emergency_stop') return 'danger'
  return 'info'
})

/**
 * 运行状态中文文本
 * 
 * @returns {string} 状态中文描述
 */
const statusText = computed(() => {
  const statusMap = {
    'disconnected': '未连接',
    'ready': '就绪',
    'moving': '运动中',
    'emergency_stop': '急停',
    'error': '错误'
  }
  return statusMap[motorStore.status] || motorStore.status
})

/**
 * 连接状态徽章样式
 */
const connectionBadgeClass = computed(() => {
  return motorStore.isConnected ? 'status-badge--online' : 'status-badge--offline'
})

/**
 * 报警代码对应的中文描述
 * 优先使用后端返回的报警文本，否则使用本地映射表
 * 
 * @returns {string} 报警中文描述
 */
const alarmDescription = computed(() => {
  if (motorStore.alarmText) {
    return motorStore.alarmText
  }
  return ALARM_CODE_MAP[motorStore.alarmCode] || `未知报警 (代码: ${motorStore.alarmCode})`
})

/**
 * 格式化状态字显示
 * @param {number} raw - 原始状态字值
 * @returns {string} 格式化后的十六进制字符串
 */
function formatStatusWord(raw) {
  if (raw === undefined || raw === null) return '0000'
  return raw.toString(16).padStart(4, '0').toUpperCase()
}

/**
 * 刷新所有状态信息
 * 并行获取设备状态、状态字和报警代码
 */
async function refreshAll() {
  refreshing.value = true
  await Promise.all([
    motorStore.fetchStatus(),
    motorStore.readStatusWord(),
    motorStore.readAlarmCode()
  ])
  refreshing.value = false
  ElMessage.success('状态已刷新')
}

/**
 * 执行报警复位操作
 */
async function handleResetAlarm() {
  const success = await motorStore.resetAlarm()
  if (success) {
    ElMessage.success('报警已复位')
    await motorStore.readAlarmCode()
  }
}

/**
 * 执行回零操作
 */
async function handleHome() {
  const success = await motorStore.home(0)
  if (success) {
    ElMessage.success('回零已启动')
  }
}

/**
 * 保存参数到EEPROM
 * 需要用户确认操作
 */
async function handleSaveParams() {
  try {
    await ElMessageBox.confirm(
      '确定要保存参数到 EEPROM 吗？',
      '确认保存',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    const success = await motorStore.saveParams()
    if (success) {
      ElMessage.success('参数已保存')
    }
  } catch {
    // 用户取消操作
  }
}

/**
 * 恢复出厂设置
 * 需要用户确认操作
 */
async function handleFactoryReset() {
  try {
    await ElMessageBox.confirm(
      '确定要恢复出厂设置吗？此操作将清除所有自定义配置！',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    const success = await motorStore.factoryReset()
    if (success) {
      ElMessage.success('已恢复出厂设置')
    }
  } catch {
    // 用户取消操作
  }
}
</script>

<style scoped>
.device-status-monitor {
  width: 100%;
}

.monitor-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  background: var(--color-surface-primary);
  transition: var(--transition-all);
}

.monitor-card:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.header-icon {
  font-size: var(--font-size-xl);
  color: var(--color-primary-500);
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
}

/* 报警横幅 */
.alarm-banner {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  margin-bottom: var(--spacing-4);
  background: linear-gradient(135deg, var(--color-error-light) 0%, rgba(229, 62, 62, 0.1) 100%);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  animation: alarm-pulse 2s ease-in-out infinite;
}

.alarm-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: var(--color-error);
  border-radius: var(--radius-md);
  color: white;
  font-size: var(--font-size-xl);
  animation: alarm-icon-shake 0.5s ease-in-out infinite;
}

.alarm-content {
  flex: 1;
}

.alarm-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-error-dark);
  margin-bottom: var(--spacing-1);
}

.alarm-message {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.alarm-close {
  color: var(--color-error);
  padding: var(--spacing-1);
}

.alarm-close:hover {
  background: rgba(229, 62, 62, 0.1);
  border-radius: var(--radius-md);
}

@keyframes alarm-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(229, 62, 62, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(229, 62, 62, 0);
  }
}

@keyframes alarm-icon-shake {
  0%, 100% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(-5deg);
  }
  75% {
    transform: rotate(5deg);
  }
}

/* 状态网格 */
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-4);
}

/* 玻璃态卡片 */
.glass-card {
  position: relative;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.9) 0%,
    rgba(255, 255, 255, 0.7) 100%
  );
  backdrop-filter: blur(10px);
  overflow: hidden;
  transition: var(--transition-all);
}

.glass-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.5),
    transparent
  );
}

.glass-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-300);
}

.status-card--alarm {
  border-color: var(--color-error);
  background: linear-gradient(
    135deg,
    rgba(229, 62, 62, 0.1) 0%,
    rgba(255, 255, 255, 0.8) 100%
  );
}

.status-card--alarm:hover {
  border-color: var(--color-error);
  box-shadow: var(--shadow-glow-error);
}

.card-header-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-secondary);
  background: rgba(0, 0, 0, 0.02);
}

.card-title {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.status-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
}

.status-badge--online {
  background: var(--color-success-light);
  color: var(--color-success-dark);
}

.status-badge--online .badge-dot {
  background: var(--color-status-online);
  box-shadow: 0 0 6px var(--color-status-online);
  animation: pulse 2s ease-in-out infinite;
}

.status-badge--offline {
  background: var(--color-error-light);
  color: var(--color-error-dark);
}

.status-badge--offline .badge-dot {
  background: var(--color-status-offline);
}

.refresh-icon-btn {
  padding: var(--spacing-1);
  color: var(--color-text-tertiary);
  transition: var(--transition-fast);
}

.refresh-icon-btn:hover {
  color: var(--color-primary-500);
  background: var(--color-interactive-hover);
  border-radius: var(--radius-md);
}

/* 状态内容 */
.status-content {
  padding: var(--spacing-4);
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) 0;
  border-bottom: 1px solid var(--color-border-secondary);
}

.status-row:last-child {
  border-bottom: none;
}

.status-row--highlight {
  background: var(--color-bg-secondary);
  margin: var(--spacing-2) calc(-1 * var(--spacing-4));
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-md);
}

.status-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.position-display {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-1);
}

.position-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
}

.position-unit {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.position-steps {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.ws-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
}

.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
}

.ws-status--connected {
  color: var(--color-success);
}

.ws-status--connected .ws-dot {
  background: var(--color-status-online);
  box-shadow: 0 0 6px var(--color-status-online);
  animation: pulse 2s ease-in-out infinite;
}

.ws-status--disconnected {
  color: var(--color-text-tertiary);
}

.ws-status--disconnected .ws-dot {
  background: var(--color-neutral-400);
}

/* 状态字显示 */
.status-word-content {
  padding: var(--spacing-4);
}

.status-word-display {
  text-align: center;
  padding: var(--spacing-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-4);
}

.status-word-value {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
  letter-spacing: 0.1em;
}

.status-flags {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-2);
}

.flag-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
}

.flag-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-neutral-400);
  transition: var(--transition-fast);
}

.flag-label {
  flex: 1;
  color: var(--color-text-secondary);
}

.flag-value {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-tertiary);
}

.flag-item--active {
  background: var(--color-success-light);
}

.flag-item--active .flag-dot {
  background: var(--color-status-online);
  box-shadow: 0 0 6px var(--color-status-online);
}

.flag-item--active .flag-value {
  color: var(--color-success-dark);
}

.flag-item--warning {
  background: var(--color-warning-light);
}

.flag-item--warning .flag-dot {
  background: var(--color-status-warning);
  box-shadow: 0 0 6px var(--color-status-warning);
  animation: pulse-fast 1s ease-in-out infinite;
}

.flag-item--warning .flag-value {
  color: var(--color-warning-dark);
}

.flag-item--error {
  background: var(--color-error-light);
}

.flag-item--error .flag-dot {
  background: var(--color-status-error);
  box-shadow: 0 0 6px var(--color-status-error);
}

.flag-item--error .flag-value {
  color: var(--color-error-dark);
}

/* 报警内容 */
.alarm-content-inner {
  padding: var(--spacing-4);
}

.alarm-code-display {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  background: linear-gradient(135deg, var(--color-error-light) 0%, rgba(229, 62, 62, 0.05) 100%);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-3);
}

.alarm-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.alarm-code {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-error);
}

.alarm-description {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-4);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.alarm-desc-icon {
  color: var(--color-primary-500);
  margin-top: 2px;
}

.reset-alarm-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-8);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.empty-icon {
  font-size: var(--font-size-3xl);
  margin-bottom: var(--spacing-2);
  opacity: 0.5;
}

/* 控制操作 */
.control-actions {
  padding: var(--spacing-4);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
}

.control-btn--primary {
  background: var(--color-primary-500);
  border-color: var(--color-primary-500);
}

.control-btn--primary:hover:not(:disabled) {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.control-btn--success {
  background: var(--color-success);
  border-color: var(--color-success);
}

.control-btn--success:hover:not(:disabled) {
  background: var(--color-success-dark);
  border-color: var(--color-success-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.control-btn--danger {
  background: var(--color-error);
  border-color: var(--color-error);
}

.control-btn--danger:hover:not(:disabled) {
  background: var(--color-error-dark);
  border-color: var(--color-error-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

/* 动画 */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.2);
  }
}

@keyframes pulse-fast {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 过渡动画 */
.slide-fade-enter-active {
  transition: all var(--transition-base);
}

.slide-fade-leave-active {
  transition: all var(--transition-slow);
}

.slide-fade-enter-from {
  transform: translateY(-10px);
  opacity: 0;
}

.slide-fade-leave-to {
  transform: translateY(10px);
  opacity: 0;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .status-flags {
    grid-template-columns: 1fr;
  }
  
  .position-value {
    font-size: var(--font-size-lg);
  }
  
  .status-word-value {
    font-size: var(--font-size-2xl);
  }
}
</style>
