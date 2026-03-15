/**
 * @file chartUtils.js
 * @path src/utils/
 * @description ECharts 图表工具函数集，提供性能优化、缩放平移、标注和导出功能
 * @author Agent
 * @date 2024-03-06
 * @dependencies echarts
 */

import * as echarts from 'echarts';

/**
 * 数据采样配置常量
 */
const SAMPLING_CONFIG = {
  /** 大数据量阈值 */
  LARGE_DATA_THRESHOLD: 10000,
  /** 默认采样数量 */
  DEFAULT_SAMPLE_SIZE: 5000,
  /** 最小采样数量 */
  MIN_SAMPLE_SIZE: 1000,
  /** 平稳数据波动阈值 */
  STABLE_FLUCTUATION_THRESHOLD: 0.01,
  /** 周期性检测窗口大小 */
  PERIOD_DETECTION_WINDOW: 100,
  /** 渐进渲染阈值 */
  PROGRESSIVE_THRESHOLD: 5000,
  /** 渐进渲染批次大小 */
  PROGRESSIVE_BATCH_SIZE: 1000,
};

/**
 * 数据特征类型枚举
 */
const DATA_CHARACTERISTICS = {
  STABLE: 'stable',      // 平稳数据
  VOLATILE: 'volatile',  // 波动数据
  PERIODIC: 'periodic',  // 周期性数据
  TREND: 'trend',        // 趋势数据
};

/**
 * 对大数据进行降采样（LTTB算法）
 * 
 * @param {Array} data - 原始数据数组
 * @param {number} threshold - 采样阈值
 * @returns {Array} 采样后的数据
 */
export function downsampleData(data, threshold = SAMPLING_CONFIG.DEFAULT_SAMPLE_SIZE) {
  if (!data || data.length <= threshold) {
    return data;
  }

  const dataLength = data.length;
  const sampled = [];

  // 保留第一个点
  sampled.push(data[0]);

  // Bucket size. Leave room for start and end data points
  const bucketSize = (dataLength - 2) / (threshold - 2);

  let a = 0; // Initially a is the first point in the triangle

  for (let i = 0; i < threshold - 2; i++) {
    // Calculate point average for next bucket
    let avgX = 0;
    let avgY = 0;
    let avgRangeStart = Math.floor((i + 0) * bucketSize) + 1;
    const avgRangeEnd = Math.floor((i + 1) * bucketSize) + 1;
    const avgRangeLength = avgRangeEnd - avgRangeStart;

    for (; avgRangeStart < avgRangeEnd; avgRangeStart++) {
      const point = data[avgRangeStart];
      avgX += point[0];
      avgY += point[1];
    }
    avgX /= avgRangeLength;
    avgY /= avgRangeLength;

    // Get the range for this bucket
    const rangeOffs = Math.floor((i + 0) * bucketSize) + 1;
    const rangeTo = Math.floor((i + 1) * bucketSize) + 1;

    // Point a
    const pointAX = data[a][0];
    const pointAY = data[a][1];

    let maxArea = -1;
    let maxAreaPoint = null;

    for (let j = rangeOffs; j < rangeTo; j++) {
      // Calculate triangle area over three points
      const area = Math.abs(
        (pointAX - avgX) * (data[j][1] - pointAY) -
        (pointAX - data[j][0]) * (avgY - pointAY)
      ) * 0.5;

      if (area > maxArea) {
        maxArea = area;
        maxAreaPoint = data[j];
        a = j; // Next a is this b
      }
    }

    if (maxAreaPoint) {
      sampled.push(maxAreaPoint);
    }
  }

  // 保留最后一个点
  sampled.push(data[dataLength - 1]);

  return sampled;
}

/**
 * 对一维数组数据进行采样
 * 
 * @param {Array<number>} dataArray - 一维数据数组
 * @param {number} threshold - 采样阈值
 * @returns {Array<number>} 采样后的数据
 */
export function downsampleArray(dataArray, threshold = SAMPLING_CONFIG.DEFAULT_SAMPLE_SIZE) {
  if (!dataArray || dataArray.length <= threshold) {
    return dataArray;
  }

  // 转换为二维数组格式 [index, value]
  const twoDimData = dataArray.map((value, index) => [index, value]);
  
  // 使用LTTB算法采样
  const sampled = downsampleData(twoDimData, threshold);
  
  // 提取值
  return sampled.map(point => point[1]);
}

