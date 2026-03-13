<template>
  <el-card class="electromagnet-control">
    <template #header>
      <div class="card-header">
        <div class="header-title">
          <el-icon class="header-icon">
            <Opportunity />
          </el-icon>
          <span>电磁铁控制</span>
        </div>
        <el-tag
          :type="statusTagType"
          size="small"
          class="status-tag"
        >
          {{ statusText }}
        </el-tag>
      </div>
    </template>

    <div class="control-content">
      <!-- 报警提示 -->
      <el-alert
        v-if="electromagnetStore.alarmMessage"
        :title="electromagnetStore.alarmMessage"
        type="error"
        :closable="true"
        class="alarm-alert"
        @close="electromagnetStore.clearAlarm"
      />

      <!-- 实时数据显示 -->
      <div class="realtime-display">
        <el-row :gutter="24">
          <el-col :span="12">
            <div class="display-item current-display">
              <div class="display-icon">
                <el-icon><Lightning /></el-icon>
              </div>
              <div class="display-content">
                <div class="label">
                  当前电流
                </div>
                <div class="value-row">
                  <span class="value mono">{{ electromagnetStore.formattedCurrent }}</span>
                  <span class="unit">A</span>
                </div>
              </div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="display-item field-display">
              <div class="display-icon">
                <el-icon><Magnet /></el-icon>
              </div>
              <div class="display-content">
                <div class="label">
                  磁场强度
                </div>
                <div class="value-row">
                  <span class="value mono">{{ electromagnetStore.formattedField }}</span>
                  <span class="unit">mT</span>
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 电流设置 -->
      <el-divider class="section-divider">
        电流设置
      </el-divider>

      <el-form
        :model="currentForm"
        label-width="100px"
        class="current-form"
      >
        <el-form-item
          label="目标电流"
          :class="{ 'is-error': currentValidation.error }"
          class="form-item"
        >
          <div class="input-group">
            <el-input-number
              v-model="currentForm.targetCurrent"
              :min="electromagnetStore.currentLimits.min"
              :max="electromagnetStore.currentLimits.max"
              :precision="3"
              :step="0.1"
              class="form-number"
              @change="validateCurrentInput"
            />
            <span class="unit-label">A</span>
            <el-tag
              v-if="currentValidation.warning"
              type="warning"
              size="small"
              class="validation-tag"
            >
              {{ currentValidation.warning }}
            </el-tag>
          </div>
          <div
            v-if="currentValidation.error"
            class="error-message"
          >
            {{ currentValidation.error }}
          </div>
        </el-form-item>

        <el-form-item
          label="目标磁场"
          class="form-item"
        >
          <div class="input-group">
            <el-input-number
              v-model="currentForm.targetField"
              :min="-1000"
              :max="1000"
              :precision="2"
              :step="10"
              class="form-number"
              @change="handleFieldChange"
            />
            <span class="unit-label">mT</span>
          </div>
        </el-form-item>

        <el-form-item class="form-item">
          <div class="button-group">
            <el-button
              type="primary"
              :disabled="!electromagnetStore.canControl || currentValidation.error"
              :loading="electromagnetStore.loading.setCurrent"
              class="set-btn"
              @click="handleSetCurrent"
            >
              设置电流
            </el-button>
            <el-button
              type="success"
              :disabled="!electromagnetStore.canControl"
              :loading="electromagnetStore.loading.setField"
              class="set-btn"
              @click="handleSetField"
            >
              设置磁场
            </el-button>
          </div>
        </el-form-item>
      </el-form>

      <!-- 电流滑块 -->
      <div class="current-slider">
        <el-slider
          v-model="currentForm.targetCurrent"
          :min="electromagnetStore.currentLimits.min"
          :max="electromagnetStore.currentLimits.max"
          :step="0.01"
          :marks="currentMarks"
          :disabled="!electromagnetStore.canControl"
          class="slider-control"
          @change="handleSliderChange"
        />
      </div>

      <!-- 扫描模式配置 -->
      <el-divider class="section-divider">
        扫描模式
      </el-divider>

      <el-form
        :model="scanForm"
        label-width="100px"
        class="scan-form"
      >
        <el-form-item
          label="扫描模式"
          class="form-item"
        >
          <el-radio-group
            v-model="scanForm.mode"
            class="mode-radio-group"
          >
            <el-radio label="linear">
              线性扫描
            </el-radio>
            <el-radio label="step">
              步进扫描
            </el-radio>
            <el-radio label="custom">
              自定义
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          label="起始电流"
          :class="{ 'is-error': scanValidation.startError }"
          class="form-item"
        >
          <div class="input-group">
            <el-input-number
              v-model="scanForm.startCurrent"
              :min="electromagnetStore.currentLimits.min"
              :max="electromagnetStore.currentLimits.max"
              :precision="3"
              :step="0.1"
              class="form-number small"
              @change="validateScanParams"
            />
            <span class="unit-label">A</span>
          </div>
          <div
            v-if="scanValidation.startError"
            class="error-message"
          >
            {{ scanValidation.startError }}
          </div>
        </el-form-item>

        <el-form-item
          label="终止电流"
          :class="{ 'is-error': scanValidation.endError }"
          class="form-item"
        >
          <div class="input-group">
            <el-input-number
              v-model="scanForm.endCurrent"
              :min="electromagnetStore.currentLimits.min"
              :max="electromagnetStore.currentLimits.max"
              :precision="3"
              :step="0.1"
              class="form-number small"
              @change="validateScanParams"
            />
            <span class="unit-label">A</span>
          </div>
          <div
            v-if="scanValidation.endError"
            class="error-message"
          >
            {{ scanValidation.endError }}
          </div>
        </el-form-item>

        <el-form-item
          v-if="scanForm.mode === 'linear'"
          label="扫描速率"
          :class="{ 'is-error': scanValidation.rateError }"
          class="form-item"
        >
          <div class="input-group">
            <el-input-number
              v-model="scanForm.scanRate"
              :min="0.01"
              :max="1"
              :precision="2"
              :step="0.01"
              class="form-number small"
              @change="validateScanParams"
            />
            <span class="unit-label">A/s</span>
          </div>
          <div
            v-if="scanValidation.rateError"
            class="error-message"
          >
            {{ scanValidation.rateError }}
          </div>
        </el-form-item>

        <el-form-item
          v-if="scanForm.mode === 'step'"
          label="步进大小"
          class="form-item"
        >
          <div class="input-group">
            <el-input-number
              v-model="scanForm.stepSize"
              :min="0.001"
              :max="5"
              :precision="3"
              :step="0.01"
              class="form-number small"
              @change="updateStepCount"
            />
            <span class="unit-label">A</span>
          </div>
        </el-form-item>

        <el-form-item
          v-if="scanForm.mode === 'step'"
          label="步数"
          :class="{ 'is-error': scanValidation.stepError }"
          class="form-item"
        >
          <el-input-number
            v-model="scanForm.stepCount"
            :min="2"
            :max="1000"
            :step="1"
            class="form-number small"
            @change="validateScanParams"
          />
          <div
            v-if="scanValidation.stepError"
            class="error-message"
          >
            {{ scanValidation.stepError }}
          </div>
        </el-form-item>

        <el-form-item
          v-if="scanForm.mode === 'step'"
          label="步间延时"
          :class="{ 'is-error': scanValidation.delayError }"
          class="form-item"
        >
          <div class="input-group">
            <el-input-number
              v-model="scanForm.stepDelay"
              :min="0.1"
              :max="60"
              :precision="1"
              :step="0.1"
              class="form-number small"
              @change="validateScanParams"
            />
            <span class="unit-label">s</span>
          </div>
          <div
            v-if="scanValidation.delayError"
            class="error-message"
          >
            {{ scanValidation.delayError }}
          </div>
        </el-form-item>

        <!-- 扫描参数预览 -->
        <el-form-item
          v-if="scanPreview.isValid"
          label="扫描预览"
          class="form-item"
        >
          <el-card
            class="scan-preview-card"
            shadow="never"
          >
            <div class="preview-item">
              <span class="preview-label">总步数:</span>
              <span class="preview-value mono">{{ scanPreview.totalSteps }}</span>
            </div>
            <div class="preview-item">
              <span class="preview-label">预计时长:</span>
              <span class="preview-value">{{ scanPreview.estimatedTime }}</span>
            </div>
            <div class="preview-item">
              <span class="preview-label">电流范围:</span>
              <span class="preview-value mono">{{ scanPreview.currentRange }}</span>
            </div>
            <div
              v-if="scanForm.mode === 'linear'"
              class="preview-item"
            >
              <span class="preview-label">扫描方向:</span>
              <span class="preview-value">{{ scanPreview.direction }}</span>
            </div>
          </el-card>
        </el-form-item>

        <el-form-item class="form-item">
          <div class="button-group">
            <el-button
              type="primary"
              :disabled="!electromagnetStore.canControl || !scanValidation.isValid"
              :loading="electromagnetStore.loading.configScan"
              class="config-btn"
              @click="handleConfigScan"
            >
              配置扫描
            </el-button>
            <el-button
              type="info"
              :disabled="!scanValidation.isValid"
              :loading="electromagnetStore.loading.validateScanConfig"
              class="config-btn"
              @click="handleValidateScanConfig"
            >
              验证参数
            </el-button>
          </div>
        </el-form-item>
      </el-form>

      <!-- 扫描控制按钮 -->
      <div class="scan-controls">
        <el-button
          type="success"
          :disabled="!electromagnetStore.canControl || electromagnetStore.isScanning"
          :loading="electromagnetStore.loading.startScan"
          class="control-btn start-btn"
          @click="handleStartScan"
        >
          <el-icon><VideoPlay /></el-icon>
          开始扫描
        </el-button>

        <el-button
          type="warning"
          :disabled="!electromagnetStore.isScanning"
          class="control-btn pause-btn"
          @click="handlePauseScan"
        >
          <el-icon><VideoPause /></el-icon>
          暂停
        </el-button>

        <el-button
          type="danger"
          :disabled="!electromagnetStore.isScanning"
          :loading="electromagnetStore.loading.stopScan"
          class="control-btn stop-btn"
          @click="handleStopScan"
        >
          <el-icon><Close /></el-icon>
          停止扫描
        </el-button>
      </div>

      <!-- 扫描进度 -->
      <div
        v-if="electromagnetStore.isScanning || electromagnetStore.isPaused"
        class="scan-progress"
      >
        <div class="progress-header">
          <span class="progress-title">扫描进度</span>
          <el-tag
            :type="electromagnetStore.isPaused ? 'warning' : 'success'"
            size="small"
          >
            {{ electromagnetStore.isPaused ? '已暂停' : '扫描中' }}
          </el-tag>
        </div>

        <el-progress
          :percentage="electromagnetStore.scanStatus.progress"
          :format="scanProgressFormat"
          :status="electromagnetStore.isPaused ? 'warning' : 'success'"
          class="progress-bar"
        />

        <div class="progress-details">
          <el-row :gutter="16">
            <el-col :span="6">
              <div class="detail-item">
                <div class="detail-label">
                  当前步数
                </div>
                <div class="detail-value mono">
                  {{ electromagnetStore.scanStatus.currentStep }} / {{ electromagnetStore.scanStatus.totalSteps }}
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="detail-item">
                <div class="detail-label">
                  当前电流
                </div>
                <div class="detail-value mono">
                  {{ electromagnetStore.scanStatus.currentCurrent.toFixed(3) }} A
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="detail-item">
                <div class="detail-label">
                  当前磁场
                </div>
                <div class="detail-value mono">
                  {{ electromagnetStore.scanStatus.currentField.toFixed(2) }} mT
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="detail-item">
                <div class="detail-label">
                  剩余时间
                </div>
                <div class="detail-value">
                  {{ formatRemainingTime(electromagnetStore.estimatedRemainingTime) }}
                </div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 扫描方向指示器 -->
        <div class="scan-direction">
          <el-icon :class="['direction-icon', electromagnetStore.scanStatus.scanDirection]">
            <component :is="electromagnetStore.scanStatus.scanDirection === 'forward' ? 'ArrowRight' : 'ArrowLeft'" />
          </el-icon>
          <span>{{ electromagnetStore.scanStatus.scanDirection === 'forward' ? '正向扫描' : '反向扫描' }}</span>
        </div>
      </div>

      <!-- 扫描数据实时绘图 -->
      <div
        v-if="electromagnetStore.isScanning || electromagnetStore.scanData.current.length > 0"
        class="scan-data-plot"
      >
        <div class="plot-header">
          <span class="plot-title">实时扫描数据</span>
          <div class="plot-actions">
            <el-button
              type="primary"
              size="small"
              text
              :icon="Download"
              :disabled="electromagnetStore.scanData.current.length === 0"
              @click="handleExportScanData"
            >
              导出数据
            </el-button>
            <el-button
              type="warning"
              size="small"
              text
              :icon="Delete"
              :disabled="electromagnetStore.scanData.current.length === 0"
              @click="handleClearScanData"
            >
              清除数据
            </el-button>
          </div>
        </div>

        <div
          ref="scanChartRef"
          class="scan-chart"
        />

        <!-- 数据统计 -->
        <div
          v-if="electromagnetStore.scanData.current.length > 0"
          class="scan-stats"
        >
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-label">
                  数据点数
                </div>
                <div class="stat-value mono">
                  {{ electromagnetStore.scanData.current.length }}
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-label">
                  电流范围
                </div>
                <div class="stat-value mono">
                  {{ scanDataStats.currentRange }}
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-label">
                  磁场范围
                </div>
                <div class="stat-value mono">
                  {{ scanDataStats.fieldRange }}
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
      </div>

      <!-- 校准曲线配置 -->
      <el-divider class="section-divider">
        校准曲线
      </el-divider>

      <div class="calibration-section">
        <div class="calibration-header">
          <span class="calibration-status">校准状态: {{ electromagnetStore.calibrationStatus }}</span>
          <div class="calibration-actions-header">
            <el-button
              type="primary"
              size="small"
              :loading="electromagnetStore.loading.fetchCalibration"
              class="action-btn"
              @click="handleFetchCalibration"
            >
              刷新校准
            </el-button>
            <el-button
              v-if="calibrationPoints.length > 0"
              type="info"
              size="small"
              class="action-btn"
              @click="handleExportCalibration"
            >
              导出数据
            </el-button>
          </div>
        </div>

        <!-- 校准质量指标 -->
        <div
          v-if="calibrationQuality.isValid"
          class="calibration-quality"
        >
          <el-row :gutter="16">
            <el-col :span="6">
              <div class="quality-item">
                <div class="quality-label">
                  拟合优度 R²
                </div>
                <div
                  class="quality-value mono"
                  :class="getQualityClass('r2')"
                >
                  {{ calibrationQuality.r2.toFixed(4) }}
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="quality-item">
                <div class="quality-label">
                  均方根误差
                </div>
                <div class="quality-value mono">
                  {{ calibrationQuality.rmse.toFixed(2) }} mT
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="quality-item">
                <div class="quality-label">
                  最大偏差
                </div>
                <div class="quality-value mono">
                  {{ calibrationQuality.maxError.toFixed(2) }} mT
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="quality-item">
                <div class="quality-label">
                  校准点数
                </div>
                <div class="quality-value mono">
                  {{ calibrationPoints.length }}
                </div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 校准曲线图表 -->
        <div
          ref="calibrationChartRef"
          class="calibration-chart"
        />

        <!-- 图表控制 -->
        <div class="chart-controls">
          <el-checkbox
            v-model="chartOptions.showFitCurve"
            @change="updateCalibrationChart"
          >
            显示拟合曲线
          </el-checkbox>
          <el-checkbox
            v-model="chartOptions.showGrid"
            @change="updateCalibrationChart"
          >
            显示网格
          </el-checkbox>
          <el-checkbox
            v-model="chartOptions.showRealtime"
            @change="updateCalibrationChart"
          >
            显示实时数据点
          </el-checkbox>
        </div>

        <!-- 添加校准点 -->
        <div class="add-calibration-point">
          <el-form
            :inline="true"
            size="small"
          >
            <el-form-item label="电流">
              <el-input-number
                v-model="newCalibrationPoint.current"
                :min="electromagnetStore.currentLimits.min"
                :max="electromagnetStore.currentLimits.max"
                :precision="3"
                :step="0.1"
                class="form-number small"
              />
              <span class="unit-label">A</span>
            </el-form-item>

            <el-form-item label="磁场">
              <el-input-number
                v-model="newCalibrationPoint.field"
                :min="-1000"
                :max="1000"
                :precision="2"
                :step="10"
                class="form-number small"
              />
              <span class="unit-label">mT</span>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :disabled="!electromagnetStore.canControl"
                class="add-point-btn"
                @click="handleAddCalibrationPoint"
              >
                添加校准点
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 校准点列表 -->
        <div
          v-if="calibrationPoints.length > 0"
          class="calibration-points-list"
        >
          <el-table
            :data="calibrationPoints"
            size="small"
            max-height="200"
            class="points-table"
          >
            <el-table-column
              prop="current"
              label="电流 (A)"
              width="120"
            >
              <template #default="{ row }">
                <span class="mono">{{ row.current.toFixed(3) }}</span>
              </template>
            </el-table-column>
            <el-table-column
              prop="field"
              label="磁场 (mT)"
              width="120"
            >
              <template #default="{ row }">
                <span class="mono">{{ row.field.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="80"
            >
              <template #default="{ $index }">
                <el-button
                  type="danger"
                  size="small"
                  link
                  class="delete-btn"
                  @click="handleRemoveCalibrationPoint($index)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 校准操作按钮 -->
        <div class="calibration-actions">
          <el-button
            type="info"
            :disabled="calibrationPoints.length < 2"
            :loading="electromagnetStore.loading.validateCalibration"
            class="calibration-btn"
            @click="handleValidateCalibration"
          >
            验证数据
          </el-button>

          <el-button
            type="success"
            :disabled="calibrationPoints.length < 2"
            :loading="electromagnetStore.loading.uploadCalibration"
            class="calibration-btn"
            @click="handleUploadCalibration"
          >
            上传校准曲线
          </el-button>

          <el-button
            type="primary"
            :disabled="calibrationPoints.length < 3"
            :loading="electromagnetStore.loading.performCalibration"
            class="calibration-btn"
            @click="handlePerformCalibration"
          >
            执行校准
          </el-button>

          <el-button
            type="danger"
            :disabled="calibrationPoints.length === 0"
            class="calibration-btn"
            @click="handleClearCalibrationPoints"
          >
            清除所有点
          </el-button>

          <el-button
            type="danger"
            :loading="electromagnetStore.loading.clearCalibration"
            class="calibration-btn"
            @click="handleClearCalibration"
          >
            清除校准数据
          </el-button>
        </div>
      </div>

      <!-- 急停按钮 -->
      <el-divider class="section-divider">
        安全控制
      </el-divider>

      <div class="safety-controls">
        <el-button
          v-if="electromagnetStore.status !== 'emergency_stop'"
          type="danger"
          size="large"
          :disabled="!electromagnetStore.isConnected"
          class="emergency-btn"
          @click="handleEmergencyStop"
        >
          <el-icon><Warning /></el-icon>
          急停
        </el-button>

        <el-button
          v-else
          type="warning"
          size="large"
          class="reset-btn"
          @click="handleResetEmergency"
        >
          <el-icon><RefreshRight /></el-icon>
          复位急停
        </el-button>

        <el-button
          type="warning"
          size="large"
          :disabled="!electromagnetStore.isConnected"
          :loading="electromagnetStore.loading.resetOvercurrent"
          class="reset-btn"
          @click="handleResetOvercurrent"
        >
          <el-icon><RefreshRight /></el-icon>
          过流保护复位
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file ElectromagnetControl.vue
 * @path src/components/
 * @description 电磁铁控制面板组件，提供电流设置、扫描模式、磁场监控及校准功能
 * @author Agent
 * @date 2024-03-06
 */

import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useElectromagnetStore } from '@/stores/electromagnet'
import { ElMessage } from 'element-plus'
import { Download, Delete, ArrowRight, ArrowLeft } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const electromagnetStore = useElectromagnetStore()

// ============ 响应式状态 ============

/** 电流设置表单 */
const currentForm = reactive({
  targetCurrent: 0,
  targetField: 0
})

/** 电流验证状态 */
const currentValidation = reactive({
  error: '',
  warning: ''
})

/** 最大电流限制常量 (A) */
const MAX_CURRENT_LIMIT = 10

/** 扫描配置表单 */
const scanForm = reactive({
  mode: 'linear',
  startCurrent: 0,
  endCurrent: 5,
  stepSize: 0.1,
  stepCount: 10,
  stepDelay: 0.5,
  scanRate: 0.1
})

/** 扫描验证状态 */
const scanValidation = reactive({
  isValid: false,
  startError: '',
  endError: '',
  rateError: '',
  stepError: '',
  delayError: ''
})

/** 扫描预览 */
const scanPreview = reactive({
  isValid: false,
  totalSteps: 0,
  estimatedTime: '',
  currentRange: '',
  direction: ''
})

/** 新校准点 */
const newCalibrationPoint = reactive({
  current: 0,
  field: 0
})

/** 校准点列表 */
const calibrationPoints = ref([])

/** 校准质量指标 */
const calibrationQuality = reactive({
  isValid: false,
  r2: 0,
  rmse: 0,
  maxError: 0
})

/** 图表选项 */
const chartOptions = reactive({
  showFitCurve: true,
  showGrid: true,
  showRealtime: true
})

/** 校准图表引用 */
const calibrationChartRef = ref(null)
let calibrationChart = null

/** 扫描数据图表引用 */
const scanChartRef = ref(null)
let scanChart = null

// ============ 计算属性 ============

/** 状态标签类型 */
const statusTagType = computed(() => {
  const statusMap = {
    'disconnected': 'info',
    'ready': 'success',
    'moving': 'warning',
    'scanning': 'primary',
    'emergency_stop': 'danger',
    'error': 'danger'
  }
  return statusMap[electromagnetStore.status] || 'info'
})

/** 状态文本 */
const statusText = computed(() => {
  const textMap = {
    'disconnected': '未连接',
    'ready': '就绪',
    'moving': '运动中',
    'scanning': '扫描中',
    'emergency_stop': '急停',
    'error': '错误'
  }
  return textMap[electromagnetStore.status] || '未知'
})

/** 电流标记点 */
const currentMarks = computed(() => {
  const min = electromagnetStore.currentLimits.min
  const max = electromagnetStore.currentLimits.max
  return {
    [min]: min + 'A',
    0: '0A',
    [max]: max + 'A'
  }
})

/** 扫描数据统计 */
const scanDataStats = computed(() => {
  const data = electromagnetStore.scanData
  if (data.current.length === 0) {
    return {
      currentRange: '-',
      fieldRange: '-'
    }
  }

  const minCurrent = Math.min(...data.current)
  const maxCurrent = Math.max(...data.current)
  const minField = Math.min(...data.field)
  const maxField = Math.max(...data.field)

  return {
    currentRange: `${minCurrent.toFixed(3)} ~ ${maxCurrent.toFixed(3)} A`,
    fieldRange: `${minField.toFixed(2)} ~ ${maxField.toFixed(2)} mT`
  }
})

// ============ 方法 ============

/**
 * 验证电流输入
 * 检查电流是否在允许范围内，并显示警告信息
 */
function validateCurrentInput(value) {
  currentValidation.error = ''
  currentValidation.warning = ''

  if (value === null || value === undefined || isNaN(value)) {
    currentValidation.error = '请输入有效的电流值'
    return false
  }

  const absValue = Math.abs(value)
  const minLimit = electromagnetStore.currentLimits.min
  const maxLimit = electromagnetStore.currentLimits.max

  // 检查是否超出硬件限制
  if (value < minLimit || value > maxLimit) {
    currentValidation.error = `电流超出硬件限制范围 (${minLimit}A ~ ${maxLimit}A)`
    return false
  }

  // 检查是否接近最大电流限制 (10A)
  if (absValue > MAX_CURRENT_LIMIT * 0.9) {
    currentValidation.warning = `警告：电流接近最大限制 ${MAX_CURRENT_LIMIT}A`
  } else if (absValue > MAX_CURRENT_LIMIT * 0.8) {
    currentValidation.warning = `注意：电流较高 (> ${MAX_CURRENT_LIMIT * 0.8}A)`
  }

  return true
}

/**
 * 设置电流
 */
async function handleSetCurrent() {
  // 验证电流
  if (!validateCurrentInput(currentForm.targetCurrent)) {
    return
  }

  const success = await electromagnetStore.setCurrent(currentForm.targetCurrent)
  if (success) {
    ElMessage.success('电流设置成功')
  }
}

/**
 * 设置磁场强度
 */
async function handleSetField() {
  const success = await electromagnetStore.setField(currentForm.targetField)
  if (success) {
    ElMessage.success('磁场设置成功')
    // 更新目标电流显示
    currentForm.targetCurrent = electromagnetStore.calculateCurrent(currentForm.targetField)
  }
}

/**
 * 磁场强度变化处理
 * 根据磁场强度计算对应的电流值
 */
function handleFieldChange(value) {
  const current = electromagnetStore.calculateCurrent(value)
  if (!isNaN(current)) {
    currentForm.targetCurrent = current
  }
}

/**
 * 滑块变化处理
 */
function handleSliderChange(value) {
  currentForm.targetCurrent = value
  // 计算对应的磁场强度
  currentForm.targetField = electromagnetStore.calculateField(value)
}

/**
 * 验证扫描参数
 * 检查起始电流、终止电流、步进等参数的合理性
 */
function validateScanParams() {
  // 重置错误状态
  scanValidation.startError = ''
  scanValidation.endError = ''
  scanValidation.rateError = ''
  scanValidation.stepError = ''
  scanValidation.delayError = ''
  scanValidation.isValid = false
  scanPreview.isValid = false

  const minLimit = electromagnetStore.currentLimits.min
  const maxLimit = electromagnetStore.currentLimits.max

  // 验证起始电流
  if (scanForm.startCurrent < minLimit || scanForm.startCurrent > maxLimit) {
    scanValidation.startError = `起始电流超出范围 (${minLimit}A ~ ${maxLimit}A)`
    return false
  }

  // 验证终止电流
  if (scanForm.endCurrent < minLimit || scanForm.endCurrent > maxLimit) {
    scanValidation.endError = `终止电流超出范围 (${minLimit}A ~ ${maxLimit}A)`
    return false
  }

  // 检查起始和终止电流是否相同
  if (Math.abs(scanForm.startCurrent - scanForm.endCurrent) < 0.001) {
    scanValidation.endError = '终止电流不能等于起始电流'
    return false
  }

  // 线性扫描模式验证
  if (scanForm.mode === 'linear') {
    if (scanForm.scanRate <= 0) {
      scanValidation.rateError = '扫描速率必须大于0'
      return false
    }
    if (scanForm.scanRate > 1) {
      scanValidation.rateError = '扫描速率过高，建议不超过1A/s'
    }
  }

  // 步进扫描模式验证
  if (scanForm.mode === 'step') {
    if (scanForm.stepCount < 2) {
      scanValidation.stepError = '步数至少为2'
      return false
    }
    if (scanForm.stepCount > 1000) {
      scanValidation.stepError = '步数过多，建议不超过1000'
      return false
    }
    if (scanForm.stepDelay < 0.1) {
      scanValidation.delayError = '步间延时不小于0.1s'
      return false
    }
  }

  // 验证通过，更新预览
  scanValidation.isValid = true
  updateScanPreview()

  return true
}

/**
 * 更新步数
 * 根据步进大小自动计算步数
 */
function updateStepCount() {
  if (scanForm.stepSize <= 0) return

  const currentRange = Math.abs(scanForm.endCurrent - scanForm.startCurrent)
  scanForm.stepCount = Math.ceil(currentRange / scanForm.stepSize) + 1

  // 限制最大步数
  if (scanForm.stepCount > 1000) {
    scanForm.stepCount = 1000
  }

  validateScanParams()
}

/**
 * 更新扫描预览
 * 计算扫描的总步数、预计时长等信息
 */
function updateScanPreview() {
  if (!scanValidation.isValid) {
    scanPreview.isValid = false
    return
  }

  const currentRange = Math.abs(scanForm.endCurrent - scanForm.startCurrent)

  // 计算总步数
  if (scanForm.mode === 'linear') {
    scanPreview.totalSteps = Math.ceil(currentRange / scanForm.scanRate)
  } else if (scanForm.mode === 'step') {
    scanPreview.totalSteps = scanForm.stepCount
  }

  // 计算预计时长
  if (scanForm.mode === 'linear') {
    const timeSeconds = currentRange / scanForm.scanRate
    scanPreview.estimatedTime = formatDuration(timeSeconds)
  } else if (scanForm.mode === 'step') {
    const timeSeconds = (scanForm.stepCount - 1) * scanForm.stepDelay
    scanPreview.estimatedTime = formatDuration(timeSeconds)
  }

  // 电流范围
  const minCurrent = Math.min(scanForm.startCurrent, scanForm.endCurrent)
  const maxCurrent = Math.max(scanForm.startCurrent, scanForm.endCurrent)
  scanPreview.currentRange = `${minCurrent.toFixed(3)}A ~ ${maxCurrent.toFixed(3)}A`

  // 扫描方向
  if (scanForm.mode === 'linear') {
    scanPreview.direction = scanForm.endCurrent > scanForm.startCurrent ? '正向扫描' : '反向扫描'
  }

  scanPreview.isValid = true
}

/**
 * 格式化时长
 * 将秒数转换为易读的时间格式
 */
function formatDuration(seconds) {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}秒`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const secs = (seconds % 60).toFixed(0)
    return `${minutes}分${secs}秒`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}小时${minutes}分`
  }
}

