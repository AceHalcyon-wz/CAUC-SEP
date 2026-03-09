<!--
  @file UserGuide.vue
  @path src/components/
  @description 用户引导组件，提供新手引导流程、热点提示、帮助文档链接等功能
  @author Agent
  @date 2024-03-07
-->

<script setup>
/**
 * @file UserGuide.vue
 * @path src/components/
 * @description 用户引导组件，提供新手引导流程、热点提示、帮助文档链接等功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

// === Props/Emits 定义 ===
const props = defineProps({
  /** 是否自动开始引导 */
  autoStart: {
    type: Boolean,
    default: false
  },
  /** 引导步骤配置 */
  steps: {
    type: Array,
    default: () => []
  },
  /** 本地存储键名 */
  storageKey: {
    type: String,
    default: 'user_guide_progress'
  },
  /** 是否显示跳过按钮 */
  showSkip: {
    type: Boolean,
    default: true
  },
  /** 是否显示进度条 */
  showProgress: {
    type: Boolean,
    default: true
  },
  /** 是否允许键盘导航 */
  keyboardNavigation: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'start'): void
  (e: 'complete'): void
  (e: 'skip'): void
  (e: 'step-change', stepIndex: number): void
  (e: 'close'): void
}>()

// === 默认引导步骤 ===
const defaultSteps = [
  {
    id: 'welcome',
    title: '欢迎使用实验控制系统',
    content: '这是一个综合性的实验设备控制平台，支持电机、电磁铁、压电陶瓷、温度等多种设备的精确控制。',
    target: null,
    position: 'center',
    image: null,
    highlight: false
  },
  {
    id: 'sidebar',
    title: '导航菜单',
    content: '通过左侧导航菜单可以快速切换不同的功能模块，包括设备控制、数据分析、实验管理等。',
    target: '.sidebar',
    position: 'right',
    image: null,
    highlight: true
  },
  {
    id: 'device-status',
    title: '设备状态监控',
    content: '顶部状态栏实时显示所有设备的连接状态，点击可查看详细信息或进行快速操作。',
    target: '.status-bar',
    position: 'bottom',
    image: null,
    highlight: true
  },
  {
    id: 'experiment-control',
    title: '实验控制面板',
    content: '在这里可以创建和管理实验，设置参数，启动/停止数据采集，导出实验数据等。',
    target: '.experiment-panel',
    position: 'left',
    image: null,
    highlight: true
  },
  {
    id: 'shortcuts',
    title: '快捷键支持',
    content: '系统支持丰富的键盘快捷键，按 ? 键可查看所有可用快捷键，提高操作效率。',
    target: null,
    position: 'center',
    image: null,
    highlight: false
  },
  {
    id: 'theme',
    title: '个性化设置',
    content: '支持亮色/暗色主题切换，可在设置中调整界面布局、字体大小等个性化选项。',
    target: '.settings-btn',
    position: 'left',
    image: null,
    highlight: true
  },
  {
    id: 'help',
    title: '获取帮助',
    content: '遇到问题时，可以点击帮助按钮查看文档，或联系技术支持获取帮助。',
    target: '.help-btn',
    position: 'left',
    image: null,
    highlight: false
  },
  {
    id: 'profile',
    title: '个人中心',
    content: '点击右上角用户头像，选择"个人中心"可以查看和编辑个人信息、设置偏好、查看操作历史记录。',
    target: '.topbar__user',
    position: 'left',
    image: null,
    highlight: true
  },
  {
    id: 'preferences',
    title: '偏好设置',
    content: '在个人中心可以自定义通知设置、显示选项、数据刷新频率等，让系统更符合您的使用习惯。',
    target: null,
    position: 'center',
    image: null,
    highlight: false
  }
]

// === 响应式状态 ===
/** 是否显示引导 */
const isVisible = ref(false)
/** 当前步骤索引 */
const currentStepIndex = ref(0)
/** 引导步骤列表 */
const guideSteps = ref([...defaultSteps, ...props.steps])
/** 是否已完成引导 */
const isCompleted = ref(false)
/** 是否显示热点提示 */
const showHotspots = ref(false)
/** 热点提示列表 */
const hotspots = ref([])
/** 目标元素位置信息 */
const targetPosition = reactive({
  top: 0,
  left: 0,
  width: 0,
  height: 0
})
/** 遮罩层位置 */
const maskPosition = reactive({
  top: 0,
  left: 0,
  width: 0,
  height: 0
})
/** 提示框位置 */
const tooltipPosition = reactive({
  top: 0,
  left: 0
})
/** 是否正在计算位置 */
const isCalculating = ref(false)

// === 计算属性 ===
/** 当前步骤 */
const currentStep = computed(() => {
  return guideSteps.value[currentStepIndex.value] || null
})

