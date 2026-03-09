<template>
  <el-card class="piezo-control">
    <template #header>
      <div class="card-header">
        <el-icon class="header-icon"><Cpu /></el-icon>
        <span class="header-title">压电陶瓷控制</span>
      </div>
    </template>

    <div class="control-content">
      <!-- 连接状态 -->
      <div class="connection-status" :class="piezoStore.isConnected ? 'connected' : 'disconnected'">
        <span class="status-dot"></span>
        <span class="status-text">{{ connectionStatus }}</span>
      </div>

      <!-- 主要控制区域 -->
      <el-tabs v-model="activeTab" class="control-tabs">
        <!-- 电压控制面板 -->
        <el-tab-pane label="电压控制" name="voltage">
          <div class="voltage-control">
            <!-- 电压滑块 -->
            <div class="voltage-slider-section">
              <div class="slider-header">
                <span class="label">输出电压</span>
                <div class="value-display">
                  <span class="value-number" :class="{ 'value-changing': isVoltageChanging }">
                    {{ voltageValue.toFixed(1) }}
                  </span>
                  <span class="value-unit">V</span>
                </div>
              </div>

              <div class="slider-container">
                <el-slider
                  v-model="voltageValue"
                  :min="piezoStore.voltageLimits.min"
                  :max="piezoStore.voltageLimits.max"
                  :step="0.1"
                  :disabled="!piezoStore.canControl"
                  show-input
                  class="voltage-slider"
                  @change="handleVoltageChange"
                  @input="onVoltageInput"
                />
                <div class="voltage-marks">
                  <span class="mark">{{ piezoStore.voltageLimits.min }}V</span>
                  <span class="mark">{{ (piezoStore.voltageLimits.max * 0.25).toFixed(1) }}V</span>
                  <span class="mark">{{ (piezoStore.voltageLimits.max * 0.5).toFixed(1) }}V</span>
                  <span class="mark">{{ (piezoStore.voltageLimits.max * 0.75).toFixed(1) }}V</span>
                  <span class="mark">{{ piezoStore.voltageLimits.max }}V</span>
                </div>
              </div>
            </div>

            <!-- 快捷电压按钮 -->
            <div class="quick-voltage-section">
              <div class="section-label">快捷设置</div>
              <div class="quick-voltage-buttons">
                <button
                  v-for="voltage in quickVoltages"
                  :key="voltage"
                  class="quick-btn"
                  :class="{ 'quick-btn--active': Math.abs(voltageValue - voltage) < 0.5 }"
                  :disabled="!piezoStore.canControl"
                  @click="setQuickVoltage(voltage)"
                >
                  {{ voltage }}V
                </button>
              </div>
            </div>

            <!-- 位移显示 -->
            <div class="displacement-section">
              <div class="section-label">实时位移</div>

              <div class="displacement-display">
                <div class="main-displacement">
                  <div class="displacement-value-wrapper">
                    <span class="displacement-value">{{ displayDisplacement }}</span>
                    <span class="displacement-unit">{{ displacementUnit }}</span>
                  </div>
                  <div class="displacement-bar">
                    <div
                      class="bar-fill"
                      :style="{ width: `${(piezoStore.currentDisplacement / piezoStore.displacementLimits.max) * 100}%` }"
                    ></div>
                  </div>
                </div>

                <div class="displacement-details">
                  <div class="detail-card">
                    <div class="detail-label">电压</div>
                    <div class="detail-value">
                      <span class="mono">{{ piezoStore.currentVoltage.toFixed(1) }}</span>
                      <span class="unit">V</span>
                    </div>
                  </div>
                  <div class="detail-card">
                    <div class="detail-label">温度</div>
                    <div class="detail-value">
                      <span class="mono">{{ currentTemperature.toFixed(1) }}</span>
                      <span class="unit">°C</span>
                    </div>
                  </div>
                  <div class="detail-card">
                    <div class="detail-label">状态</div>
                    <div class="detail-value">
                      <span class="status-badge" :class="`status-badge--${statusType}`">
                        {{ statusText }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 电压位移映射面板 -->
        <el-tab-pane label="电压位移映射" name="voltageMap">
          <PiezoVoltageMap />
        </el-tab-pane>

        <!-- 校准面板 -->
        <el-tab-pane label="校准" name="calibration">
          <PiezoCalibrationEditor />
        </el-tab-pane>

        <!-- 数据可视化面板 -->
        <el-tab-pane label="数据图表" name="chart">
          <div class="chart-panel">
            <!-- 图表控制 -->
            <div class="chart-controls">
              <el-radio-group v-model="chartType" size="small" class="chart-type-group">
                <el-radio-button label="realtime">实时曲线</el-radio-button>
                <el-radio-button label="calibration">校准曲线</el-radio-button>
                <el-radio-button label="history">历史数据</el-radio-button>
              </el-radio-group>

              <div class="chart-actions">
                <button
                  class="chart-btn"
                  :class="{ 'chart-btn--active': isCollecting }"
                  :disabled="!piezoStore.isConnected"
                  @click="toggleDataCollection"
                >
                  <el-icon><VideoCamera /></el-icon>
                  <span>{{ isCollecting ? '停止采集' : '开始采集' }}</span>
                </button>

                <button
                  class="chart-btn"
                  :disabled="chartData.length === 0"
                  @click="exportData"
                >
                  <el-icon><Download /></el-icon>
                  <span>导出</span>
                </button>

                <button
                  class="chart-btn"
                  :disabled="chartData.length === 0"
                  @click="clearChartData"
                >
                  <el-icon><Delete /></el-icon>
                  <span>清空</span>
                </button>
              </div>
            </div>

            <!-- ECharts 图表 -->
            <div ref="chartContainer" class="chart-container"></div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file PiezoControl.vue
 * @path src/components/
 * @description 压电陶瓷控制组件，使用usePiezoStore进行状态管理
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, element-plus, echarts, stores/piezo
 */

import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { usePiezoStore } from '../stores/piezo';
import { PIEZO } from '../config/constants';

// 导入新组件
import PiezoVoltageMap from './PiezoVoltageMap.vue';
import PiezoCalibrationEditor from './PiezoCalibrationEditor.vue';

// ============ Store 初始化 ============

const piezoStore = usePiezoStore();

// ============ 常量定义 ============

const quickVoltages = [0, 30, 60, 90, 120, 150];

// ============ 响应式状态 ============

// 电压控制（本地UI状态）
const voltageValue = ref(0);
const isVoltageChanging = ref(false);

// 温度（Store未提供，保留本地状态）
const currentTemperature = ref(25);

// Tab 控制
const activeTab = ref('voltage');

// 图表相关
const chartType = ref('realtime');
const isCollecting = ref(false);
const chartContainer = ref(null);
let chartInstance = null;

/** @type {import('vue').Ref<Array<{timestamp: number, voltage: number, displacement: number}>>} */
const chartData = ref([]);

// 定时器
let dataCollectionInterval = null;
let voltageChangeTimer = null;

// ============ 计算属性 ============

/**
 * 连接状态文本
 */
const connectionStatus = computed(() => {
  return piezoStore.isConnected ? '设备已连接' : '设备未连接';
});

/**
 * 状态文本映射
 */
const statusText = computed(() => {
  const statusMap = {
    'ready': '就绪',
    'idle': '空闲',
    'working': '工作中',
    'calibrating': '校准中',
    'error': '错误',
    'disconnected': '已断开'
  };
  return statusMap[piezoStore.status] || piezoStore.status;
});

/**
 * 状态类型映射（用于样式）
 */
const statusType = computed(() => {
  const typeMap = {
    'ready': 'success',
    'idle': 'success',
    'working': 'primary',
    'calibrating': 'warning',
    'error': 'danger',
    'disconnected': 'info'
  };
  return typeMap[piezoStore.status] || 'info';
});

/**
 * 显示位移（转换为μm）
 * Store中位移单位为nm，需要转换
 */
const displayDisplacement = computed(() => {
  // nm -> μm (除以1000)
  return (piezoStore.currentDisplacement / 1000).toFixed(3);
});

/**
 * 位移单位
 */
const displacementUnit = computed(() => {
  return 'μm';
});

// ============ 事件处理函数 ============

/**
 * 电压滑块输入处理
 *
 * @param {number} value - 新电压值
 */
function onVoltageInput(value) {
  isVoltageChanging.value = true;

  if (voltageChangeTimer) {
    clearTimeout(voltageChangeTimer);
  }

  voltageChangeTimer = setTimeout(() => {
    isVoltageChanging.value = false;
  }, 300);
}

/**
 * 电压滑块变化处理
 *
 * @param {number} value - 新电压值
 */
async function handleVoltageChange(value) {
  const success = await piezoStore.setVoltage(value);
  if (success) {
    ElMessage.success(`电压已设置为 ${value.toFixed(1)}V`);
  }
}

/**
 * 设置快捷电压
 *
 * @param {number} voltage - 目标电压
 */
async function setQuickVoltage(voltage) {
  voltageValue.value = voltage;
  const success = await piezoStore.setVoltage(voltage);
  if (success) {
    ElMessage.success(`电压已设置为 ${voltage}V`);
  }
}

// ============ 图表相关函数 ============

/**
 * 初始化图表
 */
function initChart() {
  if (!chartContainer.value) return;

  // 销毁旧图表实例
  if (chartInstance) {
    chartInstance.dispose();
  }

  // 创建新图表实例
  chartInstance = echarts.init(chartContainer.value);

  // 设置图表配置
  const option = {
    title: {
      text: '压电陶瓷特性曲线',
      left: 'center',
      textStyle: {
        color: 'var(--color-text-primary)',
        fontSize: 14
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['电压', '位移'],
      top: 30,
      textStyle: {
        color: 'var(--color-text-secondary)'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: [],
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      axisLabel: {
        color: 'var(--color-text-secondary)'
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '电压 (V)',
        position: 'left',
        axisLabel: {
          formatter: '{value} V',
          color: 'var(--color-text-secondary)'
        },
        axisLine: {
          lineStyle: {
            color: 'var(--color-border-primary)'
          }
        },
        splitLine: {
          lineStyle: {
            color: 'var(--color-border-secondary)'
          }
        }
      },
      {
        type: 'value',
        name: '位移 (μm)',
        position: 'right',
        axisLabel: {
          formatter: '{value} μm',
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
      }
    ],
    series: [
      {
        name: '电压',
        type: 'line',
        yAxisIndex: 0,
        data: [],
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-blue)',
          width: 2
        },
        itemStyle: {
          color: 'var(--color-data-blue)'
        }
      },
      {
        name: '位移',
        type: 'line',
        yAxisIndex: 1,
        data: [],
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-green)',
          width: 2
        },
        itemStyle: {
          color: 'var(--color-data-green)'
        }
      }
    ]
  };

  chartInstance.setOption(option);
}

