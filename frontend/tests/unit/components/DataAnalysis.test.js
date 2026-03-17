/**
 * @file DataAnalysis.test.js
 * @path frontend/tests/unit/components/
 * @description DataAnalysis组件完整单元测试
 * @author Agent
 * @date 2024-03-16
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import DataAnalysis from '@/components/analysis/DataAnalysis.vue';
import { createMockECharts, createMockMotorStore } from '../helpers/test-utils';

// Mock ECharts
const mockChartInstance = createMockECharts();

vi.mock('echarts', () => ({
  default: {
    init: vi.fn(() => mockChartInstance),
  },
  init: vi.fn(() => mockChartInstance),
}));

// Mock motor store
const mockMotorStore = createMockMotorStore({
  alarmMessage: '',
  loading: {
    smooth: false,
    hysteresis: false,
  },
  smoothSignal: vi.fn().mockResolvedValue({ smoothed_data: [1, 2, 3] }),
  analyzeHysteresis: vi.fn().mockResolvedValue({
    Hc: 0.5,
    Mr: 0.3,
    Ms: 1.0,
    x_corrected: [0, 1, 2],
    y_corrected: [0, 0.5, 1],
  }),
});

vi.mock('@/stores/motor', () => ({
  useMotorStore: vi.fn(() => mockMotorStore),
}));

// Mock API
vi.mock('@/api/analysis', () => ({
  multiModelFit: vi.fn().mockResolvedValue({
    results: [
      { model_name: '双曲正切模型', r_squared: 0.98, rmse: 0.02, aic: -100, bic: -95 },
      { model_name: '反正切模型', r_squared: 0.95, rmse: 0.05, aic: -80, bic: -75 },
    ],
    best_model: 'hyperbolic',
  }),
  generateAnalysisReport: vi.fn().mockResolvedValue({
    experiment_id: 'exp_001',
    timestamp: new Date().toISOString(),
    hysteresis_params: { Bs: 1.0, Hc: 0.5, Br: 0.3, Hs: 2.0 },
    fit_results: [],
    quality_metrics: { r_squared: 0.98 },
    recommendations: ['建议1', '建议2'],
  }),
  exportAnalysisReport: vi.fn().mockResolvedValue(new Blob(['test'])),
  getAnalysisHistory: vi.fn(() => []),
  saveAnalysisToHistory: vi.fn(),
  deleteAnalysisHistory: vi.fn(() => true),
  clearAnalysisHistory: vi.fn(() => true),
}));

// Mock chartUtils
vi.mock('@/utils/chartUtils', () => ({
  downsampleArray: vi.fn((arr) => arr),
  downsampleData: vi.fn((arr) => arr),
  createZoomConfig: vi.fn(() => []),
  createMarkPointConfig: vi.fn(() => ({})),
  createMarkLineConfig: vi.fn(() => ({})),
  exportChartAsImage: vi.fn().mockResolvedValue(undefined),
  exportChartAsSVG: vi.fn().mockResolvedValue(undefined),
  createToolboxConfig: vi.fn(() => ({})),
  createTooltipConfig: vi.fn(() => ({})),
  getLargeDataOptimization: vi.fn(() => ({
    isLargeData: false,
    animation: true,
    sampling: 'lttb',
    progressive: 200,
    progressiveThreshold: 3000,
  })),
  exportSmoothDataAsCSV: vi.fn().mockResolvedValue(undefined),
  exportHysteresisDataAsCSV: vi.fn().mockResolvedValue(undefined),
  smartSampling: vi.fn((arr) => arr),
  BatchDataProcessor: vi.fn().mockImplementation(() => ({
    process: vi.fn((data) => Promise.resolve(data)),
  })),
  FPSMonitor: vi.fn().mockImplementation(() => ({
    start: vi.fn(),
    stop: vi.fn(),
    addListener: vi.fn(),
  })),
}));

// Mock ElMessage
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

describe('DataAnalysis', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);

    // 重置mock
    vi.clearAllMocks();

    wrapper = mount(DataAnalysis, {
      global: {
        plugins: [pinia],
        stubs: {
          'el-card': {
            template: '<div class="el-card"><slot name="header" /><slot /></div>',
          },
          'el-tabs': { template: '<div class="el-tabs"><slot /></div>' },
          'el-tab-pane': { template: '<div class="el-tab-pane"><slot /></div>' },
          'el-form': { template: '<form class="el-form"><slot /></form>' },
          'el-form-item': { template: '<div class="el-form-item"><slot /></div>' },
          'el-button': { template: '<button class="el-button"><slot /></button>' },
          'el-input-number': { template: '<input type="number" class="el-input-number" />' },
          'el-select': { template: '<select class="el-select"><slot /></select>' },
          'el-option': { template: '<option class="el-option"><slot /></option>' },
          'el-switch': { template: '<input type="checkbox" class="el-switch" />' },
          'el-checkbox-group': { template: '<div class="el-checkbox-group"><slot /></div>' },
          'el-checkbox': { template: '<input type="checkbox" class="el-checkbox" />' },
          'el-table': { template: '<table class="el-table"><slot /></table>' },
          'el-table-column': { template: '<col class="el-table-column" />' },
          'el-tag': { template: '<span class="el-tag"><slot /></span>' },
          'el-alert': { template: '<div class="el-alert"><slot /></div>' },
          'el-descriptions': { template: '<dl class="el-descriptions"><slot /></dl>' },
          'el-descriptions-item': { template: '<dd class="el-descriptions-item"><slot /></dd>' },
          'el-divider': { template: '<hr class="el-divider" />' },
          'el-empty': { template: '<div class="el-empty"><slot /></div>' },
          'el-dialog': { template: '<div class="el-dialog"><slot /></div>' },
          'el-dropdown': { template: '<div class="el-dropdown"><slot /></div>' },
          'el-dropdown-menu': { template: '<ul class="el-dropdown-menu"><slot /></ul>' },
          'el-dropdown-item': { template: '<li class="el-dropdown-item"><slot /></li>' },
          'el-icon': { template: '<i class="el-icon"><slot /></i>' },
          'el-row': { template: '<div class="el-row"><slot /></div>' },
          'el-col': { template: '<div class="el-col"><slot /></div>' },
          'el-statistic': { template: '<div class="el-statistic"><slot /></div>' },
          'el-radio-group': { template: '<div class="el-radio-group"><slot /></div>' },
          'el-radio-button': { template: '<label class="el-radio-button"><slot /></label>' },
          'el-collapse-transition': { template: '<div class="el-collapse-transition"><slot /></div>' },
          'arrow-down': { template: '<span class="arrow-down"></span>' },
        },
      },
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.clearAllMocks();
  });

  // ==================== 组件渲染测试 ====================

  describe('组件渲染', () => {
    it('应该正确渲染组件', () => {
      expect(wrapper.find('.data-analysis').exists()).toBe(true);
    });

    it('应该显示标题', () => {
      expect(wrapper.text()).toContain('数据分析');
    });

    it('应该包含四个标签页', () => {
      const tabs = wrapper.findAll('.el-tab-pane');
      expect(tabs.length).toBe(4);
    });

    it('应该显示标注面板切换按钮', () => {
      expect(wrapper.text()).toContain('开启标注');
    });

    it('应该显示历史记录按钮', () => {
      expect(wrapper.text()).toContain('历史记录');
    });

    it('应该显示导出数据按钮', () => {
      expect(wrapper.text()).toContain('导出数据');
    });

    it('应该正确初始化默认标签页', () => {
      expect(wrapper.vm.activeTab).toBe('smooth');
    });

    it('应该正确初始化平滑配置', () => {
      expect(wrapper.vm.smoothConfig.method).toBe('savitzky_golay');
      expect(wrapper.vm.smoothConfig.window_length).toBe(11);
      expect(wrapper.vm.smoothConfig.polyorder).toBe(3);
    });

    it('应该正确初始化磁滞回线配置', () => {
      expect(wrapper.vm.hysteresisConfig.subtract_background).toBe(true);
      expect(wrapper.vm.hysteresisConfig.saturation_threshold).toBe(0.9);
    });
  });

  // ==================== 数据加载测试 ====================

  describe('数据加载', () => {
    it('应该生成示例数据', async () => {
      await wrapper.vm.generateDemoData();
      await flushPromises();

      expect(wrapper.vm.rawData.length).toBe(50000);
      expect(wrapper.vm.smoothedData.length).toBe(0);
    });

    it('应该生成磁滞回线示例数据', async () => {
      await wrapper.vm.generateHysteresisDemoData();
      await flushPromises();

      expect(wrapper.vm.hysteresisData.x.length).toBeGreaterThan(0);
      expect(wrapper.vm.hysteresisData.y.length).toBeGreaterThan(0);
    });

    it('应该清空数据', async () => {
      wrapper.vm.rawData = [1, 2, 3, 4, 5];
      wrapper.vm.smoothedData = [1, 2, 3];

      await wrapper.vm.generateDemoData();
      await flushPromises();

      expect(wrapper.vm.smoothedData.length).toBe(0);
    });

    it('应该生成带有噪声的数据', async () => {
      await wrapper.vm.generateDemoData();
      await flushPromises();

      // 检查数据是否包含噪声（不是完全的正弦波）
      const hasVariation = wrapper.vm.rawData.some((val, i, arr) => {
        if (i === 0) return false;
        return Math.abs(val - arr[i - 1]) > 0.1;
      });
      expect(hasVariation).toBe(true);
    });

    it('应该生成磁滞回线数据包含正向和反向扫描', async () => {
      await wrapper.vm.generateHysteresisDemoData();
      await flushPromises();

      const xData = wrapper.vm.hysteresisData.x;
      // 检查数据是否包含正向和反向扫描
      const hasPositive = xData.some(v => v > 0);
      const hasNegative = xData.some(v => v < 0);
      expect(hasPositive).toBe(true);
      expect(hasNegative).toBe(true);
    });
  });

  // ==================== 数据筛选测试 ====================

  describe('数据筛选', () => {
    it('应该应用平滑参数', async () => {
      wrapper.vm.smoothConfig = {
        method: 'savitzky_golay',
        window_length: 11,
        polyorder: 3,
        butter_lowcut: 0.1,
        butter_order: 4,
      };

      expect(wrapper.vm.smoothConfig.method).toBe('savitzky_golay');
      expect(wrapper.vm.smoothConfig.window_length).toBe(11);
    });

    it('应该应用磁滞回线分析参数', async () => {
      wrapper.vm.hysteresisConfig = {
        subtract_background: true,
        saturation_threshold: 0.9,
      };

      expect(wrapper.vm.hysteresisConfig.subtract_background).toBe(true);
      expect(wrapper.vm.hysteresisConfig.saturation_threshold).toBe(0.9);
    });

    it('应该切换标注类型', async () => {
      wrapper.vm.annotationType = 'point';
      expect(wrapper.vm.annotationType).toBe('point');

      wrapper.vm.annotationType = 'line';
      expect(wrapper.vm.annotationType).toBe('line');
    });

    it('应该切换标签页', async () => {
      wrapper.vm.activeTab = 'hysteresis';
      expect(wrapper.vm.activeTab).toBe('hysteresis');

      wrapper.vm.activeTab = 'multi-model';
      expect(wrapper.vm.activeTab).toBe('multi-model');

      wrapper.vm.activeTab = 'report';
      expect(wrapper.vm.activeTab).toBe('report');
    });

    it('应该选择多个模型进行对比', async () => {
      wrapper.vm.selectedModels = ['hyperbolic', 'arctangent'];
      expect(wrapper.vm.selectedModels.length).toBe(2);
    });
  });

  // ==================== 数据导出测试 ====================

  describe('数据导出', () => {
    it('应该导出CSV格式', async () => {
      wrapper.vm.rawData = [1, 2, 3, 4, 5];

      await wrapper.vm.exportAsCSV();

      const { exportSmoothDataAsCSV } = await import('@/utils/chartUtils');
      expect(exportSmoothDataAsCSV).toHaveBeenCalled();
    });

    it('应该导出PNG格式', async () => {
      wrapper.vm.rawData = [1, 2, 3, 4, 5];

      await wrapper.vm.exportAsPNG();

      const { exportChartAsImage } = await import('@/utils/chartUtils');
      expect(exportChartAsImage).toHaveBeenCalled();
    });

    it('应该导出SVG格式', async () => {
      wrapper.vm.rawData = [1, 2, 3, 4, 5];

      await wrapper.vm.exportAsSVG();

      const { exportChartAsSVG } = await import('@/utils/chartUtils');
      expect(exportChartAsSVG).toHaveBeenCalled();
    });

    it('应该处理导出命令', async () => {
      wrapper.vm.rawData = [1, 2, 3, 4, 5];

      await wrapper.vm.handleExportCommand('csv');
      const { exportSmoothDataAsCSV } = await import('@/utils/chartUtils');
      expect(exportSmoothDataAsCSV).toHaveBeenCalled();
    });

    it('应该在没有数据时显示警告', async () => {
      wrapper.vm.rawData = [];

      await wrapper.vm.exportAsCSV();

      const { exportSmoothDataAsCSV } = await import('@/utils/chartUtils');
      expect(exportSmoothDataAsCSV).not.toHaveBeenCalled();
    });

    it('应该导出磁滞回线数据为CSV', async () => {
      wrapper.vm.hysteresisData = { x: [0, 1, 2], y: [0, 0.5, 1] };
      wrapper.vm.activeTab = 'hysteresis';

      await wrapper.vm.exportAsCSV();

      const { exportHysteresisDataAsCSV } = await import('@/utils/chartUtils');
      expect(exportHysteresisDataAsCSV).toHaveBeenCalled();
    });
  });

  // ==================== 信号平滑功能测试 ====================

  describe('信号平滑功能', () => {
    it('应该应用Savitzky-Golay滤波', async () => {
      wrapper.vm.rawData = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
      wrapper.vm.smoothConfig.method = 'savitzky_golay';

      await wrapper.vm.applySmooth();

      expect(mockMotorStore.smoothSignal).toHaveBeenCalled();
    });

    it('应该应用巴特沃斯滤波', async () => {
      wrapper.vm.rawData = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
      wrapper.vm.smoothConfig.method = 'butterworth';

      await wrapper.vm.applySmooth();

      expect(mockMotorStore.smoothSignal).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'butterworth' })
      );
    });

    it('应该在没有数据时显示警告', async () => {
      wrapper.vm.rawData = [];

      await wrapper.vm.applySmooth();

      expect(mockMotorStore.smoothSignal).not.toHaveBeenCalled();
    });

    it('应该更新平滑后的数据', async () => {
      wrapper.vm.rawData = [1, 2, 3, 4, 5];

      await wrapper.vm.applySmooth();

      expect(wrapper.vm.smoothedData.length).toBeGreaterThan(0);
    });
  });

  // ==================== 磁滞回线分析测试 ====================

  describe('磁滞回线分析', () => {
    it('应该执行磁滞回线分析', async () => {
      wrapper.vm.hysteresisData = {
        x: [-1, 0, 1, 0, -1],
        y: [-0.5, 0, 0.5, 0, -0.5],
      };

      await wrapper.vm.analyzeHysteresis();

      expect(mockMotorStore.analyzeHysteresis).toHaveBeenCalled();
    });

    it('应该显示分析结果', async () => {
      wrapper.vm.hysteresisData = {
        x: [-1, 0, 1, 0, -1],
        y: [-0.5, 0, 0.5, 0, -0.5],
      };

      await wrapper.vm.analyzeHysteresis();

      expect(wrapper.vm.hysteresisResult).not.toBeNull();
    });

    it('应该在没有数据时显示警告', async () => {
      wrapper.vm.hysteresisData = { x: [], y: [] };

      await wrapper.vm.analyzeHysteresis();

      expect(mockMotorStore.analyzeHysteresis).not.toHaveBeenCalled();
    });
  });

  // ==================== 多模型对比测试 ====================

  describe('多模型对比', () => {
    it('应该执行多模型拟合', async () => {
      wrapper.vm.hysteresisData = {
        x: [-1, 0, 1, 0, -1],
        y: [-0.5, 0, 0.5, 0, -0.5],
      };
      wrapper.vm.selectedModels = ['hyperbolic', 'arctangent'];

      await wrapper.vm.runMultiModelFit();

      const { multiModelFit } = await import('@/api/analysis');
      expect(multiModelFit).toHaveBeenCalled();
    });

    it('应该显示拟合结果', async () => {
      wrapper.vm.hysteresisData = {
        x: [-1, 0, 1, 0, -1],
        y: [-0.5, 0, 0.5, 0, -0.5],
      };
      wrapper.vm.selectedModels = ['hyperbolic', 'arctangent'];

      await wrapper.vm.runMultiModelFit();

      expect(wrapper.vm.multiFitResults.length).toBeGreaterThan(0);
    });

    it('应该选择最佳模型', async () => {
      wrapper.vm.hysteresisData = {
        x: [-1, 0, 1, 0, -1],
        y: [-0.5, 0, 0.5, 0, -0.5],
      };
      wrapper.vm.selectedModels = ['hyperbolic', 'arctangent'];

      await wrapper.vm.runMultiModelFit();

      expect(wrapper.vm.bestModel).toBeTruthy();
    });

    it('应该在没有选择足够模型时显示警告', async () => {
      wrapper.vm.hysteresisData = {
        x: [-1, 0, 1, 0, -1],
        y: [-0.5, 0, 0.5, 0, -0.5],
      };
      wrapper.vm.selectedModels = ['hyperbolic'];

      await wrapper.vm.runMultiModelFit();

      const { multiModelFit } = await import('@/api/analysis');
      expect(multiModelFit).not.toHaveBeenCalled();
    });

    it('应该获取正确的R2标签类型', () => {
      expect(wrapper.vm.getR2TagType(0.98)).toBe('success');
      expect(wrapper.vm.getR2TagType(0.92)).toBe('primary');
      expect(wrapper.vm.getR2TagType(0.85)).toBe('warning');
      expect(wrapper.vm.getR2TagType(0.70)).toBe('danger');
    });

    it('应该获取正确的模型名称', () => {
      expect(wrapper.vm.getModelName('hyperbolic')).toBe('双曲正切模型');
      expect(wrapper.vm.getModelName('arctangent')).toBe('反正切模型');
    });
  });

  // ==================== 分析报告测试 ====================

  describe('分析报告', () => {
    it('应该生成分析报告', async () => {
      wrapper.vm.hysteresisData = {
        x: [-1, 0, 1, 0, -1],
        y: [-0.5, 0, 0.5, 0, -0.5],
      };

      await wrapper.vm.generateReport();

      const { generateAnalysisReport } = await import('@/api/analysis');
      expect(generateAnalysisReport).toHaveBeenCalled();
    });

    it('应该显示报告数据', async () => {
      wrapper.vm.hysteresisData = {
        x: [-1, 0, 1, 0, -1],
        y: [-0.5, 0, 0.5, 0, -0.5],
      };

      await wrapper.vm.generateReport();

      expect(wrapper.vm.reportData).not.toBeNull();
    });

    it('应该在没有数据时显示警告', async () => {
      wrapper.vm.hysteresisData = { x: [], y: [] };

      await wrapper.vm.generateReport();

      const { generateAnalysisReport } = await import('@/api/analysis');
      expect(generateAnalysisReport).not.toHaveBeenCalled();
    });

    it('应该导出报告为JSON格式', async () => {
      wrapper.vm.reportData = { experiment_id: 'exp_001' };

      await wrapper.vm.exportReport('json');

      const { exportAnalysisReport } = await import('@/api/analysis');
      expect(exportAnalysisReport).toHaveBeenCalled();
    });

    it('应该导出报告为CSV格式', async () => {
      wrapper.vm.reportData = { experiment_id: 'exp_001' };

      await wrapper.vm.exportReport('csv');

      const { exportAnalysisReport } = await import('@/api/analysis');
      expect(exportAnalysisReport).toHaveBeenCalled();
    });
  });

  // ==================== 历史记录测试 ====================

  describe('历史记录', () => {
    it('应该加载历史记录', async () => {
      await wrapper.vm.loadHistory();
      await flushPromises();

      const { getAnalysisHistory } = require('@/api/analysis');
      expect(getAnalysisHistory).toHaveBeenCalled();
    });

    it('应该删除历史记录', async () => {
      wrapper.vm.analysisHistory = [{ id: '1', timestamp: Date.now() }];

      await wrapper.vm.handleDeleteHistory('1');
      await flushPromises();

      const { deleteAnalysisHistory } = require('@/api/analysis');
      expect(deleteAnalysisHistory).toHaveBeenCalledWith('1');
    });

    it('应该清空历史记录', async () => {
      wrapper.vm.analysisHistory = [
        { id: '1', timestamp: Date.now() },
        { id: '2', timestamp: Date.now() },
      ];

      await wrapper.vm.handleClearHistory();
      await flushPromises();

      const { clearAnalysisHistory } = require('@/api/analysis');
      expect(clearAnalysisHistory).toHaveBeenCalled();
    });

    it('应该加载历史记录项', async () => {
      const record = {
        result: {
          h_data: [0, 1, 2],
          b_data: [0, 0.5, 1],
          results: [],
          best_model: 'hyperbolic',
        },
      };

      await wrapper.vm.loadHistoryRecord(record);
      await flushPromises();

      expect(wrapper.vm.hysteresisData.x).toEqual([0, 1, 2]);
      expect(wrapper.vm.hysteresisData.y).toEqual([0, 0.5, 1]);
    });
  });

  // ==================== 标注功能测试 ====================

  describe('标注功能', () => {
    it('应该切换标注面板显示', async () => {
      const initialState = wrapper.vm.showAnnotationPanel;
      wrapper.vm.showAnnotationPanel = !wrapper.vm.showAnnotationPanel;
      await flushPromises();
      expect(wrapper.vm.showAnnotationPanel).toBe(!initialState);
    });

    it('应该添加标注点', async () => {
      wrapper.vm.showAnnotationPanel = true;
      wrapper.vm.annotationType = 'point';

      await wrapper.vm.handleChartClick({
        dataIndex: 5,
        value: 0.5,
        seriesName: '原始数据',
      });
      await flushPromises();

      expect(wrapper.vm.markPoints.length).toBe(1);
    });

    it('应该添加标注线', async () => {
      wrapper.vm.showAnnotationPanel = true;
      wrapper.vm.annotationType = 'line';

      await wrapper.vm.handleChartClick({
        dataIndex: 5,
        value: 0.5,
        seriesName: '原始数据',
      });
      await flushPromises();

      expect(wrapper.vm.markLines.length).toBe(1);
    });

    it('应该清除所有标注', async () => {
      wrapper.vm.markPoints = [{ name: '点1', value: 0.5 }];
      wrapper.vm.markLines = [{ name: '线1', yAxis: 0.5 }];

      await wrapper.vm.clearAllMarks();
      await flushPromises();

      expect(wrapper.vm.markPoints.length).toBe(0);
      expect(wrapper.vm.markLines.length).toBe(0);
    });

    it('应该移除单个标注点', async () => {
      wrapper.vm.markPoints = [
        { name: '点1', value: 0.5 },
        { name: '点2', value: 0.6 },
      ];

      await wrapper.vm.removeMarkPoint(0);
      await flushPromises();

      expect(wrapper.vm.markPoints.length).toBe(1);
      expect(wrapper.vm.markPoints[0].name).toBe('点2');
    });

    it('应该移除单个标注线', async () => {
      wrapper.vm.markLines = [
        { name: '线1', yAxis: 0.5 },
        { name: '线2', yAxis: 0.6 },
      ];

      await wrapper.vm.removeMarkLine(0);
      await flushPromises();

      expect(wrapper.vm.markLines.length).toBe(1);
      expect(wrapper.vm.markLines[0].name).toBe('线2');
    });
  });

  // ==================== 工具函数测试 ====================

  describe('工具函数', () => {
    it('应该正确格式化时间戳', async () => {
      const timestamp = '2024-03-16T10:30:00.000Z';
      const formatted = await wrapper.vm.formatTimestamp(timestamp);
      await flushPromises();

      expect(formatted).toBeTruthy();
    });

    it('应该正确格式化参数', async () => {
      const params = { a: 1, b: 2, c: 3 };
      const formatted = await wrapper.vm.formatParameters(params);
      await flushPromises();

      expect(formatted.length).toBe(3);
      expect(formatted[0].name).toBe('a');
      expect(formatted[0].value).toBe(1);
    });

    it('应该正确处理空参数', async () => {
      const formatted = await wrapper.vm.formatParameters(null);
      await flushPromises();

      expect(formatted).toEqual([]);
    });
  });

  // ==================== 大数据量优化测试 ====================

  describe('大数据量优化', () => {
    it('应该检测大数据量', async () => {
      wrapper.vm.rawData = Array(15000).fill(0);
      await flushPromises();

      expect(wrapper.vm.isLargeSmoothData).toBe(true);
    });

    it('应该检测小数据量', async () => {
      wrapper.vm.rawData = Array(1000).fill(0);
      await flushPromises();

      expect(wrapper.vm.isLargeSmoothData).toBe(false);
    });

    it('应该检测磁滞回线大数据量', async () => {
      wrapper.vm.hysteresisData = {
        x: Array(15000).fill(0),
        y: Array(15000).fill(0),
      };
      await flushPromises();

      expect(wrapper.vm.isLargeHysteresisData).toBe(true);
    });
  });

  // ==================== 模型详情测试 ====================

  describe('模型详情', () => {
    it('应该显示模型详情对话框', async () => {
      const model = {
        model_name: '双曲正切模型',
        r_squared: 0.98,
        rmse: 0.02,
        aic: -100,
        bic: -95,
        parameters: { a: 1, b: 2 },
      };

      await wrapper.vm.viewModelDetails(model);
      await flushPromises();

      expect(wrapper.vm.selectedModelDetail).toEqual(model);
      expect(wrapper.vm.showModelDetailDialog).toBe(true);
    });
  });

  // ==================== 性能监控测试 ====================

  describe('性能监控', () => {
    it('应该获取性能报告', async () => {
      const report = await wrapper.vm.getPerformanceReport();
      await flushPromises();

      expect(report).toHaveProperty('virtualScroll');
      expect(report).toHaveProperty('dataStats');
      expect(report).toHaveProperty('cacheStats');
    });

    it('应该清理图表内存', async () => {
      wrapper.vm.chartConfigCache = { smooth: {}, hysteresis: {} };

      await wrapper.vm.cleanupChartMemory();
      await flushPromises();

      expect(wrapper.vm.chartConfigCache.smooth).toBeNull();
      expect(wrapper.vm.chartConfigCache.hysteresis).toBeNull();
    });
  });

  // ==================== 虚拟滚动测试 ====================

  describe('虚拟滚动', () => {
    it('应该检测是否需要虚拟滚动', async () => {
      wrapper.vm.rawData = Array(15000).fill(0);
      wrapper.vm.virtualScrollConfig.enabled = true;
      await flushPromises();

      expect(wrapper.vm.needsVirtualScroll).toBe(true);
    });

    it('应该更新可见数据范围', async () => {
      await wrapper.vm.updateVisibleRange(0, 5000);
      await flushPromises();

      expect(wrapper.vm.visibleDataRange.start).toBe(0);
      expect(wrapper.vm.visibleDataRange.end).toBe(5500); // 包含overscan
    });

    it('应该获取可见数据', async () => {
      wrapper.vm.rawData = Array(10000).fill(0).map((_, i) => i);
      wrapper.vm.visibleDataRange = { start: 0, end: 100 };
      await flushPromises();

      const visibleData = await wrapper.vm.getVisibleData(wrapper.vm.rawData);
      await flushPromises();

      expect(visibleData.length).toBe(100);
    });
  });
});
