<template>
  <el-card class="temperature-control">
    <template #header>
      <div class="card-header">
        <div class="header-title">
          <el-icon class="header-icon">
            <Thermometer />
          </el-icon>
          <span>温度控制面板</span>
        </div>
        <div class="header-actions">
          <!-- 紧急停止按钮 -->
          <el-button
            v-if="tempStore.status === 'emergency_stop'"
            type="warning"
            size="small"
            :loading="tempStore.loading.resetEmergency"
            class="emergency-reset-btn"
            @click="handleResetEmergencyStop"
          >
            <el-icon><RefreshRight /></el-icon>
            复位急停
          </el-button>
          <el-button
            v-else
            type="danger"
            size="small"
            class="emergency-stop-btn"
            :disabled="!tempStore.isConnected || !tempStore.canControl"
            @click="handleEmergencyStop"
          >
            <el-icon><WarningFilled /></el-icon>
            紧急停止
          </el-button>
          <div
            class="connection-badge"
            :class="connectionBadgeClass"
          >
            <span class="badge-dot" />
            {{ connectionStatus.text }}
          </div>
        </div>
      </div>
    </template>

    <!-- 急停状态警告 -->
    <el-alert
      v-if="tempStore.status === 'emergency_stop'"
      title="紧急停止已激活"
      type="error"
      :closable="false"
      show-icon
      class="emergency-alert"
    >
      温度控制系统已紧急停止，所有加热输出已关闭。请检查设备状态后复位。
    </el-alert>

    <div class="control-content">
      <!-- 温度状态卡片 -->
      <div class="temp-status-cards">
        <div
          class="status-card status-card--current"
          :class="{ 'status-card--active': tempStore.isHeating }"
        >
          <div class="card-glow" />
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Thermometer /></el-icon>
            </div>
            <div class="card-body">
              <div class="temp-display">
                <span class="temp-value mono">{{ formatTempValue(tempStore.currentTemp) }}</span>
                <span class="temp-unit">K</span>
              </div>
              <div class="temp-celsius mono">
                {{ tempStore.kelvinToCelsius(tempStore.currentTemp).toFixed(1) }}°C
              </div>
              <div class="card-label">
                当前温度
              </div>
            </div>
            <div
              class="status-indicator"
              :class="statusIndicatorClass"
            >
              <span class="indicator-dot" />
              {{ tempStore.tempStatusText }}
            </div>
          </div>
        </div>

        <div class="status-card status-card--target">
          <div class="card-glow" />
          <div class="card-content">
            <div class="card-icon card-icon--target">
              <el-icon><Aim /></el-icon>
            </div>
            <div class="card-body">
              <div class="temp-display">
                <span class="temp-value mono">{{ formatTempValue(tempStore.targetTemp) }}</span>
                <span class="temp-unit">K</span>
              </div>
              <div class="temp-celsius mono">
                {{ tempStore.kelvinToCelsius(tempStore.targetTemp).toFixed(1) }}°C
              </div>
              <div class="card-label">
                目标温度
              </div>
            </div>
            <div
              class="status-indicator"
              :class="tempStore.isHeating ? 'status-indicator--heating' : 'status-indicator--standby'"
            >
              <span class="indicator-dot" />
              {{ tempStore.isHeating ? '加热中' : '待机' }}
            </div>
          </div>
        </div>

        <div class="status-card status-card--rate">
          <div class="card-glow" />
          <div class="card-content">
            <div class="card-icon card-icon--rate">
              <el-icon><Odometer /></el-icon>
            </div>
            <div class="card-body">
              <div class="temp-display">
                <span class="temp-value mono">{{ tempStore.heatingRate.toFixed(2) }}</span>
                <span class="temp-unit">K/s</span>
              </div>
              <div class="temp-celsius">
                升温速率
              </div>
              <div class="card-label">
                实时监测
              </div>
            </div>
            <div class="power-indicator">
              <div class="power-bar">
                <div
                  class="power-fill"
                  :style="{ width: `${tempStore.outputPower}%` }"
                />
              </div>
              <span class="power-text mono">{{ tempStore.outputPower.toFixed(1) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 温度曲线图表 -->
      <div class="chart-section">
        <div class="section-header">
          <span class="section-title">温度曲线实时显示</span>
          <div class="chart-legend">
            <span class="legend-item legend-item--current">
              <span class="legend-dot" />当前温度
            </span>
            <span class="legend-item legend-item--target">
              <span class="legend-dot" />目标温度
            </span>
          </div>
        </div>
        <div class="chart-container">
          <VChart
            ref="tempChart"
            :option="chartOption"
            :autoresize="true"
            class="temp-chart"
          />
        </div>
      </div>

      <!-- 目标温度设置 -->
      <div class="control-section">
        <div class="section-header">
          <span class="section-title">目标温度设置</span>
          <el-tag
            v-if="tempValidationMessage"
            :type="tempValidation.valid ? 'success' : 'danger'"
            size="small"
          >
            {{ tempValidationMessage }}
          </el-tag>
        </div>
        <div class="control-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">目标温度</label>
              <div class="input-wrapper">
                <el-input-number
                  v-model="tempForm.targetTemp"
                  :min="tempStore.tempLimits.min"
                  :max="tempStore.tempLimits.max"
                  :precision="1"
                  :step="1"
                  class="temp-input"
                  @change="handleTempChange"
                />
                <span class="input-unit">
                  K <span class="unit-hint">({{ tempStore.kelvinToCelsius(tempForm.targetTemp).toFixed(1) }}°C)</span>
                </span>
              </div>
              <div class="temp-range-hint">
                有效范围: {{ tempStore.tempLimits.min }}K - {{ tempStore.tempLimits.max }}K
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">升温速率</label>
              <div class="input-wrapper">
                <el-input-number
                  v-model="tempForm.heatingRate"
                  :min="0.1"
                  :max="10"
                  :precision="1"
                  :step="0.5"
                  class="temp-input"
                />
                <span class="input-unit">K/min</span>
              </div>
            </div>
          </div>

          <div class="form-actions">
            <el-button
              type="primary"
              :disabled="!tempStore.canControl || !tempValidation.valid"
              :loading="tempStore.loading.setTemp"
              class="action-btn action-btn--primary"
              @click="handleSetTargetTemp"
            >
              <el-icon><Check /></el-icon>
              应用设置
            </el-button>
            <el-button
              :disabled="!tempStore.canControl"
              class="action-btn action-btn--secondary"
              @click="handleStopHeating"
            >
              <el-icon><Close /></el-icon>
              停止加热
            </el-button>
          </div>
        </div>
      </div>

      <!-- PID 参数配置 -->
      <div class="control-section">
        <div class="section-header">
          <span class="section-title">PID 参数配置</span>
          <div class="pid-status">
            <el-tag
              v-if="pidValidationResult"
              :type="pidValidationResult.valid ? 'success' : 'warning'"
              size="small"
            >
              {{ pidValidationResult.valid ? '参数有效' : pidValidationResult.message }}
            </el-tag>
          </div>
        </div>
        <div class="pid-grid">
          <div class="pid-item">
            <label class="form-label">比例系数 Kp</label>
            <el-input-number
              v-model="pidForm.kp"
              :min="0"
              :max="100"
              :precision="2"
              :step="0.5"
              class="pid-input"
            />
          </div>
          <div class="pid-item">
            <label class="form-label">积分系数 Ki</label>
            <el-input-number
              v-model="pidForm.ki"
              :min="0"
              :max="10"
              :precision="3"
              :step="0.1"
              class="pid-input"
            />
          </div>
          <div class="pid-item">
            <label class="form-label">微分系数 Kd</label>
            <el-input-number
              v-model="pidForm.kd"
              :min="0"
              :max="50"
              :precision="2"
              :step="0.5"
              class="pid-input"
            />
          </div>
        </div>
        <div class="form-actions">
          <el-button
            type="primary"
            :disabled="!tempStore.canControl"
            :loading="tempStore.loading.pidConfig"
            class="action-btn action-btn--primary"
            @click="handleConfigurePID"
          >
            <el-icon><Setting /></el-icon>
            应用 PID 参数
          </el-button>
          <el-button
            :loading="tempStore.loading.validatePID"
            class="action-btn action-btn--secondary"
            @click="handleValidatePID"
          >
            <el-icon><Check /></el-icon>
            验证参数
          </el-button>
          <el-button
            class="action-btn action-btn--secondary"
            @click="handleResetPID"
          >
            <el-icon><RefreshRight /></el-icon>
            重置默认值
          </el-button>
          <el-button
            v-if="!pidControlActive"
            type="success"
            :disabled="!tempStore.canControl"
            :loading="tempStore.loading.startPID"
            class="action-btn action-btn--success"
            @click="handleStartPIDControl"
          >
            <el-icon><VideoPlay /></el-icon>
            启动PID
          </el-button>
          <el-button
            v-else
            type="warning"
            :loading="tempStore.loading.stopPID"
            class="action-btn action-btn--warning"
            @click="handleStopPIDControl"
          >
            <el-icon><VideoPause /></el-icon>
            停止PID
          </el-button>
        </div>
      </div>

      <!-- 程序控温 -->
      <div class="control-section">
        <div class="section-header">
          <span class="section-title">程序控温</span>
        </div>
        <el-tabs
          v-model="activeProgramTab"
          type="border-card"
          class="program-tabs"
        >
          <!-- 程序列表 -->
          <el-tab-pane
            label="程序列表"
            name="list"
          >
            <div class="program-list">
              <el-table
                :data="tempStore.programCurves"
                style="width: 100%"
                class="program-table"
                @row-click="handleSelectProgram"
              >
                <el-table-column
                  prop="name"
                  label="程序名称"
                  width="200"
                />
                <el-table-column
                  prop="segments"
                  label="段数"
                  width="80"
                >
                  <template #default="{ row }">
                    {{ row.segments ? row.segments.length : 0 }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="duration"
                  label="总时长"
                  width="120"
                >
                  <template #default="{ row }">
                    {{ calculateTotalDuration(row.segments) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="description"
                  label="描述"
                />
                <el-table-column
                  label="操作"
                  width="200"
                >
                  <template #default="{ row }">
                    <el-button
                      type="success"
                      size="small"
                      :disabled="!tempStore.canControl || tempStore.isProgramRunning"
                      @click.stop="handleStartProgram(row.id)"
                    >
                      运行
                    </el-button>
                    <el-button
                      type="danger"
                      size="small"
                      @click.stop="handleDeleteProgram(row.id)"
                    >
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>

              <!-- 程序控制按钮 -->
              <div
                v-if="tempStore.isProgramRunning"
                class="program-control"
              >
                <el-progress
                  :percentage="tempStore.programProgress"
                  :status="tempStore.programStatus === 'paused' ? 'warning' : ''"
                  class="program-progress"
                />
                <div class="control-buttons">
                  <el-button
                    v-if="tempStore.programStatus === 'running'"
                    type="warning"
                    @click="handlePauseProgram"
                  >
                    <el-icon><VideoPause /></el-icon>
                    暂停
                  </el-button>
                  <el-button
                    v-if="tempStore.programStatus === 'paused'"
                    type="success"
                    @click="handleResumeProgram"
                  >
                    <el-icon><VideoPlay /></el-icon>
                    恢复
                  </el-button>
                  <el-button
                    type="danger"
                    @click="handleStopProgram"
                  >
                    <el-icon><Close /></el-icon>
                    停止
                  </el-button>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 创建程序 -->
          <el-tab-pane
            label="创建程序"
            name="create"
          >
            <el-form
              :model="programForm"
              label-width="120px"
              class="program-form"
            >
              <el-form-item label="程序名称">
                <el-input
                  v-model="programForm.name"
                  placeholder="请输入程序名称"
                  style="width: 300px"
                />
              </el-form-item>

              <el-form-item label="程序描述">
                <el-input
                  v-model="programForm.description"
                  type="textarea"
                  :rows="2"
                  placeholder="请输入程序描述"
                  style="width: 500px"
                />
              </el-form-item>

              <!-- 温度段列表 -->
              <el-form-item label="温度段">
                <div class="segment-list">
                  <el-table
                    :data="programForm.segments"
                    border
                    style="width: 100%"
                  >
                    <el-table-column
                      type="index"
                      label="序号"
                      width="60"
                    />
                    <el-table-column
                      label="段类型"
                      width="120"
                    >
                      <template #default="{ row }">
                        <el-select
                          v-model="row.type"
                          size="small"
                          placeholder="选择类型"
                        >
                          <el-option
                            label="升温段"
                            value="heat"
                          >
                            <el-icon><Top /></el-icon>
                            <span style="margin-left: 5px;">升温段</span>
                          </el-option>
                          <el-option
                            label="恒温段"
                            value="hold"
                          >
                            <el-icon><Minus /></el-icon>
                            <span style="margin-left: 5px;">恒温段</span>
                          </el-option>
                          <el-option
                            label="降温段"
                            value="cool"
                          >
                            <el-icon><Bottom /></el-icon>
                            <span style="margin-left: 5px;">降温段</span>
                          </el-option>
                        </el-select>
                      </template>
                    </el-table-column>
                    <el-table-column
                      label="目标温度 (K)"
                      width="150"
                    >
                      <template #default="{ row }">
                        <el-input-number
                          v-model="row.targetTemp"
                          :min="tempStore.tempLimits.min"
                          :max="tempStore.tempLimits.max"
                          :precision="1"
                          size="small"
                        />
                      </template>
                    </el-table-column>
                    <el-table-column
                      label="持续时间 (min)"
                      width="150"
                    >
                      <template #default="{ row }">
                        <el-input-number
                          v-model="row.duration"
                          :min="0"
                          :max="1000"
                          :precision="1"
                          size="small"
                          :disabled="row.type === 'heat' || row.type === 'cool'"
                        />
                      </template>
                    </el-table-column>
                    <el-table-column
                      label="速率 (K/min)"
                      width="150"
                    >
                      <template #default="{ row }">
                        <el-input-number
                          v-model="row.rate"
                          :min="0.1"
                          :max="20"
                          :precision="1"
                          size="small"
                          :disabled="row.type === 'hold'"
                        />
                      </template>
                    </el-table-column>
                    <el-table-column
                      label="操作"
                      width="120"
                    >
                      <template #default="{ $index }">
                        <el-button
                          type="danger"
                          size="small"
                          :disabled="programForm.segments.length <= 1"
                          @click="handleRemoveSegment($index)"
                        >
                          删除
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>

                  <el-button
                    type="primary"
                    size="small"
                    class="add-segment-btn"
                    @click="handleAddSegment"
                  >
                    <el-icon><Plus /></el-icon>
                    添加温度段
                  </el-button>
                </div>
              </el-form-item>

              <!-- 程序预览图 -->
              <el-form-item label="程序预览">
                <div class="preview-chart-container">
                  <VChart
                    :option="previewChartOption"
                    :autoresize="true"
                    class="preview-chart"
                  />
                </div>
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="tempStore.loading.createProgram"
                  @click="handleCreateProgram"
                >
                  <el-icon><Check /></el-icon>
                  创建程序
                </el-button>
                <el-button @click="handleResetProgramForm">
                  <el-icon><RefreshRight /></el-icon>
                  重置
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 温度保护配置 -->
      <div class="control-section">
        <div class="section-header">
          <span class="section-title">温度保护配置</span>
        </div>
        <div class="protection-grid">
          <div class="protection-item">
            <label class="form-label">最高温度限制 (K)</label>
            <el-input-number
              v-model="protectionForm.maxTemp"
              :min="tempStore.tempLimits.min"
              :max="tempStore.tempLimits.max"
              :precision="1"
              :step="10"
              class="protection-input"
            />
            <span class="input-hint">{{ tempStore.kelvinToCelsius(protectionForm.maxTemp).toFixed(1) }}°C</span>
          </div>
          <div class="protection-item">
            <label class="form-label">最低温度限制 (K)</label>
            <el-input-number
              v-model="protectionForm.minTemp"
              :min="tempStore.tempLimits.min"
              :max="tempStore.tempLimits.max"
              :precision="1"
              :step="10"
              class="protection-input"
            />
            <span class="input-hint">{{ tempStore.kelvinToCelsius(protectionForm.minTemp).toFixed(1) }}°C</span>
          </div>
          <div class="protection-item protection-item--switch">
            <label class="form-label">超温自动关机</label>
            <el-switch
              v-model="protectionForm.enableShutdown"
              active-text="启用"
              inactive-text="禁用"
            />
          </div>
        </div>
        <div class="form-actions">
          <el-button
            type="primary"
            :disabled="!tempStore.canControl"
            :loading="tempStore.loading.setProtection"
            class="action-btn action-btn--primary"
            @click="handleSetProtection"
          >
            <el-icon><Shield /></el-icon>
            应用保护配置
          </el-button>
          <el-button
            :disabled="!tempStore.canControl"
            class="action-btn action-btn--secondary"
            @click="handleClearProtectionStatus"
          >
            <el-icon><RefreshRight /></el-icon>
            清除保护状态
          </el-button>
        </div>
      </div>

      <!-- 历史记录管理 -->
      <div class="control-section">
        <div class="section-header">
          <span class="section-title">历史记录管理</span>
          <div class="history-actions">
            <el-button
              size="small"
              @click="handleFetchHistory"
            >
              <el-icon><Refresh /></el-icon>
              刷新历史
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleClearHistory"
            >
              <el-icon><Delete /></el-icon>
              清除历史
            </el-button>
          </div>
        </div>
        <div class="history-info">
          <span class="history-count">当前数据点: {{ tempStore.tempHistory.length }}</span>
          <span class="history-max">最大容量: {{ maxHistoryPoints }}</span>
        </div>
        <div class="form-actions">
          <el-button
            type="primary"
            :disabled="tempStore.tempHistory.length === 0"
            class="action-btn action-btn--primary"
            @click="handleExportHistory('csv')"
          >
            <el-icon><Download /></el-icon>
            导出 CSV
          </el-button>
          <el-button
            type="success"
            :disabled="tempStore.tempHistory.length === 0"
            class="action-btn action-btn--secondary"
            @click="handleExportHistory('json')"
          >
            <el-icon><Download /></el-icon>
            导出 JSON
          </el-button>
        </div>
      </div>

      <!-- 连接控制 -->
      <div class="connection-section">
        <el-button
          v-if="!tempStore.isConnected"
          type="primary"
          :loading="tempStore.isConnecting"
          class="connect-btn connect-btn--connect"
          @click="handleConnect"
        >
          <el-icon><Link /></el-icon>
          连接温控器
        </el-button>
        <el-button
          v-else
          type="danger"
          class="connect-btn connect-btn--disconnect"
          @click="handleDisconnect"
        >
          <el-icon><Disconnect /></el-icon>
          断开连接
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file TemperatureControl.vue
 * @path src/components/
 * @description 温度控制面板组件，实现目标温度设置、PID参数配置、程序控温曲线编辑和温度曲线实时显示
 * @author Agent
 * @date 2024-03-07
 */

import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useTemperatureStore } from '../stores/temperature'
import { ElMessage, ElMessageBox } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent
])

// ============ Store ============
const tempStore = useTemperatureStore()

// ============ Refs ============
const tempChart = ref(null)
const activeProgramTab = ref('list')

// ============ 响应式状态 ============

/** 温度设置表单 */
const tempForm = reactive({
  targetTemp: 298.15,
  heatingRate: 2.0
})

/** PID 参数表单 */
const pidForm = reactive({
  kp: 10.0,
  ki: 0.5,
  kd: 2.0
})

/** 程序创建表单 */
const programForm = reactive({
  name: '',
  description: '',
  segments: [
    { type: 'heat', targetTemp: 300, duration: 0, rate: 5 },
    { type: 'hold', targetTemp: 300, duration: 30, rate: 0 },
    { type: 'cool', targetTemp: 100, duration: 0, rate: 3 }
  ]
})

/** 温度保护配置表单 */
const protectionForm = reactive({
  maxTemp: 380,
  minTemp: 85,
  enableShutdown: true
})

/** PID 验证结果 */
const pidValidationResult = ref(null)

/** PID 控制是否激活 */
const pidControlActive = ref(false)

/** 温度历史最大点数 */
const maxHistoryPoints = 500

// ============ 计算属性 ============

/** 温度验证结果 */
const tempValidation = computed(() => {
  return tempStore.validateTemperature(tempForm.targetTemp)
})

/** 温度验证消息 */
const tempValidationMessage = computed(() => {
  if (!tempValidation.value.valid) {
    return tempValidation.value.message
  }
  return ''
})

/** 连接状态 */
const connectionStatus = computed(() => {
  if (tempStore.isConnected) {
    return { type: 'success', text: '已连接' }
  } else if (tempStore.isConnecting) {
    return { type: 'warning', text: '连接中...' }
  } else {
    return { type: 'danger', text: '未连接' }
  }
})

/** 连接状态徽章样式 */
const connectionBadgeClass = computed(() => {
  if (tempStore.isConnected) return 'connection-badge--connected'
  if (tempStore.isConnecting) return 'connection-badge--connecting'
  return 'connection-badge--disconnected'
})

/** 状态指示器样式 */
const statusIndicatorClass = computed(() => {
  if (tempStore.isHeating) return 'status-indicator--heating'
  if (tempStore.tempStatusType === 'success') return 'status-indicator--stable'
  if (tempStore.tempStatusType === 'warning') return 'status-indicator--warning'
  return 'status-indicator--normal'
})

/**
 * 格式化温度数值显示
 * @param {number} temp - 温度值
 * @returns {string} 格式化后的温度值
 */
function formatTempValue(temp) {
  return temp.toFixed(2)
}

/** 温度曲线图表配置 */
const chartOption = computed(() => ({
  title: {
    show: false
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'cross',
      crossStyle: {
        color: 'var(--color-neutral-400)'
      }
    },
    backgroundColor: 'var(--color-surface-elevated)',
    borderColor: 'var(--color-border-primary)',
    borderWidth: 1,
    textStyle: {
      color: 'var(--color-text-primary)',
      fontFamily: 'var(--font-family-mono)'
    },
    formatter: (params) => {
      let result = `<div style="font-weight: 600; margin-bottom: 4px;">时间: ${new Date(params[0].value[0]).toLocaleTimeString()}</div>`
      params.forEach(param => {
        const tempK = param.value[1]
        const tempC = tempStore.kelvinToCelsius(tempK)
        result += `<div style="display: flex; align-items: center; gap: 8px;">
          <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: ${param.color};"></span>
          <span>${param.seriesName}: <span style="font-family: var(--font-family-mono); font-weight: 600;">${tempK.toFixed(2)}K</span> <span style="color: var(--color-text-tertiary);">(${tempC.toFixed(2)}°C)</span></span>
        </div>`
      })
      return result
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '15%',
    top: '10%',
    containLabel: true
  },
  xAxis: {
    type: 'time',
    splitLine: {
      show: false
    },
    axisLine: {
      lineStyle: {
        color: 'var(--color-border-primary)'
      }
    },
    axisLabel: {
      color: 'var(--color-text-secondary)',
      fontFamily: 'var(--font-family-mono)',
      formatter: (value) => {
        const date = new Date(value)
        return `${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
      }
    }
  },
  yAxis: {
    type: 'value',
    name: '温度 (K)',
    nameTextStyle: {
      color: 'var(--color-text-secondary)',
      fontFamily: 'var(--font-family-sans)'
    },
    splitLine: {
      lineStyle: {
        color: 'var(--color-border-secondary)',
        type: 'dashed'
      }
    },
    axisLine: {
      show: false
    },
    axisLabel: {
      color: 'var(--color-text-secondary)',
      fontFamily: 'var(--font-family-mono)'
    }
  },
  dataZoom: [
    {
      type: 'inside',
      start: 0,
      end: 100
    },
    {
      start: 0,
      end: 100,
      borderColor: 'var(--color-border-primary)',
      fillerColor: 'var(--color-interactive-selected)',
      handleStyle: {
        color: 'var(--color-primary-500)'
      },
      textStyle: {
        color: 'var(--color-text-secondary)'
      }
    }
  ],
  series: [
    {
      name: '当前温度',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: 'var(--color-data-cyan)'
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(6, 182, 212, 0.25)' },
            { offset: 1, color: 'rgba(6, 182, 212, 0.02)' }
          ]
        }
      },
      data: tempStore.tempHistory.map(item => [item.timestamp, item.current])
    },
    {
      name: '目标温度',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: 'var(--color-data-orange)',
        type: 'dashed'
      },
      data: tempStore.tempHistory.map(item => [item.timestamp, item.target])
    }
  ]
}))

/** 程序预览图表配置 */
const previewChartOption = computed(() => {
  const segments = programForm.segments
  if (segments.length === 0) {
    return {}
  }

  const data = []
  let currentTime = 0
  let currentTemp = segments[0].targetTemp

  segments.forEach((segment) => {
    data.push([currentTime, currentTemp])

    if (segment.type === 'heat' || segment.type === 'cool') {
      if (segment.rate > 0 && segment.targetTemp !== currentTemp) {
        const tempDiff = segment.targetTemp - currentTemp
        const heatTime = Math.abs(tempDiff) / segment.rate
        currentTime += heatTime
        data.push([currentTime, segment.targetTemp])
        currentTemp = segment.targetTemp
      }
    } else if (segment.type === 'hold') {
      if (segment.duration > 0) {
        currentTime += segment.duration
        data.push([currentTime, currentTemp])
      }
    }
  })

  return {
    title: {
      show: false
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'var(--color-surface-elevated)',
      borderColor: 'var(--color-border-primary)',
      borderWidth: 1,
      textStyle: {
        color: 'var(--color-text-primary)',
        fontFamily: 'var(--font-family-mono)'
      },
      formatter: (params) => {
        const point = params[0]
        return `<div>时间: <span style="font-weight: 600;">${point.value[0].toFixed(1)} min</span></div>
                <div>温度: <span style="font-weight: 600;">${point.value[1].toFixed(1)}K</span> <span style="color: var(--color-text-tertiary);">(${tempStore.kelvinToCelsius(point.value[1]).toFixed(1)}°C)</span></div>`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '时间 (min)',
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      splitLine: {
        show: false
      },
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      axisLabel: {
        color: 'var(--color-text-secondary)',
        fontFamily: 'var(--font-family-mono)'
      }
    },
    yAxis: {
      type: 'value',
      name: '温度 (K)',
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      splitLine: {
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      },
      axisLine: {
        show: false
      },
      axisLabel: {
        color: 'var(--color-text-secondary)',
        fontFamily: 'var(--font-family-mono)'
      }
    },
    series: [
      {
        name: '温度',
        type: 'line',
        step: 'middle',
        lineStyle: {
          width: 2,
          color: 'var(--color-data-green)'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(16, 185, 129, 0.25)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.02)' }
            ]
          }
        },
        data: data
      }
    ]
  }
})

// ============ 方法 ============

/**
 * 设置目标温度
 */
async function handleSetTargetTemp() {
  const success = await tempStore.setTargetTemp(tempForm.targetTemp)
  if (success) {
    ElMessage.success('目标温度设置成功')
  }
}

/**
 * 停止加热
 */
async function handleStopHeating() {
  try {
    await tempStore.setTargetTemp(tempStore.currentTemp)
    ElMessage.success('已停止加热')
  } catch (error) {
    ElMessage.error('停止加热失败')
  }
}

/**
 * 配置 PID 参数
 */
async function handleConfigurePID() {
  const success = await tempStore.configurePID(pidForm)
  if (success) {
    ElMessage.success('PID 参数配置成功')
  }
}

/**
 * 重置 PID 参数为默认值
 */
function handleResetPID() {
  pidForm.kp = 10.0
  pidForm.ki = 0.5
  pidForm.kd = 2.0
  pidValidationResult.value = null
  ElMessage.info('已重置为默认 PID 参数')
}

/**
 * 验证 PID 参数
 */
async function handleValidatePID() {
  const result = await tempStore.validatePIDParams(pidForm)
  if (result) {
    pidValidationResult.value = result
    if (result.valid) {
      ElMessage.success('PID 参数验证通过')
    } else {
      ElMessage.warning(result.message || 'PID 参数验证失败')
    }
  }
}

/**
 * 启动 PID 控制
 */
async function handleStartPIDControl() {
  const success = await tempStore.startPIDControl()
  if (success) {
    pidControlActive.value = true
    ElMessage.success('PID 控制已启动')
  }
}

/**
 * 停止 PID 控制
 */
async function handleStopPIDControl() {
  const success = await tempStore.stopPIDControl()
  if (success) {
    pidControlActive.value = false
    ElMessage.success('PID 控制已停止')
  }
}

/**
 * 温度值变化处理
 * @param {number} value - 新的温度值
 */
function handleTempChange(value) {
  const validation = tempStore.validateTemperature(value)
  if (!validation.valid) {
    ElMessage.warning(validation.message)
  }
}

/**
 * 添加温度段
 */
function handleAddSegment() {
  const lastSegment = programForm.segments[programForm.segments.length - 1]
  programForm.segments.push({
    type: 'hold',
    targetTemp: lastSegment.targetTemp,
    duration: 10,
    rate: 0
  })
}

/**
 * 删除温度段
 * @param {number} index - 段索引
 */
function handleRemoveSegment(index) {
  programForm.segments.splice(index, 1)
}

/**
 * 计算程序总时长
 * @param {Array} segments - 温度段列表
 * @returns {string} 总时长字符串
 */
function calculateTotalDuration(segments) {
  if (!segments || segments.length === 0) return '0 min'

  let totalTime = 0
  let currentTemp = segments[0].targetTemp

  segments.forEach(segment => {
    if ((segment.type === 'heat' || segment.type === 'cool') && segment.rate > 0) {
      const tempDiff = Math.abs(segment.targetTemp - currentTemp)
      totalTime += tempDiff / segment.rate
    }
    if (segment.type === 'hold' && segment.duration > 0) {
      totalTime += segment.duration
    }
    currentTemp = segment.targetTemp
  })

  return `${totalTime.toFixed(1)} min`
}

/**
 * 创建程序
 */
async function handleCreateProgram() {
  if (!programForm.name) {
    ElMessage.warning('请输入程序名称')
    return
  }

  if (programForm.segments.length === 0) {
    ElMessage.warning('请至少添加一个温度段')
    return
  }

  const success = await tempStore.createProgram({
    name: programForm.name,
    description: programForm.description,
    segments: programForm.segments
  })

  if (success) {
    ElMessage.success('程序创建成功')
    handleResetProgramForm()
    activeProgramTab.value = 'list'
  }
}

/**
 * 重置程序表单
 */
function handleResetProgramForm() {
  programForm.name = ''
  programForm.description = ''
  programForm.segments = [
    { type: 'heat', targetTemp: 300, duration: 0, rate: 5 },
    { type: 'hold', targetTemp: 300, duration: 30, rate: 0 },
    { type: 'cool', targetTemp: 100, duration: 0, rate: 3 }
  ]
}

/**
 * 选择程序
 * @param {Object} row - 程序行数据
 */
function handleSelectProgram(row) {
  console.log('Selected program:', row)
}

/**
 * 启动程序
 * @param {string} programId - 程序ID
 */
async function handleStartProgram(programId) {
  const success = await tempStore.startProgram(programId)
  if (success) {
    ElMessage.success('程序已启动')
  }
}

/**
 * 暂停程序
 */
async function handlePauseProgram() {
  const success = await tempStore.pauseProgram()
  if (success) {
    ElMessage.success('程序已暂停')
  }
}

/**
 * 恢复程序
 */
async function handleResumeProgram() {
  const success = await tempStore.resumeProgram()
  if (success) {
    ElMessage.success('程序已恢复')
  }
}

/**
 * 停止程序
 */
async function handleStopProgram() {
  try {
    await ElMessageBox.confirm('确定要停止当前运行的程序吗？', '确认', {
      type: 'warning'
    })

    const success = await tempStore.stopProgram()
    if (success) {
      ElMessage.success('程序已停止')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 删除程序
 * @param {string} programId - 程序ID
 */
async function handleDeleteProgram(programId) {
  try {
    await ElMessageBox.confirm('确定要删除该程序吗？', '确认', {
      type: 'warning'
    })

    const success = await tempStore.deleteProgram(programId)
    if (success) {
      ElMessage.success('程序已删除')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 连接温控器
 */
async function handleConnect() {
  const success = await tempStore.connect()
  if (success) {
    ElMessage.success('温控器连接成功')
  }
}

/**
 * 断开温控器
 */
async function handleDisconnect() {
  try {
    await ElMessageBox.confirm('确定要断开温控器连接吗？', '确认', {
      type: 'warning'
    })

    await tempStore.disconnect()
    ElMessage.success('温控器已断开')
  } catch {
    // 用户取消
  }
}

/**
 * 紧急停止
 */
async function handleEmergencyStop() {
  try {
    await ElMessageBox.confirm(
      '紧急停止将立即关闭所有加热输出，确定要执行吗？',
      '紧急停止确认',
      {
        type: 'error',
        confirmButtonText: '确认急停',
        cancelButtonText: '取消'
      }
    )

    const success = await tempStore.emergencyStop()
    if (success) {
      ElMessage.error('紧急停止已执行，所有加热输出已关闭')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 复位急停状态
 */
async function handleResetEmergencyStop() {
  try {
    await ElMessageBox.confirm(
      '确定要复位急停状态吗？复位后可恢复正常控制。',
      '复位确认',
      {
        type: 'warning'
      }
    )

    const success = await tempStore.resetEmergencyStop()
    if (success) {
      ElMessage.success('急停状态已复位，可恢复正常控制')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 设置温度保护配置
 */
async function handleSetProtection() {
  // 验证温度范围
  if (protectionForm.minTemp >= protectionForm.maxTemp) {
    ElMessage.warning('最低温度限制必须小于最高温度限制')
    return
  }

  const success = await tempStore.setProtectionConfig({
    max_temp: protectionForm.maxTemp,
    min_temp: protectionForm.minTemp,
    enable_shutdown: protectionForm.enableShutdown
  })

  if (success) {
    ElMessage.success('温度保护配置已应用')
  }
}

/**
 * 清除温度保护状态
 */
async function handleClearProtectionStatus() {
  const success = await tempStore.clearProtectionStatus()
  if (success) {
    ElMessage.success('温度保护状态已清除')
  }
}

/**
 * 获取温度历史记录
 */
async function handleFetchHistory() {
  const endTime = Date.now()
  const startTime = endTime - 3600000 // 最近1小时

  const history = await tempStore.fetchTemperatureHistory({
    start_time: startTime,
    end_time: endTime,
    interval: 1 // 1秒间隔
  })

  if (history) {
    ElMessage.success(`已获取 ${history.length} 条历史记录`)
  }
}

/**
 * 清除温度历史记录
 */
async function handleClearHistory() {
  try {
    await ElMessageBox.confirm('确定要清除所有温度历史记录吗？', '确认', {
      type: 'warning'
    })

    const success = await tempStore.clearTemperatureHistory()
    if (success) {
      ElMessage.success('温度历史记录已清除')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 导出温度历史记录
 * @param {string} format - 导出格式 ('csv' 或 'json')
 */
async function handleExportHistory(format) {
  try {
    const blob = await tempStore.exportTemperatureHistory(format)
    if (blob) {
      // 创建下载链接
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `temperature_history_${Date.now()}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      ElMessage.success(`历史记录已导出为 ${format.toUpperCase()} 格式`)
    }
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  }
}

// ============ 生命周期 ============

onMounted(async () => {
  tempStore.init()

  // 初始化表单数据
  tempForm.targetTemp = tempStore.targetTemp
  tempForm.heatingRate = 2.0
  pidForm.kp = tempStore.pidParams.kp
  pidForm.ki = tempStore.pidParams.ki
  pidForm.kd = tempStore.pidParams.kd

  // 初始化保护配置
  protectionForm.maxTemp = tempStore.tempLimits.warning_high
  protectionForm.minTemp = tempStore.tempLimits.warning_low

  // 获取 PID 参数
  await tempStore.fetchPIDParams()
})

onUnmounted(() => {
  tempStore.cleanup()
})

watch(() => tempStore.targetTemp, (newVal) => {
  tempForm.targetTemp = newVal
})

watch(() => tempStore.pidParams, (newVal) => {
  pidForm.kp = newVal.kp
  pidForm.ki = newVal.ki
  pidForm.kd = newVal.kd
}, { deep: true })

watch(() => tempStore.tempLimits, (newVal) => {
  protectionForm.maxTemp = newVal.warning_high
  protectionForm.minTemp = newVal.warning_low
}, { deep: true })
</script>

<style scoped>
.temperature-control {
  margin-bottom: var(--spacing-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  background: var(--color-surface-primary);
  transition: var(--transition-all);
}

.temperature-control:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.emergency-stop-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border: 2px solid #ef4444;
  color: #ffffff;
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-base);
  padding: var(--spacing-2) var(--spacing-4);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
  animation: pulse-emergency 2s ease-in-out infinite;
  position: relative;
  overflow: hidden;
}

.emergency-stop-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shine 3s infinite;
}

.emergency-stop-btn:hover {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  border-color: #dc2626;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.6);
}

.emergency-stop-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.4);
}

.emergency-stop-btn .el-icon {
  font-size: var(--font-size-lg);
  animation: shake 0.5s ease-in-out infinite;
}

.emergency-reset-btn {
  animation: pulse-warning 1.5s ease-in-out infinite;
}

.emergency-alert {
  margin-bottom: var(--spacing-4);
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

.connection-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  animation: pulse 2s ease-in-out infinite;
}

.connection-badge--connected {
  background: var(--color-success-light);
  color: var(--color-success-dark);
}

.connection-badge--connected .badge-dot {
  background: var(--color-status-online);
  box-shadow: 0 0 8px var(--color-status-online);
}

.connection-badge--connecting {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.connection-badge--connecting .badge-dot {
  background: var(--color-status-warning);
  box-shadow: 0 0 8px var(--color-status-warning);
  animation: pulse-fast 1s ease-in-out infinite;
}

.connection-badge--disconnected {
  background: var(--color-error-light);
  color: var(--color-error-dark);
}

.connection-badge--disconnected .badge-dot {
  background: var(--color-status-error);
  animation: none;
}

.control-content {
  padding: var(--spacing-2) 0;
}

/* 温度状态卡片 */
.temp-status-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-6);
}