/**
 * 更新图表数据
 */
function updateChart() {
  if (!chartInstance || chartData.value.length === 0) return;

  const times = chartData.value.map(d => {
    const date = new Date(d.timestamp);
    return `${date.getHours()}:${date.getMinutes()}:${date.getSeconds()}`;
  });

  const voltages = chartData.value.map(d => d.voltage);
  // 位移从nm转为μm
  const displacements = chartData.value.map(d => d.displacement / 1000);

  chartInstance.setOption({
    xAxis: {
      data: times
    },
    series: [
      { data: voltages },
      { data: displacements }
    ]
  });
}

/**
 * 切换数据采集
 */
function toggleDataCollection() {
  isCollecting.value = !isCollecting.value;

  if (isCollecting.value) {
    startDataCollection();
    ElMessage.success('开始数据采集');
  } else {
    stopDataCollection();
    ElMessage.info('停止数据采集');
  }
}

/**
 * 开始数据采集
 */
function startDataCollection() {
  if (dataCollectionInterval) {
    clearInterval(dataCollectionInterval);
  }

  dataCollectionInterval = setInterval(() => {
    if (chartData.value.length > 100) {
      chartData.value.shift(); // 保持最多 100 个数据点
    }

    chartData.value.push({
      timestamp: Date.now(),
      voltage: piezoStore.currentVoltage,
      displacement: piezoStore.currentDisplacement
    });

    updateChart();
  }, 500);
}

