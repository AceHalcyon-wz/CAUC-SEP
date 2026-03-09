/**
 * @file chartPerformanceExample.js
 * @path docs/examples/
 * @description 图表性能优化使用示例
 * @author Agent
 * @date 2024-03-07
 */

import {
  smartSampling,
  adaptiveSampling,
  detectDataCharacteristics,
  getLargeDataChartConfig,
  measureChartPerformance,
  FPSMonitor,
  generateOptimizationSuggestions,
  BatchDataProcessor,
} from '@/utils/chartUtils';

/**
 * 示例1: 智能数据采样
 */
export function exampleSmartSampling() {
  const largeData = Array.from({ length: 1000000 }, (_, i) => ({
    x: i,
    y: Math.sin(i / 10000) * Math.random() * 100,
  }));

  const sampledData = smartSampling(largeData, 5000);
  
  console.log(`原始数据: ${largeData.length} 点`);
  console.log(`采样后: ${sampledData.length} 点`);
  
  return sampledData;
}

/**
 * 示例2: 自适应采样策略
 */
export function exampleAdaptiveSampling() {
  const stableData = {
    x: Array.from({ length: 50000 }, (_, i) => i),
    y: Array.from({ length: 50000 }, (_, i) => 100 + Math.random() * 2),
  };
  
  const periodicData = {
    x: Array.from({ length: 50000 }, (_, i) => i),
    y: Array.from({ length: 50000 }, (_, i) => Math.sin(i / 100) * 50),
  };
  
  const volatileData = {
    x: Array.from({ length: 50000 }, (_, i) => i),
    y: Array.from({ length: 50000 }, (_, i) => Math.random() * 100),
  };
  
  console.log('平稳数据特征:', detectDataCharacteristics(stableData.y));
  console.log('周期性数据特征:', detectDataCharacteristics(periodicData.y));
  console.log('波动数据特征:', detectDataCharacteristics(volatileData.y));
  
  const sampledStable = adaptiveSampling(stableData.x, stableData.y, 5000);
  const sampledPeriodic = adaptiveSampling(periodicData.x, periodicData.y, 5000);
  const sampledVolatile = adaptiveSampling(volatileData.x, volatileData.y, 5000);
  
  return {
    stable: sampledStable,
    periodic: sampledPeriodic,
    volatile: sampledVolatile,
  };
}

/**
 * 示例3: 大数据量图表配置
 */
export function exampleLargeDataChartConfig() {
  const dataLength = 100000;
  
  const config = getLargeDataChartConfig(dataLength);
  
  const chartOption = {
    ...config,
    xAxis: {
      type: 'category',
      data: Array.from({ length: dataLength }, (_, i) => i),
    },
    yAxis: {
      type: 'value',
    },
    series: [{
      type: 'line',
      data: Array.from({ length: dataLength }, (_, i) => Math.sin(i / 1000) * 100),
      large: true,
      largeThreshold: 5000,
      progressive: 1000,
      progressiveThreshold: 5000,
    }],
  };
  
  return chartOption;
}

/**
 * 示例4: 性能监控
 */
export function examplePerformanceMonitoring(chartInstance) {
  const fpsMonitor = new FPSMonitor();
  
  fpsMonitor.addListener((fps, history) => {
    console.log(`当前FPS: ${fps}`);
    console.log(`平均FPS: ${fpsMonitor.getAverageFPS()}`);
    console.log(`性能评级: ${fpsMonitor.getPerformanceRating()}`);
  });
  
  fpsMonitor.start();
  
  const performanceMonitor = measureChartPerformance(chartInstance, (metrics) => {
    console.log('渲染性能指标:', metrics);
    
    const suggestions = generateOptimizationSuggestions(metrics);
    console.log('优化建议:', suggestions);
  });
  
  return {
    fpsMonitor,
    performanceMonitor,
    
    stop() {
      fpsMonitor.stop();
      performanceMonitor.stop();
    },
  };
}

/**
 * 示例5: 批量数据处理
 */
export async function exampleBatchDataProcessing() {
  const processor = new BatchDataProcessor(1000, 16);
  
  const largeDataset = Array.from({ length: 100000 }, (_, i) => ({
    id: i,
    value: Math.random() * 100,
  }));
  
  const result = await processor.process(
    largeDataset,
    (batch, startIndex) => {
      return batch.map(item => ({
        ...item,
        processed: true,
        timestamp: Date.now(),
      }));
    },
    (processed, total) => {
      console.log(`进度: ${processed}/${total} (${((processed / total) * 100).toFixed(2)}%)`);
    }
  );
  
  console.log(`处理完成，共 ${result.length} 条数据`);
  return result;
}

/**
 * 示例6: 完整的图表优化流程
 */
export function exampleCompleteOptimization(chartInstance, rawData) {
  const characteristics = detectDataCharacteristics(rawData.y);
  console.log('数据特征:', characteristics);
  
  const sampledData = adaptiveSampling(rawData.x, rawData.y, 5000);
  
  const optimizationConfig = getLargeDataChartConfig(sampledData.xData.length);
  
  const option = {
    ...optimizationConfig,
    xAxis: {
      type: 'category',
      data: sampledData.xData,
    },
    yAxis: {
      type: 'value',
    },
    series: [{
      type: 'line',
      data: sampledData.yData,
      smooth: false,
      symbol: 'none',
      sampling: 'lttb',
    }],
  };
  
  chartInstance.setOption(option);
  
  const monitor = examplePerformanceMonitoring(chartInstance);
  
  return {
    sampledData,
    monitor,
  };
}