.status-card {
  position: relative;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  background: var(--color-surface-primary);
  overflow: hidden;
  transition: var(--transition-all);
}

.status-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.status-card--active {
  border-color: var(--color-accent-500);
}

.status-card--active .card-glow {
  opacity: 1;
}

.card-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-accent-400), var(--color-accent-600));
  opacity: 0;
  transition: var(--transition-base);
}

.status-card--current .card-glow {
  background: linear-gradient(90deg, var(--color-data-cyan), var(--color-primary-500));
  opacity: 1;
}

.status-card--target .card-glow {
  background: linear-gradient(90deg, var(--color-data-orange), var(--color-warning));
  opacity: 1;
}

.status-card--rate .card-glow {
  background: linear-gradient(90deg, var(--color-data-green), var(--color-success));
  opacity: 1;
}

.card-content {
  padding: var(--spacing-4);
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: var(--color-primary-50);
  margin-bottom: var(--spacing-3);
  font-size: var(--font-size-2xl);
  color: var(--color-primary-500);
  transition: var(--transition-all);
}

.card-icon--target {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.card-icon--rate {
  background: var(--color-success-light);
  color: var(--color-success);
}

.card-body {
  margin-bottom: var(--spacing-3);
}

.temp-display {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-1);
  margin-bottom: var(--spacing-1);
}