/**
 * 智能数据采样算法
 * 当数据点超过阈值时自动启用采样，保留关键特征
 * 
 * @param {Array} data - 原始数据数组，支持一维或二维格式
 * @param {number} maxPoints - 最大数据点数
 * @returns {Array} 采样后的数据
 */
export function smartSampling(data, maxPoints = SAMPLING_CONFIG.DEFAULT_SAMPLE_SIZE) {
  if (!data || data.length <= maxPoints) {
    return data;
  }

  // 检测数据格式
  const isTwoDimensional = Array.isArray(data[0]) && data[0].length === 2;
  
  if (isTwoDimensional) {
    // 二维数据直接使用LTTB算法
    return downsampleData(data, maxPoints);
  } else {
    // 一维数据转换为二维后采样
    return downsampleArray(data, maxPoints);
  }
}

/**
 * 检测数据特征
 * 
 * @param {Array<number>} data - 一维数据数组
 * @returns {string} 数据特征类型
 */
export function detectDataCharacteristics(data) {
  if (!data || data.length < 10) {
    return DATA_CHARACTERISTICS.STABLE;
  }

  // 计算基本统计量
  const mean = data.reduce((sum, val) => sum + val, 0) / data.length;
  const variance = data.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / data.length;
  const stdDev = Math.sqrt(variance);
  
  // 计算变异系数（标准差/均值）
  const cv = mean !== 0 ? stdDev / Math.abs(mean) : stdDev;
  
  // 检测平稳性
  if (cv < SAMPLING_CONFIG.STABLE_FLUCTUATION_THRESHOLD) {
    return DATA_CHARACTERISTICS.STABLE;
  }

  // 检测周期性
  const windowSize = Math.min(SAMPLING_CONFIG.PERIOD_DETECTION_WINDOW, Math.floor(data.length / 3));
  const autocorr = calculateAutocorrelation(data, windowSize);
  
  if (autocorr.maxCorrelation > 0.7 && autocorr.period > 0) {
    return DATA_CHARACTERISTICS.PERIODIC;
  }

  // 检测趋势
  const trend = detectTrend(data);
  if (Math.abs(trend) > 0.5) {
    return DATA_CHARACTERISTICS.TREND;
  }

  // 默认为波动数据
  return DATA_CHARACTERISTICS.VOLATILE;
}

/**
 * 计算自相关性（用于周期性检测）
 * 
 * @param {Array<number>} data - 数据数组
 * @param {number} maxLag - 最大延迟
 * @returns {Object} 包含最大相关性和周期
 */
function calculateAutocorrelation(data, maxLag) {
  const n = data.length;
  const mean = data.reduce((sum, val) => sum + val, 0) / n;
  const variance = data.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0);
  
  let maxCorrelation = -1;
  let period = 0;
  
  for (let lag = 1; lag < maxLag; lag++) {
    let correlation = 0;
    for (let i = 0; i < n - lag; i++) {
      correlation += (data[i] - mean) * (data[i + lag] - mean);
    }
    correlation /= variance;
    
    if (correlation > maxCorrelation) {
      maxCorrelation = correlation;
      period = lag;
    }
  }
  
  return { maxCorrelation, period };
}

/**
 * 检测数据趋势
 * 
 * @param {Array<number>} data - 数据数组
 * @returns {number} 趋势值（-1到1之间）
 */
function detectTrend(data) {
  const n = data.length;
  const xMean = (n - 1) / 2;
  const yMean = data.reduce((sum, val) => sum + val, 0) / n;
  
  let numerator = 0;
  let denominator = 0;
  
  for (let i = 0; i < n; i++) {
    numerator += (i - xMean) * (data[i] - yMean);
    denominator += Math.pow(i - xMean, 2);
  }
  
  // 归一化趋势值
  const slope = denominator !== 0 ? numerator / denominator : 0;
  const range = Math.max(...data) - Math.min(...data);
  
  return range !== 0 ? slope * n / range : 0;
}

/**
 * 自适应采样策略
 * 根据数据特征自动选择最佳采样方法
 * 
 * @param {Array<number>} xData - X轴数据
 * @param {Array<number>} yData - Y轴数据
 * @param {number} maxPoints - 最大数据点数
 * @returns {Object} 采样后的数据 { xData, yData }
 */
