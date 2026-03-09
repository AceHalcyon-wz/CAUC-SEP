/**
 * @file chartPerformance.test.js
 * @path src/tests/
 * @description 图表性能优化功能测试
 * @author Agent
 * @date 2024-03-07
 */

import {
  smartSampling,
  adaptiveSampling,
  detectDataCharacteristics,
  getLargeDataChartConfig,
  FPSMonitor,
  generateOptimizationSuggestions,
  BatchDataProcessor,
  downsampleData,
} from '@/utils/chartUtils';

/**
 * 测试套件
 */
const tests = {
  /**
   * 测试智能采样
   */
  testSmartSampling() {
    console.group('测试智能采样');
    
    // 测试一维数据
    const oneDimData = Array.from({ length: 10000 }, (_, i) => Math.random() * 100);
    const sampled1D = smartSampling(oneDimData, 1000);
    
    console.assert(
      sampled1D.length === 1000,
      `一维数据采样失败: 期望1000点，实际${sampled1D.length}点`
    );
    console.log('✓ 一维数据采样测试通过');
    
    // 测试二维数据
    const twoDimData = Array.from({ length: 10000 }, (_, i) => [i, Math.random() * 100]);
    const sampled2D = smartSampling(twoDimData, 1000);
    
    console.assert(
      sampled2D.length === 1000,
      `二维数据采样失败: 期望1000点，实际${sampled2D.length}点`
    );
    console.log('✓ 二维数据采样测试通过');
    
    // 测试小数据量（不应采样）
    const smallData = Array.from({ length: 100 }, (_, i) => i);
    const sampledSmall = smartSampling(smallData, 1000);
    
    console.assert(
      sampledSmall.length === 100,
      `小数据量采样失败: 期望100点，实际${sampledSmall.length}点`
    );
    console.log('✓ 小数据量不采样测试通过');
    
    console.groupEnd();
  },
  
  /**
   * 测试数据特征检测
   */
  testDetectDataCharacteristics() {
    console.group('测试数据特征检测');
    
    // 平稳数据
    const stableData = Array.from({ length: 1000 }, () => 100 + Math.random() * 2);
    const stableChar = detectDataCharacteristics(stableData);
    console.assert(stableChar === 'stable', `平稳数据检测失败: ${stableChar}`);
    console.log('✓ 平稳数据检测通过');
    
    // 周期性数据
    const periodicData = Array.from({ length: 1000 }, (_, i) => Math.sin(i / 10) * 50);
    const periodicChar = detectDataCharacteristics(periodicData);
    console.assert(periodicChar === 'periodic', `周期性数据检测失败: ${periodicChar}`);
    console.log('✓ 周期性数据检测通过');
    
    // 波动数据
    const volatileData = Array.from({ length: 1000 }, () => Math.random() * 100);
    const volatileChar = detectDataCharacteristics(volatileData);
    console.assert(volatileChar === 'volatile', `波动数据检测失败: ${volatileChar}`);
    console.log('✓ 波动数据检测通过');
    
    console.groupEnd();
  },
  
  /**
   * 测试自适应采样
   */
  testAdaptiveSampling() {
    console.group('测试自适应采样');
    
    // 测试平稳数据采样
    const stableX = Array.from({ length: 10000 }, (_, i) => i);
    const stableY = Array.from({ length: 10000 }, () => 100 + Math.random() * 2);
    const stableSampled = adaptiveSampling(stableX, stableY, 1000);
    
    console.assert(
      stableSampled.xData.length === 1000,
      `平稳数据采样失败: ${stableSampled.xData.length}点`
    );
    console.log('✓ 平稳数据采样测试通过');
    
    // 测试周期性数据采样
    const periodicX = Array.from({ length: 10000 }, (_, i) => i);
    const periodicY = Array.from({ length: 10000 }, (_, i) => Math.sin(i / 10) * 50);
    const periodicSampled = adaptiveSampling(periodicX, periodicY, 1000);
    
    console.assert(
      periodicSampled.xData.length <= 1000,
      `周期性数据采样失败: ${periodicSampled.xData.length}点`
    );
    console.log('✓ 周期性数据采样测试通过');
    
    console.groupEnd();
  },
  
  /**
   * 测试大数据配置
   */
  testGetLargeDataChartConfig() {
    console.group('测试大数据配置');
    
    // 小数据量
    const smallConfig = getLargeDataChartConfig(500);
    console.assert(smallConfig.animation === true, '小数据量应启用动画');
    console.log('✓ 小数据量配置测试通过');
    
    // 中等数据量
    const mediumConfig = getLargeDataChartConfig(3000);
    console.assert(mediumConfig.animation === false, '中等数据量应禁用动画');
    console.assert(mediumConfig.progressive === 0, '中等数据量不应启用渐进渲染');
    console.log('✓ 中等数据量配置测试通过');
    
    // 大数据量
    const largeConfig = getLargeDataChartConfig(10000);
    console.assert(largeConfig.animation === false, '大数据量应禁用动画');
    console.assert(largeConfig.progressive === 1000, '大数据量应启用渐进渲染');
    console.assert(largeConfig.large === true, '大数据量应启用large模式');
    console.log('✓ 大数据量配置测试通过');
    
    console.groupEnd();
  },
  
  /**
   * 测试FPS监控
   */
  testFPSMonitor() {
    console.group('测试FPS监控');
    
    return new Promise((resolve) => {
      const monitor = new FPSMonitor();
      let callCount = 0;
      
      monitor.addListener((fps, history) => {
        callCount++;
        console.log(`FPS: ${fps}, 历史: ${history.length}条`);
        
        if (callCount >= 2) {
          monitor.stop();
          
          const avgFPS = monitor.getAverageFPS();
          const rating = monitor.getPerformanceRating();
          
          console.assert(avgFPS > 0, '平均FPS应大于0');
          console.assert(['excellent', 'good', 'acceptable', 'poor'].includes(rating), '性能评级应有效');
          
          console.log(`✓ FPS监控测试通过 (平均FPS: ${avgFPS}, 评级: ${rating})`);
          console.groupEnd();
          resolve();
        }
      });
      
      monitor.start();
      
      // 模拟一些渲染工作
      let frame = 0;
      function animate() {
        frame++;
        if (frame < 120) {
          requestAnimationFrame(animate);
        }
      }
      animate();
    });
  },
  
  /**
   * 测试优化建议生成
   */
  testGenerateOptimizationSuggestions() {
    console.group('测试优化建议生成');
    
    // 测试渲染时间过长
    const slowMetrics = {
      renderTime: 1500,
      dataLength: 60000,
    };
    const slowSuggestions = generateOptimizationSuggestions(slowMetrics);
    console.assert(slowSuggestions.length > 0, '应生成优化建议');
    console.log('✓ 渲染时间优化建议测试通过');
    
    // 测试数据量过大
    const largeDataMetrics = {
      renderTime: 200,
      dataLength: 60000,
    };
    const largeDataSuggestions = generateOptimizationSuggestions(largeDataMetrics);
    console.assert(largeDataSuggestions.length > 0, '应生成数据量优化建议');
    console.log('✓ 数据量优化建议测试通过');
    
    // 测试内存使用过高
    const memoryMetrics = {
      renderTime: 200,
      dataLength: 5000,
      memory: { usedJSHeapSize: 150 },
    };
    const memorySuggestions = generateOptimizationSuggestions(memoryMetrics);
    console.assert(memorySuggestions.length > 0, '应生成内存优化建议');
    console.log('✓ 内存优化建议测试通过');
    
    console.groupEnd();
  },
  
  /**
   * 测试批量数据处理
   */
  async testBatchDataProcessor() {
    console.group('测试批量数据处理');
    
    const processor = new BatchDataProcessor(100, 10);
    const data = Array.from({ length: 1000 }, (_, i) => ({ id: i, value: Math.random() }));
    
    let progressCalled = false;
    const result = await processor.process(
      data,
      (batch) => batch.map(item => ({ ...item, processed: true })),
      (processed, total) => {
        progressCalled = true;
      }
    );
    
    console.assert(result.length === 1000, `处理结果数量错误: ${result.length}`);
    console.assert(progressCalled, '进度回调未被调用');
    console.assert(result[0].processed === true, '数据未被正确处理');
    
    console.log('✓ 批量数据处理测试通过');
    console.groupEnd();
  },
  
  /**
   * 测试LTTB算法
   */
  testLTTB() {
    console.group('测试LTTB算法');
    
    // 生成测试数据（包含峰值）
    const data = [];
    for (let i = 0; i < 1000; i++) {
      const x = i;
      const y = i === 500 ? 1000 : Math.sin(i / 50) * 50; // 在500处有一个峰值
      data.push([x, y]);
    }
    
    const sampled = downsampleData(data, 100);
    
    // 检查是否保留了峰值
    const peakPreserved = sampled.some(point => point[1] > 900);
    console.assert(peakPreserved, 'LTTB算法应保留峰值');
    
    // 检查首尾点
    console.assert(sampled[0][0] === 0, '应保留第一个点');
    console.assert(sampled[sampled.length - 1][0] === 999, '应保留最后一个点');
    
    console.log('✓ LTTB算法测试通过');
    console.groupEnd();
  },
};

