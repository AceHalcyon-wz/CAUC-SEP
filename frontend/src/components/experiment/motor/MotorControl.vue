<template>
  <div class="motor-control-wrapper">
    <!-- 急停按钮（固定在顶部） -->
    <el-card
      class="emergency-stop-card"
      :class="{ 'emergency-active': motorStore.isEmergencyStopped }"
    >
      <div class="emergency-stop-container">
        <el-button
          type="danger"
          size="large"
          :loading="motorStore.loading.emergencyStop"
          :disabled="!motorStore.isConnected"
          class="emergency-stop-btn"
          @click="handleEmergencyStop"
        >
          <el-icon class="emergency-icon">
            <WarningFilled />
          </el-icon>
          <span class="emergency-text">急停</span>
        </el-button>
        <transition name="zoom-fade">
          <el-button
            v-if="motorStore.isEmergencyStopped"
            type="warning"
            size="large"
            :loading="motorStore.loading.resetEmergency"
            class="reset-emergency-btn"
            @click="handleResetEmergency"
          >
            <el-icon><RefreshRight /></el-icon>
            <span>复位急停</span>
          </el-button>
        </transition>
      </div>
      <transition name="slide-fade">
        <el-alert
          v-if="motorStore.isEmergencyStopped"
          title="电机处于急停状态，请先复位后再进行操作"
          type="error"
          :closable="false"
          show-icon
          class="emergency-alert"
        />
      </transition>
    </el-card>

    <!-- 运动控制卡片 -->
    <el-card class="motor-control">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon">
            <SetUp />
          </el-icon>
          <span class="header-title">运动控制</span>
        </div>
      </template>

      <div class="control-content">
        <!-- 错误提示 -->
        <transition name="slide-fade">
          <el-alert
            v-if="motorStore.alarmMessage"
            :title="motorStore.alarmMessage"
            type="error"
            closable
            class="error-alert"
            @close="motorStore.clearAlarm()"
          />
        </transition>

        <!-- 限位提示 -->
        <el-alert
          :title="`限位范围: ${motorStore.limits.negative_mm}mm ~ ${motorStore.limits.positive_mm}mm`"
          :type="limitAlertType"
          :closable="false"
          class="limit-alert"
        >
          <template #icon>
            <el-icon><InfoFilled /></el-icon>
          </template>
          <template #default>
            <div class="limit-info">
              <div class="limit-text">
                限位范围: {{ motorStore.limits.negative_mm }}mm ~ {{ motorStore.limits.positive_mm }}mm
              </div>
              <div
                v-if="limitWarning"
                class="limit-warning-text"
              >
                <el-icon><Warning /></el-icon>
                {{ limitWarning }}
              </div>
            </div>
          </template>
        </el-alert>

        <!-- 运动参数 -->
        <el-form
          :model="moveForm"
          label-width="100px"
          class="move-form"
        >
          <el-form-item label="目标位置">
            <div class="form-item-content">
              <el-input-number
                v-model="moveForm.position"
                :min="motorStore.limits.negative_mm"
                :max="motorStore.limits.positive_mm"
                :precision="3"
                :step="0.1"
                class="position-input"
                :class="positionInputClass"
                @change="validatePosition"
              />
              <span class="unit">mm</span>
              <transition name="fade">
                <el-tag
                  v-if="positionError"
                  type="danger"
                  size="small"
                  class="error-tag"
                >
                  {{ positionError }}
                </el-tag>
              </transition>
            </div>
          </el-form-item>

          <el-form-item label="运动速度">
            <div class="form-item-content">
              <el-input-number
                v-model="moveForm.velocity"
                :min="VELOCITY_MIN"
                :max="VELOCITY_MAX"
                :precision="1"
                :step="1"
                class="velocity-input"
                @change="validateVelocity"
              />
              <span class="unit">mm/s</span>
              <span class="range-hint">({{ VELOCITY_MIN }}-{{ VELOCITY_MAX }})</span>
              <transition name="fade">
                <el-tag
                  v-if="velocityError"
                  type="danger"
                  size="small"
                  class="error-tag"
                >
                  {{ velocityError }}
                </el-tag>
              </transition>
            </div>
          </el-form-item>
        </el-form>

        <!-- 轨迹预览 -->
        <MotorTrajectoryPreview
          :target-position="moveForm.position"
          :velocity="moveForm.velocity"
        />

        <!-- 运动按钮 -->
        <div class="button-group">
          <el-button
            type="primary"
            size="large"
            :disabled="!motorStore.canControl || !!positionError || !!velocityError"
            :loading="isMoving"
            class="action-btn move-btn"
            @click="handleMoveAbsolute"
          >
            <el-icon><Position /></el-icon>
            <span>绝对定位</span>
          </el-button>

          <!-- 回零按钮 -->
          <el-button
            type="success"
            size="large"
            :disabled="!motorStore.canControl"
            :loading="motorStore.loading.home"
            class="action-btn home-btn"
            @click="handleHome"
          >
            <el-icon><HomeFilled /></el-icon>
            <span>回零</span>
          </el-button>

          <!-- 回零模式选择器 -->
          <el-form-item
            label="回零模式"
            class="home-mode-selector"
          >
            <el-select
              v-model="homeForm.mode"
              placeholder="选择回零模式"
              size="small"
              class="home-mode-select"
            >
              <el-option
                v-for="option in HOME_MODE_OPTIONS"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
            <el-tooltip
              content="根据DM2C-RS556手册，不同模式适用于不同的限位和原点信号配置"
              placement="top"
            >
              <el-icon class="tooltip-icon">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </el-form-item>

          <!-- JOG控制 -->
          <div class="jog-buttons">
            <el-button
              type="warning"
              size="large"
              :disabled="!motorStore.canControl || !!velocityError"
              :class="{ 'jog-active': jogState.active && jogState.direction === -1 }"
              class="jog-btn jog-btn-left"
              @mousedown="startJog(-1)"
              @mouseup="stopJog"
              @mouseleave="stopJog"
            >
              <el-icon><ArrowLeft /></el-icon>
              <span>JOG-</span>
              <transition name="fade">
                <span
                  v-if="jogState.active && jogState.direction === -1"
                  class="jog-indicator"
                >
                  运行中
                </span>
              </transition>
            </el-button>

            <el-button
              type="warning"
              size="large"
              :disabled="!motorStore.canControl || !!velocityError"
              :class="{ 'jog-active': jogState.active && jogState.direction === 1 }"
              class="jog-btn jog-btn-right"
              @mousedown="startJog(1)"
              @mouseup="stopJog"
              @mouseleave="stopJog"
            >
              <span>JOG+</span>
              <el-icon><ArrowRight /></el-icon>
              <transition name="fade">
                <span
                  v-if="jogState.active && jogState.direction === 1"
                  class="jog-indicator"
                >
                  运行中
                </span>
              </transition>
            </el-button>
          </div>
        </div>

        <!-- 限位设置 -->
        <el-divider class="limit-divider">
          <el-icon><Setting /></el-icon>
          <span>限位设置</span>
        </el-divider>
        
        <el-form
          :model="limitForm"
          label-width="100px"
          size="small"
          class="limit-form"
        >
          <el-form-item label="正向限位">
            <div class="form-item-content">
              <el-input-number
                v-model="limitForm.positive"
                :min="0"
                :max="100"
                :precision="1"
                class="limit-input"
              />
              <span class="unit">mm</span>
            </div>
          </el-form-item>

          <el-form-item label="负向限位">
            <div class="form-item-content">
              <el-input-number
                v-model="limitForm.negative"
                :min="-100"
                :max="0"
                :precision="1"
                class="limit-input"
              />
              <span class="unit">mm</span>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button 
              type="primary" 
              size="small" 
              class="apply-limit-btn"
              @click="handleSetLimits"
            >
              <el-icon><Check /></el-icon>
              <span>应用限位</span>
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <!-- PR路径配置 -->
    <PRPathConfig />

    <!-- 位置预设 -->
    <MotorPositionPreset />

    <!-- 运动历史记录 -->
    <MotorHistoryPanel />
  </div>