/**
 * 配置扫描
 */
async function handleConfigScan() {
  // 验证扫描参数
  if (!validateScanParams()) {
    ElMessage.warning('请检查扫描参数')
    return
  }

  const success = await electromagnetStore.configureScan(scanForm)
  if (success) {
    ElMessage.success('扫描配置成功')
  }
}

/**
 * 验证扫描参数
 */
async function handleValidateScanConfig() {
  const result = await electromagnetStore.validateScanConfig(scanForm)
  if (result) {
    if (result.valid) {
      ElMessage.success('扫描参数验证通过')
    } else {
      ElMessage.warning(`参数验证失败: ${result.message || '未知错误'}`)
    }
  }
}

/**
 * 开始扫描
 */
async function handleStartScan() {
  const success = await electromagnetStore.startScan()
  if (success) {
    ElMessage.success('扫描已开始')
  }
}

/**
 * 暂停扫描
 */
async function handlePauseScan() {
  const success = await electromagnetStore.pauseScan()
  if (success) {
    ElMessage.info('扫描已暂停')
  }
}

/**
 * 停止扫描
 */
async function handleStopScan() {
  const success = await electromagnetStore.stopScan()
  if (success) {
    ElMessage.warning('扫描已停止')
  }
}

/**
 * 扫描进度格式化
 */