/**
 * 停止数据采集
 */
function stopDataCollection() {
  if (dataCollectionInterval) {
    clearInterval(dataCollectionInterval);
    dataCollectionInterval = null;
  }
}

/**
 * 导出数据
 */
function exportData() {
  if (chartData.value.length === 0) {
    ElMessage.warning('没有数据可导出');
    return;
  }

  const csvContent = [
    '时间戳,电压(V),位移(μm)',
    ...chartData.value.map(d =>
      `${d.timestamp},${d.voltage.toFixed(3)},${(d.displacement / 1000).toFixed(3)}`
    )
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', `piezo_data_${Date.now()}.csv`);
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  ElMessage.success('数据导出成功');
}

/**
 * 清空图表数据
 */
function clearChartData() {
  chartData.value = [];
  piezoStore.clearHistory();
  updateChart();
  ElMessage.info('数据已清空');
}

/**
 * 更新校准曲线图表
 */
function updateCalibrationChart() {
  if (!chartInstance || piezoStore.calibrationData.points.length === 0) return;

  const points = piezoStore.calibrationData.points;
  const voltages = points.map(d => d.voltage.toFixed(1));
  const displacements = points.map(d => (d.displacement / 1000).toFixed(3)); // nm -> μm
  const theoreticals = points.map(d => (d.voltage * 0.1).toFixed(3)); // 理论位移

  chartInstance.setOption({
    title: {
      text: '压电陶瓷校准曲线'
    },
    xAxis: {
      type: 'category',
      data: voltages,
      name: '电压 (V)'
    },
    yAxis: [
      {
        type: 'value',
        name: '位移 (μm)',
        position: 'left'
      }
    ],
    series: [
      {
        name: '实际位移',
        type: 'line',
        yAxisIndex: 0,
        data: displacements,
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-blue)',
          width: 2
        },
        itemStyle: {
          color: 'var(--color-data-blue)'
        }
      },
      {
        name: '理论位移',
        type: 'line',
        yAxisIndex: 0,
        data: theoreticals,
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-yellow)',
          type: 'dashed',
          width: 2
        },
        itemStyle: {
          color: 'var(--color-data-yellow)'
        }
      }
    ]
  });
}