</template>

<script setup>
/**
 * @file MotorControl.vue
 * @path src/components/
 * @description 电机运动控制组件，提供绝对定位、JOG点动、回零、急停、限位设置及PR路径配置功能
 * @author Agent
 * @date 2024-03-06
 */

import { ref, reactive, computed, onUnmounted } from 'vue'
import { useMotorStore } from '@/stores/motor'
import { ElMessage } from 'element-plus'
import { PRPathConfig } from '@/components/device'
import MotorPositionPreset from './MotorPositionPreset.vue'
import MotorTrajectoryPreview from './MotorTrajectoryPreview.vue'
import MotorHistoryPanel from './MotorHistoryPanel.vue'
import { validatePosition as validatePosUtil, validateVelocity as validateVelUtil } from '@/utils/validation'
import { MOTOR } from '@/config/constants'

// ============ 常量定义 ============
/** 最小速度限制 mm/s */
const VELOCITY_MIN = MOTOR.MIN_VELOCITY
/** 最大速度限制 mm/s */
const VELOCITY_MAX = MOTOR.MAX_VELOCITY

const motorStore = useMotorStore()

// ============ 响应式状态 ============

/** 运动表单数据 */
const moveForm = reactive({
  position: 0,
  velocity: 10
})

/** 回零模式选项（根据DM2C-RS556用户手册V1.8） */
const HOME_MODE_OPTIONS = [
  { value: 0, label: '单次正向限位回零' },
  { value: 1, label: '单次负向限位回零' },
  { value: 2, label: '单次原点信号回零' },
  { value: 3, label: '原点信号+正向限位' },
  { value: 4, label: '原点信号+负向限位' },
  { value: 5, label: '正向限位回零' },
  { value: 6, label: '负向限位回零' },
  { value: 7, label: '原点信号回零' },
  { value: 8, label: '原点+正向限位' },
  { value: 9, label: '原点+负向限位' }
]

