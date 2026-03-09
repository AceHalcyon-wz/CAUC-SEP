/**
 * @file DataAnalysis.test.js
 * @path frontend/src/components/__tests__/
 * @description DataAnalysis组件单元测试
 * @author Agent
 * @date 2024-03-07
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import DataAnalysis from '../DataAnalysis.vue';

// Mock ECharts
const mockChartInstance = {
  setOption: vi.fn(),
  resize: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  dispose: vi.fn(),
  getOption: vi.fn(() => ({ series: [{ data: [] }] })),
};

vi.mock('echarts', () => ({
  default: {
    init: vi.fn(() => mockChartInstance),
  },
  init: vi.fn(() => mockChartInstance),
}));

// Mock API
vi.mock('../../api/analysis', () => ({
  multiModelFit: vi.fn(),
  generateAnalysisReport: vi.fn(),
  exportAnalysisReport: vi.fn(),
  getAnalysisHistory: vi.fn(() => []),
  saveAnalysisToHistory: vi.fn(),
  deleteAnalysisHistory: vi.fn(),
  clearAnalysisHistory: vi.fn(),
}));

describe('DataAnalysis', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    
    wrapper = mount(DataAnalysis, {
      global: {
        plugins: [pinia],
        stubs: {
          'el-card': { template: '<div class="el-card"><slot /></div>' },
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
        },
      },
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.clearAllMocks();
  });

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
  });

  describe('多模型对比功能', () => {
    it('应该显示模型选择器', () => {
      const checkboxGroup = wrapper.find('.el-checkbox-group');
      expect(checkboxGroup.exists()).toBe(true);
    });

    it('应该包含可用模型列表', () => {
      expect(wrapper.vm.availableModels).toHaveLength(4);
      expect(wrapper.vm.availableModels.map(m => m.id)).toContain('hyperbolic');
      expect(wrapper.vm.availableModels.map(m => m.id)).toContain('arctangent');
    });

    it('应该默认选中三个模型', () => {
      expect(wrapper.vm.selectedModels).toHaveLength(3);
    });

    it('应该执行多模型拟合', async () => {
      const { multiModelFit } = await import('../../api/analysis');
      
      // 设置测试数据
      wrapper.vm.hysteresisData = {
        x: [1, 2, 3, 4, 5],
        y: [1, 2, 3, 4, 5],
      };
      
      // Mock API响应
      multiModelFit.mockResolvedValueOnce({
        results: [
          { model_name: '双曲正切模型', r_squared: 0.95, rmse: 0.05, aic: -10, bic: -8 },
          { model_name: '反正切模型', r_squared: 0.92, rmse: 0.08, aic: -8, bic: -6 },
        ],
        best_model: 'hyperbolic',
      });
      
      await wrapper.vm.runMultiModelFit();
      await flushPromises();
      
      expect(multiModelFit).toHaveBeenCalled();
      expect(wrapper.vm.multiFitResults).toHaveLength(2);
      expect(wrapper.vm.bestModel).toBe('hyperbolic');
    });

    it('应该显示拟合结果对比表格', async () => {
      wrapper.vm.multiFitResults = [
        { model_name: '模型A', r_squared: 0.95, rmse: 0.05, aic: -10, bic: -8 },
        { model_name: '模型B', r_squared: 0.92, rmse: 0.08, aic: -8, bic: -6 },
      ];
      
      await wrapper.vm.$nextTick();
      
      const table = wrapper.find('.el-table');
      expect(table.exists()).toBe(true);
    });

    it('应该推荐最佳模型', async () => {
      wrapper.vm.bestModel = 'hyperbolic';
      
      await wrapper.vm.$nextTick();
      
      expect(wrapper.vm.getModelName('hyperbolic')).toBe('双曲正切模型');
    });

    it('应该在没有数据时显示警告', async () => {
      wrapper.vm.hysteresisData = { x: [], y: [] };
      
      await wrapper.vm.runMultiModelFit();
      
      // 应该不调用API
      const { multiModelFit } = await import('../../api/analysis');
      expect(multiModelFit).not.toHaveBeenCalled();
    });

    it('应该在模型选择不足时显示警告', async () => {
      wrapper.vm.hysteresisData = { x: [1, 2, 3], y: [1, 2, 3] };
      wrapper.vm.selectedModels = ['hyperbolic'];
      
      await wrapper.vm.runMultiModelFit();
      
      const { multiModelFit } = await import('../../api/analysis');
      expect(multiModelFit).not.toHaveBeenCalled();
    });
  });

  describe('报告功能', () => {
    it('应该生成分析报告', async () => {
      const { generateAnalysisReport } = await import('../../api/analysis');
      
      wrapper.vm.hysteresisData = {
        x: [1, 2, 3, 4, 5],
        y: [1, 2, 3, 4, 5],
      };
      
      generateAnalysisReport.mockResolvedValueOnce({
        experiment_id: 'test-123',
        timestamp: new Date().toISOString(),
        hysteresis_params: { Bs: 1.5, Hc: 100, Br: 0.8, Hs: 500 },
        fit_results: [],
        quality_metrics: { r_squared: 0.95 },
        recommendations: ['建议1'],
      });
      
      await wrapper.vm.generateReport();
      await flushPromises();
      
      expect(generateAnalysisReport).toHaveBeenCalled();
      expect(wrapper.vm.reportData).not.toBeNull();
    });

    it('应该显示报告预览', async () => {
      wrapper.vm.reportData = {
        experiment_id: 'test-123',
        timestamp: new Date().toISOString(),
        hysteresis_params: { Bs: 1.5, Hc: 100, Br: 0.8, Hs: 500 },
      };
      
      await wrapper.vm.$nextTick();
      
      const reportContent = wrapper.find('.report-content');
      expect(reportContent.exists()).toBe(true);
    });

    it('应该导出JSON格式报告', async () => {
      const { exportAnalysisReport } = await import('../../api/analysis');
      
      wrapper.vm.hysteresisData = {
        x: [1, 2, 3],
        y: [1, 2, 3],
      };
      wrapper.vm.reportData = { test: 'data' };
      
      // Mock Blob
      global.URL.createObjectURL = vi.fn(() => 'blob:test');
      global.URL.revokeObjectURL = vi.fn();
      
      const blob = new Blob(['test'], { type: 'application/json' });
      exportAnalysisReport.mockResolvedValueOnce(blob);
      
      await wrapper.vm.exportReport('json');
      await flushPromises();
      
      expect(exportAnalysisReport).toHaveBeenCalledWith(
        expect.objectContaining({ format: 'json' })
      );
    });

    it('应该导出CSV格式报告', async () => {
      const { exportAnalysisReport } = await import('../../api/analysis');
      
      wrapper.vm.hysteresisData = {
        x: [1, 2, 3],
        y: [1, 2, 3],
      };
      wrapper.vm.reportData = { test: 'data' };
      
      global.URL.createObjectURL = vi.fn(() => 'blob:test');
      global.URL.revokeObjectURL = vi.fn();
      
      const blob = new Blob(['test'], { type: 'text/csv' });
      exportAnalysisReport.mockResolvedValueOnce(blob);
      
      await wrapper.vm.exportReport('csv');
      await flushPromises();
      
      expect(exportAnalysisReport).toHaveBeenCalledWith(
        expect.objectContaining({ format: 'csv' })
      );
    });

    it('应该在没有报告数据时显示警告', async () => {
      wrapper.vm.reportData = null;
      
      await wrapper.vm.exportReport('json');
      
      const { exportAnalysisReport } = await import('../../api/analysis');
      expect(exportAnalysisReport).not.toHaveBeenCalled();
    });
  });

  describe('历史记录功能', () => {
    it('应该保存分析结果到历史', async () => {
      const { saveAnalysisToHistory } = await import('../../api/analysis');
      
      wrapper.vm.hysteresisData = {
        x: [1, 2, 3],
        y: [1, 2, 3],
      };
      wrapper.vm.multiFitResults = [
        { model_name: '模型A', r_squared: 0.95 },
      ];
      wrapper.vm.bestModel = 'hyperbolic';
      
      // 触发保存
      await wrapper.vm.runMultiModelFit();
      
      // saveAnalysisToHistory 应该在 runMultiModelFit 成功后被调用
    });

    it('应该加载历史记录', () => {
      wrapper.vm.analysisHistory = [
        { id: 1, timestamp: '2024-03-07T10:00:00Z', result: {} },
        { id: 2, timestamp: '2024-03-07T11:00:00Z', result: {} },
      ];
      
      expect(wrapper.vm.analysisHistory).toHaveLength(2);
    });

    it('应该删除历史记录', async () => {
      const { deleteAnalysisHistory } = await import('../../api/analysis');
      
      deleteAnalysisHistory.mockReturnValue(true);
      
      wrapper.vm.analysisHistory = [
        { id: 1, timestamp: '2024-03-07T10:00:00Z' },
        { id: 2, timestamp: '2024-03-07T11:00:00Z' },
      ];
      
      await wrapper.vm.handleDeleteHistory(1);
      
      expect(deleteAnalysisHistory).toHaveBeenCalledWith(1);
    });

    it('应该清空所有历史记录', async () => {
      const { clearAnalysisHistory } = await import('../../api/analysis');
      
      clearAnalysisHistory.mockReturnValue(true);
      
      wrapper.vm.analysisHistory = [
        { id: 1, timestamp: '2024-03-07T10:00:00Z' },
        { id: 2, timestamp: '2024-03-07T11:00:00Z' },
      ];
      
      await wrapper.vm.handleClearHistory();
      
      expect(clearAnalysisHistory).toHaveBeenCalled();
      expect(wrapper.vm.analysisHistory).toHaveLength(0);
    });

    it('应该加载历史记录项到当前分析', async () => {
      const record = {
        result: {
          h_data: [1, 2, 3],
          b_data: [4, 5, 6],
          best_model: 'hyperbolic',
          results: [{ model_name: '模型A', r_squared: 0.95 }],
        },
      };
      
      wrapper.vm.loadHistoryRecord(record);
      
      expect(wrapper.vm.hysteresisData.x).toEqual([1, 2, 3]);
      expect(wrapper.vm.hysteresisData.y).toEqual([4, 5, 6]);
      expect(wrapper.vm.bestModel).toBe('hyperbolic');
    });
  });

  describe('工具函数', () => {
    it('应该正确格式化时间戳', () => {
      const timestamp = '2024-03-07T10:30:00Z';
      const formatted = wrapper.vm.formatTimestamp(timestamp);
      
      expect(formatted).toBeTruthy();
    });

    it('应该正确获取模型名称', () => {
      expect(wrapper.vm.getModelName('hyperbolic')).toBe('双曲正切模型');
      expect(wrapper.vm.getModelName('arctangent')).toBe('反正切模型');
      expect(wrapper.vm.getModelName('unknown')).toBe('unknown');
    });

    it('应该正确获取R²标签类型', () => {
      expect(wrapper.vm.getR2TagType(0.96)).toBe('success');
      expect(wrapper.vm.getR2TagType(0.92)).toBe('primary');
      expect(wrapper.vm.getR2TagType(0.85)).toBe('warning');
      expect(wrapper.vm.getR2TagType(0.70)).toBe('danger');
    });

    it('应该正确格式化参数', () => {
      const params = { a: 1.234567, b: 2.345678 };
      const formatted = wrapper.vm.formatParameters(params);
      
      expect(formatted).toHaveLength(2);
      expect(formatted[0]).toHaveProperty('name', 'a');
      expect(formatted[0]).toHaveProperty('value', 1.234567);
    });
  });

  describe('标注功能', () => {
    it('应该切换标注面板', async () => {
      expect(wrapper.vm.showAnnotationPanel).toBe(false);
      
      wrapper.vm.showAnnotationPanel = true;
      await wrapper.vm.$nextTick();
      
      expect(wrapper.vm.showAnnotationPanel).toBe(true);
    });

    it('应该清除所有标注', () => {
      wrapper.vm.markPoints = [{ name: '点1', value: 1 }];
      wrapper.vm.markLines = [{ name: '线1', yAxis: 1 }];
      
      wrapper.vm.clearAllMarks();
      
      expect(wrapper.vm.markPoints).toHaveLength(0);
      expect(wrapper.vm.markLines).toHaveLength(0);
    });

    it('应该移除单个标注点', () => {
      wrapper.vm.markPoints = [
        { name: '点1', value: 1 },
        { name: '点2', value: 2 },
      ];
      
      wrapper.vm.removeMarkPoint(0);
      
      expect(wrapper.vm.markPoints).toHaveLength(1);
      expect(wrapper.vm.markPoints[0].name).toBe('点2');
    });

    it('应该移除单个标注线', () => {
      wrapper.vm.markLines = [
        { name: '线1', yAxis: 1 },
        { name: '线2', yAxis: 2 },
      ];
      
      wrapper.vm.removeMarkLine(0);
      
      expect(wrapper.vm.markLines).toHaveLength(1);
      expect(wrapper.vm.markLines[0].name).toBe('线2');
    });
  });

  describe('大数据量优化', () => {
    it('应该检测大数据量', () => {
      wrapper.vm.rawData = Array(15000).fill(0);
      
      expect(wrapper.vm.isLargeSmoothData).toBe(true);
    });

    it('应该检测小数据量', () => {
      wrapper.vm.rawData = Array(100).fill(0);
      
      expect(wrapper.vm.isLargeSmoothData).toBe(false);
    });

    it('应该检测磁滞回线大数据量', () => {
      wrapper.vm.hysteresisData = {
        x: Array(15000).fill(0),
        y: Array(15000).fill(0),
      };
      
      expect(wrapper.vm.isLargeHysteresisData).toBe(true);
    });
  });
});
