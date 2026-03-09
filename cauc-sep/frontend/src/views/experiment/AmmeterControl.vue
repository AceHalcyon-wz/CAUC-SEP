<template>
  <div class="ammeter-control-page">
    <!-- 页面标题 - 状态指示器位于顶部 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon">
          <Aim />
        </el-icon>
        <div class="header-text">
          <h1 class="page-title">
            微电流测量
          </h1>
          <p class="page-description">
            高精度多通道电流采集与分析
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-tag
          type="info"
          effect="dark"
          size="large"
          class="status-indicator"
        >
          <el-icon><Aim /></el-icon>
          高精度测量
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
        <AmmeterControl class="control-card" />
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
                  <Aim />
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
                  当前电流
                </div>
                <div class="status-value mono highlight">
                  {{ currentCurrent.toFixed(6) }} A
                </div>
              </div>
              <div class="status-item">
                <div class="status-label">
                  采样率
                </div>
                <div class="status-value mono">
                  {{ sampleRate }} S/s
                </div>
              </div>
              <div class="status-item">
                <div class="status-label">
                  工作模式
                </div>
                <el-tag
                  :type="workModeType"
                  size="small"
                >
                  {{ workModeText }}
                </el-tag>
              </div>
              <div class="status-item">
                <div class="status-label">
                  通道数
                </div>
                <div class="status-value mono">
                  {{ channelCount }}
                </div>
              </div>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 测量精度卡片 - 可折叠 -->
        <el-card class="precision-card">
          <template #header>
            <div
              class="card-header"
              @click="togglePrecisionPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <SetUp />
                </el-icon>
                <span class="header-title">测量精度</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': precisionCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!precisionCollapsed">
              <el-descriptions
                :column="1"
                border
                size="small"
              >
                <el-descriptions-item label="分辨率">
                  <span class="mono">{{ resolution }} pA</span>
                </el-descriptions-item>
                <el-descriptions-item label="准确度">
                  <el-tag
                    :type="accuracyType"
                    size="small"
                  >
                    {{ accuracy }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="量程">
                  {{ measurementRange }}
                </el-descriptions-item>
                <el-descriptions-item label="噪声抑制">
                  <el-tag
                    type="success"
                    size="small"
                  >
                    {{ noiseRejection }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
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
 * @file AmmeterControl.vue
 * @path src/views/experiment/
 * @description 微电流测量页面，提供采集控制、通道配置和数据可视化功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed } from 'vue'
import { Aim, SetUp, InfoFilled } from '@element-plus/icons-vue'
import AmmeterControl from '@/components/AmmeterControl.vue'

/** 当前电流 */
const currentCurrent = ref(0)

/** 采样率 */
const sampleRate = ref(1000)

/** 通道数 */
const channelCount = ref(4)

/** 工作模式 */
const workMode = ref('continuous')

/** 分辨率 */
const resolution = ref(10)

/** 准确度 */
const accuracy = ref('0.1%')

/** 量程 */
const measurementRange = ref('100pA - 10mA')

/** 噪声抑制 */
const noiseRejection = ref('> 80dB')

/** 状态面板折叠状态 */
const statusCollapsed = ref(false)

/** 精度面板折叠状态 */
const precisionCollapsed = ref(false)

/** 提示面板折叠状态 */
const tipsCollapsed = ref(false)

/** 工作模式文本 */
const workModeText = computed(() => {
  const modeMap = {
    continuous: '连续采集',
    triggered: '触发采集',
    burst: '突发采集'
  }
  return modeMap[workMode.value] || '未知'
})

/** 工作模式标签类型 */
const workModeType = computed(() => {
  const typeMap = {
    continuous: 'primary',
    triggered: 'success',
    burst: 'warning'
  }
  return typeMap[workMode.value] || 'info'
})

/** 准确度标签类型 */
const accuracyType = computed(() => {
  return 'success'
})

/** 操作提示 */
const operationTips = [
  {
    title: '量程选择',
    type: 'info',
    description: '请根据预期电流大小选择合适的量程'
  },
  {
    title: '屏蔽保护',
    type: 'warning',
    description: '微电流测量时请使用屏蔽线缆避免干扰'
  },
  {
    title: '预热时间',
    type: 'success',
    description: '设备预热30分钟后可达到最佳精度'
  }
]

/**
 * 切换状态面板折叠状态
 */
function toggleStatusPanel() {
  statusCollapsed.value = !statusCollapsed.value
}

/**
 * 切换精度面板折叠状态
 */
function togglePrecisionPanel() {
  precisionCollapsed.value = !precisionCollapsed.value
}

/**
 * 切换提示面板折叠状态
 */
function toggleTipsPanel() {
  tipsCollapsed.value = !tipsCollapsed.value
}
</script>

<style scoped lang="scss">
.ammeter-control-page {
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
.precision-card,
.tips-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
  background: var(--color-surface-primary);
  border: none;
}

.control-card:hover,
.status-card:hover,
.precision-card:hover,
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
  .ammeter-control-page {
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
  .ammeter-control-page {
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
}
</style>