/** 回零配置表单 */
const homeForm = reactive({
  mode: 0
})

/** 限位表单数据 */
const limitForm = reactive({
  positive: 50,
  negative: -50
})

/** 运动状态标志 */
const isMoving = ref(false)

/** JOG定时器ID */
let jogInterval = null

/** JOG运动状态 */
const jogState = reactive({
  active: false,
  direction: 0
})

/** 位置验证错误信息 */
const positionError = ref('')
/** 速度验证错误信息 */
const velocityError = ref('')

// ============ 计算属性 ============

/**
 * 位置输入框样式类
 * 根据限位距离动态改变颜色
 */
const positionInputClass = computed(() => {
  const posLimit = motorStore.limits.positive_mm
  const negLimit = motorStore.limits.negative_mm
  const position = moveForm.position
  const warningThreshold = 5

  // 超出限位
  if (position > posLimit || position < negLimit) {
    return 'position-error'
  }

  // 接近限位
  if (Math.abs(position - posLimit) < warningThreshold || Math.abs(position - negLimit) < warningThreshold) {
    return 'position-warning'
  }

  return ''
})

/**
 * 限位警告类型
 */
const limitAlertType = computed(() => {
  const posLimit = motorStore.limits.positive_mm
  const negLimit = motorStore.limits.negative_mm
  const position = moveForm.position

  if (position > posLimit || position < negLimit) {
    return 'error'
  }

  const warningThreshold = 5
  if (Math.abs(position - posLimit) < warningThreshold || Math.abs(position - negLimit) < warningThreshold) {
    return 'warning'
  }

  return 'info'
})

/**
 * 限位警告文本
 */
const limitWarning = computed(() => {
  const posLimit = motorStore.limits.positive_mm
  const negLimit = motorStore.limits.negative_mm
  const position = moveForm.position

  if (position > posLimit) {
    return '目标位置超出正向限位！'
  }
  if (position < negLimit) {
    return '目标位置超出负向限位！'
  }

  const warningThreshold = 5
  if (Math.abs(position - posLimit) < warningThreshold) {
    return '目标位置接近正向限位边界'
  }
  if (Math.abs(position - negLimit) < warningThreshold) {
    return '目标位置接近负向限位边界'
  }

  return ''
})