export function adaptiveSampling(xData, yData, maxPoints = SAMPLING_CONFIG.DEFAULT_SAMPLE_SIZE) {
  if (!xData || !yData || xData.length <= maxPoints) {
    return { xData: xData || [], yData: yData || [] };
  }

  // 检测数据特征
  const characteristics = detectDataCharacteristics(yData);
  
  // 根据特征选择采样策略
  switch (characteristics) {
    case DATA_CHARACTERISTICS.STABLE:
      // 平稳数据：使用简单等间隔采样
      return uniformSampling(xData, yData, maxPoints);
    
    case DATA_CHARACTERISTICS.PERIODIC:
      // 周期性数据：保留峰值和谷值
      return peakPreservingSampling(xData, yData, maxPoints);
    
    case DATA_CHARACTERISTICS.TREND:
      // 趋势数据：使用LTTB保留趋势特征
      return lttbSampling(xData, yData, maxPoints);
    
    case DATA_CHARACTERISTICS.VOLATILE:
    default:
      // 波动数据：使用LTTB保留关键转折点
      return lttbSampling(xData, yData, maxPoints);
  }
}

/**
 * 等间隔采样
 * 
 * @param {Array<number>} xData - X轴数据
 * @param {Array<number>} yData - Y轴数据
 * @param {number} maxPoints - 最大数据点数
 * @returns {Object} 采样后的数据
 */
function uniformSampling(xData, yData, maxPoints) {
  const step = Math.floor(xData.length / maxPoints);
  const sampledX = [];
  const sampledY = [];
  
  // 保留第一个点
  sampledX.push(xData[0]);
  sampledY.push(yData[0]);
  
  // 等间隔采样
  for (let i = step; i < xData.length - step; i += step) {
    sampledX.push(xData[i]);
    sampledY.push(yData[i]);
  }
  
  // 保留最后一个点
  sampledX.push(xData[xData.length - 1]);
  sampledY.push(yData[yData.length - 1]);
  
  return { xData: sampledX, yData: sampledY };
}

/**
 * 峰值保留采样
 * 
 * @param {Array<number>} xData - X轴数据
 * @param {Array<number>} yData - Y轴数据
 * @param {number} maxPoints - 最大数据点数
 * @returns {Object} 采样后的数据
 */
function peakPreservingSampling(xData, yData, maxPoints) {
  const n = xData.length;
  const indices = new Set();
  
  // 添加首尾点
  indices.add(0);
  indices.add(n - 1);
  
  // 检测局部极值点
  for (let i = 1; i < n - 1; i++) {
    const prev = yData[i - 1];
    const curr = yData[i];
    const next = yData[i + 1];
    
    // 局部最大值或最小值
    if ((curr > prev && curr > next) || (curr < prev && curr < next)) {
      indices.add(i);
    }
  }
  
  // 如果极值点数量仍然过多，进行二次采样
  if (indices.size > maxPoints) {
    const sortedIndices = Array.from(indices).sort((a, b) => a - b);
    const step = Math.floor(sortedIndices.length / maxPoints);
    const sampledIndices = new Set([0, n - 1]);
    
    for (let i = 0; i < sortedIndices.length; i += step) {
      sampledIndices.add(sortedIndices[i]);
    }
    
    return {
      xData: Array.from(sampledIndices).sort((a, b) => a - b).map(i => xData[i]),
      yData: Array.from(sampledIndices).sort((a, b) => a - b).map(i => yData[i])
    };
  }
  
  // 如果极值点数量不足，补充等间隔点
  if (indices.size < maxPoints) {
    const remaining = maxPoints - indices.size;
    const step = Math.floor(n / remaining);
    
    for (let i = step; i < n - step; i += step) {
      indices.add(i);
    }
  }
  
  const sortedIndices = Array.from(indices).sort((a, b) => a - b);
  
  return {
    xData: sortedIndices.map(i => xData[i]),
    yData: sortedIndices.map(i => yData[i])
  };
}

/**
 * LTTB采样（Largest-Triangle-Three-Buckets）
 * 
 * @param {Array<number>} xData - X轴数据
 * @param {Array<number>} yData - Y轴数据
 * @param {number} maxPoints - 最大数据点数
 * @returns {Object} 采样后的数据
 */
function lttbSampling(xData, yData, maxPoints) {
  // 转换为二维数组
  const twoDimData = xData.map((x, i) => [x, yData[i]]);
  
  // 使用LTTB算法
  const sampled = downsampleData(twoDimData, maxPoints);
  
  return {
    xData: sampled.map(point => point[0]),
    yData: sampled.map(point => point[1])
  };
}

