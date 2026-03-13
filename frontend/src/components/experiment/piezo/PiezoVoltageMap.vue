<template>
  <div class="voltage-map-container">
    <!-- 标题和工具栏 -->
    <div class="map-header">
      <div class="header-left">
        <h3 class="map-title">
          电压-位移实时映射
        </h3>
        <div class="status-indicators">
          <span class="indicator">
            <span
              class="indicator-dot"
              :class="isCollecting ? 'active' : ''"
            />
            <span class="indicator-label">{{ isCollecting ? '采集中' : '已停止' }}</span>
          </span>
          <span class="indicator">
            <span class="indicator-label">数据点: {{ mapData.length }}</span>
          </span>
        </div>
      </div>
      <div class="header-right">
        <button
          class="tool-btn"
          :class="{ 'tool-btn--active': isCollecting }"
          :disabled="!piezoStore.isConnected"
          title="开始/停止采集"
          @click="toggleCollection"
        >
          <el-icon><VideoCamera /></el-icon>
          <span>{{ isCollecting ? '停止' : '采集' }}</span>
        </button>
        <button
          class="tool-btn"
          :disabled="mapData.length === 0"
          title="导出映射数据"
          @click="exportMapData"
        >
          <el-icon><Download /></el-icon>
          <span>导出</span>
        </button>
        <button
          class="tool-btn"
          :disabled="mapData.length === 0"
          title="清空数据"
          @click="clearMapData"
        >
          <el-icon><Delete /></el-icon>
          <span>清空</span>
        </button>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="chart-wrapper">
      <div
        ref="chartContainer"
        class="chart-container"
      />

      <!-- 当前工作点指示器 -->
      <div
        v-if="showWorkingPoint"
        class="working-point"
      >
        <div class="point-label">
          当前工作点
        </div>
        <div class="point-info">
          <div class="info-item">
            <span class="info-label">电压:</span>
            <span class="info-value">{{ currentVoltage.toFixed(1) }} V</span>
          </div>
          <div class="info-item">
            <span class="info-label">位移:</span>
            <span class="info-value">{{ currentDisplacement.toFixed(3) }} μm</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 映射统计信息 -->
    <div
      v-if="mapData.length > 0"
      class="map-statistics"
    >
      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">
            平均位移
          </div>
          <div class="stat-value">
            {{ averageDisplacement.toFixed(3) }} μm
          </div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><Top /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">
            最大位移
          </div>
          <div class="stat-value">
            {{ maxDisplacement.toFixed(3) }} μm
          </div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><Bottom /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">
            最小位移
          </div>
          <div class="stat-value">
            {{ minDisplacement.toFixed(3) }} μm
          </div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><DataAnalysis /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">
            线性度
          </div>
          <div class="stat-value">
            {{ linearity.toFixed(2) }}%
          </div>
        </div>
      </div>
    </div>

    <!-- 导出格式选择对话框 -->
    <el-dialog
      v-model="showExportDialog"
      title="导出映射数据"
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
  </div>
</template>

<script setup>
/**
 * @file PiezoVoltageMap.vue
 * @path src/components/
 * @description 电压-位移实时映射显示组件，支持实时数据采集、曲线显示和数据导出
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, element-plus, echarts, stores/piezo
 */

import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { usePiezoStore } from '@/stores/piezo';

// ============ Store 初始化 ============

const piezoStore = usePiezoStore();

// ============ 响应式状态 ============

/** 图表容器引用 */
const chartContainer = ref(null);

/** 图表实例 */
let chartInstance = null;

/** 是否正在采集数据 */
const isCollecting = ref(false);

/** 映射数据 */
const mapData = ref([]);

/** 采集定时器 */
let collectionInterval = null;

/** 最大数据点数 */
const maxDataPoints = 500;

/** 是否显示工作点 */
const showWorkingPoint = ref(true);

/** 导出对话框 */
const showExportDialog = ref(false);

/** 导出表单 */
const exportForm = ref({
  format: 'csv',
  filename: `voltage_map_${Date.now()}`
});

// ============ 计算属性 ============

/**
 * 当前电压
 */
