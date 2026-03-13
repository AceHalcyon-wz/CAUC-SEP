<script setup lang="ts">
/**
 * @file ChartAnalysis.vue
 * @path src/components/
 * @description 图表分析核心组件，支持多种图表类型、交互式缩放平移、数据标注和配置管理
 * @author Agent
 * @date 2024-03-07
 */

import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';
import ChartToolbar from './ChartToolbar.vue';
import {
  createZoomConfig,
  createTooltipConfig,
  createToolboxConfig,
  createMarkPointConfig,
  createMarkLineConfig,
  exportChartAsImage,
  exportChartAsSVG,
  exportDataAsCSV,
  downsampleData,
  smartSampling,
  measureChartPerformance,
  FPSMonitor,
} from '@/utils/chartUtils';

/** 图表配置模板接口 */
interface ChartConfig {
  id: string;
  name: string;
  chartType: string;
  showGrid: boolean;
  enableZoom: boolean;
  series: any[];
  xAxis: any;
  yAxis: any;
  annotations: Annotation[];
  createdAt: string;
}

/** 标注接口 */
interface Annotation {
  id: string;
  type: 'point' | 'line' | 'area' | 'measure';
  data: any;
  label?: string;
  color?: string;
}

/** Props定义 */
interface Props {
  /** 图表数据 */
  data?: {
    xData: number[];
    yData: number[];
    name?: string;
  }[];
  /** 初始图表类型 */
  initialChartType?: string;
  /** 是否显示工具栏 */
  showToolbar?: boolean;
  /** 是否启用标注 */
  enableAnnotation?: boolean;
  /** 图表高度 */
  height?: string;
}

/** Emits定义 */
const emit = defineEmits<{
  (e: 'chartClick', params: any): void;
  (e: 'annotationAdd', annotation: Annotation): void;
  (e: 'configChange', config: ChartConfig): void;
}>();

const props = withDefaults(defineProps<Props>(), {
  data: () => [],
  initialChartType: 'line',
  showToolbar: true,
  enableAnnotation: true,
  height: '500px',
});

/** 图表容器引用 */
const chartContainerRef = ref<HTMLElement | null>(null);

/** 图表实例 */
let chartInstance: echarts.ECharts | null = null;

/** 当前图表类型 */
const chartType = ref(props.initialChartType);

/** 显示网格 */
const showGrid = ref(true);

/** 启用缩放 */
const enableZoom = ref(true);

/** 缩放级别 */
const zoomLevel = ref(100);

/** 当前标注模式 */
const annotationMode = ref('none');

/** 标注列表 */
const annotations = ref<Annotation[]>([]);

/** 是否全屏 */
const isFullscreen = ref(false);

/** 图表配置模板列表 */
const configTemplates = ref<ChartConfig[]>([]);

/** 图表颜色 */
const chartColors = [
  '#409eff',
  '#67c23a',
  '#e6a23c',
  '#f56c6c',
  '#9c27b0',
  '#00bcd4',
];

/** 临时标注数据 */
const tempAnnotation = reactive({
  startPoint: null as any,
  endPoint: null as any,
  isDrawing: false,
});

/**
 * 初始化图表
 */
function initChart(): void {
  if (!chartContainerRef.value) return;

  // 销毁旧实例
  if (chartInstance) {
    chartInstance.dispose();
  }

  // 创建新实例
  chartInstance = echarts.init(chartContainerRef.value);

  // 设置初始配置
  updateChart();

  // 绑定事件
  bindChartEvents();

  // 监听窗口大小变化
  window.addEventListener('resize', handleResize);
}

/**
 * 绑定图表事件
 */
function bindChartEvents(): void {
  if (!chartInstance) return;

  // 点击事件
  chartInstance.on('click', (params: any) => {
    emit('chartClick', params);
    handleChartClick(params);
  });

  // 数据缩放事件
  chartInstance.on('datazoom', (params: any) => {
    const newZoomLevel = Math.round(
      ((params.end || 100) - (params.start || 0)) / 100 * 100
    );
    zoomLevel.value = Math.max(25, Math.min(500, newZoomLevel));
  });
}

/**
 * 处理图表点击事件
 * 
 * @param {any} params - 点击参数
 */
