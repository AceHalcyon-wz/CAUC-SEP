<template>
  <div class="calibration-editor">
    <!-- 编辑器头部 -->
    <div class="editor-header">
      <div class="header-left">
        <h3 class="editor-title">
          校准曲线编辑器
        </h3>
        <div class="calibration-mode">
          <span class="mode-label">校准模式:</span>
          <el-select
            v-model="currentMode"
            size="small"
            @change="handleModeChange"
          >
            <el-option
              label="线性校准"
              value="linear"
            />
            <el-option
              label="多项式校准"
              value="polynomial"
            />
            <el-option
              label="查表校准"
              value="lookup_table"
            />
            <el-option
              label="自动校准"
              value="auto"
            />
          </el-select>
        </div>
      </div>
      <div class="header-right">
        <button
          class="tool-btn"
          title="导入校准数据"
          @click="importCalibrationData"
        >
          <el-icon><Upload /></el-icon>
          <span>导入</span>
        </button>
        <button
          class="tool-btn"
          :disabled="calibrationPoints.length === 0"
          title="导出校准数据"
          @click="exportCalibrationData"
        >
          <el-icon><Download /></el-icon>
          <span>导出</span>
        </button>
        <button
          class="tool-btn"
          title="校准历史"
          @click="showHistoryDialog = true"
        >
          <el-icon><Clock /></el-icon>
          <span>历史</span>
        </button>
      </div>
    </div>

    <!-- 主编辑区域 -->
    <div class="editor-main">
      <!-- 图表区域 -->
      <div class="chart-section">
        <div
          ref="chartContainer"
          class="chart-container"
        />

        <!-- 图例说明 -->
        <div class="chart-legend">
          <div class="legend-item">
            <span class="legend-dot legend-dot--actual" />
            <span class="legend-label">实际校准点</span>
          </div>
          <div class="legend-item">
            <span class="legend-line legend-line--fitted" />
            <span class="legend-label">拟合曲线</span>
          </div>
          <div class="legend-item">
            <span class="legend-line legend-line--theoretical" />
            <span class="legend-label">理论曲线</span>
          </div>
        </div>
      </div>

      <!-- 控制面板 -->
      <div class="control-panel">
        <!-- 校准点列表 -->
        <div class="points-section">
          <div class="section-header">
            <h4 class="section-title">
              校准点列表
            </h4>
            <button
              class="add-btn"
              :disabled="!piezoStore.canControl"
              @click="addCalibrationPoint"
            >
              <el-icon><Plus /></el-icon>
              <span>添加点</span>
            </button>
          </div>

          <div
            v-if="calibrationPoints.length > 0"
            class="points-list"
          >
            <div
              v-for="(point, index) in calibrationPoints"
              :key="index"
              class="point-item"
              :class="{ 'point-item--selected': selectedIndex === index }"
              @click="selectPoint(index)"
            >
              <div class="point-index">
                {{ index + 1 }}
              </div>
              <div class="point-data">
                <div class="data-row">
                  <span class="data-label">电压:</span>
                  <input
                    v-model.number="point.voltage"
                    type="number"
                    step="0.1"
                    min="0"
                    max="150"
                    class="data-input"
                    @change="handlePointChange(index)"
                  >
                  <span class="data-unit">V</span>
                </div>
                <div class="data-row">
                  <span class="data-label">位移:</span>
                  <input
                    v-model.number="point.displacement"
                    type="number"
                    step="0.001"
                    class="data-input"
                    @change="handlePointChange(index)"
                  >
                  <span class="data-unit">μm</span>
                </div>
              </div>
              <button
                class="delete-btn"
                title="删除此点"
                @click.stop="deletePoint(index)"
              >
                <el-icon><Close /></el-icon>
              </button>
            </div>
          </div>

          <div
            v-else
            class="empty-state"
          >
            <el-icon class="empty-icon">
              <Document />
            </el-icon>
            <p class="empty-text">
              暂无校准点
            </p>
            <p class="empty-hint">
              点击"添加点"按钮开始校准
            </p>
          </div>
        </div>

        <!-- 拟合参数 -->
        <div
          v-if="fitResult"
          class="fit-params"
        >
          <h4 class="section-title">
            拟合参数
          </h4>
          <div class="params-grid">
            <div class="param-item">
              <span class="param-label">拟合类型:</span>
              <span class="param-value">{{ fitResult.type }}</span>
            </div>
            <div class="param-item">
              <span class="param-label">R²:</span>
              <span class="param-value">{{ fitResult.r2.toFixed(4) }}</span>
            </div>
            <div
              v-if="fitResult.type === 'linear'"
              class="param-item"
            >
              <span class="param-label">斜率 (a):</span>
              <span class="param-value">{{ fitResult.coefficients.a.toFixed(6) }}</span>
            </div>
            <div
              v-if="fitResult.type === 'linear'"
              class="param-item"
            >
              <span class="param-label">截距 (b):</span>
              <span class="param-value">{{ fitResult.coefficients.b.toFixed(6) }}</span>
            </div>
            <div
              v-if="fitResult.type === 'polynomial'"
              class="param-item"
            >
              <span class="param-label">多项式系数:</span>
              <span class="param-value">{{ fitResult.coefficients.map(c => c.toFixed(6)).join(', ') }}</span>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <button
            class="action-btn action-btn--primary"
            :disabled="calibrationPoints.length < 2"
            @click="performFit"
          >
            <el-icon><Check /></el-icon>
            <span>执行拟合</span>
          </button>
          <button
            class="action-btn"
            :disabled="!fitResult"
            @click="applyCalibration"
          >
            <el-icon><Select /></el-icon>
            <span>应用校准</span>
          </button>
          <button
            class="action-btn"
            :disabled="calibrationPoints.length === 0"
            @click="clearPoints"
          >
            <el-icon><Delete /></el-icon>
            <span>清空</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 校准进度显示 -->
    <div
      v-if="isCalibrating"
      class="calibration-progress"
    >
      <div class="progress-header">
        <span class="progress-title">校准进度</span>
        <span class="progress-percent">{{ calibrationProgress }}%</span>
      </div>
      <el-progress
        :percentage="calibrationProgress"
        :stroke-width="8"
        :show-text="false"
        :color="progressColor"
      />
      <div class="progress-steps">
        <div
          v-for="(step, index) in calibrationSteps"
          :key="index"
          class="step-item"
          :class="{
            'step-item--active': currentStep === index,
            'step-item--completed': currentStep > index
          }"
        >
          <div class="step-indicator">
            {{ index + 1 }}
          </div>
          <div class="step-label">
            {{ step }}
          </div>
        </div>
      </div>
    </div>

    <!-- 校准结果统计 -->
    <div
      v-if="fitResult && !isCalibrating"
      class="calibration-result"
    >
      <h4 class="result-title">
        校准结果统计
      </h4>
      <div class="result-stats">
        <div class="stat-item">
          <div class="stat-icon stat-icon--success">
            <el-icon><SuccessFilled /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">
              拟合优度
            </div>
            <div class="stat-value">
              {{ (fitResult.r2 * 100).toFixed(2) }}%
            </div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon stat-icon--primary">
            <el-icon><DataAnalysis /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">
              平均误差
            </div>
            <div class="stat-value">
              {{ averageError.toFixed(4) }} μm
            </div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon stat-icon--warning">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">
              最大误差
            </div>
            <div class="stat-value">
              {{ maxError.toFixed(4) }} μm
            </div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon stat-icon--info">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">
              校准点数
            </div>
            <div class="stat-value">
              {{ calibrationPoints.length }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="showImportDialog"
      title="导入校准数据"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        :model="importForm"
        label-width="100px"
      >
        <el-form-item label="导入方式">
          <el-radio-group v-model="importForm.method">
            <el-radio label="file">
              文件上传
            </el-radio>
            <el-radio label="paste">
              粘贴数据
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          v-if="importForm.method === 'file'"
          label="文件格式"
        >
          <el-select v-model="importForm.format">
            <el-option
              label="CSV"
              value="csv"
            />
            <el-option
              label="JSON"
              value="json"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="importForm.method === 'file'"
          label="选择文件"
        >
          <input
            type="file"
            :accept="importForm.format === 'csv' ? '.csv' : '.json'"
            class="file-input"
            @change="handleFileSelect"
          >
        </el-form-item>

        <el-form-item
          v-if="importForm.method === 'paste'"
          label="数据内容"
        >
          <el-input
            v-model="importForm.content"
            type="textarea"
            :rows="8"
            placeholder="粘贴CSV格式数据（每行：电压,位移）"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showImportDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="confirmImport"
        >
          确认导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 导出对话框 -->
    <el-dialog
      v-model="showExportDialog"
      title="导出校准数据"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form
        :model="exportForm"
        label-width="100px"
      >
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportForm.format">
            <el-radio label="csv">
              CSV
            </el-radio>
            <el-radio label="json">
              JSON
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="文件名">
          <el-input
            v-model="exportForm.filename"
            placeholder="请输入文件名"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExportDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="confirmExport"
        >
          确认导出
        </el-button>
      </template>
    </el-dialog>

    <!-- 历史版本对话框 -->
    <el-dialog
      v-model="showHistoryDialog"
      title="校准历史版本"
      width="600px"
    >
      <div
        v-if="calibrationHistory.length > 0"
        class="history-list"
      >
        <div
          v-for="(item, index) in calibrationHistory"
          :key="index"
          class="history-item"
        >
          <div class="history-info">
            <div class="history-time">
              {{ formatTime(item.timestamp) }}
            </div>
            <div class="history-meta">
              <span class="meta-item">模式: {{ item.mode }}</span>
              <span class="meta-item">点数: {{ item.points.length }}</span>
              <span class="meta-item">R²: {{ item.r2.toFixed(4) }}</span>
            </div>
          </div>
          <div class="history-actions">
            <button
              class="history-btn"
              @click="restoreHistory(index)"
            >
              <el-icon><RefreshRight /></el-icon>
              <span>恢复</span>
            </button>
            <button
              class="history-btn history-btn--danger"
              @click="deleteHistory(index)"
            >
              <el-icon><Delete /></el-icon>
              <span>删除</span>
            </button>
          </div>
        </div>
      </div>
      <div
        v-else
        class="empty-state"
      >
        <el-icon class="empty-icon">
          <Clock />
        </el-icon>
        <p class="empty-text">
          暂无历史版本
        </p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file PiezoCalibrationEditor.vue
 * @path src/components/
 * @description 校准曲线可视化编辑器，支持拖拽调整、实时预览、多种校准模式
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, element-plus, echarts, stores/piezo
 */

import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import * as echarts from 'echarts';
import { usePiezoStore } from '@/stores/piezo';

// ============ Store 初始化 ============

const piezoStore = usePiezoStore();

// ============ 响应式状态 ============

/** 图表容器引用 */
const chartContainer = ref(null);

/** 图表实例 */
let chartInstance = null;

/** 当前校准模式 */
const currentMode = ref('linear');

/** 校准点数据 */
const calibrationPoints = ref([]);

/** 选中的校准点索引 */
const selectedIndex = ref(-1);

/** 拟合结果 */
const fitResult = ref(null);

/** 是否正在校准 */
const isCalibrating = ref(false);

/** 校准进度 */
const calibrationProgress = ref(0);

/** 当前步骤 */
const currentStep = ref(0);

/** 校准步骤 */
const calibrationSteps = ref([
  '准备校准环境',
  '采集校准点',
  '执行拟合计算',
  '验证校准结果',
  '保存校准数据'
]);

/** 进度条颜色 */
const progressColor = ref('#3182ce');

/** 导入对话框 */
const showImportDialog = ref(false);

/** 导入表单 */
const importForm = ref({
  method: 'file',
  format: 'csv',
  content: '',
  file: null
});

/** 导出对话框 */
const showExportDialog = ref(false);

/** 导出表单 */
const exportForm = ref({
  format: 'csv',
  filename: `calibration_${Date.now()}`
});

/** 历史对话框 */
const showHistoryDialog = ref(false);

/** 校准历史 */
const calibrationHistory = ref([]);

/** 拖拽状态 */
const isDragging = ref(false);

/** 拖拽的点索引 */
const dragPointIndex = ref(-1);

// ============ 计算属性 ============

/**
 * 平均误差
 */
const averageError = computed(() => {
  if (!fitResult.value || calibrationPoints.value.length === 0) return 0;

  let totalError = 0;
  calibrationPoints.value.forEach(point => {
    const predicted = predictDisplacement(point.voltage);
    const error = Math.abs(point.displacement - predicted);
    totalError += error;
  });

  return totalError / calibrationPoints.value.length;
});

/**
 * 最大误差
 */
const maxError = computed(() => {
  if (!fitResult.value || calibrationPoints.value.length === 0) return 0;

  let maxErr = 0;
  calibrationPoints.value.forEach(point => {
    const predicted = predictDisplacement(point.voltage);
    const error = Math.abs(point.displacement - predicted);
    if (error > maxErr) maxErr = error;
  });

  return maxErr;
});

// ============ 图表初始化与更新 ============

/**
 * 初始化图表
 */
function initChart() {
  if (!chartContainer.value) return;

  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartContainer.value);

  const option = {
    title: {
      text: '校准曲线',
      left: 'center',
      top: 10,
      textStyle: {
        color: 'var(--color-text-primary)',
        fontSize: 16,
        fontWeight: 600
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params) => {
        if (!params || params.length === 0) return '';
        let html = '<div style="padding: 8px;">';
        params.forEach(param => {
          html += `
            <div style="margin: 4px 0;">
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${param.color};margin-right:8px;"></span>
              <span>${param.seriesName}: ${param.value[1].toFixed(3)} μm</span>
            </div>
          `;
        });
        html += '</div>';
        return html;
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%',
      top: '20%'
    },
    xAxis: {
      type: 'value',
      name: '电压 (V)',
      nameLocation: 'middle',
      nameGap: 30,
      min: 0,
      max: 150,
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      axisLabel: {
        color: 'var(--color-text-secondary)'
      },
      splitLine: {
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '位移 (μm)',
      nameLocation: 'middle',
      nameGap: 40,
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      axisLabel: {
        color: 'var(--color-text-secondary)'
      },
      splitLine: {
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '实际校准点',
        type: 'scatter',
        data: [],
        symbolSize: 12,
        itemStyle: {
          color: 'var(--color-primary-500)',
          borderColor: '#fff',
          borderWidth: 2
        },
        emphasis: {
          itemStyle: {
            color: 'var(--color-primary-600)',
            borderColor: '#fff',
            borderWidth: 3
          }
        }
      },
      {
        name: '拟合曲线',
        type: 'line',
        data: [],
        smooth: false,
        showSymbol: false,
        lineStyle: {
          color: 'var(--color-data-green)',
          width: 2
        }
      },
      {
        name: '理论曲线',
        type: 'line',
        data: [],
        smooth: false,
        showSymbol: false,
        lineStyle: {
          color: 'var(--color-data-yellow)',
          type: 'dashed',
          width: 2
        }
      }
    ]
  };

  chartInstance.setOption(option);

  // 绑定拖拽事件
  chartInstance.on('mousedown', 'series.scatter', handleMouseDown);
  chartInstance.on('mousemove', handleMouseMove);
  chartInstance.on('mouseup', handleMouseUp);
}

/**
 * 更新图表数据
 */
function updateChart() {
  if (!chartInstance) return;

  // 校准点数据
  const pointsData = calibrationPoints.value.map(p => [p.voltage, p.displacement]);

  // 拟合曲线数据
  const fittedData = [];
  if (fitResult.value) {
    for (let v = 0; v <= 150; v += 1) {
      fittedData.push([v, predictDisplacement(v)]);
    }
  }

  // 理论曲线数据（假设线性关系 0.1 μm/V）
  const theoreticalData = [];
  for (let v = 0; v <= 150; v += 1) {
    theoreticalData.push([v, v * 0.1]);
  }

  chartInstance.setOption({
    series: [
      { data: pointsData },
      { data: fittedData },
      { data: theoreticalData }
    ]
  });
}

// ============ 拖拽处理 ============

/**
 * 鼠标按下事件
 */
function handleMouseDown(params) {
  if (params.componentType !== 'series' || params.seriesIndex !== 0) return;

  isDragging.value = true;
  dragPointIndex.value = params.dataIndex;

  // 禁用图表的默认拖拽行为
  chartInstance.getZr().setCursorStyle('move');
}

/**
 * 鼠标移动事件
 */
function handleMouseMove(params) {
  if (!isDragging.value || dragPointIndex.value < 0) return;

  const pointInPixel = [params.offsetX, params.offsetY];
  const pointInGrid = chartInstance.convertFromPixel('grid', pointInPixel);

  // 更新校准点位置
  const newVoltage = Math.max(0, Math.min(150, pointInGrid[0]));
  const newDisplacement = Math.max(0, pointInGrid[1]);

  calibrationPoints.value[dragPointIndex.value].voltage = newVoltage;
  calibrationPoints.value[dragPointIndex.value].displacement = newDisplacement;

  updateChart();
}

/**
 * 鼠标释放事件
 */
function handleMouseUp() {
  if (isDragging.value && dragPointIndex.value >= 0) {
    // 触发校准点变化事件
    handlePointChange(dragPointIndex.value);
  }

  isDragging.value = false;
  dragPointIndex.value = -1;
}

// ============ 校准点管理 ============

/**
 * 添加校准点
 */
function addCalibrationPoint() {
  const voltage = piezoStore.currentVoltage;
  const displacement = piezoStore.currentDisplacement / 1000; // nm -> μm

  calibrationPoints.value.push({
    voltage: voltage,
    displacement: displacement,
    timestamp: Date.now()
  });

  updateChart();
  ElMessage.success('已添加校准点');
}

/**
 * 选择校准点
 */
function selectPoint(index) {
  selectedIndex.value = index;
}

/**
 * 删除校准点
 */
function deletePoint(index) {
  calibrationPoints.value.splice(index, 1);
  selectedIndex.value = -1;
  updateChart();
  ElMessage.info('已删除校准点');
}

/**
 * 清空所有校准点
 */
function clearPoints() {
  ElMessageBox.confirm(
    '确定要清空所有校准点吗？',
    '确认清空',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    calibrationPoints.value = [];
    fitResult.value = null;
    selectedIndex.value = -1;
    updateChart();
    ElMessage.success('已清空所有校准点');
  }).catch(() => {
    // 用户取消
  });
}

/**
 * 处理校准点变化
 */
function handlePointChange(index) {
  updateChart();

  // 如果已有拟合结果，自动重新拟合
  if (fitResult.value) {
    performFit();
  }
}

// ============ 校准模式与拟合 ============

/**
 * 处理校准模式变化
 */
function handleModeChange(mode) {
  // 模式切换时清除拟合结果
  fitResult.value = null;
  updateChart();
}

/**
 * 执行拟合
 */
function performFit() {
  if (calibrationPoints.value.length < 2) {
    ElMessage.warning('至少需要2个校准点才能进行拟合');
    return;
  }

  try {
    let result = null;

    if (currentMode.value === 'linear') {
      result = performLinearFit();
    } else if (currentMode.value === 'polynomial') {
      result = performPolynomialFit();
    } else if (currentMode.value === 'lookup_table') {
      result = performLookupTableFit();
    } else if (currentMode.value === 'auto') {
      // 自动选择最佳拟合方式
      const linearResult = performLinearFit();
      const polyResult = performPolynomialFit();
      result = linearResult.r2 >= polyResult.r2 ? linearResult : polyResult;
    }

    fitResult.value = result;
    updateChart();

    ElMessage.success(`拟合完成，R² = ${result.r2.toFixed(4)}`);
  } catch (error) {
    ElMessage.error('拟合失败: ' + error.message);
  }
}

/**
 * 线性拟合
 */
function performLinearFit() {
  const points = calibrationPoints.value;
  const n = points.length;

  const sumX = points.reduce((acc, p) => acc + p.voltage, 0);
  const sumY = points.reduce((acc, p) => acc + p.displacement, 0);
  const sumXY = points.reduce((acc, p) => acc + p.voltage * p.displacement, 0);
  const sumX2 = points.reduce((acc, p) => acc + p.voltage * p.voltage, 0);
  const sumY2 = points.reduce((acc, p) => acc + p.displacement * p.displacement, 0);

  const a = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const b = (sumY - a * sumX) / n;

  // 计算 R²
  const yMean = sumY / n;
  let ssTotal = 0;
  let ssResidual = 0;

  points.forEach(p => {
    const predicted = a * p.voltage + b;
    ssTotal += Math.pow(p.displacement - yMean, 2);
    ssResidual += Math.pow(p.displacement - predicted, 2);
  });

  const r2 = 1 - (ssResidual / ssTotal);

  return {
    type: 'linear',
    coefficients: { a, b },
    r2: r2
  };
}

/**
 * 多项式拟合（二次）
 */
function performPolynomialFit() {
  const points = calibrationPoints.value;
  const n = points.length;

  // 构建矩阵方程组 (简化实现，仅支持二次多项式)
  const sumX = points.reduce((acc, p) => acc + p.voltage, 0);
  const sumX2 = points.reduce((acc, p) => acc + p.voltage * p.voltage, 0);
  const sumX3 = points.reduce((acc, p) => acc + Math.pow(p.voltage, 3), 0);
  const sumX4 = points.reduce((acc, p) => acc + Math.pow(p.voltage, 4), 0);
  const sumY = points.reduce((acc, p) => acc + p.displacement, 0);
  const sumXY = points.reduce((acc, p) => acc + p.voltage * p.displacement, 0);
  const sumX2Y = points.reduce((acc, p) => acc + p.voltage * p.voltage * p.displacement, 0);

  // 解线性方程组 (使用克莱姆法则)
  const det = n * sumX2 * sumX4 + sumX * sumX3 * sumX2 + sumX2 * sumX * sumX3
            - sumX2 * sumX2 * sumX2 - n * sumX3 * sumX3 - sumX * sumX * sumX4;

  const a0 = (sumY * sumX2 * sumX4 + sumX * sumX3 * sumX2Y + sumX2 * sumXY * sumX3
            - sumX2 * sumX2 * sumX2Y - sumY * sumX3 * sumX3 - sumX * sumXY * sumX4) / det;

  const a1 = (n * sumXY * sumX4 + sumY * sumX3 * sumX2 + sumX2 * sumX * sumX2Y
            - sumX2 * sumXY * sumX2 - n * sumX3 * sumX2Y - sumY * sumX * sumX4) / det;

  const a2 = (n * sumX2 * sumX2Y + sumX * sumXY * sumX2 + sumY * sumX * sumX3
            - sumY * sumX2 * sumX2 - n * sumXY * sumX3 - sumX * sumX * sumX2Y) / det;

  // 计算 R²
  const yMean = sumY / n;
  let ssTotal = 0;
  let ssResidual = 0;

  points.forEach(p => {
    const predicted = a0 + a1 * p.voltage + a2 * p.voltage * p.voltage;
    ssTotal += Math.pow(p.displacement - yMean, 2);
    ssResidual += Math.pow(p.displacement - predicted, 2);
  });

  const r2 = 1 - (ssResidual / ssTotal);

  return {
    type: 'polynomial',
    coefficients: [a0, a1, a2],
    r2: r2
  };
}

/**
 * 查表拟合
 */
function performLookupTableFit() {
  const points = [...calibrationPoints.value].sort((a, b) => a.voltage - b.voltage);

  // 查表法不进行拟合，直接使用插值
  return {
    type: 'lookup_table',
    coefficients: { points: points },
    r2: 1.0 // 查表法完美拟合
  };
}

/**
 * 预测位移
 */
function predictDisplacement(voltage) {
  if (!fitResult.value) return voltage * 0.1; // 默认理论值

  const result = fitResult.value;

  if (result.type === 'linear') {
    return result.coefficients.a * voltage + result.coefficients.b;
  } else if (result.type === 'polynomial') {
    const coef = result.coefficients;
    return coef[0] + coef[1] * voltage + coef[2] * voltage * voltage;
  } else if (result.type === 'lookup_table') {
    // 线性插值
    const points = result.coefficients.points;
    for (let i = 0; i < points.length - 1; i++) {
      if (voltage >= points[i].voltage && voltage <= points[i + 1].voltage) {
        const ratio = (voltage - points[i].voltage) / (points[i + 1].voltage - points[i].voltage);
        return points[i].displacement + ratio * (points[i + 1].displacement - points[i].displacement);
      }
    }
    return points[points.length - 1].displacement;
  }

  return voltage * 0.1;
}

/**
 * 应用校准
 */
async function applyCalibration() {
  if (!fitResult.value) {
    ElMessage.warning('请先执行拟合');
    return;
  }

  try {
    // 保存到历史
    saveToHistory();

    // 调用Store应用校准
    const result = await piezoStore.performCalibration(currentMode.value);

    if (result) {
      ElMessage.success('校准已应用');
    } else {
      ElMessage.error('应用校准失败');
    }
  } catch (error) {
    ElMessage.error('应用校准错误: ' + error.message);
  }
}

// ============ 数据导入导出 ============

/**
 * 导入校准数据
 */
function importCalibrationData() {
  showImportDialog.value = true;
}

/**
 * 处理文件选择
 */
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  importForm.value.file = file;
}