// ============ 验证函数 ============

/**
 * 验证位置参数是否在软件限位范围内
 * 
 * @returns {boolean} 验证是否通过
 */
function validatePosition() {
  const minLimit = motorStore.limits.negative_mm
  const maxLimit = motorStore.limits.positive_mm
  const result = validatePosUtil(moveForm.position, minLimit, maxLimit)
  
  if (!result.valid) {
    positionError.value = result.message
    return false
  }
  
  positionError.value = ''
  return true
}

/**
 * 验证速度参数是否在有效范围内
 * 
 * @returns {boolean} 验证是否通过
 */
function validateVelocity() {
  const result = validateVelUtil(moveForm.velocity, VELOCITY_MIN, VELOCITY_MAX)
  
  if (!result.valid) {
    velocityError.value = result.message
    return false
  }
  
  velocityError.value = ''
  return true
}

// ============ 运动控制函数 ============

/**
 * 绝对定位操作
 * 包含位置验证和错误处理
 */
async function handleMoveAbsolute() {
  // 前置验证
  if (!validatePosition()) {
    ElMessage.error(positionError.value)
    motorStore.addMovementRecord({
      type: 'absolute',
      targetPosition: moveForm.position,
      velocity: moveForm.velocity,
      success: false,
      errorMessage: positionError.value
    })
    return
  }
  
  if (!validateVelocity()) {
    ElMessage.error(velocityError.value)
    motorStore.addMovementRecord({
      type: 'absolute',
      targetPosition: moveForm.position,
      velocity: moveForm.velocity,
      success: false,
      errorMessage: velocityError.value
    })
    return
  }

  isMoving.value = true
  
  try {
    const success = await motorStore.moveAbsolute(moveForm.position, moveForm.velocity)
    
    // 记录运动历史
    motorStore.addMovementRecord({
      type: 'absolute',
      targetPosition: moveForm.position,
      velocity: moveForm.velocity,
      success: success
    })
    
    if (success) {
      ElMessage.success('运动指令已发送')
    } else if (motorStore.alarmMessage) {
      // 显示API返回的错误信息
      ElMessage.error(motorStore.alarmMessage)
    }
  } catch (error) {
    // 捕获并显示异常错误
    const errorMsg = error.response?.data?.detail || error.message || '运动指令发送失败'
    ElMessage.error(errorMsg)
    
    // 记录失败历史
    motorStore.addMovementRecord({
      type: 'absolute',
      targetPosition: moveForm.position,
      velocity: moveForm.velocity,
      success: false,
      errorMessage: errorMsg
    })
  } finally {
    isMoving.value = false
  }
}

/**
 * 回零操作
 * 执行电机回零校准，使用用户选择的回零模式
 */
async function handleHome() {
  const success = await motorStore.home(homeForm.mode)
  if (success) {
    ElMessage.success(`回零指令已发送（模式${homeForm.mode}: ${HOME_MODE_OPTIONS[homeForm.mode].label}）`)
  }
}

/**
 * 急停操作
 * 立即停止电机运动
 */
async function handleEmergencyStop() {
  try {
    const success = await motorStore.emergencyStop()
    if (success) {
      ElMessage.warning('急停已触发')
    }
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || '急停操作失败'
    ElMessage.error(errorMsg)
  }
}

/**
 * 复位急停状态
 */
async function handleResetEmergency() {
  const success = await motorStore.resetEmergency()
  if (success) {
    ElMessage.success('急停已复位')
  }
}

/**
 * 开始JOG运动
 * 
 * @param {number} direction - 运动方向，1为正向，-1为负向
 */
function startJog(direction) {
  if (!motorStore.canControl) return
  
  // 速度验证
  if (!validateVelocity()) {
    ElMessage.error(velocityError.value)
    return
  }

  // 清除可能存在的旧interval，防止多个interval同时运行
  if (jogInterval) {
    clearInterval(jogInterval)
    jogInterval = null
  }
  
  // 更新JOG状态
  jogState.active = true
  jogState.direction = direction
  
  // 立即执行一次
  motorStore.jog(direction, moveForm.velocity)
  
  // 持续JOG
  jogInterval = setInterval(() => {
    motorStore.jog(direction, moveForm.velocity)
  }, 300)
}