// ============ 生命周期钩子 ============

onMounted(() => {
  // 初始化图表
  nextTick(() => {
    initChart();
  });

  // 初始化Store
  piezoStore.init();

  // 连接WebSocket
  piezoStore.connectWebSocket();

  // 同步电压值
  voltageValue.value = piezoStore.currentVoltage;

  // 窗口大小变化时重新调整图表
  window.addEventListener('resize', () => {
    if (chartInstance) {
      chartInstance.resize();
    }
  });
});

onBeforeUnmount(() => {
  // 停止数据采集
  stopDataCollection();

  // 清理Store资源
  piezoStore.cleanup();

  // 销毁图表实例
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }

  // 清除定时器
  if (voltageChangeTimer) {
    clearTimeout(voltageChangeTimer);
  }
});

// ============ 监听器 ============

// 监听图表类型变化
watch(chartType, (newType) => {
  if (newType === 'calibration' && piezoStore.calibrationData.points.length > 0) {
    // 显示校准曲线
    updateCalibrationChart();
  } else if (newType === 'realtime') {
    updateChart();
  } else if (newType === 'history') {
    // 使用Store的历史数据
    chartData.value = [...piezoStore.historyData];
    updateChart();
  }
});

// 监听Store电压变化，同步到本地
watch(() => piezoStore.currentVoltage, (newVoltage) => {
  if (Math.abs(voltageValue.value - newVoltage) > 0.1) {
    voltageValue.value = newVoltage;
  }
});

// 监听Store历史数据变化
watch(() => piezoStore.historyData, (newData) => {
  if (chartType.value === 'realtime' && isCollecting.value) {
    // 实时模式下，使用Store的历史数据更新图表
    chartData.value = [...newData].slice(-100);
    updateChart();
  }
}, { deep: true });
</script>

<style scoped>
.piezo-control {
  margin-bottom: var(--spacing-5);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
}

.piezo-control:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-accent-500);
}

.header-title {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.control-content {
  padding: var(--spacing-2) 0;
}

/* 连接状态 */
.connection-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-4);
  transition: var(--transition-all);
}

.connection-status.connected {
  background: linear-gradient(135deg, var(--color-success-light), rgba(56, 161, 105, 0.1));
  border: 1px solid rgba(56, 161, 105, 0.3);
}

.connection-status.disconnected {
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  position: relative;
}

.connected .status-dot {
  background: var(--color-status-online);
}

.connected .status-dot::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--color-status-online);
  animation: dot-pulse 2s ease-in-out infinite;
}

.disconnected .status-dot {
  background: var(--color-status-offline);
}

@keyframes dot-pulse {
  0%, 100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(2);
  }
}