function scanProgressFormat(percentage) {
  return percentage.toFixed(1) + '%'
}

/**
 * 格式化剩余时间
 * @param {number} seconds - 剩余秒数
 * @returns {string} 格式化的时间字符串
 */
function formatRemainingTime(seconds) {
  if (!seconds || seconds <= 0) {
    return '-'
  }

  if (seconds < 60) {
    return `${Math.ceil(seconds)}秒`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const secs = Math.ceil(seconds % 60)
    return `${minutes}分${secs}秒`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}小时${minutes}分`
  }
}

/**
 * 初始化扫描数据图表
 */
function initScanChart() {
  if (!scanChartRef.value) return

  scanChart = echarts.init(scanChartRef.value)

  const option = {
    grid: {
      left: '10%',
      right: '5%',
      top: '10%',
      bottom: '15%'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'var(--color-surface-elevated)',
      borderColor: 'var(--color-border-primary)',
      textStyle: {
        color: 'var(--color-text-primary)'
      },
      formatter: (params) => {
        if (params.length === 0) return ''
        const index = params[0].dataIndex
        const current = electromagnetStore.scanData.current[index]
        const field = electromagnetStore.scanData.field[index]
        return `电流: ${current.toFixed(3)} A<br/>磁场: ${field.toFixed(2)} mT`
      }
    },
    legend: {
      data: ['电流', '磁场'],
      top: 0,
      right: 10,
      textStyle: {
        color: 'var(--color-text-secondary)'
      }
    },
    xAxis: {
      type: 'category',
      name: '数据点',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      splitLine: {
        show: false
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '电流 (A)',
        nameLocation: 'middle',
        nameGap: 40,
        nameTextStyle: {
          color: 'var(--color-text-secondary)'
        },
        axisLine: {
          lineStyle: {
            color: 'var(--color-data-blue)'
          }
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: 'var(--color-border-secondary)',
            type: 'dashed'
          }
        }
      },
      {
        type: 'value',
        name: '磁场 (mT)',
        nameLocation: 'middle',
        nameGap: 40,
        nameTextStyle: {
          color: 'var(--color-text-secondary)'
        },
        axisLine: {
          lineStyle: {
            color: 'var(--color-data-green)'
          }
        },
        splitLine: {
          show: false
        }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: 0,
        filterMode: 'none'
      },
      {
        type: 'slider',
        xAxisIndex: 0,
        filterMode: 'none',
        height: 20,
        bottom: 5
      }
    ],
    series: [
      {
        name: '电流',
        type: 'line',
        yAxisIndex: 0,
        data: [],
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-blue)',
          width: 2
        },
        symbol: 'none'
      },
      {
        name: '磁场',
        type: 'line',
        yAxisIndex: 1,
        data: [],
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-green)',
          width: 2
        },
        symbol: 'none'
      }
    ]
  }

  scanChart.setOption(option)
}

/**
 * 更新扫描数据图表
 */
function updateScanChart() {
  if (!scanChart) return

  const data = electromagnetStore.scanData
  const indices = data.current.map((_, i) => i)

  scanChart.setOption({
    xAxis: {
      data: indices
    },
    series: [
      { data: data.current },
      { data: data.field }
    ]
  })
}

/**
 * 导出扫描数据
 */
function handleExportScanData() {
  const csvContent = electromagnetStore.exportScanData()
  if (!csvContent) {
    ElMessage.warning('没有扫描数据可导出')
    return
  }

  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `scan_data_${new Date().toISOString().slice(0, 10)}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  ElMessage.success('扫描数据已导出')
}