.temp-value {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  letter-spacing: 0.02em;
}

.temp-unit {
  font-size: var(--font-size-lg);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

.temp-celsius {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-1);
}

.card-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  animation: pulse 2s ease-in-out infinite;
}

.status-indicator--heating {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.status-indicator--heating .indicator-dot {
  background: var(--color-status-warning);
  box-shadow: 0 0 6px var(--color-status-warning);
  animation: pulse-fast 1s ease-in-out infinite;
}

.status-indicator--stable {
  background: var(--color-success-light);
  color: var(--color-success-dark);
}

.status-indicator--stable .indicator-dot {
  background: var(--color-status-online);
  box-shadow: 0 0 6px var(--color-status-online);
}

.status-indicator--warning {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.status-indicator--warning .indicator-dot {
  background: var(--color-status-warning);
  box-shadow: 0 0 6px var(--color-status-warning);
}

.status-indicator--normal {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.status-indicator--normal .indicator-dot {
  background: var(--color-neutral-400);
  animation: none;
}

.status-indicator--standby {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.status-indicator--standby .indicator-dot {
  background: var(--color-neutral-400);
  animation: none;
}

.power-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.power-bar {
  flex: 1;
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.power-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-success), var(--color-warning));
  border-radius: var(--radius-full);
  transition: width var(--transition-base);
}

.power-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  min-width: 48px;
  text-align: right;
}

/* 图表区域 */
.chart-section {
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-4);
  background: var(--color-surface-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-4);
}