/**
 * 确认导入
 */
async function confirmImport() {
  try {
    let data = null;

    if (importForm.value.method === 'file' && importForm.value.file) {
      const text = await importForm.value.file.text();

      if (importForm.value.format === 'csv') {
        data = parseCSV(text);
      } else if (importForm.value.format === 'json') {
        data = JSON.parse(text);
      }
    } else if (importForm.value.method === 'paste' && importForm.value.content) {
      data = parseCSV(importForm.value.content);
    }

    if (data && Array.isArray(data)) {
      calibrationPoints.value = data;
      fitResult.value = null;
      updateChart();
      showImportDialog.value = false;
      ElMessage.success(`成功导入 ${data.length} 个校准点`);
    } else {
      ElMessage.error('数据格式错误');
    }
  } catch (error) {
    ElMessage.error('导入失败: ' + error.message);
  }
}

/**
 * 解析CSV数据
 */
function parseCSV(text) {
  const lines = text.trim().split('\n');
  const points = [];

  // 跳过标题行（如果有）
  const startIndex = lines[0].includes('电压') || lines[0].includes('voltage') ? 1 : 0;

  for (let i = startIndex; i < lines.length; i++) {
    const parts = lines[i].split(',').map(s => s.trim());
    if (parts.length >= 2) {
      const voltage = parseFloat(parts[0]);
      const displacement = parseFloat(parts[1]);

      if (!isNaN(voltage) && !isNaN(displacement)) {
        points.push({
          voltage: voltage,
          displacement: displacement,
          timestamp: Date.now()
        });
      }
    }
  }

  return points;
}