/** 进度百分比 */
const progressPercent = computed(() => {
  if (guideSteps.value.length === 0) return 0
  return Math.round(((currentStepIndex.value + 1) / guideSteps.value.length) * 100)
})

/** 是否为第一步 */
const isFirstStep = computed(() => currentStepIndex.value === 0)

/** 是否为最后一步 */
const isLastStep = computed(() => currentStepIndex.value === guideSteps.value.length - 1)

/** 提示框位置样式 */
const tooltipStyle = computed(() => {
  return {
    top: `${tooltipPosition.top}px`,
    left: `${tooltipPosition.left}px`
  }
})

// === 方法 ===
/**
 * 开始引导
 */
function start() {
  isVisible.value = true
  currentStepIndex.value = 0
  isCompleted.value = false
  emit('start')
  emit('update:visible', true)

  nextTick(() => {
    updatePositions()
  })
}

/**
 * 完成引导
 */
function complete() {
  isCompleted.value = true
  isVisible.value = false
  saveProgress()
  emit('complete')
  emit('update:visible', false)
}

/**
 * 跳过引导
 */
function skip() {
  isVisible.value = false
  saveProgress()
  emit('skip')
  emit('update:visible', false)
}

/**
 * 关闭引导
 */
function close() {
  isVisible.value = false
  emit('close')
  emit('update:visible', false)
}

/**
 * 下一步
 */
function nextStep() {
  if (isLastStep.value) {
    complete()
  } else {
    currentStepIndex.value++
    emit('step-change', currentStepIndex.value)
    nextTick(() => {
      updatePositions()
    })
  }
}

/**
 * 上一步
 */
function prevStep() {
  if (!isFirstStep.value) {
    currentStepIndex.value--
    emit('step-change', currentStepIndex.value)
    nextTick(() => {
      updatePositions()
    })
  }
}

/**
 * 跳转到指定步骤
 *
 * @param {number} index - 步骤索引
 */
function goToStep(index) {
  if (index >= 0 && index < guideSteps.value.length) {
    currentStepIndex.value = index
    emit('step-change', currentStepIndex.value)
    nextTick(() => {
      updatePositions()
    })
  }
}

/**
 * 更新位置信息
 */
async function updatePositions() {
  if (!currentStep.value) return

  isCalculating.value = true

  await nextTick()

  const step = currentStep.value

  // 如果没有目标元素，居中显示
  if (!step.target) {
    targetPosition.top = 0
    targetPosition.left = 0
    targetPosition.width = 0
    targetPosition.height = 0
    maskPosition.top = 0
    maskPosition.left = 0
    maskPosition.width = 0
    maskPosition.height = 0

    // 居中显示提示框
    tooltipPosition.top = window.innerHeight / 2 - 100
    tooltipPosition.left = window.innerWidth / 2 - 200
  } else {
    // 获取目标元素位置
    const targetEl = document.querySelector(step.target)
    if (targetEl) {
      const rect = targetEl.getBoundingClientRect()

      targetPosition.top = rect.top
      targetPosition.left = rect.left
      targetPosition.width = rect.width
      targetPosition.height = rect.height

      // 计算遮罩层位置（带边距）
      const padding = 8
      maskPosition.top = rect.top - padding
      maskPosition.left = rect.left - padding
      maskPosition.width = rect.width + padding * 2
      maskPosition.height = rect.height + padding * 2

      // 高亮目标元素
      if (step.highlight) {
        targetEl.classList.add('guide-highlight')
      }

      // 计算提示框位置
      calculateTooltipPosition(step.position)
    }
  }

  isCalculating.value = false
}

/**
 * 计算提示框位置
 *
 * @param {string} position - 位置类型
 */
function calculateTooltipPosition(position) {
  const tooltipWidth = 400
  const tooltipHeight = 200
  const offset = 16

  switch (position) {
    case 'top':
      tooltipPosition.top = targetPosition.top - tooltipHeight - offset
      tooltipPosition.left = targetPosition.left + targetPosition.width / 2 - tooltipWidth / 2
      break
    case 'bottom':
      tooltipPosition.top = targetPosition.top + targetPosition.height + offset
      tooltipPosition.left = targetPosition.left + targetPosition.width / 2 - tooltipWidth / 2
      break
    case 'left':
      tooltipPosition.top = targetPosition.top + targetPosition.height / 2 - tooltipHeight / 2
      tooltipPosition.left = targetPosition.left - tooltipWidth - offset
      break
    case 'right':
      tooltipPosition.top = targetPosition.top + targetPosition.height / 2 - tooltipHeight / 2
      tooltipPosition.left = targetPosition.left + targetPosition.width + offset
      break
    default:
      // 居中
      tooltipPosition.top = window.innerHeight / 2 - tooltipHeight / 2
      tooltipPosition.left = window.innerWidth / 2 - tooltipWidth / 2
  }

  // 边界检测
  tooltipPosition.top = Math.max(16, Math.min(tooltipPosition.top, window.innerHeight - tooltipHeight - 16))
  tooltipPosition.left = Math.max(16, Math.min(tooltipPosition.left, window.innerWidth - tooltipWidth - 16))
}