.section-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.chart-legend {
  display: flex;
  gap: var(--spacing-4);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
}

.legend-item--current .legend-dot {
  background: var(--color-data-cyan);
}

.legend-item--target .legend-dot {
  background: var(--color-data-orange);
}

.chart-container {
  background: var(--color-surface-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-2);
}

.temp-chart {
  width: 100%;
  height: 350px;
}

/* 控制区域 */
.control-section {
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-4);
  background: var(--color-surface-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

.control-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-6);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.temp-input {
  width: 200px;
}

/* 目标温度输入框样式优化 */
.temp-input :deep(.el-input-number) {
  width: 100%;
}

.temp-input :deep(.el-input-number .el-input__wrapper) {
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  box-shadow: none;
  transition: var(--transition-all);
}

.temp-input :deep(.el-input-number .el-input__wrapper:hover) {
  border-color: var(--color-primary-400);
}

.temp-input :deep(.el-input-number .el-input__wrapper.is-focus) {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.temp-input :deep(.el-input-number .el-input__inner) {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  text-align: center;
}

.temp-input :deep(.el-input-number__decrease),
.temp-input :deep(.el-input-number__increase) {
  background: var(--color-bg-tertiary);
  border-left: 1px solid var(--color-border-primary);
  border-right: 1px solid var(--color-border-primary);
  color: var(--color-text-secondary);
  transition: var(--transition-all);
}

.temp-input :deep(.el-input-number__decrease:hover),
.temp-input :deep(.el-input-number__increase:hover) {
  background: var(--color-interactive-hover);
  color: var(--color-primary-500);
}

.input-unit {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.unit-hint {
  color: var(--color-text-tertiary);
}

.form-actions {
  display: flex;
  gap: var(--spacing-3);
  padding-top: var(--spacing-2);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
}

.action-btn--primary {
  background: var(--color-primary-500);
  border-color: var(--color-primary-500);
  color: var(--color-text-inverse);
}

.action-btn--primary:hover:not(:disabled) {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.action-btn--secondary {
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  color: var(--color-text-primary);
}

.action-btn--secondary:hover:not(:disabled) {
  background: var(--color-interactive-hover);
  border-color: var(--color-border-secondary);
}

.action-btn--success {
  background: var(--color-success);
  border-color: var(--color-success);
  color: var(--color-text-inverse);
}

.action-btn--success:hover:not(:disabled) {
  background: var(--color-success-dark);
  border-color: var(--color-success-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.action-btn--warning {
  background: var(--color-warning);
  border-color: var(--color-warning);
  color: var(--color-text-inverse);
}

.action-btn--warning:hover:not(:disabled) {
  background: var(--color-warning-dark);
  border-color: var(--color-warning-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.temp-range-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-1);
}

.pid-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

/* PID 参数 */
.pid-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.pid-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.pid-input {
  width: 100%;
}

/* 程序控温 */
.program-tabs {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.program-list {
  padding: var(--spacing-2) 0;
}

.program-table {
  border-radius: var(--radius-md);
  overflow: hidden;
}

.program-control {
  margin-top: var(--spacing-4);
  padding: var(--spacing-4);
  background: var(--color-surface-primary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.program-progress {
  margin-bottom: var(--spacing-3);
}

.control-buttons {
  display: flex;
  gap: var(--spacing-3);
  justify-content: center;
}

.segment-list {
  width: 100%;
}

.add-segment-btn {
  margin-top: var(--spacing-3);
}

.preview-chart-container {
  width: 100%;
}

.preview-chart {
  width: 100%;
  height: 280px;
}

/* 连接控制 */
.connection-section {
  display: flex;
  justify-content: center;
  padding: var(--spacing-4);
}

.connect-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-6);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  transition: var(--transition-all);
}

.connect-btn--connect {
  background: var(--color-primary-500);
  border-color: var(--color-primary-500);
}

.connect-btn--connect:hover {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-primary);
}

.connect-btn--disconnect {
  background: var(--color-error);
  border-color: var(--color-error);
}

.connect-btn--disconnect:hover {
  background: var(--color-error-dark);
  border-color: var(--color-error-dark);
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-error);
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

@keyframes pulse-emergency {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(239, 68, 68, 0);
  }
}

@keyframes pulse-warning {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(245, 158, 11, 0);
  }
}

@keyframes shine {
  0% {
    left: -100%;
  }
  50%, 100% {
    left: 100%;
  }
}

@keyframes shake {
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

/* 保护配置 */
.protection-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.protection-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.protection-item--switch {
  justify-content: center;
}

.protection-input {
  width: 100%;
}

.input-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 历史记录管理 */
.history-actions {
  display: flex;
  gap: var(--spacing-2);
}

.history-info {
  display: flex;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-3);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.history-count {
  font-weight: var(--font-weight-medium);
}

.history-max {
  color: var(--color-text-tertiary);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .temp-status-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .pid-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .protection-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .temp-status-cards {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .pid-grid {
    grid-template-columns: 1fr;
  }

  .protection-grid {
    grid-template-columns: 1fr;
  }

  .temp-value {
    font-size: var(--font-size-2xl);
  }

  .temp-chart {
    height: 280px;
  }

  .header-actions {
    flex-wrap: wrap;
  }

  .history-info {
    flex-direction: column;
    gap: var(--spacing-2);
  }
}
</style>