/**
 * 创建数据缩放和平移配置
 * 
 * @param {Object} options - 配置选项
 * @param {boolean} options.inside - 是否启用内置缩放
 * @param {boolean} options.slider - 是否显示滑动条
 * @param {number} options.start - 初始起始位置百分比
 * @param {number} options.end - 初始结束位置百分比
 * @param {string} options.xAxisIndex - X轴索引
 * @param {string} options.yAxisIndex - Y轴索引
 * @returns {Object} ECharts dataZoom 配置
 */
export function createZoomConfig(options = {}) {
  const {
    inside = true,
    slider = true,
    start = 0,
    end = 100,
    xAxisIndex = 0,
    yAxisIndex = 0,
  } = options;

  const dataZoom = [];

  // 内置缩放（鼠标滚轮、拖拽）
  if (inside) {
    dataZoom.push({
      type: 'inside',
      xAxisIndex,
      yAxisIndex,
      start,
      end,
      zoomOnMouseWheel: true,
      moveOnMouseMove: true,
      moveOnMouseWheel: false,
      preventDefaultMouseMove: false,
    });
  }

  // 滑动条缩放
  if (slider) {
    dataZoom.push({
      type: 'slider',
      xAxisIndex,
      start,
      end,
      height: 20,
      bottom: 10,
      borderColor: '#ccc',
      backgroundColor: '#f0f0f0',
      fillerColor: 'rgba(64, 158, 255, 0.2)',
      handleStyle: {
        color: '#409eff',
      },
      textStyle: {
        color: '#333',
      },
    });
  }

  return dataZoom;
}

/**
 * 创建标注点配置
 * 
 * @param {Array} markPoints - 标注点数组
 * @param {Object} options - 配置选项
 * @returns {Object} ECharts markPoint 配置
 */
export function createMarkPointConfig(markPoints = [], options = {}) {
  const {
    symbol = 'pin',
    symbolSize = 40,
    itemColor = '#f56c6c',
    labelColor = '#fff',
  } = options;

  if (!markPoints || markPoints.length === 0) {
    return {};
  }

  return {
    symbol,
    symbolSize,
    itemStyle: {
      color: itemColor,
    },
    label: {
      show: true,
      color: labelColor,
      fontSize: 12,
    },
    data: markPoints.map(point => ({
      name: point.name || '',
      coord: point.coord,
      value: point.value,
      itemStyle: point.color ? { color: point.color } : undefined,
    })),
  };
}

/**
 * 创建标注线配置
 * 
 * @param {Array} markLines - 标注线数组
 * @param {Object} options - 配置选项
 * @returns {Object} ECharts markLine 配置
 */
export function createMarkLineConfig(markLines = [], options = {}) {
  const {
    lineColor = '#409eff',
    lineType = 'dashed',
    lineWidth = 2,
  } = options;

  if (!markLines || markLines.length === 0) {
    return {};
  }

  return {
    symbol: ['none', 'arrow'],
    lineStyle: {
      color: lineColor,
      type: lineType,
      width: lineWidth,
    },
    label: {
      show: true,
      position: 'end',
      formatter: '{b}: {c}',
    },
    data: markLines.map(line => ({
      name: line.name || '',
      yAxis: line.yAxis,
      xAxis: line.xAxis,
    })),
  };
}

/**
 * 导出图表为图片
 * 
 * @param {Object} chartInstance - ECharts 实例
 * @param {Object} options - 导出选项
 * @param {string} options.fileName - 文件名
 * @param {string} options.type - 图片类型 (png/jpeg/svg)
 * @param {number} options.pixelRatio - 像素比
 * @param {string} options.backgroundColor - 背景颜色
 * @returns {Promise<void>}
 */
export async function exportChartAsImage(chartInstance, options = {}) {
  if (!chartInstance) {
    throw new Error('图表实例不存在');
  }

  const {
    fileName = 'chart',
    type = 'png',
    pixelRatio = 2,
    backgroundColor = '#fff',
  } = options;

  try {
    const url = chartInstance.getDataURL({
      type,
      pixelRatio,
      backgroundColor,
    });

    // 创建下载链接
    const link = document.createElement('a');
    link.download = `${fileName}.${type}`;
    link.href = url;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    return true;
  } catch (error) {
    console.error('导出图表失败:', error);
    throw error;
  }
}

/**
 * 导出图表为 SVG
 * 
 * @param {Object} chartInstance - ECharts 实例
 * @param {string} fileName - 文件名
 * @returns {Promise<void>}
 */