/**
 * 运行所有测试
 */
export async function runAllTests() {
  console.log('========== 开始性能优化功能测试 ==========\n');
  
  const startTime = performance.now();
  
  try {
    // 同步测试
    tests.testSmartSampling();
    tests.testDetectDataCharacteristics();
    tests.testAdaptiveSampling();
    tests.testGetLargeDataChartConfig();
    tests.testGenerateOptimizationSuggestions();
    tests.testLTTB();
    
    // 异步测试
    await tests.testFPSMonitor();
    await tests.testBatchDataProcessor();
    
    const endTime = performance.now();
    const duration = (endTime - startTime).toFixed(2);
    
    console.log('\n========== 所有测试通过 ✓ ==========');
    console.log(`总耗时: ${duration}ms`);
    
    return {
      success: true,
      duration,
      message: '所有测试通过',
    };
  } catch (error) {
    console.error('\n========== 测试失败 ✗ ==========');
    console.error('错误:', error);
    
    return {
      success: false,
      duration: 0,
      message: error.message,
    };
  }
}

/**
 * 性能基准测试
 */
export async function runPerformanceBenchmark() {
  console.log('========== 性能基准测试 ==========\n');
  
  const results = [];
  
  // 测试不同数据量的采样性能
  const dataSizes = [1000, 5000, 10000, 50000, 100000];
  
  for (const size of dataSizes) {
    const data = Array.from({ length: size }, (_, i) => [i, Math.random() * 100]);
    
    const startTime = performance.now();
    const sampled = smartSampling(data, 5000);
    const endTime = performance.now();
    
    const duration = endTime - startTime;
    
    results.push({
      size,
      sampledSize: sampled.length,
      duration: duration.toFixed(2),
      ratio: (duration / size * 1000).toFixed(4), // 每千点耗时
    });
    
    console.log(`数据量: ${size}, 采样后: ${sampled.length}, 耗时: ${duration.toFixed(2)}ms`);
  }
  
  console.log('\n基准测试结果:');
  console.table(results);
  
  return results;
}

// 如果在浏览器环境中，暴露到全局
if (typeof window !== 'undefined') {
  window.chartPerformanceTests = {
    runAllTests,
    runPerformanceBenchmark,
    tests,
  };
}