/**
 * 保存进度
 */
function saveProgress() {
  try {
    const data = {
      completed: isCompleted.value,
      lastStepIndex: currentStepIndex.value,
      completedAt: Date.now()
    }
    localStorage.setItem(props.storageKey, JSON.stringify(data))
  } catch (error) {
    console.error('[UserGuide] 保存进度失败:', error)
  }
}

/**
 * 加载进度
 */
function loadProgress() {
  try {
    const data = localStorage.getItem(props.storageKey)
    if (data) {
      const parsed = JSON.parse(data)
      isCompleted.value = parsed.completed
      return parsed
    }
  } catch (error) {
    console.error('[UserGuide] 加载进度失败:', error)
  }
  return null
}

/**
 * 重置进度
 */
function resetProgress() {
  isCompleted.value = false
  currentStepIndex.value = 0
  localStorage.removeItem(props.storageKey)
}

/**
 * 显示热点提示
 *
 * @param {Array} hotspotList - 热点列表
 */
function showHotspotTips(hotspotList) {
  hotspots.value = hotspotList
  showHotspots.value = true
}

/**
 * 隐藏热点提示
 */
function hideHotspotTips() {
  showHotspots.value = false
}

/**
 * 键盘事件处理
 *
 * @param {KeyboardEvent} event - 键盘事件
 */
function handleKeydown(event) {
  if (!isVisible.value || !props.keyboardNavigation) return

  switch (event.key) {
    case 'ArrowRight':
    case 'Enter':
      nextStep()
      break
    case 'ArrowLeft':
      prevStep()
      break
    case 'Escape':
      skip()
      break
  }
}

/**
 * 窗口大小变化处理
 */
function handleResize() {
  if (isVisible.value) {
    updatePositions()
  }
}

/**
 * 添加引导步骤
 *
 * @param {Object} step - 步骤配置
 * @param {number} [index] - 插入位置
 */
function addStep(step, index) {
  if (typeof index === 'number' && index >= 0) {
    guideSteps.value.splice(index, 0, step)
  } else {
    guideSteps.value.push(step)
  }
}

/**
 * 移除引导步骤
 *
 * @param {number} index - 步骤索引
 */
function removeStep(index) {
  guideSteps.value.splice(index, 1)
}

// === 生命周期 ===
onMounted(() => {
  // 加载进度
  const progress = loadProgress()

  // 自动开始引导
  if (props.autoStart && !progress?.completed) {
    start()
  }

  // 添加事件监听
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleResize)

  // 移除高亮类
  document.querySelectorAll('.guide-highlight').forEach(el => {
    el.classList.remove('guide-highlight')
  })
})

// 监听步骤变化
watch(currentStepIndex, () => {
  // 移除之前的高亮
  document.querySelectorAll('.guide-highlight').forEach(el => {
    el.classList.remove('guide-highlight')
  })
})