export async function exportChartAsSVG(chartInstance, fileName = 'chart') {
  if (!chartInstance) {
    throw new Error('图表实例不存在');
  }

  try {
    const url = chartInstance.getDataURL({
      type: 'svg',
    });

    // SVG 是 base64 编码的，需要解码
    const svgContent = decodeURIComponent(url.split(',')[1]);
    
    // 创建 Blob
    const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const blobUrl = URL.createObjectURL(blob);

    // 创建下载链接
    const link = document.createElement('a');
    link.download = `${fileName}.svg`;
    link.href = blobUrl;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // 释放 Blob URL
    URL.revokeObjectURL(blobUrl);

    return true;
  } catch (error) {
    console.error('导出 SVG 失败:', error);
    throw error;
  }
}

/**
 * 创建工具箱配置（包含导出功能）
 * 
 * @param {Object} options - 配置选项
 * @returns {Object} ECharts toolbox 配置
 */
export function createToolboxConfig(options = {}) {
  const {
    showZoom = true,
    showRestore = true,
    showSaveAsImage = true,
    showDataView = false,
  } = options;

  const feature = {};

  if (showDataView) {
    feature.dataView = {
      show: true,
      readOnly: true,
      title: '数据视图',
      lang: ['数据视图', '关闭', '刷新'],
    };
  }

  if (showZoom) {
    feature.dataZoom = {
      show: true,
      title: {
        zoom: '区域缩放',
        back: '区域还原',
      },
    };
  }

  if (showRestore) {
    feature.restore = {
      show: true,
      title: '还原',
    };
  }

  if (showSaveAsImage) {
    feature.saveAsImage = {
      show: true,
      title: '保存为图片',
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff',
    };
  }

  return {
    show: true,
    right: 20,
    top: 10,
    feature,
  };
}

/**
 * 创建提示框配置
 * 
 * @param {Object} options - 配置选项
 * @returns {Object} ECharts tooltip 配置
 */
export function createTooltipConfig(options = {}) {
  const {
    trigger = 'axis',
    show = true,
    confine = true,
  } = options;

  return {
    show,
    trigger,
    confine,
    axisPointer: {
      type: 'cross',
      lineStyle: {
        color: '#999',
        width: 1,
        type: 'dashed',
      },
      crossStyle: {
        color: '#999',
      },
    },
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderColor: '#ddd',
    borderWidth: 1,
    textStyle: {
      color: '#333',
    },
  };
}

/**
 * 优化大数据量图表配置
 * 
 * @param {number} dataLength - 数据长度
 * @returns {Object} 优化配置
 */
export function getLargeDataOptimization(dataLength) {
  const isLargeData = dataLength > SAMPLING_CONFIG.LARGE_DATA_THRESHOLD;

  return {
    isLargeData,
    animation: !isLargeData,
    sampling: isLargeData ? 'lttb' : 'none',
    progressive: isLargeData ? 200 : 0,
    progressiveThreshold: SAMPLING_CONFIG.LARGE_DATA_THRESHOLD,
  };
}

/**
 * 获取大数据量图表配置
 * 根据数据量自动调整渲染策略
 * 
 * @param {number} dataLength - 数据长度
 * @returns {Object} ECharts优化配置
 */
export function getLargeDataChartConfig(dataLength) {
  const isLargeData = dataLength > SAMPLING_CONFIG.PROGRESSIVE_THRESHOLD;
  
  return {
    // 动画配置：小数据量启用动画，大数据量禁用
    animation: dataLength < 1000,
    animationDuration: dataLength < 1000 ? 750 : 0,
    animationEasing: 'cubicOut',
    
    // 渐进渲染配置
    progressive: isLargeData ? SAMPLING_CONFIG.PROGRESSIVE_BATCH_SIZE : 0,
    progressiveThreshold: SAMPLING_CONFIG.PROGRESSIVE_THRESHOLD,
    progressiveChunkMode: isLargeData ? 'sequential' : 'auto',
    
    // 大数据模式
    large: isLargeData,
    largeThreshold: SAMPLING_CONFIG.PROGRESSIVE_THRESHOLD,
    
    // 性能优化
    hoverLayerThreshold: 3000,
    useUTC: false,
    
    // 渲染优化
    renderMode: isLargeData ? 'incremental' : 'auto',
    
    // 提示框优化
    tooltip: {
      confine: true,
      renderMode: 'html',
      appendToBody: true,
    },
    
    // 网格优化
    grid: {
      containLabel: true,
    },
  };
}

/**
 * 图表渲染性能监控
 * 监控图表渲染耗时和性能指标
 * 
 * @param {Object} chartInstance - ECharts实例
 * @param {Function} callback - 渲染完成回调
 * @returns {Object} 性能监控对象
 */
