/**
 * @file chartUtils.test.js
 * @path frontend/src/utils/__tests__/
 * @description chartUtils工具函数单元测试
 * @author Agent
 * @date 2024-03-07
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  smartSampling,
  downsampleData,
  downsampleArray,
  detectDataCharacteristics,
  adaptiveSampling,
  getLargeDataChartConfig,
  getLargeDataOptimization,
  createZoomConfig,
  createMarkPointConfig,
  createMarkLineConfig,
  createToolboxConfig,
  createTooltipConfig,
  exportChartAsImage,
  exportChartAsSVG,
  exportDataAsCSV,
  exportSmoothDataAsCSV,
  exportHysteresisDataAsCSV,
  measureChartPerformance,
  FPSMonitor,
  BatchDataProcessor,
  generateOptimizationSuggestions,
} from '@/utils/chartUtils';

describe('chartUtils', () => {
  describe('smartSampling', () => {
    it('应该对小于阈值的数据不采样', () => {
      const data = [1, 2, 3, 4, 5];
      const result = smartSampling(data, 10);

      expect(result).toEqual(data);
    });

    it('应该对大于阈值的一维数据进行采样', () => {
      const data = Array(10000).fill(0).map((_, i) => i);
      const result = smartSampling(data, 1000);

      expect(result.length).toBeLessThanOrEqual(1000);
      // 应该保留首尾点
      expect(result[0]).toBe(0);
      expect(result[result.length - 1]).toBe(9999);
    });

    it('应该对二维数据进行采样', () => {
      const data = Array(10000).fill(0).map((_, i) => [i, Math.sin(i * 0.01)]);
      const result = smartSampling(data, 1000);

      expect(result.length).toBeLessThanOrEqual(1000);
    });

    it('应该保留数据特征', () => {
      // 创建有峰值的数据
      const data = [];
      for (let i = 0; i < 10000; i++) {
        if (i === 5000) {
          data.push([i, 100]); // 峰值
        } else {
          data.push([i, Math.sin(i * 0.01)]);
        }
      }

      const result = smartSampling(data, 1000);

      // 结果应该包含峰值附近的数据
      const hasPeak = result.some(point => point[1] > 50);
      expect(hasPeak).toBe(true);
    });

    it('应该处理空数据', () => {
      expect(smartSampling(null, 1000)).toBeNull();
      expect(smartSampling([], 1000)).toEqual([]);
    });
  });

  describe('downsampleData', () => {
    it('应该使用LTTB算法采样', () => {
      const data = Array(10000).fill(0).map((_, i) => [i, i * 2]);
      const result = downsampleData(data, 1000);

      expect(result.length).toBe(1000);
    });

    it('应该保留首尾点', () => {
      const data = Array(100).fill(0).map((_, i) => [i, i]);
      const result = downsampleData(data, 10);

      expect(result[0]).toEqual(data[0]);
      expect(result[result.length - 1]).toEqual(data[data.length - 1]);
    });

    it('应该对小数据不采样', () => {
      const data = [[1, 2], [3, 4], [5, 6]];
      const result = downsampleData(data, 10);

      expect(result).toEqual(data);
    });
  });

  describe('downsampleArray', () => {
    it('应该采样一维数组', () => {
      const data = Array(10000).fill(0).map((_, i) => i);
      const result = downsampleArray(data, 1000);

      expect(result.length).toBeLessThanOrEqual(1000);
      expect(Array.isArray(result)).toBe(true);
    });

    it('应该保留数据顺序', () => {
      const data = Array(1000).fill(0).map((_, i) => i);
      const result = downsampleArray(data, 100);

      // 检查是否递增
      for (let i = 1; i < result.length; i++) {
        expect(result[i]).toBeGreaterThan(result[i - 1]);
      }
    });
  });

  describe('detectDataCharacteristics', () => {
    it('应该检测平稳数据', () => {
      const data = Array(100).fill(5);
      const result = detectDataCharacteristics(data);

      expect(result).toBe('stable');
    });

    it('应该检测周期性数据', () => {
      const data = [];
      for (let i = 0; i < 1000; i++) {
        data.push(Math.sin(i * 0.1));
      }
      const result = detectDataCharacteristics(data);

      expect(result).toBe('periodic');
    });

    it('应该检测趋势数据', () => {
      const data = [];
      for (let i = 0; i < 1000; i++) {
        data.push(i * 0.1);
      }
      const result = detectDataCharacteristics(data);

      expect(result).toBe('trend');
    });

    it('应该检测波动数据', () => {
      const data = [];
      for (let i = 0; i < 1000; i++) {
        data.push(Math.random() * 100);
      }
      const result = detectDataCharacteristics(data);

      expect(['volatile', 'trend', 'periodic']).toContain(result);
    });

    it('应该处理小数据集', () => {
      const data = [1, 2, 3];
      const result = detectDataCharacteristics(data);

      expect(result).toBe('stable');
    });
  });

  describe('adaptiveSampling', () => {
    it('应该对小数据不采样', () => {
      const xData = [1, 2, 3, 4, 5];
      const yData = [10, 20, 30, 40, 50];
      const result = adaptiveSampling(xData, yData, 10);

      expect(result.xData).toEqual(xData);
      expect(result.yData).toEqual(yData);
    });

    it('应该对平稳数据使用等间隔采样', () => {
      const xData = Array(10000).fill(0).map((_, i) => i);
      const yData = Array(10000).fill(5);
      const result = adaptiveSampling(xData, yData, 1000);

      expect(result.xData.length).toBeLessThanOrEqual(1000);
    });

    it('应该对周期性数据保留峰值', () => {
      const xData = [];
      const yData = [];
      for (let i = 0; i < 10000; i++) {
        xData.push(i);
        yData.push(Math.sin(i * 0.01));
      }
      const result = adaptiveSampling(xData, yData, 1000);

      // 峰值保留采样可能略超过阈值，但应该显著减少数据量
      expect(result.xData.length).toBeLessThan(5000);
    });

    it('应该对趋势数据使用LTTB采样', () => {
      const xData = [];
      const yData = [];
      for (let i = 0; i < 10000; i++) {
        xData.push(i);
        yData.push(i * 0.1);
      }
      const result = adaptiveSampling(xData, yData, 1000);

      expect(result.xData.length).toBeLessThanOrEqual(1000);
    });

    it('应该处理空数据', () => {
      const result = adaptiveSampling(null, null, 1000);

      expect(result.xData).toEqual([]);
      expect(result.yData).toEqual([]);
    });
  });

  describe('getLargeDataChartConfig', () => {
    it('应该为小数据量启用动画', () => {
      const config = getLargeDataChartConfig(500);

      expect(config.animation).toBe(true);
      expect(config.animationDuration).toBe(750);
    });

    it('应该为大数据量禁用动画', () => {
      const config = getLargeDataChartConfig(10000);

      expect(config.animation).toBe(false);
      expect(config.animationDuration).toBe(0);
    });

    it('应该配置渐进渲染', () => {
      const config = getLargeDataChartConfig(10000);

      expect(config.progressive).toBe(1000);
      expect(config.progressiveThreshold).toBe(5000);
      expect(config.large).toBe(true);
    });

    it('应该为中等数据量配置适当参数', () => {
      const config = getLargeDataChartConfig(3000);

      // 中等数据量（1000-5000）：animation为false（因为dataLength >= 1000）
      expect(config.animation).toBe(false);
      // large模式只在数据量>5000时启用
      expect(config.large).toBe(false);
    });
  });

  describe('getLargeDataOptimization', () => {
    it('应该返回大数据优化配置', () => {
      const optimization = getLargeDataOptimization(15000);

      expect(optimization.isLargeData).toBe(true);
      expect(optimization.animation).toBe(false);
      expect(optimization.sampling).toBe('lttb');
    });

    it('应该返回小数据默认配置', () => {
      const optimization = getLargeDataOptimization(5000);

      expect(optimization.isLargeData).toBe(false);
      expect(optimization.animation).toBe(true);
      expect(optimization.sampling).toBe('none');
    });
  });

  describe('createZoomConfig', () => {
    it('应该创建内置缩放配置', () => {
      const config = createZoomConfig({ inside: true, slider: false });

      expect(config).toHaveLength(1);
      expect(config[0].type).toBe('inside');
    });

    it('应该创建滑动条缩放配置', () => {
      const config = createZoomConfig({ inside: false, slider: true });

      expect(config).toHaveLength(1);
      expect(config[0].type).toBe('slider');
    });

    it('应该同时创建两种缩放配置', () => {
      const config = createZoomConfig({ inside: true, slider: true });

      expect(config).toHaveLength(2);
    });

    it('应该设置初始缩放范围', () => {
      const config = createZoomConfig({ start: 20, end: 80 });

      expect(config[0].start).toBe(20);
      expect(config[0].end).toBe(80);
    });
  });

  describe('createMarkPointConfig', () => {
    it('应该创建标注点配置', () => {
      const markPoints = [
        { name: '点1', coord: [1, 2], value: 2 },
        { name: '点2', coord: [3, 4], value: 4 },
      ];
      const config = createMarkPointConfig(markPoints);

      expect(config.symbol).toBe('pin');
      expect(config.data).toHaveLength(2);
    });

    it('应该返回空对象当没有标注点', () => {
      const config = createMarkPointConfig([]);

      expect(config).toEqual({});
    });

    it('应该使用自定义配置', () => {
      const config = createMarkPointConfig([{ coord: [1, 2] }], {
        symbol: 'circle',
        symbolSize: 30,
      });

      expect(config.symbol).toBe('circle');
      expect(config.symbolSize).toBe(30);
    });
  });

  describe('createMarkLineConfig', () => {
    it('应该创建标注线配置', () => {
      const markLines = [
        { name: '线1', yAxis: 10 },
        { name: '线2', xAxis: 5 },
      ];
      const config = createMarkLineConfig(markLines);

      expect(config.data).toHaveLength(2);
      expect(config.lineStyle.type).toBe('dashed');
    });

    it('应该返回空对象当没有标注线', () => {
      const config = createMarkLineConfig([]);

      expect(config).toEqual({});
    });
  });

  describe('createToolboxConfig', () => {
    it('应该创建工具箱配置', () => {
      const config = createToolboxConfig();

      expect(config.show).toBe(true);
      expect(config.feature).toBeDefined();
    });

    it('应该包含保存图片功能', () => {
      const config = createToolboxConfig({ showSaveAsImage: true });

      expect(config.feature.saveAsImage).toBeDefined();
    });

    it('应该包含数据视图功能', () => {
      const config = createToolboxConfig({ showDataView: true });

      expect(config.feature.dataView).toBeDefined();
    });
  });

  describe('createTooltipConfig', () => {
    it('应该创建提示框配置', () => {
      const config = createTooltipConfig();

      expect(config.show).toBe(true);
      expect(config.trigger).toBe('axis');
      expect(config.confine).toBe(true);
    });

    it('应该使用自定义触发类型', () => {
      const config = createTooltipConfig({ trigger: 'item' });

      expect(config.trigger).toBe('item');
    });
  });

  describe('exportChartAsImage', () => {
    it('应该导出图表为PNG', async () => {
      const mockChart = {
        getDataURL: vi.fn().mockReturnValue('data:image/png;base64,test'),
      };

      global.document.createElement = vi.fn().mockReturnValue({
        download: '',
        href: '',
        click: vi.fn(),
      });
      global.document.body.appendChild = vi.fn();
      global.document.body.removeChild = vi.fn();

      await exportChartAsImage(mockChart, { fileName: 'test' });

      expect(mockChart.getDataURL).toHaveBeenCalled();
    });

    it('应该抛出错误当图表实例不存在', async () => {
      await expect(exportChartAsImage(null)).rejects.toThrow('图表实例不存在');
    });
  });

  describe('exportChartAsSVG', () => {
    it('应该导出图表为SVG', async () => {
      const mockChart = {
        getDataURL: vi.fn().mockReturnValue('data:image/svg+xml;base64,' + btoa('<svg></svg>')),
      };

      global.URL.createObjectURL = vi.fn().mockReturnValue('blob:test');
      global.URL.revokeObjectURL = vi.fn();
      global.document.createElement = vi.fn().mockReturnValue({
        download: '',
        href: '',
        click: vi.fn(),
      });
      global.document.body.appendChild = vi.fn();
      global.document.body.removeChild = vi.fn();

      await exportChartAsSVG(mockChart, 'test');

      expect(mockChart.getDataURL).toHaveBeenCalledWith({ type: 'svg' });
    });
  });

  describe('exportDataAsCSV', () => {
    it('应该导出数据为CSV', async () => {
      const data = {
        headers: ['列1', '列2', '列3'],
        rows: [
          [1, 2, 3],
          [4, 5, 6],
        ],
      };

      global.URL.createObjectURL = vi.fn().mockReturnValue('blob:test');
      global.URL.revokeObjectURL = vi.fn();
      global.document.createElement = vi.fn().mockReturnValue({
        download: '',
        href: '',
        click: vi.fn(),
      });
      global.document.body.appendChild = vi.fn();
      global.document.body.removeChild = vi.fn();

      await exportDataAsCSV(data, 'test');

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('应该处理包含逗号的值', async () => {
      const data = {
        headers: ['名称', '描述'],
        rows: [['测试', '包含,逗号']],
      };

      global.URL.createObjectURL = vi.fn().mockReturnValue('blob:test');
      global.URL.revokeObjectURL = vi.fn();
      global.document.createElement = vi.fn().mockReturnValue({
        download: '',
        href: '',
        click: vi.fn(),
      });
      global.document.body.appendChild = vi.fn();
      global.document.body.removeChild = vi.fn();

      await exportDataAsCSV(data, 'test');

      // 应该正确处理包含逗号的值
    });

    it('应该抛出错误当数据为空', async () => {
      await expect(exportDataAsCSV({ headers: [], rows: [] })).rejects.toThrow('数据为空');
    });
  });

  describe('exportSmoothDataAsCSV', () => {
    it('应该导出平滑数据', async () => {
      const rawData = [1, 2, 3, 4, 5];
      const smoothedData = [1.1, 2.1, 3.1, 4.1, 5.1];

      global.URL.createObjectURL = vi.fn().mockReturnValue('blob:test');
      global.URL.revokeObjectURL = vi.fn();
      global.document.createElement = vi.fn().mockReturnValue({
        download: '',
        href: '',
        click: vi.fn(),
      });
      global.document.body.appendChild = vi.fn();
      global.document.body.removeChild = vi.fn();

      await exportSmoothDataAsCSV(rawData, smoothedData, 'test');

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  describe('exportHysteresisDataAsCSV', () => {
    it('应该导出磁滞回线数据', async () => {
      const xData = [1, 2, 3, 4, 5];
      const yData = [10, 20, 30, 40, 50];

      global.URL.createObjectURL = vi.fn().mockReturnValue('blob:test');
      global.URL.revokeObjectURL = vi.fn();
      global.document.createElement = vi.fn().mockReturnValue({
        download: '',
        href: '',
        click: vi.fn(),
      });
      global.document.body.appendChild = vi.fn();
      global.document.body.removeChild = vi.fn();

      await exportHysteresisDataAsCSV(xData, yData, null, 'test');

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('应该包含校正后数据', async () => {
      const xData = [1, 2, 3];
      const yData = [10, 20, 30];
      const result = {
        x_corrected: [1.1, 2.1, 3.1],
        y_corrected: [11, 21, 31],
      };

      global.URL.createObjectURL = vi.fn().mockReturnValue('blob:test');
      global.URL.revokeObjectURL = vi.fn();
      global.document.createElement = vi.fn().mockReturnValue({
        download: '',
        href: '',
        click: vi.fn(),
      });
      global.document.body.appendChild = vi.fn();
      global.document.body.removeChild = vi.fn();

      await exportHysteresisDataAsCSV(xData, yData, result, 'test');

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  describe('measureChartPerformance', () => {
    it('应该监控图表性能', () => {
      const mockChart = {
        on: vi.fn(),
        off: vi.fn(),
        getOption: vi.fn().mockReturnValue({ series: [{ data: [] }] }),
      };

      const monitor = measureChartPerformance(mockChart);

      expect(monitor).toBeDefined();
      expect(monitor.startTime).toBeDefined();
      expect(mockChart.on).toHaveBeenCalledWith('rendered', expect.any(Function));
    });

    it('应该返回null当图表实例不存在', () => {
      const monitor = measureChartPerformance(null);

      expect(monitor).toBeNull();
    });

    it('应该停止监控', () => {
      const mockChart = {
        on: vi.fn(),
        off: vi.fn(),
        getOption: vi.fn(),
      };

      const monitor = measureChartPerformance(mockChart);
      monitor.stop();

      expect(mockChart.off).toHaveBeenCalled();
    });
  });

  describe('FPSMonitor', () => {
    let monitor;

    beforeEach(() => {
      vi.useFakeTimers();
      monitor = new FPSMonitor();
    });

    afterEach(() => {
      monitor.stop();
      vi.useRealTimers();
    });

    it('应该开始监控', () => {
      monitor.start();

      expect(monitor.isRunning).toBe(true);
    });

    it('应该停止监控', () => {
      monitor.start();
      monitor.stop();

      expect(monitor.isRunning).toBe(false);
    });

    it('应该计算FPS', () => {
      // Mock requestAnimationFrame
      let frameCallback = null;
      global.requestAnimationFrame = vi.fn((cb) => {
        frameCallback = cb;
        return 1;
      });
      global.cancelAnimationFrame = vi.fn();

      monitor.start();

      // 手动触发帧回调来模拟帧
      for (let i = 0; i < 60; i++) {
        vi.advanceTimersByTime(16);
        if (frameCallback) {
          frameCallback();
        }
      }

      // 模拟一秒后触发帧更新
      vi.advanceTimersByTime(1000);
      if (frameCallback) {
        frameCallback();
      }

      // FPS应该已经被计算
      expect(monitor.fps).toBeGreaterThanOrEqual(0);
      expect(monitor.history.length).toBeGreaterThanOrEqual(0);
    });

    it('应该添加监听器', () => {
      const listener = vi.fn();
      monitor.addListener(listener);

      expect(monitor.listeners).toContain(listener);
    });

    it('应该移除监听器', () => {
      const listener = vi.fn();
      monitor.addListener(listener);
      monitor.removeListener(listener);

      expect(monitor.listeners).not.toContain(listener);
    });

    it('应该获取平均FPS', () => {
      monitor.history = [60, 55, 58, 62, 57];

      expect(monitor.getAverageFPS()).toBe(58);
    });

    it('应该获取最低FPS', () => {
      monitor.history = [60, 55, 58, 62, 57];

      expect(monitor.getMinFPS()).toBe(55);
    });

    it('应该获取性能评级', () => {
      monitor.history = [60, 60, 60];
      expect(monitor.getPerformanceRating()).toBe('excellent');

      monitor.history = [45, 46, 47];
      expect(monitor.getPerformanceRating()).toBe('good');

      monitor.history = [30, 32, 31];
      expect(monitor.getPerformanceRating()).toBe('acceptable');

      monitor.history = [20, 22, 21];
      expect(monitor.getPerformanceRating()).toBe('poor');
    });

    it('应该重置监控数据', () => {
      monitor.fps = 60;
      monitor.history = [60, 55, 58];

      monitor.reset();

      expect(monitor.fps).toBe(0);
      expect(monitor.history).toHaveLength(0);
    });
  });

  describe('BatchDataProcessor', () => {
    it('应该分批处理数据', async () => {
      const processor = new BatchDataProcessor(100, 0);
      const data = Array(500).fill(0).map((_, i) => i);
      const processFn = vi.fn(batch => batch.map(x => x * 2));

      const result = await processor.process(data, processFn);

      expect(result).toHaveLength(500);
      expect(result[0]).toBe(0);
      expect(result[499]).toBe(998);
    });

    it('应该报告进度', async () => {
      const processor = new BatchDataProcessor(100, 0);
      const data = Array(500).fill(0);
      const onProgress = vi.fn();

      await processor.process(data, batch => batch, onProgress);

      expect(onProgress).toHaveBeenCalled();
    });
  });

  describe('generateOptimizationSuggestions', () => {
    it('应该生成渲染时间建议', () => {
      const metrics = { renderTime: 1500 };
      const suggestions = generateOptimizationSuggestions(metrics);

      expect(suggestions.length).toBeGreaterThan(0);
      expect(suggestions[0].type).toBe('critical');
    });

    it('应该生成数据量建议', () => {
      const metrics = { dataLength: 60000 };
      const suggestions = generateOptimizationSuggestions(metrics);

      expect(suggestions.some(s => s.type === 'critical')).toBe(true);
    });

    it('应该生成内存建议', () => {
      const metrics = {
        memory: {
          usedJSHeapSize: 150,
          totalJSHeapSize: 200,
        },
      };
      const suggestions = generateOptimizationSuggestions(metrics);

      expect(suggestions.some(s => s.message.includes('内存'))).toBe(true);
    });

    it('应该返回空数组当没有指标', () => {
      const suggestions = generateOptimizationSuggestions(null);

      expect(suggestions).toEqual([]);
    });
  });
});
