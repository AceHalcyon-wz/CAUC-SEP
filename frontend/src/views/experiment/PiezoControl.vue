<template>
  <div class="piezo-control-page">
    <!-- 页面标题 - 状态指示器位于顶部 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon">
          <Cpu />
        </el-icon>
        <div class="header-text">
          <h1 class="page-title">
            压电陶瓷控制
          </h1>
          <p class="page-description">
            纳米级精密位移控制与校准
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-tag
          :type="connectionStatusType"
          effect="dark"
          size="large"
          class="status-indicator"
        >
          <el-icon><Cpu /></el-icon>
          {{ connectionStatusText }}
        </el-tag>
      </div>
    </div>

    <!-- 主内容区域 - 左右分栏布局 -->
    <el-row
      :gutter="24"
      class="content-row"
    >
      <!-- 左侧：控制面板 -->
      <el-col
        :xs="24"
        :lg="12"
        class="control-col"
      >
        <PiezoControlPanel class="control-card" />
      </el-col>

      <!-- 右侧：实时数据展示区域（支持折叠） -->
      <el-col
        :xs="24"
        :lg="12"
        class="info-col"
      >
        <!-- 实时状态卡片 - 可折叠 -->
        <el-card class="status-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleStatusPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <DataLine />
                </el-icon>
                <span class="header-title">实时状态</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': statusCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div
              v-show="!statusCollapsed"
              class="status-grid"
            >
              <div class="status-item">
                <div class="status-label">
                  当前电压
                </div>
                <div class="status-value mono">
                  {{ store.currentVoltage.toFixed(2) }} V
                </div>
              </div>
              <div class="status-item">
                <div class="status-label">
                  当前位移
                </div>
                <div class="status-value mono highlight">
                  {{ store.currentDisplacement.toFixed(3) }} nm
                </div>
              </div>
              <div class="status-item">
                <div class="status-label">
                  控制模式
                </div>
                <el-tag
                  :type="controlModeType"
                  size="small"
                >
                  {{ controlModeText }}
                </el-tag>
              </div>
              <div class="status-item">
                <div class="status-label">
                  校准状态
                </div>
                <el-tag
                  :type="calibrationStatusType"
                  size="small"
                >
                  {{ calibrationStatusText }}
                </el-tag>
              </div>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 校准信息卡片 - 可折叠 -->
        <el-card class="calibration-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleCalibrationPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <SetUp />
                </el-icon>
                <span class="header-title">校准信息</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': calibrationCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!calibrationCollapsed">
              <el-descriptions
                :column="1"
                border
                size="small"
              >
                <el-descriptions-item label="校准系数">
                  <span class="mono">{{ calibrationCoefficient }}</span>
                </el-descriptions-item>
                <el-descriptions-item label="R² 拟合度">
                  <el-tag
                    :type="r2StatusType"
                    size="small"
                  >
                    {{ r2Value }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="校准点数">
                  {{ calibrationPointCount }}
                </el-descriptions-item>
                <el-descriptions-item label="上次校准">
                  {{ lastCalibrationDate }}
                </el-descriptions-item>
                <el-descriptions-item label="校准状态">
                  <el-tag
                    :type="calibrationStatusType"
                    size="small"
                  >
                    {{ calibrationStatusText }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>

              <!-- 校准数据导出按钮 -->
              <div class="export-actions">
                <el-button
                  type="primary"
                  size="small"
                  :disabled="!store.isCalibrated"
                  @click="exportCalibrationCSV"
                >
                  <el-icon><Download /></el-icon>
                  导出CSV
                </el-button>
                <el-button
                  type="success"
                  size="small"
                  :disabled="!store.isCalibrated"
                  @click="exportCalibrationJSON"
                >
                  <el-icon><Document /></el-icon>
                  导出JSON
                </el-button>
              </div>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 快捷操作卡片 - 可折叠 -->
        <el-card class="actions-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleActionsPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <Operation />
                </el-icon>
                <span class="header-title">快捷操作</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': actionsCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div
              v-show="!actionsCollapsed"
              class="quick-actions"
            >
              <el-button
                type="warning"
                size="large"
                :loading="store.loading.zero"
                :disabled="!store.canControl"
                @click="handleZero"
              >
                <el-icon><RefreshLeft /></el-icon>
                归零
              </el-button>
              <el-button
                type="danger"
                size="large"
                :loading="store.loading.maxExtend"
                :disabled="!store.canControl"
                @click="handleMaxExtend"
              >
                <el-icon><TopRight /></el-icon>
                最大伸展
              </el-button>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 操作提示卡片 - 可折叠 -->
        <el-card class="tips-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleTipsPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <InfoFilled />
                </el-icon>
                <span class="header-title">操作提示</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': tipsCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!tipsCollapsed">
              <el-alert
                v-for="(tip, index) in operationTips"
                :key="index"
                :title="tip.title"
                :type="tip.type"
                :description="tip.description"
                :closable="false"
                show-icon
                class="tip-alert"
              />
            </div>
          </el-collapse-transition>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * @file PiezoControl.vue
 * @path src/views/experiment/
 * @description 压电陶瓷控制页面，提供电压控制、校准和数据可视化功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, stores/piezo, components/experiment/piezo
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Cpu,
  DataLine,
  SetUp,
  InfoFilled,
  ArrowDown,
  Download,
  Document,
  Operation,
  RefreshLeft,
  TopRight
} from '@element-plus/icons-vue'
import { PiezoControl as PiezoControlPanel } from '@/components/experiment/piezo'
import { usePiezoStore } from '@/stores/piezo'
import { ElMessage } from 'element-plus'

// ==================== Store 引入 ====================

/** 压电陶瓷控制器Store */
const store = usePiezoStore()

// ==================== 面板折叠状态 ====================

/** 状态面板折叠状态 */
const statusCollapsed = ref(false)

/** 校准面板折叠状态 */
const calibrationCollapsed = ref(false)

/** 操作面板折叠状态 */
const actionsCollapsed = ref(false)

/** 提示面板折叠状态 */
const tipsCollapsed = ref(false)

// ==================== 计算属性 ====================

/** 连接状态文本 */
const connectionStatusText = computed(() => {
  if (store.isConnecting) return '连接中...'
  if (store.isConnected) return '已连接'
  return '未连接'
})

/** 连接状态标签类型 */
const connectionStatusType = computed(() => {
  if (store.isConnecting) return 'warning'
  if (store.isConnected) return 'success'
  return 'danger'
})

/** 控制模式文本 */
const controlModeText = computed(() => {
  const modeMap = {
    voltage: '电压控制',
    displacement: '位移控制'
  }
  return modeMap[store.controlMode] || '未知'
})

/** 控制模式标签类型 */
const controlModeType = computed(() => {
  const typeMap = {
    voltage: 'primary',
    displacement: 'success'
  }
  return typeMap[store.controlMode] || 'info'
})

/** 校准状态文本 */
const calibrationStatusText = computed(() => {
  const statusMap = {
    idle: '未校准',
    calibrating: '校准中',
    completed: '已校准',
    error: '校准错误'
  }

  if (store.isCalibrated) {
    return '已校准'
  }
  return statusMap[store.calibrationStatus] || '未知'
})

/** 校准状态标签类型 */
const calibrationStatusType = computed(() => {
  if (store.isCalibrated) return 'success'
  if (store.calibrationStatus === 'calibrating') return 'warning'
  if (store.calibrationStatus === 'error') return 'danger'
  return 'info'
})

/** 校准系数显示 */
const calibrationCoefficient = computed(() => {
  if (!store.isCalibrated || !store.calibrationData.coefficients) {
    return '未校准'
  }

  const coef = store.calibrationData.coefficients
  if (coef.type === 'linear') {
    return `${coef.a.toFixed(4)} nm/V + ${coef.b.toFixed(4)}`
  }
  return '多项式拟合'
})

/** R²值 */
const r2Value = computed(() => {
  const r2 = store.calculateR2()
  return r2.toFixed(4)
})

/** R²状态类型 */
const r2StatusType = computed(() => {
  const r2 = store.calculateR2()
  if (r2 >= 0.99) return 'success'
  if (r2 >= 0.95) return 'warning'
  return 'danger'
})

/** 校准点数 */
const calibrationPointCount = computed(() => {
  return store.calibrationData.points.length
})

/** 上次校准日期 */
const lastCalibrationDate = computed(() => {
  const timestamp = store.calibrationData.lastCalibrated
  if (!timestamp) return '从未校准'

  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
})

// ==================== 数据 ====================

/** 操作提示 */
const operationTips = [
  {
    title: '电压范围',
    type: 'info',
    description: `工作电压范围: ${store.voltageLimits.min}-${store.voltageLimits.max}V，请勿超出范围`
  },
  {
    title: '位移控制',
    type: 'warning',
    description: '位移控制模式需要先完成校准，确保校准系数准确'
  },
  {
    title: '校准周期',
    type: 'success',
    description: '建议每30天进行一次校准以确保精度'
  }
]

// ==================== 方法 ====================

/**
 * 切换状态面板折叠状态
 */
function toggleStatusPanel() {
  statusCollapsed.value = !statusCollapsed.value
}

/**
 * 切换校准面板折叠状态
 */
function toggleCalibrationPanel() {
  calibrationCollapsed.value = !calibrationCollapsed.value
}

/**
 * 切换操作面板折叠状态
 */
function toggleActionsPanel() {
  actionsCollapsed.value = !actionsCollapsed.value
}

/**
 * 切换提示面板折叠状态
 */
function toggleTipsPanel() {
  tipsCollapsed.value = !tipsCollapsed.value
}

/**
 * 导出校准数据为CSV
 */
function exportCalibrationCSV() {
  store.downloadCalibrationFile('csv', `calibration_${Date.now()}`)
  ElMessage.success('校准数据已导出为CSV格式')
}

/**
 * 导出校准数据为JSON
 */
function exportCalibrationJSON() {
  store.downloadCalibrationFile('json', `calibration_${Date.now()}`)
  ElMessage.success('校准数据已导出为JSON格式')
}

/**
 * 处理归零操作
 */
async function handleZero() {
  const success = await store.zero()
  if (success) {
    ElMessage.success('归零成功')
  }
}

/**
 * 处理最大伸展操作
 */
async function handleMaxExtend() {
  const success = await store.maxExtend()
  if (success) {
    ElMessage.success('最大伸展完成')
  }
}

// ==================== 生命周期 ====================

/**
 * 组件挂载时初始化
 */
onMounted(() => {
  store.init()
})

/**
 * 组件卸载时清理资源
 */
onUnmounted(() => {
  store.cleanup()
})
</script>

<style scoped lang="scss">
.piezo-control-page {
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
  color: var(--color-info);
  padding: var(--spacing-3);
  background-color: var(--color-info-light);
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
.content-row {
  margin: 0;
}

.control-col,
.info-col {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-5);
}

/* ==================== 卡片样式 ==================== */
.control-card,
.status-card,
.calibration-card,
.actions-card,
.tips-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
  background: var(--color-surface-primary);
  border: none;
}