function handleChartClick(params: any): void {
  if (annotationMode.value === 'none' || !props.enableAnnotation) return;

  const { dataIndex, value, name } = params;

  switch (annotationMode.value) {
    case 'point':
      addPointAnnotation(dataIndex, value, name);
      break;
    case 'line':
      handleLineAnnotation(dataIndex, value);
      break;
    case 'area':
      handleAreaAnnotation(dataIndex, value);
      break;
    case 'measure':
      handleMeasureAnnotation(dataIndex, value);
      break;
  }
}

/**
 * 添加点标注
 * 
 * @param {number} dataIndex - 数据索引
 * @param {any} value - 数据值
 * @param {string} name - 系列名称
 */
function addPointAnnotation(dataIndex: number, value: any, name: string): void {
  const annotation: Annotation = {
    id: `point_${Date.now()}`,
    type: 'point',
    data: {
      coord: [dataIndex, value],
      value: value.toFixed(3),
    },
    label: `标注点 ${annotations.value.length + 1}`,
    color: '#f56c6c',
  };

  annotations.value.push(annotation);
  updateChartAnnotations();
  emit('annotationAdd', annotation);
  ElMessage.success('已添加点标注');
}

/**
 * 处理线标注
 * 
 * @param {number} dataIndex - 数据索引
 * @param {any} value - 数据值
 */
function handleLineAnnotation(dataIndex: number, value: any): void {
  if (!tempAnnotation.isDrawing) {
    tempAnnotation.startPoint = { dataIndex, value };
    tempAnnotation.isDrawing = true;
    ElMessage.info('请点击第二个点完成线标注');
  } else {
    const annotation: Annotation = {
      id: `line_${Date.now()}`,
      type: 'line',
      data: {
        start: tempAnnotation.startPoint,
        end: { dataIndex, value },
      },
      label: `线标注 ${annotations.value.length + 1}`,
      color: '#409eff',
    };

    annotations.value.push(annotation);
    updateChartAnnotations();
    emit('annotationAdd', annotation);

    // 重置临时状态
    tempAnnotation.startPoint = null;
    tempAnnotation.isDrawing = false;
    ElMessage.success('已添加线标注');
  }
}

/**
 * 处理区域标注
 * 
 * @param {number} dataIndex - 数据索引
 * @param {any} value - 数据值
 */
function handleAreaAnnotation(dataIndex: number, value: any): void {
  if (!tempAnnotation.isDrawing) {
    tempAnnotation.startPoint = { dataIndex, value };
    tempAnnotation.isDrawing = true;
    ElMessage.info('请点击对角点完成区域标注');
  } else {
    const annotation: Annotation = {
      id: `area_${Date.now()}`,
      type: 'area',
      data: {
        start: tempAnnotation.startPoint,
        end: { dataIndex, value },
      },
      label: `区域标注 ${annotations.value.length + 1}`,
      color: 'rgba(64, 158, 255, 0.3)',
    };

    annotations.value.push(annotation);
    updateChartAnnotations();
    emit('annotationAdd', annotation);

    // 重置临时状态
    tempAnnotation.startPoint = null;
    tempAnnotation.isDrawing = false;
    ElMessage.success('已添加区域标注');
  }
}

/**
 * 处理距离测量
 * 
 * @param {number} dataIndex - 数据索引
 * @param {any} value - 数据值
 */
function handleMeasureAnnotation(dataIndex: number, value: any): void {
  if (!tempAnnotation.isDrawing) {
    tempAnnotation.startPoint = { dataIndex, value };
    tempAnnotation.isDrawing = true;
    ElMessage.info('请点击第二个点测量距离');
  } else {
    const dx = Math.abs(dataIndex - tempAnnotation.startPoint.dataIndex);
    const dy = Math.abs(value - tempAnnotation.startPoint.value);
    const distance = Math.sqrt(dx * dx + dy * dy);

    const annotation: Annotation = {
      id: `measure_${Date.now()}`,
      type: 'measure',
      data: {
        start: tempAnnotation.startPoint,
        end: { dataIndex, value },
        distance: distance.toFixed(3),
      },
      label: `距离: ${distance.toFixed(3)}`,
      color: '#e6a23c',
    };

    annotations.value.push(annotation);
    updateChartAnnotations();
    emit('annotationAdd', annotation);

    // 重置临时状态
    tempAnnotation.startPoint = null;
    tempAnnotation.isDrawing = false;
    ElMessage.success(`测量距离: ${distance.toFixed(3)}`);
  }
}