const currentVoltage = computed(() => piezoStore.currentVoltage);

/**
 * 当前位移（转换为μm）
 */
const currentDisplacement = computed(() => piezoStore.currentDisplacement / 1000);

/**
 * 平均位移
 */
const averageDisplacement = computed(() => {
  if (mapData.value.length === 0) return 0;
  const sum = mapData.value.reduce((acc, d) => acc + d.displacement, 0);
  return sum / mapData.value.length;
});

/**
 * 最大位移
 */
const maxDisplacement = computed(() => {
  if (mapData.value.length === 0) return 0;
  return Math.max(...mapData.value.map(d => d.displacement));
});

/**
 * 最小位移
 */
const minDisplacement = computed(() => {
  if (mapData.value.length === 0) return 0;
  return Math.min(...mapData.value.map(d => d.displacement));
});

/**
 * 线性度（R²）
 */
const linearity = computed(() => {
  if (mapData.value.length < 2) return 0;

  // 计算线性回归 R²
  const n = mapData.value.length;
  const sumX = mapData.value.reduce((acc, d) => acc + d.voltage, 0);
  const sumY = mapData.value.reduce((acc, d) => acc + d.displacement, 0);
  const sumXY = mapData.value.reduce((acc, d) => acc + d.voltage * d.displacement, 0);
  const sumX2 = mapData.value.reduce((acc, d) => acc + d.voltage * d.voltage, 0);
  const sumY2 = mapData.value.reduce((acc, d) => acc + d.displacement * d.displacement, 0);

  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));

  if (denominator === 0) return 0;

  const r = numerator / denominator;
  return r * r * 100; // R² 转为百分比
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
      text: '电压-位移特性曲线',
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
        type: 'cross',
        crossStyle: {
          color: '#999'
        }
      },
      formatter: (params) => {
        if (!params || params.length === 0) return '';
        const data = params[0];
        return `
          <div style="padding: 8px;">
            <div style="margin-bottom: 4px; font-weight: 600;">电压: ${data.value[0].toFixed(1)} V</div>
            <div>位移: ${data.value[1].toFixed(3)} μm</div>
          </div>
        `;
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
        color: 'var(--color-text-secondary)',
        formatter: '{value}'
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
        color: 'var(--color-text-secondary)',
        formatter: '{value}'
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
        name: '电压-位移',
        type: 'line',
        data: [],
        smooth: false,
        showSymbol: false,
        lineStyle: {
          color: 'var(--color-primary-500)',
          width: 2
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(49, 130, 206, 0.3)' },
              { offset: 1, color: 'rgba(49, 130, 206, 0.05)' }
            ]
          }
        }
      },
      {
        name: '当前工作点',
        type: 'scatter',
        data: [],
        symbolSize: 12,
        itemStyle: {
          color: 'var(--color-accent-500)',
          borderColor: '#fff',
          borderWidth: 2
        },
        emphasis: {
          itemStyle: {
            color: 'var(--color-accent-600)',
            borderColor: '#fff',
            borderWidth: 3
          }
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
  if (!chartInstance) return;

  // 转换数据格式 [voltage, displacement]
  const seriesData = mapData.value.map(d => [d.voltage, d.displacement]);

  // 当前工作点
  const workingPoint = [[currentVoltage.value, currentDisplacement.value]];

  chartInstance.setOption({
    series: [
      { data: seriesData },
      { data: workingPoint }
    ]
  });
}

/**
 * 更新当前工作点
 */
function updateWorkingPoint() {
  if (!chartInstance || mapData.value.length === 0) return;

  const workingPoint = [[currentVoltage.value, currentDisplacement.value]];

  chartInstance.setOption({
    series: [
      {},
      { data: workingPoint }
    ]
  });
}

// ============ 数据采集控制 ============

/**
 * 切换数据采集
 */
function toggleCollection() {
  isCollecting.value = !isCollecting.value;

  if (isCollecting.value) {
    startCollection();
    ElMessage.success('开始数据采集');
  } else {
    stopCollection();
    ElMessage.info('停止数据采集');
  }
}

/**
 * 开始数据采集
 */
function startCollection() {
  if (collectionInterval) {
    clearInterval(collectionInterval);
  }

  collectionInterval = setInterval(() => {
    // 添加数据点
    addDataPoint();

    // 更新图表
    updateChart();
  }, 200); // 每200ms采集一次
}

/**
 * 停止数据采集
 */
function stopCollection() {
  if (collectionInterval) {
    clearInterval(collectionInterval);
    collectionInterval = null;
  }
}

/**
 * 添加数据点
 */
function addDataPoint() {
  const dataPoint = {
    timestamp: Date.now(),
    voltage: piezoStore.currentVoltage,
    displacement: piezoStore.currentDisplacement / 1000 // nm -> μm
  };

  mapData.value.push(dataPoint);

  // 限制数据点数量
  if (mapData.value.length > maxDataPoints) {
    mapData.value.shift();
  }
}

// ============ 数据导出 ============

/**
 * 导出映射数据
 */
function exportMapData() {
  if (mapData.value.length === 0) {
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
      '时间戳,电压(V),位移(μm)',
      ...mapData.value.map(d =>
        `${d.timestamp},${d.voltage.toFixed(3)},${d.displacement.toFixed(3)}`
      )
    ].join('\n');
    mimeType = 'text/csv;charset=utf-8;';
    extension = 'csv';
  } else if (format === 'json') {
    content = JSON.stringify({
      metadata: {
        exportTime: new Date().toISOString(),
        dataPoints: mapData.value.length,
        averageDisplacement: averageDisplacement.value,
        maxDisplacement: maxDisplacement.value,
        minDisplacement: minDisplacement.value,
        linearity: linearity.value
      },
      data: mapData.value
    }, null, 2);
    mimeType = 'application/json;charset=utf-8;';
    extension = 'json';
  }

  // 创建下载链接
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

/**
 * 清空映射数据
 */
function clearMapData() {
  mapData.value = [];
  updateChart();
  ElMessage.info('数据已清空');
}

// ============ 生命周期钩子 ============

onMounted(() => {
  nextTick(() => {
    initChart();
  });

  // 窗口大小变化时调整图表
  window.addEventListener('resize', () => {
    if (chartInstance) {
      chartInstance.resize();
    }
  });
});

onBeforeUnmount(() => {
  stopCollection();

  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
});

// ============ 监听器 ============

// 监听电压和位移变化，实时更新工作点
watch([currentVoltage, currentDisplacement], () => {
  if (isCollecting.value) {
    updateWorkingPoint();
  }
});
</script>

<style scoped>
.voltage-map-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  padding: var(--spacing-4);
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

/* 头部样式 */
.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--spacing-3);
  border-bottom: 1px solid var(--color-border-secondary);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.map-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.status-indicators {
  display: flex;
  gap: var(--spacing-4);
}

.indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-status-offline);
  transition: var(--transition-all);
}

.indicator-dot.active {
  background: var(--color-status-online);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.indicator-label {
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

.tool-btn--active {
  border-color: var(--color-primary-500);
  background: var(--color-primary-500);
  color: white;
}

.tool-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 图表区域 */
.chart-wrapper {
  position: relative;
  width: 100%;
  height: 400px;
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.chart-container {
  width: 100%;
  height: 100%;
}

/* 当前工作点指示器 */
.working-point {
  position: absolute;
  top: var(--spacing-3);
  right: var(--spacing-3);
  padding: var(--spacing-3);
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(8px);
}

.point-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-2);
}

.point-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.info-item {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-3);
}

.info-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.info-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

/* 统计信息 */
.map-statistics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-3);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.stat-card:hover {
  border-color: var(--color-primary-400);
  box-shadow: var(--shadow-sm);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--color-primary-50);
  color: var(--color-primary-500);
  font-size: var(--font-size-xl);
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-1);
}

.stat-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .map-statistics {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .map-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-3);
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }

  .map-statistics {
    grid-template-columns: 1fr;
  }

  .chart-wrapper {
    height: 300px;
  }

  .working-point {
    top: var(--spacing-2);
    right: var(--spacing-2);
    padding: var(--spacing-2);
  }
}
</style>