/**
 * 导出校准数据
 */
function exportCalibrationData() {
  if (calibrationPoints.value.length === 0) {
    ElMessage.warning('没有数据可导出');
    return;
  }

  showExportDialog.value = true;
}

/**
 * 确认导出
 */
function confirmExport() {
  const { format, filename } = exportForm.value;

  let content = '';
  let mimeType = '';
  let extension = '';

  if (format === 'csv') {
    content = [
      '电压(V),位移(μm)',
      ...calibrationPoints.value.map(p =>
        `${p.voltage.toFixed(3)},${p.displacement.toFixed(3)}`
      )
    ].join('\n');
    mimeType = 'text/csv;charset=utf-8;';
    extension = 'csv';
  } else if (format === 'json') {
    content = JSON.stringify({
      metadata: {
        exportTime: new Date().toISOString(),
        mode: currentMode.value,
        pointCount: calibrationPoints.value.length,
        fitResult: fitResult.value
      },
      points: calibrationPoints.value
    }, null, 2);
    mimeType = 'application/json;charset=utf-8;';
    extension = 'json';
  }

  const blob = new Blob([content], { type: mimeType });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.${extension}`);
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);

  showExportDialog.value = false;
  ElMessage.success(`数据已导出为 ${extension.toUpperCase()} 格式`);
}

// ============ 历史版本管理 ============

/**
 * 保存到历史
 */
function saveToHistory() {
  const historyItem = {
    timestamp: Date.now(),
    mode: currentMode.value,
    points: [...calibrationPoints.value],
    r2: fitResult.value?.r2 || 0
  };

  calibrationHistory.value.unshift(historyItem);

  // 限制历史记录数量
  if (calibrationHistory.value.length > 20) {
    calibrationHistory.value.pop();
  }

  // 保存到本地存储
  localStorage.setItem('piezo_calibration_history', JSON.stringify(calibrationHistory.value));
}

/**
 * 恢复历史版本
 */
function restoreHistory(index) {
  const item = calibrationHistory.value[index];
  if (!item) return;

  calibrationPoints.value = [...item.points];
  currentMode.value = item.mode;

  // 重新拟合
  performFit();

  showHistoryDialog.value = false;
  ElMessage.success('已恢复历史版本');
}

/**
 * 删除历史版本
 */
function deleteHistory(index) {
  calibrationHistory.value.splice(index, 1);
  localStorage.setItem('piezo_calibration_history', JSON.stringify(calibrationHistory.value));
  ElMessage.info('已删除历史版本');
}

/**
 * 格式化时间
 */
function formatTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * 加载历史记录
 */
function loadHistory() {
  try {
    const saved = localStorage.getItem('piezo_calibration_history');
    if (saved) {
      calibrationHistory.value = JSON.parse(saved);
    }
  } catch (error) {
    console.error('Failed to load calibration history:', error);
  }
}

// ============ 生命周期钩子 ============

onMounted(() => {
  nextTick(() => {
    initChart();
  });

  // 加载历史记录
  loadHistory();

  // 同步Store中的校准数据
  if (piezoStore.calibrationData.points.length > 0) {
    calibrationPoints.value = piezoStore.calibrationData.points.map(p => ({
      voltage: p.voltage,
      displacement: p.displacement / 1000, // nm -> μm
      timestamp: p.timestamp
    }));
    updateChart();
  }

  // 窗口大小变化时调整图表
  window.addEventListener('resize', () => {
    if (chartInstance) {
      chartInstance.resize();
    }
  });
});

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
});

// ============ 监听器 ============

// 监听Store校准数据变化
watch(() => piezoStore.calibrationData.points, (newPoints) => {
  if (newPoints && newPoints.length > 0) {
    calibrationPoints.value = newPoints.map(p => ({
      voltage: p.voltage,
      displacement: p.displacement / 1000,
      timestamp: p.timestamp
    }));
    updateChart();
  }
}, { deep: true });
</script>

<style scoped>
.calibration-editor {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  padding: var(--spacing-4);
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

/* 头部样式 */
.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--spacing-3);
  border-bottom: 1px solid var(--color-border-secondary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.editor-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.calibration-mode {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.mode-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.header-right {
  display: flex;
  gap: var(--spacing-2);
}

.tool-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-all);
}

.tool-btn:hover:not(:disabled) {
  border-color: var(--color-primary-400);
  color: var(--color-text-primary);
  background: var(--color-interactive-hover);
}

.tool-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 主编辑区域 */
.editor-main {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: var(--spacing-4);
}

/* 图表区域 */
.chart-section {
  position: relative;
}

.chart-container {
  width: 100%;
  height: 450px;
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
}

.chart-legend {
  position: absolute;
  bottom: var(--spacing-3);
  left: var(--spacing-3);
  display: flex;
  gap: var(--spacing-4);
  padding: var(--spacing-2) var(--spacing-3);
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-sm);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
}

.legend-dot--actual {
  background: var(--color-primary-500);
}

.legend-line {
  width: 20px;
  height: 2px;
}

.legend-line--fitted {
  background: var(--color-data-green);
}

.legend-line--theoretical {
  background: var(--color-data-yellow);
  background: repeating-linear-gradient(
    90deg,
    var(--color-data-yellow),
    var(--color-data-yellow) 3px,
    transparent 3px,
    transparent 6px
  );
}

.legend-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

/* 控制面板 */
.control-panel {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.section-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.add-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-2);
  border: 1px solid var(--color-primary-400);
  border-radius: var(--radius-sm);
  background: var(--color-primary-50);
  color: var(--color-primary-600);
  font-size: var(--font-size-xs);
  cursor: pointer;
  transition: var(--transition-all);
}

.add-btn:hover:not(:disabled) {
  background: var(--color-primary-100);
}

.add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 校准点列表 */
.points-section {
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-3);
  max-height: 300px;
  overflow-y: auto;
}

.points-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.point-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-2);
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-all);
}

.point-item:hover {
  border-color: var(--color-primary-400);
}

.point-item--selected {
  border-color: var(--color-primary-500);
  background: var(--color-primary-50);
}

.point-index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--color-primary-100);
  color: var(--color-primary-600);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
}

.point-data {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.data-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.data-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  min-width: 40px;
}

.data-input {
  flex: 1;
  padding: var(--spacing-1) var(--spacing-2);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
  transition: var(--transition-all);
}

.data-input:focus {
  outline: none;
  border-color: var(--color-primary-400);
}

.data-unit {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: var(--transition-all);
}

.delete-btn:hover {
  background: var(--color-error-light);
  color: var(--color-error-dark);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-6);
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-3);
}

.empty-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-1);
}

.empty-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin: 0;
}

/* 拟合参数 */
.fit-params {
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-3);
}

.params-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.param-item {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
}

.param-label {
  color: var(--color-text-secondary);
}

.param-value {
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
  font-weight: var(--font-weight-medium);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: var(--transition-all);
}

.action-btn:hover:not(:disabled) {
  border-color: var(--color-primary-400);
  background: var(--color-interactive-hover);
}

.action-btn--primary {
  border-color: var(--color-primary-500);
  background: var(--color-primary-500);
  color: white;
}

.action-btn--primary:hover:not(:disabled) {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 校准进度 */
.calibration-progress {
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-4);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.progress-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.progress-percent {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
  font-family: var(--font-family-mono);
}

.progress-steps {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-4);
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-2);
  flex: 1;
}

.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--color-neutral-200);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  transition: var(--transition-all);
}

.step-item--active .step-indicator {
  background: var(--color-primary-500);
  color: white;
}

.step-item--completed .step-indicator {
  background: var(--color-success-dark);
  color: white;
}

.step-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  text-align: center;
}

.step-item--active .step-label {
  color: var(--color-primary-600);
  font-weight: var(--font-weight-medium);
}

/* 校准结果统计 */
.calibration-result {
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-4);
}

.result-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-3);
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-3);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-2);
  background: var(--color-surface-primary);
  border-radius: var(--radius-sm);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
}

.stat-icon--success {
  background: var(--color-success-light);
  color: var(--color-success-dark);
}

.stat-icon--primary {
  background: rgba(49, 130, 206, 0.1);
  color: var(--color-data-blue);
}

.stat-icon--warning {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.stat-icon--info {
  background: var(--color-neutral-100);
  color: var(--color-text-secondary);
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.stat-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

/* 历史列表 */
.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3);
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
}

.history-info {
  flex: 1;
}

.history-time {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-1);
}

.history-meta {
  display: flex;
  gap: var(--spacing-3);
}

.meta-item {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.history-actions {
  display: flex;
  gap: var(--spacing-2);
}

.history-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-2);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-sm);
  background: var(--color-surface-primary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  cursor: pointer;
  transition: var(--transition-all);
}

.history-btn:hover {
  border-color: var(--color-primary-400);
  color: var(--color-text-primary);
}

.history-btn--danger:hover {
  border-color: var(--color-error-dark);
  background: var(--color-error-light);
  color: var(--color-error-dark);
}

/* 文件输入 */
.file-input {
  width: 100%;
  padding: var(--spacing-2);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .editor-main {
    grid-template-columns: 1fr;
  }

  .chart-container {
    height: 350px;
  }

  .result-stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .editor-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-3);
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-2);
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }

  .progress-steps {
    flex-direction: column;
    gap: var(--spacing-2);
  }

  .step-item {
    flex-direction: row;
    justify-content: flex-start;
  }
}
</style>