.control-card:hover,
.status-card:hover,
.calibration-card:hover,
.actions-card:hover,
.tips-card:hover {
  box-shadow: var(--shadow-lg);
}

/* 卡片头部 */
:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-4) var(--spacing-6);
  cursor: pointer;
  user-select: none;
  transition: var(--transition-all);
}

:deep(.el-card__header:hover) {
  background-color: var(--color-bg-tertiary);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-2);
}

.header-left-section {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.header-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* 折叠图标 */
.collapse-icon {
  font-size: var(--font-size-lg);
  color: var(--color-text-tertiary);
  transition: var(--transition-transform);
}

.collapse-icon.is-collapsed {
  transform: rotate(-90deg);
}

/* ==================== 状态网格 ==================== */
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-4);
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  padding: var(--spacing-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-primary-500);
  transition: var(--transition-all);
}

.status-item:hover {
  background-color: var(--color-bg-tertiary);
  transform: translateX(4px);
}

.status-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--font-weight-medium);
}

.status-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.status-value.highlight {
  color: var(--color-primary-500);
}

.mono {
  font-family: var(--font-family-mono);
}

/* ==================== 导出操作按钮 ==================== */
.export-actions {
  display: flex;
  gap: var(--spacing-3);
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
}

/* ==================== 快捷操作 ==================== */
.quick-actions {
  display: flex;
  gap: var(--spacing-4);
  justify-content: center;
  padding: var(--spacing-4);
}

.quick-actions .el-button {
  flex: 1;
  max-width: 150px;
}

/* ==================== 提示 ==================== */
.tip-alert {
  margin-bottom: var(--spacing-3);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.tip-alert:hover {
  transform: translateX(4px);
}

.tip-alert:last-child {
  margin-bottom: 0;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1024px) {
  .piezo-control-page {
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

  .control-col,
  .info-col {
    margin-bottom: var(--spacing-5);
  }
}

@media (max-width: 768px) {
  .piezo-control-page {
    padding: var(--spacing-3);
  }

  .page-header {
    padding: var(--spacing-4);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .control-col,
  .info-col {
    gap: var(--spacing-4);
  }

  .status-grid {
    grid-template-columns: 1fr;
  }

  .status-value {
    font-size: var(--font-size-lg);
  }

  .status-indicator {
    padding: var(--spacing-1) var(--spacing-3);
    font-size: var(--font-size-xs);
  }

  .quick-actions {
    flex-direction: column;
    align-items: center;
  }

  .quick-actions .el-button {
    max-width: 100%;
    width: 100%;
  }

  .export-actions {
    flex-direction: column;
  }
}
</style>