export function measureChartPerformance(chartInstance, callback) {
  if (!chartInstance) {
    console.warn('图表实例不存在，无法监控性能');
    return null;
  }

  const startTime = performance.now();
  let renderCount = 0;
  
  // 监听渲染完成事件
  const handleRendered = () => {
    renderCount++;
    const endTime = performance.now();
    const renderTime = endTime - startTime;
    
    const metrics = {
      renderTime: renderTime.toFixed(2),
      renderCount,
      dataLength: chartInstance.getOption()?.series?.[0]?.data?.length || 0,
      memory: performance.memory ? {
        usedJSHeapSize: (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2),
        totalJSHeapSize: (performance.memory.totalJSHeapSize / 1024 / 1024).toFixed(2),
      } : null,
    };
    
    console.log(`[Chart Performance] Render time: ${metrics.renderTime}ms, Data points: ${metrics.dataLength}`);
    
    if (callback && typeof callback === 'function') {
      callback(metrics);
    }
  };
  
  // 绑定事件
  chartInstance.on('rendered', handleRendered);
  
  // 返回监控对象
  return {
    startTime,
    renderCount,
    
    /**
     * 停止监控
     */
    stop() {
      chartInstance.off('rendered', handleRendered);
    },
    
    /**
     * 获取当前性能指标
     */
    getMetrics() {
      const endTime = performance.now();
      return {
        elapsedTime: (endTime - startTime).toFixed(2),
        renderCount,
        averageRenderTime: renderCount > 0 ? ((endTime - startTime) / renderCount).toFixed(2) : 0,
      };
    }
  };
}

/**
 * FPS监控类
 * 实时监控页面渲染帧率
 */
export class FPSMonitor {
  constructor() {
    this.fps = 0;
    this.frames = 0;
    this.lastTime = performance.now();
    this.frameId = null;
    this.isRunning = false;
    this.listeners = [];
    this.history = [];
    this.maxHistoryLength = 60;
  }
  
  /**
   * 开始监控
   */
  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.lastTime = performance.now();
    this.frames = 0;
    
    this.tick();
  }
  
  /**
   * 停止监控
   */
  stop() {
    this.isRunning = false;
    if (this.frameId) {
      cancelAnimationFrame(this.frameId);
      this.frameId = null;
    }
  }
  
  /**
   * 帧更新
   */
  tick() {
    if (!this.isRunning) return;
    
    this.frames++;
    const currentTime = performance.now();
    const elapsed = currentTime - this.lastTime;
    
    // 每秒更新一次FPS
    if (elapsed >= 1000) {
      this.fps = Math.round((this.frames * 1000) / elapsed);
      this.frames = 0;
      this.lastTime = currentTime;
      
      // 记录历史
      this.history.push(this.fps);
      if (this.history.length > this.maxHistoryLength) {
        this.history.shift();
      }
      
      // 通知监听器
      this.notifyListeners();
    }
    
    this.frameId = requestAnimationFrame(() => this.tick());
  }
  
  /**
   * 添加监听器
   * @param {Function} listener - 监听函数
   */
  addListener(listener) {
    if (typeof listener === 'function') {
      this.listeners.push(listener);
    }
  }
  
  /**
   * 移除监听器
   * @param {Function} listener - 监听函数
   */
  removeListener(listener) {
    const index = this.listeners.indexOf(listener);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }
  
  /**
   * 通知所有监听器
   */
  notifyListeners() {
    this.listeners.forEach(listener => {
      try {
        listener(this.fps, this.history);
      } catch (error) {
        console.error('FPS监听器执行错误:', error);
      }
    });
  }
  
  /**
   * 获取平均FPS
   * @returns {number} 平均FPS
   */
  getAverageFPS() {
    if (this.history.length === 0) return 0;
    const sum = this.history.reduce((a, b) => a + b, 0);
    return Math.round(sum / this.history.length);
  }
  
  /**
   * 获取最低FPS
   * @returns {number} 最低FPS
   */
  getMinFPS() {
    if (this.history.length === 0) return 0;
    return Math.min(...this.history);
  }
  
  /**
   * 获取性能评级
   * @returns {string} 性能评级（excellent/good/acceptable/poor）
   */
  getPerformanceRating() {
    const avgFPS = this.getAverageFPS();
    
    if (avgFPS >= 55) return 'excellent';
    if (avgFPS >= 45) return 'good';
    if (avgFPS >= 30) return 'acceptable';
    return 'poor';
  }
  
  /**
   * 重置监控数据
   */
  reset() {
    this.fps = 0;
    this.frames = 0;
    this.lastTime = performance.now();
    this.history = [];
  }
}