/**
 * 清除扫描数据
 */
function handleClearScanData() {
  electromagnetStore.clearScanData()
  updateScanChart()
  ElMessage.info('扫描数据已清除')
}

/**
 * 添加校准点
 */
function handleAddCalibrationPoint() {
  calibrationPoints.value.push({
    current: newCalibrationPoint.current,
    field: newCalibrationPoint.field
  })

  // 更新图表
  updateCalibrationChart()

  ElMessage.success('校准点已添加')
}

/**
 * 删除校准点
 */
function handleRemoveCalibrationPoint(index) {
  calibrationPoints.value.splice(index, 1)
  updateCalibrationChart()
}

/**
 * 清除所有校准点
 */
function handleClearCalibrationPoints() {
  calibrationPoints.value = []
  updateCalibrationChart()
}

/**
 * 清除校准数据（从设备端清除）
 */
async function handleClearCalibration() {
  const success = await electromagnetStore.clearCalibration()
  if (success) {
    ElMessage.success('校准数据已清除')
    calibrationPoints.value = []
    calibrationQuality.isValid = false
    updateCalibrationChart()
  }
}

/**
 * 上传校准曲线
 */
async function handleUploadCalibration() {
  const success = await electromagnetStore.uploadCalibration(calibrationPoints.value)
  if (success) {
    ElMessage.success('校准曲线已上传')
  }
}