/**
 * 停止JOG运动
 */
function stopJog() {
  if (jogInterval) {
    clearInterval(jogInterval)
    jogInterval = null
  }
  
  // 重置JOG状态
  jogState.active = false
  jogState.direction = 0
}

/**
 * 设置限位参数
 */
async function handleSetLimits() {
  if (limitForm.negative >= limitForm.positive) {
    ElMessage.error('负向限位必须小于正向限位')
    return
  }
  
  try {
    const success = await motorStore.setLimits(limitForm.positive, limitForm.negative)
    
    if (success) {
      ElMessage.success('限位设置已应用')
    } else if (motorStore.alarmMessage) {
      ElMessage.error(motorStore.alarmMessage)
    }
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || '限位设置失败'
    ElMessage.error(errorMsg)
  }
}

// 组件卸载时清理JOG定时器
onUnmounted(() => {
  stopJog()
})
</script>

<style scoped>
.motor-control-wrapper {
  width: 100%;
}

/* ==================== 急停按钮样式 ==================== */

.emergency-stop-card {
  margin-bottom: var(--spacing-6);
  border: 2px solid var(--color-error);
  background: linear-gradient(135deg, var(--color-surface-primary) 0%, var(--color-error-light) 100%);
  transition: var(--transition-all);
}

.emergency-stop-card.emergency-active {
  border-color: var(--color-error);
  animation: emergency-pulse-border 1.5s ease-in-out infinite;
}

@keyframes emergency-pulse-border {
  0%, 100% {
    border-color: var(--color-error);
    box-shadow: 0 0 20px rgba(229, 62, 62, 0.3);
  }
  50% {
    border-color: var(--color-error-dark);
    box-shadow: 0 0 40px rgba(229, 62, 62, 0.6);
  }
}

.emergency-stop-container {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--spacing-6);
  padding: var(--spacing-4);
}

.emergency-stop-btn {
  width: 240px;
  height: 90px;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 50%, #991b1b 100%);
  border: 3px solid #7f1d1d;
  box-shadow: 
    0 8px 16px rgba(229, 62, 62, 0.3),
    inset 0 2px 4px rgba(255, 255, 255, 0.2);
  transition: var(--transition-all);
  position: relative;
  overflow: hidden;
}

/* 急停按钮脉冲动画 */
.emergency-stop-btn:not(:disabled) {
  animation: pulse-emergency 2s ease-in-out infinite;
}

@keyframes pulse-emergency {
  0%, 100% {
    box-shadow: 
      0 8px 16px rgba(229, 62, 62, 0.3),
      inset 0 2px 4px rgba(255, 255, 255, 0.2),
      0 0 30px rgba(229, 62, 62, 0.4);
  }
  50% {
    box-shadow: 
      0 8px 16px rgba(229, 62, 62, 0.4),
      inset 0 2px 4px rgba(255, 255, 255, 0.3),
      0 0 60px rgba(229, 62, 62, 0.7);
  }
}

.emergency-stop-btn:not(:disabled):hover {
  transform: scale(1.05);
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 50%, #b91c1c 100%);
}

.emergency-stop-btn:not(:disabled):active {
  transform: scale(0.98);
}

.emergency-icon {
  font-size: 28px;
  margin-right: var(--spacing-2);
}

.emergency-text {
  margin-left: var(--spacing-2);
  letter-spacing: 0.1em;
}

.reset-emergency-btn {
  width: 160px;
  height: 90px;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.reset-emergency-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-warning);
}

.emergency-alert {
  margin-top: var(--spacing-4);
  border-radius: var(--radius-md);
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
  20%, 40%, 60%, 80% { transform: translateX(5px); }
}

/* ==================== 运动控制卡片样式 ==================== */