/**
 * 图表性能优化建议生成器
 * 根据性能指标生成优化建议
 * 
 * @param {Object} metrics - 性能指标
 * @returns {Array<string>} 优化建议列表
 */
export function generateOptimizationSuggestions(metrics) {
  const suggestions = [];
  
  if (!metrics) return suggestions;
  
  // 渲染时间建议
  if (metrics.renderTime > 1000) {
    suggestions.push({
      type: 'critical',
      message: '渲染时间过长（>1秒），建议启用数据采样或渐进渲染',
      actions: ['使用smartSampling函数采样数据', '启用large模式配置'],
    });
  } else if (metrics.renderTime > 500) {
    suggestions.push({
      type: 'warning',
      message: '渲染时间较长（>500ms），可考虑优化',
      actions: ['减少数据点数量', '禁用动画效果'],
    });
  }
  
  // 数据量建议
  if (metrics.dataLength > 50000) {
    suggestions.push({
      type: 'critical',
      message: '数据量过大（>50000点），强烈建议采样',
      actions: ['使用adaptiveSampling自动采样', '考虑分页或虚拟滚动'],
    });
  } else if (metrics.dataLength > 10000) {
    suggestions.push({
      type: 'warning',
      message: '数据量较大（>10000点），建议优化',
      actions: ['启用渐进渲染', '使用large模式'],
    });
  }
  
  // 内存建议
  if (metrics.memory && metrics.memory.usedJSHeapSize > 100) {
    suggestions.push({
      type: 'warning',
      message: '内存使用较高（>100MB），注意内存泄漏',
      actions: ['检查是否有未释放的图表实例', '及时销毁不用的图表'],
    });
  }
  
  return suggestions;
}

/**
 * 批量数据处理工具
 * 用于分批处理大数据，避免阻塞主线程
 */
export class BatchDataProcessor {
  /**
   * @param {number} batchSize - 每批处理的数据量
   * @param {number} delay - 批次间延迟（毫秒）
   */
  constructor(batchSize = 1000, delay = 16) {
    this.batchSize = batchSize;
    this.delay = delay;
  }
  
  /**
   * 分批处理数据
   * @param {Array} data - 原始数据
   * @param {Function} processor - 处理函数
   * @param {Function} onProgress - 进度回调
   * @returns {Promise<Array>} 处理后的数据
   */
  async process(data, processor, onProgress) {
    const result = [];
    const total = data.length;
    
    for (let i = 0; i < total; i += this.batchSize) {
      const batch = data.slice(i, i + this.batchSize);
      const processed = processor(batch, i);
      result.push(...processed);
      
      // 报告进度
      if (onProgress && typeof onProgress === 'function') {
        onProgress(Math.min(i + this.batchSize, total), total);
      }
      
      // 让出主线程
      if (i + this.batchSize < total) {
        await this.sleep(this.delay);
      }
    }
    
    return result;
  }
  