/**
 * 更新图表标注
 */
function updateChartAnnotations(): void {
  if (!chartInstance) return;

  const option = chartInstance.getOption() as any;

  // 为每个系列添加标注
  if (option.series && option.series.length > 0) {
    const markPoints = annotations.value
      .filter(a => a.type === 'point')
      .map(a => ({
        name: a.label,
        coord: a.data.coord,
        value: a.data.value,
        itemStyle: { color: a.color },
      }));

    const markLines = annotations.value
      .filter(a => a.type === 'line' || a.type === 'measure')
      .map(a => [
        {
          name: a.label,
          coord: [a.data.start.dataIndex, a.data.start.value],
        },
        {
          coord: [a.data.end.dataIndex, a.data.end.value],
          label: {
            formatter: a.label,
          },
        },
      ]);

    option.series[0].markPoint = createMarkPointConfig(markPoints);
    option.series[0].markLine = createMarkLineConfig(
      markLines.flat().filter(Boolean)
    );

    chartInstance.setOption(option);
  }
}

/**
 * 更新图表
 */
function updateChart(): void {
  if (!chartInstance || !props.data || props.data.length === 0) return;

  const series = props.data.map((item, index) => {
    const baseConfig = {
      name: item.name || `数据系列 ${index + 1}`,
      data: item.yData,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 2,
        color: chartColors[index % chartColors.length],
      },
      itemStyle: {
        color: chartColors[index % chartColors.length],
      },
    };

    // 根据图表类型配置
    switch (chartType.value) {
      case 'line':
        return {
          ...baseConfig,
          type: 'line',
        };
      case 'scatter':
        return {
          ...baseConfig,
          type: 'scatter',
          symbolSize: 8,
        };
      case 'bar':
        return {
          ...baseConfig,
          type: 'bar',
          barMaxWidth: 40,
        };
      case 'area':
        return {
          ...baseConfig,
          type: 'line',
          areaStyle: {
            color: chartColors[index % chartColors.length],
            opacity: 0.3,
          },
        };
      case 'mixed':
        // 混合图表：第一个系列为折线，其余为柱状
        return {
          ...baseConfig,
          type: index === 0 ? 'line' : 'bar',
          ...(index !== 0 && { barMaxWidth: 40 }),
        };
      default:
        return {
          ...baseConfig,
          type: 'line',
        };
    }
  });

  const option = {
    backgroundColor: '#ffffff',
    grid: {
      left: '8%',
      right: '5%',
      top: '12%',
      bottom: enableZoom.value ? '18%' : '12%',
      containLabel: true,
    },
    tooltip: createTooltipConfig(),
    legend: {
      top: 10,
      textStyle: { color: '#4a5568' },
    },
    xAxis: {
      type: 'category',
      data: props.data[0]?.xData || [],
      name: 'X轴',
      nameTextStyle: { color: '#4a5568' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#4a5568' },
      splitLine: {
        show: showGrid.value,
        lineStyle: { color: '#edf2f7' },
      },
    },
    yAxis: {
      type: 'value',
      name: 'Y轴',
      nameTextStyle: { color: '#4a5568' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#4a5568' },
      splitLine: {
        show: showGrid.value,
        lineStyle: { color: '#edf2f7' },
      },
    },
    dataZoom: enableZoom.value
      ? createZoomConfig({
          slider: true,
          inside: true,
        })
      : [],
    toolbox: createToolboxConfig({
      showZoom: false,
      showRestore: true,
      showSaveAsImage: false,
    }),
    series,
  };

  chartInstance.setOption(option, true);

  // 更新标注
  if (annotations.value.length > 0) {
    updateChartAnnotations();
  }
}

// ==================== 增强的缩放平移功能 ====================

/** 缩放动画配置 */
const zoomAnimationConfig = {
  duration: 300,
  easing: 'cubicOut',
}

/** 平移状态 */
const panState = ref({
  isPanning: false,
  startX: 0,
  startY: 0,
  startDataZoom: null as any,
})

/** 缩放历史记录（用于撤销） */
const zoomHistory = ref<Array<{ start: number; end: number }>>([])
const zoomHistoryIndex = ref(-1)

/**
 * 处理缩放放大
 * 支持平滑动画和性能优化
 */
function handleZoomIn(): void {
  if (!chartInstance) return;

  const option = chartInstance.getOption() as any;
  if (option.dataZoom && option.dataZoom.length > 0) {
    const currentStart = option.dataZoom[0].start || 0;
    const currentEnd = option.dataZoom[0].end || 100;
    const range = currentEnd - currentStart;
    
    // 平滑缩放动画
    const newRange = range * 0.8;
    const center = (currentStart + currentEnd) / 2;
    const newStart = Math.max(0, center - newRange / 2);
    const newEnd = Math.min(100, center + newRange / 2);

    // 保存到历史记录
    saveZoomHistory(currentStart, currentEnd);

    // 平滑缩放动画
    animateZoom(currentStart, currentEnd, newStart, newEnd);
  }
}

/**
 * 处理缩放缩小（带动画）
 */
function handleZoomOut(): void {
  if (!chartInstance) return;

  const option = chartInstance.getOption() as any;
  if (option.dataZoom && option.dataZoom.length > 0) {
    const currentStart = option.dataZoom[0].start || 0;
    const currentEnd = option.dataZoom[0].end || 100;
    const range = currentEnd - currentStart;
    const newRange = Math.min(100, range * 1.25);
    const center = (currentStart + currentEnd) / 2;
    const newStart = Math.max(0, center - newRange / 2);
    const newEnd = Math.min(100, center + newRange / 2);

    // 保存到历史记录
    saveZoomHistory(currentStart, currentEnd);

    // 平滑缩放动画
    animateZoom(currentStart, currentEnd, newStart, newEnd);
  }
}

/**
 * 平滑缩放动画
 * 
 * @param {number} fromStart - 起始开始位置
 * @param {number} fromEnd - 起始结束位置
 * @param {number} toStart - 目标开始位置
 * @param {number} toEnd - 目标结束位置
 */
function animateZoom(fromStart: number, fromEnd: number, toStart: number, toEnd: number): void {
  if (!chartInstance) return;

  const startTime = Date.now();
  const duration = zoomAnimationConfig.duration;

  function animate() {
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // 缓动函数
    const eased = easeOutCubic(progress);
    
    // 计算当前值
    const currentStart = fromStart + (toStart - fromStart) * eased;
    const currentEnd = fromEnd + (toEnd - fromEnd) * eased;

    // 应用缩放
    chartInstance!.dispatchAction({
      type: 'dataZoom',
      start: currentStart,
      end: currentEnd,
    });

    // 更新缩放级别
    zoomLevel.value = Math.round(100 / (currentEnd - currentStart) * 100);

    // 继续动画
    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  }

  requestAnimationFrame(animate);
}

/**
 * 缓动函数（三次方缓出）
 * 
 * @param {number} t - 进度 (0-1)
 * @returns {number} 缓动后的值
 */
function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

/**
 * 保存缩放历史记录
 * 
 * @param {number} start - 开始位置
 * @param {number} end - 结束位置
 */
function saveZoomHistory(start: number, end: number): void {
  // 移除当前位置之后的历史
  zoomHistory.value = zoomHistory.value.slice(0, zoomHistoryIndex.value + 1);
  
  // 添加新记录
  zoomHistory.value.push({ start, end });
  zoomHistoryIndex.value = zoomHistory.value.length - 1;
  
  // 限制历史记录数量
  if (zoomHistory.value.length > 20) {
    zoomHistory.value.shift();
    zoomHistoryIndex.value--;
  }
}

/**
 * 撤销缩放
 */
function undoZoom(): void {
  if (zoomHistoryIndex.value > 0) {
    zoomHistoryIndex.value--;
    const history = zoomHistory.value[zoomHistoryIndex.value];
    
    if (history && chartInstance) {
      animateZoom(
        chartInstance.getOption().dataZoom[0].start,
        chartInstance.getOption().dataZoom[0].end,
        history.start,
        history.end
      );
    }
  }
}

/**
 * 重做缩放
 */
function redoZoom(): void {
  if (zoomHistoryIndex.value < zoomHistory.value.length - 1) {
    zoomHistoryIndex.value++;
    const history = zoomHistory.value[zoomHistoryIndex.value];
    
    if (history && chartInstance) {
      animateZoom(
        chartInstance.getOption().dataZoom[0].start,
        chartInstance.getOption().dataZoom[0].end,
        history.start,
        history.end
      );
    }
  }
}

/**
 * 重置视图
 */
function handleResetView(): void {
  if (!chartInstance) return;

  // 保存当前状态到历史
  const option = chartInstance.getOption() as any;
  if (option.dataZoom && option.dataZoom.length > 0) {
    saveZoomHistory(option.dataZoom[0].start, option.dataZoom[0].end);
  }

  // 平滑重置动画
  animateZoom(
    option.dataZoom?.[0]?.start || 0,
    option.dataZoom?.[0]?.end || 100,
    0,
    100
  );

  zoomLevel.value = 100;
  ElMessage.success('视图已重置');
}

/**
 * 缩放到指定区域
 * 
 * @param {number} start - 开始位置百分比
 * @param {number} end - 结束位置百分比
 */
function zoomToRegion(start: number, end: number): void {
  if (!chartInstance) return;

  const option = chartInstance.getOption() as any;
  if (option.dataZoom && option.dataZoom.length > 0) {
    saveZoomHistory(option.dataZoom[0].start, option.dataZoom[0].end);
    animateZoom(option.dataZoom[0].start, option.dataZoom[0].end, start, end);
  }
}

/**
 * 处理鼠标滚轮缩放
 * 
 * @param {WheelEvent} event - 滚轮事件
 */
function handleWheelZoom(event: WheelEvent): void {
  if (!enableZoom.value || !chartInstance) return;

  event.preventDefault();

  const delta = event.deltaY > 0 ? 1.1 : 0.9;
  
  const option = chartInstance.getOption() as any;
  if (option.dataZoom && option.dataZoom.length > 0) {
    const currentStart = option.dataZoom[0].start || 0;
    const currentEnd = option.dataZoom[0].end || 100;
    const range = currentEnd - currentStart;
    const center = (currentStart + currentEnd) / 2;
    
    const newRange = Math.min(100, Math.max(5, range * delta));
    const newStart = Math.max(0, center - newRange / 2);
    const newEnd = Math.min(100, center + newRange / 2);

    chartInstance.dispatchAction({
      type: 'dataZoom',
      start: newStart,
      end: newEnd,
    });

    zoomLevel.value = Math.round(100 / newRange * 100);
  }
}

/**
 * 处理双击重置
 */
function handleDoubleClick(): void {
  handleResetView();
}

/**
 * 导出图片
 * 
 * @param {string} format - 图片格式
 */
async function handleExportImage(format: string): Promise<void> {
  if (!chartInstance) {
    ElMessage.warning('图表未初始化');
    return;
  }

  try {
    const fileName = `chart_${Date.now()}`;

    if (format === 'svg') {
      await exportChartAsSVG(chartInstance, fileName);
    } else {
      await exportChartAsImage(chartInstance, {
        fileName,
        type: format as 'png' | 'jpeg',
        pixelRatio: 2,
      });
    }

    ElMessage.success(`图表已导出为${format.toUpperCase()}格式`);
  } catch (error) {
    console.error('导出失败:', error);
    ElMessage.error('导出失败，请重试');
  }
}

/**
 * 导出配置
 */
function handleExportConfig(): void {
  if (!chartInstance) return;

  const config: ChartConfig = {
    id: `config_${Date.now()}`,
    name: `图表配置 ${new Date().toLocaleString()}`,
    chartType: chartType.value,
    showGrid: showGrid.value,
    enableZoom: enableZoom.value,
    series: props.data,
    xAxis: {},
    yAxis: {},
    annotations: annotations.value,
    createdAt: new Date().toISOString(),
  };

  const blob = new Blob([JSON.stringify(config, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `chart_config_${Date.now()}.json`;
  link.click();
  URL.revokeObjectURL(url);

  ElMessage.success('配置已导出');
}

/**
 * 导入配置
 */
function handleImportConfig(): void {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';

  input.onchange = (e: Event) => {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const config: ChartConfig = JSON.parse(event.target?.result as string);

        // 应用配置
        chartType.value = config.chartType;
        showGrid.value = config.showGrid;
        enableZoom.value = config.enableZoom;
        annotations.value = config.annotations || [];

        updateChart();

        ElMessage.success('配置已导入');
      } catch (error) {
        console.error('导入配置失败:', error);
        ElMessage.error('配置文件格式错误');
      }
    };
    reader.readAsText(file);
  };

  input.click();
}

/**
 * 保存为模板
 */
function handleSaveTemplate(): void {
  if (!chartInstance) return;

  const template: ChartConfig = {
    id: `template_${Date.now()}`,
    name: `模板 ${configTemplates.value.length + 1}`,
    chartType: chartType.value,
    showGrid: showGrid.value,
    enableZoom: enableZoom.value,
    series: [],
    xAxis: {},
    yAxis: {},
    annotations: [],
    createdAt: new Date().toISOString(),
  };

  configTemplates.value.push(template);

  // 保存到本地存储
  localStorage.setItem(
    'chartTemplates',
    JSON.stringify(configTemplates.value)
  );

  ElMessage.success('模板已保存');
}

/**
 * 切换全屏
 */
function handleToggleFullscreen(): void {
  if (!chartContainerRef.value) return;

  if (!isFullscreen.value) {
    chartContainerRef.value.requestFullscreen?.();
  } else {
    document.exitFullscreen?.();
  }

  isFullscreen.value = !isFullscreen.value;
}

/**
 * 清除标注
 */
function handleClearAnnotations(): void {
  annotations.value = [];
  updateChart();
}

/**
 * 处理窗口大小变化
 */
function handleResize(): void {
  chartInstance?.resize();
}

/**
 * 导出数据为CSV
 * 支持大数据量导出和自定义格式
 */
async function handleExportCSV(): Promise<void> {
  if (!props.data || props.data.length === 0) {
    ElMessage.warning('没有数据可导出');
    return;
  }

  try {
    // 显示导出进度
    const loading = ElMessage({
      message: '正在导出数据...',
      type: 'info',
      duration: 0,
    });

    // 构建CSV数据
    const headers = ['序号', ...props.data.map((_, i) => `数据系列${i + 1}`)];
    const rows = [];
    
    // 使用分批处理避免阻塞主线程
    const batchSize = 10000;
    const totalRows = props.data[0].yData.length;
    
    for (let i = 0; i < totalRows; i += batchSize) {
      const batchEnd = Math.min(i + batchSize, totalRows);
      
      for (let j = i; j < batchEnd; j++) {
        rows.push([
          j,
          ...props.data.map(d => d.yData[j]?.toFixed(6) || ''),
        ]);
      }
      
      // 让出主线程
      if (i + batchSize < totalRows) {
        await new Promise(resolve => setTimeout(resolve, 0));
      }
    }

    await exportDataAsCSV({ headers, rows }, `chart_data_${Date.now()}`);
    
    loading.close();
    ElMessage.success('数据已导出为CSV');
  } catch (error) {
    console.error('导出CSV失败:', error);
    ElMessage.error('导出失败，请重试');
  }
}

/**
 * 导出数据为JSON
 * 包含完整的图表配置和数据
 */
async function handleExportJSON(): Promise<void> {
  if (!props.data || props.data.length === 0) {
    ElMessage.warning('没有数据可导出');
    return;
  }

  try {
    const exportData = {
      metadata: {
        exportTime: new Date().toISOString(),
        chartType: chartType.value,
        seriesCount: props.data.length,
        dataPoints: props.data[0].yData.length,
      },
      config: {
        showGrid: showGrid.value,
        enableZoom: enableZoom.value,
        annotations: annotations.value,
      },
      data: props.data.map((series, index) => ({
        name: series.name || `数据系列 ${index + 1}`,
        xData: series.xData,
        yData: series.yData,
      })),
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `chart_data_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);

    ElMessage.success('数据已导出为JSON');
  } catch (error) {
    console.error('导出JSON失败:', error);
    ElMessage.error('导出失败，请重试');
  }
}

/**
 * 导出数据为Excel格式（CSV with BOM）
 * 确保Excel正确识别中文
 */
async function handleExportExcel(): Promise<void> {
  if (!props.data || props.data.length === 0) {
    ElMessage.warning('没有数据可导出');
    return;
  }

  try {
    // 构建Excel兼容的CSV
    const headers = ['序号', ...props.data.map((_, i) => `数据系列${i + 1}`)];
    const rows = props.data[0].yData.map((_, index) => [
      index,
      ...props.data.map(d => d.yData[index]?.toFixed(6) || ''),
    ]);

    // 添加UTF-8 BOM
    const BOM = '\uFEFF';
    const csvContent = BOM + [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `chart_data_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);

    ElMessage.success('数据已导出为Excel格式');
  } catch (error) {
    console.error('导出Excel失败:', error);
    ElMessage.error('导出失败，请重试');
  }
}

// 监听数据变化
watch(
  () => props.data,
  () => {
    nextTick(() => {
      updateChart();
    });
  },
  { deep: true }
);

// 监听图表类型变化
watch(chartType, () => {
  updateChart();
});

// 监听网格显示变化
watch(showGrid, () => {
  updateChart();
});

// 监听缩放启用变化
watch(enableZoom, () => {
  updateChart();
});

// 组件挂载时初始化
onMounted(() => {
  nextTick(() => {
    initChart();

    // 加载本地模板
    const savedTemplates = localStorage.getItem('chartTemplates');
    if (savedTemplates) {
      try {
        configTemplates.value = JSON.parse(savedTemplates);
      } catch (error) {
        console.error('加载模板失败:', error);
      }
    }
  });
});

// 组件卸载时清理
onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  chartInstance?.dispose();
});