// 暴露方法给父组件
defineExpose({
  start,
  complete,
  skip,
  close,
  nextStep,
  prevStep,
  goToStep,
  resetProgress,
  showHotspotTips,
  hideHotspotTips,
  addStep,
  removeStep
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isVisible"
        class="user-guide-overlay"
      >
        <!-- 遮罩层 -->
        <div class="guide-mask">
          <!-- 高亮区域遮罩 -->
          <div
            v-if="currentStep?.target && currentStep?.highlight"
            class="highlight-mask"
            :style="{
              top: `${maskPosition.top}px`,
              left: `${maskPosition.left}px`,
              width: `${maskPosition.width}px`,
              height: `${maskPosition.height}px`
            }"
          />
        </div>

        <!-- 提示框 -->
        <div
          class="guide-tooltip"
          :class="[`position-${currentStep?.position || 'center'}`]"
          :style="tooltipStyle"
        >
          <!-- 进度条 -->
          <div
            v-if="showProgress"
            class="progress-bar"
          >
            <div
              class="progress-fill"
              :style="{ width: `${progressPercent}%` }"
            />
          </div>

          <!-- 内容区域 -->
          <div class="tooltip-content">
            <!-- 标题 -->
            <h3 class="tooltip-title">
              {{ currentStep?.title }}
            </h3>

            <!-- 图片 -->
            <img
              v-if="currentStep?.image"
              :src="currentStep.image"
              class="tooltip-image"
              alt="引导图片"
            >

            <!-- 描述 -->
            <p class="tooltip-description">
              {{ currentStep?.content }}
            </p>
          </div>

          <!-- 步骤指示器 -->
          <div class="step-indicators">
            <span
              v-for="(step, index) in guideSteps"
              :key="step.id"
              :class="['indicator', { active: index === currentStepIndex, completed: index < currentStepIndex }]"
              @click="goToStep(index)"
            />
          </div>

          <!-- 操作按钮 -->
          <div class="tooltip-actions">
            <button
              v-if="showSkip"
              class="btn skip-btn"
              @click="skip"
            >
              跳过引导
            </button>

            <div class="nav-buttons">
              <button
                v-if="!isFirstStep"
                class="btn prev-btn"
                @click="prevStep"
              >
                上一步
              </button>
              <button
                class="btn next-btn"
                @click="nextStep"
              >
                {{ isLastStep ? '完成' : '下一步' }}
              </button>
            </div>
          </div>

          <!-- 步骤计数 -->
          <div class="step-count">
            {{ currentStepIndex + 1 }} / {{ guideSteps.length }}
          </div>
        </div>

        <!-- 热点提示 -->
        <Transition name="fade">
          <div
            v-if="showHotspots"
            class="hotspots-container"
          >
            <div
              v-for="hotspot in hotspots"
              :key="hotspot.id"
              class="hotspot"
              :style="{
                top: `${hotspot.top}px`,
                left: `${hotspot.left}px`
              }"
            >
              <div class="hotspot-dot" />
              <div class="hotspot-tooltip">
                {{ hotspot.content }}
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped lang="scss">
.user-guide-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2000;
  pointer-events: none;
}

.guide-mask {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  pointer-events: auto;
}

.highlight-mask {
  position: absolute;
  border-radius: 8px;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.7);
  background: transparent;
  pointer-events: none;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.7), 0 0 0 4px var(--primary-color, #1890ff);
  }
  50% {
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.7), 0 0 0 8px var(--primary-color, #1890ff);
  }
}

.guide-tooltip {
  position: absolute;
  width: 400px;
  max-width: 90vw;
  background: var(--bg-color, #fff);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  pointer-events: auto;
  overflow: hidden;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.progress-bar {
  height: 3px;
  background: var(--bg-secondary, #f0f0f0);
}

.progress-fill {
  height: 100%;
  background: var(--primary-color, #1890ff);
  transition: width 0.3s ease;
}

.tooltip-content {
  padding: 24px;
}

.tooltip-title {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color, #262626);
}

.tooltip-image {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 16px;
}

.tooltip-description {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-secondary, #595959);
}

.step-indicators {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 0 24px 16px;
}

.indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-color, #d9d9d9);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--primary-color, #1890ff);
    opacity: 0.7;
  }

  &.active {
    background: var(--primary-color, #1890ff);
    transform: scale(1.2);
  }

  &.completed {
    background: var(--success-color, #52c41a);
  }
}

.tooltip-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color, #e8e8e8);
  background: var(--bg-secondary, #fafafa);
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.skip-btn {
  background: transparent;
  color: var(--text-secondary, #8c8c8c);

  &:hover {
    color: var(--text-color, #262626);
  }
}

.nav-buttons {
  display: flex;
  gap: 8px;
}

.prev-btn {
  background: var(--bg-color, #fff);
  border: 1px solid var(--border-color, #d9d9d9);
  color: var(--text-color, #262626);

  &:hover {
    border-color: var(--primary-color, #1890ff);
    color: var(--primary-color, #1890ff);
  }
}

.next-btn {
  background: var(--primary-color, #1890ff);
  color: #fff;

  &:hover {
    background: #40a9ff;
  }
}

.step-count {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 8px;
  background: var(--bg-secondary, #f0f0f0);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary, #8c8c8c);
}

.hotspots-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.hotspot {
  position: absolute;
  pointer-events: auto;
}

.hotspot-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--primary-color, #1890ff);
  cursor: pointer;
  animation: pulse-dot 1.5s ease-in-out infinite;

  &::before {
    content: '?';
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    color: #fff;
    font-size: 14px;
    font-weight: bold;
  }
}

@keyframes pulse-dot {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(24, 144, 255, 0.4);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 0 10px rgba(24, 144, 255, 0);
  }
}

.hotspot-tooltip {
  position: absolute;
  left: 32px;
  top: 50%;
  transform: translateY(-50%);
  padding: 8px 12px;
  background: var(--bg-color, #fff);
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  font-size: 13px;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s;
}

.hotspot:hover .hotspot-tooltip {
  opacity: 1;
  visibility: visible;
}

// 过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// 全局高亮样式
:deep(.guide-highlight) {
  position: relative;
  z-index: 2001 !important;
}
</style>