  /**
   * 延迟函数
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * 创建图表基础配置
 * 
 * @param {Object} options - 配置选项
 * @returns {Object} 基础配置
 */
export function createBaseChartConfig(options = {}) {
  const {
    title = '',
    showZoom = true,
    showToolbox = true,
    largeData = false,
  } = options;

  return {
    title: {
      text: title,
      left: 'center',
      top: 10,
    },
    tooltip: createTooltipConfig(),
    grid: {
      left: '3%',
      right: '4%',
      bottom: largeData ? '15%' : '10%',
      top: '15%',
      containLabel: true,
    },
    dataZoom: showZoom ? createZoomConfig({ slider: largeData }) : [],
    toolbox: showToolbox ? createToolboxConfig() : {},
  };
}

/**
 * 添加数据点标注
 * 
 * @param {Object} chartInstance - ECharts 实例
 * @param {number} seriesIndex - 系列索引
 * @param {Object} markPoint - 标注点配置
 */
export function addMarkPoint(chartInstance, seriesIndex, markPoint) {
  if (!chartInstance) return;

  const option = chartInstance.getOption();
  if (option.series && option.series[seriesIndex]) {
    option.series[seriesIndex].markPoint = markPoint;
    chartInstance.setOption(option);
  }
}

/**
 * 添加标注线
 * 
 * @param {Object} chartInstance - ECharts 实例
 * @param {number} seriesIndex - 系列索引
 * @param {Object} markLine - 标注线配置
 */
export function addMarkLine(chartInstance, seriesIndex, markLine) {
  if (!chartInstance) return;

  const option = chartInstance.getOption();
  if (option.series && option.series[seriesIndex]) {
    option.series[seriesIndex].markLine = markLine;
    chartInstance.setOption(option);
  }
}

/**
 * 清除所有标注
 * 
 * @param {Object} chartInstance - ECharts 实例
 * @param {number} seriesIndex - 系列索引
 */
export function clearMarks(chartInstance, seriesIndex) {
  if (!chartInstance) return;

  const option = chartInstance.getOption();
  if (option.series && option.series[seriesIndex]) {
    option.series[seriesIndex].markPoint = {};
    option.series[seriesIndex].markLine = {};
    chartInstance.setOption(option);
  }
}

/**
 * 导出数据为CSV文件
 * 
 * @param {Object} data - 要导出的数据
 * @param {Array} data.headers - CSV表头数组
 * @param {Array<Array>} data.rows - 数据行数组
 * @param {string} fileName - 文件名（不含扩展名）
 * @returns {Promise<void>}
 */
export async function exportDataAsCSV(data, fileName = 'data') {
  const { headers = [], rows = [] } = data;

  if (!headers.length || !rows.length) {
    throw new Error('数据为空，无法导出');
  }

  try {
    // 构建CSV内容
    const csvRows = [];
    
    // 添加表头
    csvRows.push(headers.join(','));
    
    // 添加数据行
    rows.forEach(row => {
      const values = row.map(value => {
        // 处理包含逗号或引号的值
        if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      });
      csvRows.push(values.join(','));
    });

    // 添加UTF-8 BOM以确保Excel正确识别中文
    const BOM = '\uFEFF';
    const csvContent = BOM + csvRows.join('\n');
    
    // 创建Blob
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
    const blobUrl = URL.createObjectURL(blob);

    // 创建下载链接
    const link = document.createElement('a');
    link.download = `${fileName}.csv`;
    link.href = blobUrl;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // 释放Blob URL
    URL.revokeObjectURL(blobUrl);

    return true;
  } catch (error) {
    console.error('导出CSV失败:', error);
    throw error;
  }
}

/**
 * 导出信号平滑数据为CSV
 * 
 * @param {Array<number>} rawData - 原始数据数组
 * @param {Array<number>} smoothedData - 平滑后数据数组
 * @param {string} fileName - 文件名
 * @returns {Promise<void>}
 */
export async function exportSmoothDataAsCSV(rawData, smoothedData, fileName = '信号平滑数据') {
  const headers = ['采样点', '原始数据', '平滑数据'];
  const maxLength = Math.max(rawData.length, smoothedData.length);
  
  const rows = [];
  for (let i = 0; i < maxLength; i++) {
    rows.push([
      i,
      rawData[i] !== undefined ? rawData[i].toFixed(6) : '',
      smoothedData[i] !== undefined ? smoothedData[i].toFixed(6) : ''
    ]);
  }

  return exportDataAsCSV({ headers, rows }, fileName);
}

/**
 * 导出磁滞回线数据为CSV
 * 
 * @param {Array<number>} xData - X轴数据（磁场H）
 * @param {Array<number>} yData - Y轴数据（磁矩M）
 * @param {Object} result - 分析结果（可选）
 * @param {string} fileName - 文件名
 * @returns {Promise<void>}
 */
export async function exportHysteresisDataAsCSV(xData, yData, result = null, fileName = '磁滞回线数据') {
  const headers = ['磁场(H)', '磁矩(M)'];
  
  // 如果有分析结果，添加额外列
  if (result && result.x_corrected && result.y_corrected) {
    headers.push('校正后磁场(H)', '校正后磁矩(M)');
  }

  const rows = [];
  const maxLength = xData.length;
  
  for (let i = 0; i < maxLength; i++) {
    const row = [
      xData[i] !== undefined ? xData[i].toFixed(6) : '',
      yData[i] !== undefined ? yData[i].toFixed(6) : ''
    ];
    
    if (result && result.x_corrected && result.y_corrected) {
      row.push(
        result.x_corrected[i] !== undefined ? result.x_corrected[i].toFixed(6) : '',
        result.y_corrected[i] !== undefined ? result.y_corrected[i].toFixed(6) : ''
      );
    }
    
    rows.push(row);
  }

  return exportDataAsCSV({ headers, rows }, fileName);
}