// 暴露方法给父组件
defineExpose({
  chartInstance,
  updateChart,
  handleExportImage,
  handleExportCSV,
  handleClearAnnotations,
});
</script>

<template>
  <div
    class="chart-analysis"
    :class="{ fullscreen: isFullscreen }"
  >
    <!-- 工具栏 -->
    <ChartToolbar
      v-if="showToolbar"
      v-model:chart-type="chartType"
      v-model:show-grid="showGrid"
      v-model:enable-zoom="enableZoom"
      v-model:zoom-level="zoomLevel"
      v-model:annotation-mode="annotationMode"
      @zoom-in="handleZoomIn"
      @zoom-out="handleZoomOut"
      @reset-view="handleResetView"
      @export-image="handleExportImage"
      @export-config="handleExportConfig"
      @import-config="handleImportConfig"
      @save-template="handleSaveTemplate"
      @toggle-fullscreen="handleToggleFullscreen"
      @clear-annotations="handleClearAnnotations"
    />

    <!-- 图表容器 -->
    <div class="chart-wrapper">
      <div
        ref="chartContainerRef"
        class="chart-container"
        :style="{ height: height }"
      />

      <!-- 空状态 -->
      <div
        v-if="!data || data.length === 0"
        class="empty-state"
      >
        <el-icon :size="64">
          <i class="el-icon-pie-chart" />
        </el-icon>
        <p>暂无图表数据</p>
        <p class="hint">
          请添加数据后查看图表
        </p>
      </div>
    </div>

    <!-- 标注列表 -->
    <div
      v-if="annotations.length > 0"
      class="annotations-panel"
    >
      <div class="panel-header">
        <span>标注列表</span>
        <el-button
          type="danger"
          size="small"
          text
          @click="handleClearAnnotations"
        >
          清除全部
        </el-button>
      </div>
      <div class="annotation-list">
        <div
          v-for="annotation in annotations"
          :key="annotation.id"
          class="annotation-item"
        >
          <div class="annotation-info">
            <el-icon :style="{ color: annotation.color }">
              <i :class="`el-icon-${annotation.type}`" />
            </el-icon>
            <span>{{ annotation.label }}</span>
          </div>
          <el-button
            type="danger"
            size="small"
            text
            @click="annotations = annotations.filter(a => a.id !== annotation.id)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chart-analysis {
  display: flex;
  flex-direction: column;
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);

  &.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
    border-radius: 0;
  }
}

.chart-wrapper {
  position: relative;
  flex: 1;
  padding: var(--spacing-4);
  background-color: var(--color-surface-primary);
}

.chart-container {
  width: 100%;
  min-height: 400px;
}

.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
  text-align: center;

  .el-icon {
    color: var(--color-neutral-400);
    margin-bottom: var(--spacing-4);
    opacity: 0.6;
  }

  p {
    margin: var(--spacing-1) 0;
    font-size: var(--font-size-base);
  }

  .hint {
    font-size: var(--font-size-sm);
    color: var(--color-text-disabled);
  }
}

.annotations-panel {
  border-top: 1px solid var(--color-border-primary);
  background-color: var(--color-bg-secondary);
  padding: var(--spacing-4);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.annotation-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  max-height: 200px;
  overflow-y: auto;
}

.annotation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) var(--spacing-3);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.annotation-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .chart-analysis {
    border-radius: 0;
  }

  .chart-wrapper {
    padding: var(--spacing-2);
  }

  .chart-container {
    min-height: 300px;
  }
}
</style>