.motor-control {
  margin-bottom: var(--spacing-6);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.motor-control:hover {
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

.control-content {
  padding: var(--spacing-2) 0;
}

/* 警告提示样式 */
.error-alert {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-md);
}

.limit-alert {
  margin-bottom: var(--spacing-5);
  border-radius: var(--radius-md);
  background-color: var(--color-bg-secondary);
}

.limit-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.limit-text {
  font-weight: var(--font-weight-medium);
}

.limit-warning-text {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-sm);
  color: var(--color-warning-600);
  margin-top: var(--spacing-1);
}

.limit-warning-text .el-icon {
  font-size: var(--font-size-base);
}

/* 表单样式 */
.move-form {
  margin-bottom: var(--spacing-5);
}

.form-item-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.position-input,
.velocity-input {
  width: 180px;
}

/* 限位警告样式 */
.position-input.position-warning :deep(.el-input__wrapper) {
  border-color: var(--color-warning-500);
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2);
  animation: pulse-warning 1.5s ease-in-out infinite;
}

.position-input.position-error :deep(.el-input__wrapper) {
  border-color: var(--color-error-500);
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
  animation: pulse-error 1s ease-in-out infinite;
}

@keyframes pulse-warning {
  0%, 100% {
    box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.4);
  }
}

@keyframes pulse-error {
  0%, 100% {
    box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.5);
  }
}

.limit-input {
  width: 150px;
}

.unit {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.range-hint {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
}

.error-tag {
  margin-left: var(--spacing-2);
}

/* 按钮组样式 */
.button-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.action-btn {
  width: 100%;
  height: 48px;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.move-btn:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-primary);
}

.home-btn:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-success);
}

.home-mode-selector {
  margin-top: var(--spacing-3);
  margin-bottom: var(--spacing-2);
}

.home-mode-select {
  width: 200px;
}

.action-btn:active {
  transform: translateY(0);
}

/* JOG按钮样式 */
.jog-buttons {
  display: flex;
  gap: var(--spacing-3);
}

.jog-btn {
  flex: 1;
  height: 52px;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
  position: relative;
}

.jog-btn:not(:disabled):hover {
  transform: translateY(-2px);
}

.jog-btn:active {
  transform: translateY(0);
}

/* JOG激活状态 */
.jog-active {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
  border-color: #b45309 !important;
  color: #fff !important;
  box-shadow: 
    0 0 20px rgba(245, 158, 11, 0.5),
    inset 0 2px 4px rgba(255, 255, 255, 0.2);
  animation: jog-pulse 0.8s ease-in-out infinite;
}

@keyframes jog-pulse {
  0%, 100% {
    box-shadow: 
      0 0 20px rgba(245, 158, 11, 0.5),
      inset 0 2px 4px rgba(255, 255, 255, 0.2);
  }
  50% {
    box-shadow: 
      0 0 35px rgba(245, 158, 11, 0.7),
      inset 0 2px 4px rgba(255, 255, 255, 0.3);
  }
}

.jog-indicator {
  display: inline-flex;
  align-items: center;
  margin-left: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-2);
  background-color: rgba(255, 255, 255, 0.25);
  border-radius: var(--radius-base);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  backdrop-filter: blur(4px);
}

/* 限位设置区域 */
.limit-divider {
  margin: var(--spacing-6) 0;
}

.limit-divider :deep(.el-divider__text) {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  background-color: var(--color-surface-primary);
}

.limit-form {
  margin-top: var(--spacing-4);
}

.apply-limit-btn {
  transition: var(--transition-all);
}

.apply-limit-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

/* ==================== 响应式优化 ==================== */

@media (max-width: 768px) {
  .emergency-stop-container {
    flex-direction: column;
    gap: var(--spacing-4);
  }
  
  .emergency-stop-btn {
    width: 100%;
    max-width: 280px;
  }
  
  .reset-emergency-btn {
    width: 100%;
    max-width: 200px;
  }
  
  .jog-buttons {
    flex-direction: column;
  }
  
  .jog-btn {
    width: 100%;
  }
  
  .form-item-content {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .position-input,
  .velocity-input,
  .limit-input {
    width: 100%;
  }
}
</style>