/**
 * 验证校准数据
 */
async function handleValidateCalibration() {
  const result = await electromagnetStore.validateCalibration(calibrationPoints.value)
  if (result) {
    if (result.valid) {
      ElMessage.success(`校准数据验证通过，预计精度: ${result.accuracy || '未知'}`)
    } else {
      ElMessage.warning(`校准数据验证失败: ${result.message || '未知错误'}`)
    }
  }
}

/**
 * 执行校准
 */
async function handlePerformCalibration() {
  const result = await electromagnetStore.performCalibration(calibrationPoints.value)
  if (result) {
    ElMessage.success('校准执行成功')
    updateCalibrationChart()
  }
}

/**
 * 获取校准曲线
 */
async function handleFetchCalibration() {
  const result = await electromagnetStore.fetchCalibration()
  if (result && result.points) {
    calibrationPoints.value = result.points
    updateCalibrationChart()
    calculateCalibrationQuality()
  }
}

/**
 * 计算校准质量指标
 * 计算R²、RMSE、最大偏差等指标
 */
function calculateCalibrationQuality() {
  if (calibrationPoints.value.length < 3) {
    calibrationQuality.isValid = false
    return
  }

  const coefficients = electromagnetStore.calibrationCurve.coefficients
  if (!coefficients) {
    calibrationQuality.isValid = false
    return
  }

  // 计算预测值和残差
  const points = calibrationPoints.value
  const predicted = points.map(p => electromagnetStore.calculateField(p.current))
  const actual = points.map(p => p.field)

  // 计算残差
  const residuals = actual.map((a, i) => a - predicted[i])

  // 计算R²
  const meanActual = actual.reduce((sum, a) => sum + a, 0) / actual.length
  const ssTotal = actual.reduce((sum, a) => sum + Math.pow(a - meanActual, 2), 0)
  const ssResidual = residuals.reduce((sum, r) => sum + r * r, 0)
  calibrationQuality.r2 = 1 - (ssResidual / ssTotal)

  // 计算RMSE
  calibrationQuality.rmse = Math.sqrt(ssResidual / actual.length)

  // 计算最大偏差
  calibrationQuality.maxError = Math.max(...residuals.map(Math.abs))

  calibrationQuality.isValid = true
}