.status-text {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.control-tabs {
  margin-top: var(--spacing-2);
}

/* 通用标签样式 */
.section-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 电压控制样式 */
.voltage-control {
  padding: var(--spacing-2) 0;
}

.voltage-slider-section {
  margin-bottom: var(--spacing-6);
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
}

.slider-header .label {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.value-display {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-1);
}

.value-number {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
  transition: var(--transition-colors);
}

.value-number.value-changing {
  color: var(--color-accent-500);
  animation: value-flash 0.3s ease;
}

@keyframes value-flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.value-unit {
  font-size: var(--font-size-lg);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

/* 滑块容器 */
.slider-container {
  padding: 0 var(--spacing-2);
}

/* 电压滑块样式 - el-slider 组件上直接添加 class */
.voltage-slider.el-slider {
  --el-slider-main-bg-color: var(--color-primary-500);
  --el-slider-runway-bg-color: var(--color-neutral-200);
}

/* 滑块轨道样式 */
.voltage-slider.el-slider :deep(.el-slider__runway) {
  background-color: var(--color-neutral-200);
  border-radius: var(--radius-full);
}

/* 滑块进度条样式 */
.voltage-slider.el-slider :deep(.el-slider__bar) {
  background: linear-gradient(90deg, var(--color-primary-400), var(--color-primary-500));
  border-radius: var(--radius-full);
}

/* 滑块按钮样式 */
.voltage-slider.el-slider :deep(.el-slider__button-wrapper) {
  transition: var(--transition-all);
}

.voltage-slider.el-slider :deep(.el-slider__button) {
  border: 3px solid var(--color-primary-500);
  background: var(--color-surface-primary);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
}

.voltage-slider.el-slider :deep(.el-slider__button:hover) {
  transform: scale(1.2);
  box-shadow: var(--shadow-glow-primary);
}

/* 滑块输入框样式 */
.voltage-slider.el-slider :deep(.el-input-number) {
  width: 100px;
}

.voltage-slider.el-slider :deep(.el-input-number .el-input__wrapper) {
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-sm);
}

.voltage-marks {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-2);
  padding: 0 var(--spacing-1);
}

.mark {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

/* 快捷电压按钮 */
.quick-voltage-section {
  margin-bottom: var(--spacing-6);
}

.quick-voltage-buttons {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--spacing-2);
}

.quick-btn {
  padding: var(--spacing-3) var(--spacing-2);
  border: 2px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  font-family: var(--font-family-mono);
  cursor: pointer;
  transition: var(--transition-all);
}

.quick-btn:hover:not(:disabled) {
  border-color: var(--color-primary-400);
  background: var(--color-interactive-hover);
  transform: translateY(-2px);
}

.quick-btn--active {
  border-color: var(--color-primary-500);
  background: var(--color-primary-500);
  color: white;
  box-shadow: var(--shadow-glow-primary);
}

.quick-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 位移显示区域 */
.displacement-section {
  margin-bottom: var(--spacing-4);
}

.displacement-display {
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-5);
}

.main-displacement {
  margin-bottom: var(--spacing-5);
}

.displacement-value-wrapper {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-4);
}

.displacement-value {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-data-green);
  font-family: var(--font-family-mono);
  letter-spacing: 2px;
}

.displacement-unit {
  font-size: var(--font-size-xl);
  color: var(--color-text-tertiary);
}

.displacement-bar {
  height: 8px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-data-green), var(--color-accent-500));
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

/* 详细信息卡片 */
.displacement-details {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-3);
}

.detail-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-secondary);
  border-radius: var(--radius-sm);
}

.detail-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-1);
}

.detail-value .mono {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

.detail-value .unit {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.status-badge {
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.status-badge--success {
  background: var(--color-success-light);
  color: var(--color-success-dark);
}

.status-badge--primary {
  background: rgba(49, 130, 206, 0.1);
  color: var(--color-data-blue);
}

.status-badge--warning {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.status-badge--danger {
  background: var(--color-error-light);
  color: var(--color-error-dark);
}

.status-badge--info {
  background: var(--color-neutral-100);
  color: var(--color-text-secondary);
}

/* 图表面板样式 */
.chart-panel {
  padding: var(--spacing-2) 0;
}

.chart-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
  flex-wrap: wrap;
  gap: var(--spacing-3);
}

.chart-type-group {
  display: flex;
}

.chart-actions {
  display: flex;
  gap: var(--spacing-2);
}

.chart-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-sm);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-all);
}

.chart-btn:hover:not(:disabled) {
  border-color: var(--color-primary-400);
  color: var(--color-text-primary);
}

.chart-btn--active {
  border-color: var(--color-primary-500);
  background: var(--color-primary-500);
  color: white;
}

.chart-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chart-container {
  width: 100%;
  height: 400px;
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .displacement-details {
    grid-template-columns: 1fr;
  }

  .quick-voltage-buttons {
    grid-template-columns: repeat(3, 1fr);
  }

  .calibration-actions {
    grid-template-columns: 1fr;
  }

  .chart-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .chart-actions {
    justify-content: space-between;
  }

  .value-number {
    font-size: var(--font-size-2xl);
  }

  .displacement-value {
    font-size: var(--font-size-3xl);
  }
}
</style>