/**
 * 获取质量指标样式类
 */
function getQualityClass(type) {
  if (type === 'r2') {
    if (calibrationQuality.r2 >= 0.99) return 'quality-excellent'
    if (calibrationQuality.r2 >= 0.95) return 'quality-good'
    if (calibrationQuality.r2 >= 0.90) return 'quality-fair'
    return 'quality-poor'
  }
  return ''
}

/**
 * 导出校准数据
 */
function handleExportCalibration() {
  if (calibrationPoints.value.length === 0) {
    ElMessage.warning('没有校准数据可导出')
    return
  }

  // 生成CSV数据
  const headers = ['电流(A)', '磁场(mT)', '预测磁场(mT)', '偏差(mT)']
  const rows = calibrationPoints.value.map(p => {
    const predicted = electromagnetStore.calculateField(p.current)
    const error = p.field - predicted
    return [p.current.toFixed(4), p.field.toFixed(2), predicted.toFixed(2), error.toFixed(2)]
  })

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n')

  // 创建下载链接
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `calibration_${new Date().toISOString().slice(0, 10)}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  ElMessage.success('校准数据已导出')
}

/**
 * 急停
 */
async function handleEmergencyStop() {
  const success = await electromagnetStore.emergencyStop()
  if (success) {
    ElMessage.error('急停已触发')
  }
}

/**
 * 复位急停
 */
async function handleResetEmergency() {
  const success = await electromagnetStore.resetEmergency()
  if (success) {
    ElMessage.success('急停已复位')
  }
}

/**
 * 过流保护复位
 */
async function handleResetOvercurrent() {
  const success = await electromagnetStore.resetOvercurrent()
  if (success) {
    ElMessage.success('过流保护已复位')
  }
}

/**
 * 初始化校准图表
 */
function initCalibrationChart() {
  if (!calibrationChartRef.value) return

  calibrationChart = echarts.init(calibrationChartRef.value)

  const option = {
    grid: {
      left: '15%',
      right: '5%',
      top: '10%',
      bottom: '15%'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'var(--color-surface-elevated)',
      borderColor: 'var(--color-border-primary)',
      textStyle: {
        color: 'var(--color-text-primary)'
      },
      formatter: (params) => {
        if (params.length === 0) return ''
        const point = params[0]
        let tooltip = `电流: ${point.value[0].toFixed(3)} A<br/>磁场: ${point.value[1].toFixed(2)} mT`
        
        // 如果是校准点，显示偏差
        if (point.seriesName === '校准点') {
          const predicted = electromagnetStore.calculateField(point.value[0])
          const error = point.value[1] - predicted
          tooltip += `<br/>偏差: ${error.toFixed(2)} mT`
        }
        
        return tooltip
      }
    },
    legend: {
      data: ['校准点', '拟合曲线', '实时数据'],
      top: 0,
      right: 10,
      textStyle: {
        color: 'var(--color-text-secondary)'
      }
    },
    xAxis: {
      type: 'value',
      name: '电流 (A)',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      min: electromagnetStore.currentLimits.min,
      max: electromagnetStore.currentLimits.max,
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      splitLine: {
        show: chartOptions.showGrid,
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '磁场 (mT)',
      nameLocation: 'middle',
      nameGap: 40,
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      splitLine: {
        show: chartOptions.showGrid,
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '校准点',
        type: 'scatter',
        data: [],
        symbolSize: 10,
        itemStyle: {
          color: 'var(--color-data-blue)'
        },
        emphasis: {
          itemStyle: {
            borderColor: 'var(--color-text-primary)',
            borderWidth: 2
          }
        }
      },
      {
        name: '拟合曲线',
        type: 'line',
        data: [],
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-green)',
          width: 2
        },
        symbol: 'none'
      },
      {
        name: '实时数据',
        type: 'scatter',
        data: [],
        symbolSize: 8,
        itemStyle: {
          color: 'var(--color-data-red)'
        }
      }
    ]
  }

  calibrationChart.setOption(option)
}

/**
 * 更新校准图表
 */
function updateCalibrationChart() {
  if (!calibrationChart) return

  // 校准点数据
  const pointsData = calibrationPoints.value.map(p => [p.current, p.field])

  // 拟合曲线数据
  const fitData = []
  if (chartOptions.showFitCurve && electromagnetStore.calibrationCurve.coefficients) {
    const min = electromagnetStore.currentLimits.min
    const max = electromagnetStore.currentLimits.max
    const step = (max - min) / 100

    for (let current = min; current <= max; current += step) {
      const field = electromagnetStore.calculateField(current)
      fitData.push([current, field])
    }
  }

  // 实时数据点
  let realtimeData = []
  if (chartOptions.showRealtime && electromagnetStore.currentCurrent !== 0) {
    realtimeData = [[
      electromagnetStore.currentCurrent,
      electromagnetStore.currentField
    ]]
  }

  calibrationChart.setOption({
    xAxis: {
      splitLine: {
        show: chartOptions.showGrid
      }
    },
    yAxis: {
      splitLine: {
        show: chartOptions.showGrid
      }
    },
    series: [
      { data: pointsData },
      { data: fitData },
      { data: realtimeData }
    ]
  })
}

/**
 * 窗口大小变化处理
 */
function handleResize() {
  calibrationChart?.resize()
}

// ============ 监听器 ============

// 监听当前电流变化，更新目标磁场
watch(() => electromagnetStore.currentCurrent, (newVal) => {
  currentForm.targetField = electromagnetStore.calculateField(newVal)
})

// 监听目标电流变化，更新目标磁场
watch(() => currentForm.targetCurrent, (newVal) => {
  currentForm.targetField = electromagnetStore.calculateField(newVal)
})

// 监听校准系数变化，更新图表
watch(() => electromagnetStore.calibrationCurve.coefficients, () => {
  updateCalibrationChart()
}, { deep: true })

// 监听扫描模式变化，重新验证参数
watch(() => scanForm.mode, () => {
  validateScanParams()
})

// 监听扫描参数变化，更新预览
watch([
  () => scanForm.startCurrent,
  () => scanForm.endCurrent,
  () => scanForm.stepCount,
  () => scanForm.stepDelay,
  () => scanForm.scanRate
], () => {
  if (scanValidation.isValid) {
    updateScanPreview()
  }
})

// 监听扫描数据变化，更新图表
watch(() => electromagnetStore.scanData.current, () => {
  updateScanChart()
}, { deep: true })

// ============ 生命周期 ============

onMounted(() => {
  electromagnetStore.init()
  initCalibrationChart()
  initScanChart()
  window.addEventListener('resize', handleResize)

  // 初始化目标磁场
  currentForm.targetField = electromagnetStore.calculateField(currentForm.targetCurrent)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  calibrationChart?.dispose()
  scanChart?.dispose()
  electromagnetStore.cleanup()
})
</script>

<style scoped>
.electromagnet-control {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.electromagnet-control:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-2);
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

.status-tag {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
}

.control-content {
  padding: var(--spacing-3) 0;
}

.alarm-alert {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-md);
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 实时数据显示 */
.realtime-display {
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-4);
  background: linear-gradient(135deg, var(--color-primary-600) 0%, var(--color-accent-700) 100%);
  border-radius: var(--radius-lg);
  color: var(--color-text-inverse);
}

.display-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.display-item:hover {
  background-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.display-icon {
  font-size: var(--font-size-3xl);
  opacity: 0.9;
}

.display-content {
  flex: 1;
}

.display-content .label {
  font-size: var(--font-size-sm);
  opacity: 0.9;
  margin-bottom: var(--spacing-1);
}

.value-row {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-2);
}

.display-content .value {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  font-family: var(--font-family-mono);
  letter-spacing: 0.05em;
}

.display-content .unit {
  font-size: var(--font-size-base);
  opacity: 0.8;
}

/* 分割线 */
.section-divider {
  margin: var(--spacing-4) 0;
}

/* 表单样式 */
.current-form,
.scan-form {
  margin-bottom: var(--spacing-4);
}

.form-item {
  margin-bottom: var(--spacing-3);
  transition: var(--transition-all);
}

.form-item:hover {
  background-color: var(--color-interactive-hover);
  border-radius: var(--radius-sm);
}

.input-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.form-number {
  width: 200px;
}

.form-number.small {
  width: 150px;
}

.unit-label {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  min-width: 30px;
}

.validation-tag {
  margin-left: var(--spacing-2);
}

.error-message {
  color: var(--color-error);
  font-size: var(--font-size-xs);
  line-height: 1.2;
  padding-top: var(--spacing-1);
}

.set-btn {
  margin-left: var(--spacing-2);
}

/* 按钮组样式 */
.button-group {
  display: flex;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

/* 滑块样式 */
.current-slider {
  padding: 0 var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.slider-control {
  --el-slider-main-bg-color: var(--color-primary-500);
  --el-slider-runway-bg-color: var(--color-border-primary);
}

/* 扫描模式单选组 */
.mode-radio-group {
  display: flex;
  gap: var(--spacing-4);
}

/* 扫描预览卡片 */
.scan-preview-card {
  width: 100%;
  background-color: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
}

.preview-item {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-2) 0;
  border-bottom: 1px dashed var(--color-border-primary);
}

.preview-item:last-child {
  border-bottom: none;
}

.preview-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.preview-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
}

.config-btn {
  min-width: 120px;
}

/* 扫描控制按钮 */
.scan-controls {
  display: flex;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-4);
}

.control-btn {
  flex: 1;
  transition: var(--transition-all);
}

.control-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* 扫描进度 */
.scan-progress {
  padding: var(--spacing-4);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-4);
  border: 1px solid var(--color-border-primary);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.progress-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.progress-bar {
  margin-bottom: var(--spacing-3);
}

.progress-details {
  margin-bottom: var(--spacing-3);
}

.detail-item {
  text-align: center;
  padding: var(--spacing-2);
}

.detail-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-1);
}

.detail-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.scan-direction {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.direction-icon {
  font-size: var(--font-size-lg);
  transition: var(--transition-all);
}

.direction-icon.forward {
  color: var(--color-success);
}

.direction-icon.backward {
  color: var(--color-primary-500);
}

/* 扫描数据绘图 */
.scan-data-plot {
  padding: var(--spacing-4);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-4);
  border: 1px solid var(--color-border-primary);
}

.plot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.plot-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.plot-actions {
  display: flex;
  gap: var(--spacing-2);
}

.scan-chart {
  width: 100%;
  height: 300px;
  margin-bottom: var(--spacing-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.scan-stats {
  padding: var(--spacing-3);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-sm);
}

.stat-item {
  text-align: center;
  padding: var(--spacing-2);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-1);
}

.stat-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

/* 校准区域 */
.calibration-section {
  margin-bottom: var(--spacing-4);
}

.calibration-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.calibration-status {
  font-weight: var(--font-weight-medium);
}

.calibration-actions-header {
  display: flex;
  gap: var(--spacing-2);
}

.action-btn {
  transition: var(--transition-all);
}

.action-btn:hover {
  transform: translateY(-2px);
}

/* 校准质量指标 */
.calibration-quality {
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-3);
  border: 1px solid var(--color-border-primary);
}

.quality-item {
  text-align: center;
  padding: var(--spacing-2);
}

.quality-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-1);
}

.quality-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.quality-excellent {
  color: var(--color-success);
}

.quality-good {
  color: var(--color-primary-500);
}

.quality-fair {
  color: var(--color-warning);
}

.quality-poor {
  color: var(--color-error);
}

/* 校准图表 */
.calibration-chart {
  width: 100%;
  height: 300px;
  margin-bottom: var(--spacing-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

/* 图表控制 */
.chart-controls {
  display: flex;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-3);
  padding: var(--spacing-2);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-sm);
}

/* 添加校准点 */
.add-calibration-point {
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-3);
  border: 1px solid var(--color-border-primary);
}

.add-point-btn {
  transition: var(--transition-all);
}

.add-point-btn:hover {
  transform: translateY(-2px);
}

/* 校准点列表 */
.calibration-points-list {
  margin-bottom: var(--spacing-3);
}

.points-table {
  font-size: var(--font-size-sm);
}

.mono {
  font-family: var(--font-family-mono);
}

.delete-btn {
  transition: var(--transition-all);
}

.delete-btn:hover {
  transform: translateX(4px);
}

/* 校准操作按钮 */
.calibration-actions {
  display: flex;
  gap: var(--spacing-3);
}

.calibration-btn {
  flex: 1;
  transition: var(--transition-all);
}

.calibration-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* 安全控制 */
.safety-controls {
  display: flex;
  justify-content: center;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.emergency-btn,
.reset-btn {
  min-width: 160px;
  height: 60px;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  transition: var(--transition-all);
}

.emergency-btn:hover,
.reset-btn:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-glow-error);
}

.reset-btn:hover {
  box-shadow: var(--shadow-glow-warning);
}

/* Element Plus 样式覆盖 */
:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
}

:deep(.el-divider__text) {
  background-color: var(--color-surface-primary);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

:deep(.el-input-number) {
  font-family: var(--font-family-mono);
}

:deep(.el-slider__marks-text) {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

:deep(.el-table) {
  background-color: var(--color-surface-primary);
}

:deep(.el-table th.el-table__cell) {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .realtime-display .el-col {
    margin-bottom: var(--spacing-3);
  }
  
  .display-content .value {
    font-size: var(--font-size-2xl);
  }
  
  .scan-controls {
    flex-direction: column;
  }
  
  .calibration-actions {
    flex-direction: column;
  }
  
  .calibration-quality .el-col {
    margin-bottom: var(--spacing-2);
  }

  .progress-details .el-col {
    margin-bottom: var(--spacing-2);
  }

  .scan-chart {
    height: 250px;
  }

  .scan-stats .el-col {
    margin-bottom: var(--spacing-2);
  }
}
</style>
