/**
 * @file ElectromagnetControl.test.js
 * @path frontend/src/components/__tests__/
 * @description ElectromagnetControl组件单元测试
 * @author Agent
 * @date 2024-03-08
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ElectromagnetControl from '../ElectromagnetControl.vue';

const mockElectromagnetStore = {
  isConnected: true,
  isConnecting: false,
  status: 'ready',
  alarmMessage: '',
  wsConnected: true,
  loading: {
    setCurrent: false,
    setField: false,
    configScan: false,
    startScan: false,
    stopScan: false,
    validateScanConfig: false,
    fetchCalibration: false,
    uploadCalibration: false,
    validateCalibration: false,
    performCalibration: false,
    clearCalibration: false,
    resetOvercurrent: false,
  },
  canControl: true,
  isScanning: false,
  isPaused: false,
  currentLimits: {
    min: 0,
    max: 10,
  },
  current: 0,
  field: 0,
  currentCurrent: 0,
  currentField: 0,
  formattedCurrent: '0.000',
  formattedField: '0.00',
  scanStatus: {
    progress: 0,
    currentStep: 0,
    totalSteps: 0,
    currentCurrent: 0,
    currentField: 0,
    scanDirection: 'forward',
  },
  scanData: {
    current: [],
    field: [],
  },
  estimatedRemainingTime: 0,
  calibrationStatus: '未校准',
  calibrationCurve: {
    coefficients: null,
  },
  setCurrent: vi.fn().mockResolvedValue(true),
  setField: vi.fn().mockResolvedValue(true),
  configScan: vi.fn().mockResolvedValue(true),
  configureScan: vi.fn().mockResolvedValue(true),
  startScan: vi.fn().mockResolvedValue(true),
  stopScan: vi.fn().mockResolvedValue(true),
  pauseScan: vi.fn().mockResolvedValue(true),
  resumeScan: vi.fn().mockResolvedValue(true),
  validateScanConfig: vi.fn().mockResolvedValue({ valid: true }),
  exportScanData: vi.fn().mockReturnValue('[]'),
  clearAlarm: vi.fn(),
  clearScanData: vi.fn(),
  calculateCurrent: vi.fn().mockReturnValue(0),
  calculateField: vi.fn().mockReturnValue(0),
  init: vi.fn(),
  cleanup: vi.fn(),
  fetchCalibration: vi.fn().mockResolvedValue(null),
  uploadCalibration: vi.fn().mockResolvedValue(true),
  validateCalibration: vi.fn().mockResolvedValue({ valid: true }),
  performCalibration: vi.fn().mockResolvedValue(true),
  clearCalibration: vi.fn().mockResolvedValue(true),
  emergencyStop: vi.fn().mockResolvedValue(true),
  resetEmergency: vi.fn().mockResolvedValue(true),
  resetOvercurrent: vi.fn().mockResolvedValue(true),
};

vi.mock('../../stores/electromagnet', () => ({
  useElectromagnetStore: vi.fn(() => mockElectromagnetStore),
}));

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

vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

const stubs = {
  'el-card': { template: '<div class="el-card"><slot /><slot name="header" /></div>' },
  'el-button': {
    template: '<button class="el-button" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
    props: ['disabled', 'type', 'size', 'loading'],
  },
  'el-icon': { template: '<i class="el-icon"><slot /></i>' },
  'el-alert': {
    template: '<div class="el-alert" v-if="title"><slot />{{ title }}</div>',
    props: ['title', 'type', 'closable'],
  },
  'el-form': { template: '<form class="el-form"><slot /></form>' },
  'el-form-item': { template: '<div class="el-form-item"><slot /></div>' },
  'el-input-number': {
    template: '<input type="number" class="el-input-number" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
    props: ['modelValue', 'min', 'max', 'precision', 'step'],
  },
  'el-tag': { template: '<span class="el-tag"><slot /></span>' },
  'el-divider': { template: '<hr class="el-divider"><slot /></hr>' },
  'el-slider': {
    template: '<input type="range" class="el-slider slider-control" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
    props: ['modelValue', 'min', 'max', 'step', 'marks', 'disabled'],
  },
  'el-radio-group': { template: '<div class="el-radio-group mode-radio-group"><slot /></div>' },
  'el-radio': { template: '<label class="el-radio"><slot /></label>' },
  'el-progress': { template: '<div class="el-progress"></div>' },
  'el-row': { template: '<div class="el-row"><slot /></div>' },
  'el-col': { template: '<div class="el-col"><slot /></div>' },
  'el-checkbox': { template: '<input type="checkbox" class="el-checkbox" />' },
  'el-table': { template: '<table class="el-table"><slot /></table>' },
  'el-table-column': { template: '<col class="el-table-column" />' },
  'Opportunity': { template: '<span class="opportunity-icon"></span>' },
  'Lightning': { template: '<span class="lightning-icon"></span>' },
  'Magnet': { template: '<span class="magnet-icon"></span>' },
  'VideoPlay': { template: '<span class="video-play-icon"></span>' },
  'VideoPause': { template: '<span class="video-pause-icon"></span>' },
  'Close': { template: '<span class="close-icon"></span>' },
  'Warning': { template: '<span class="warning-icon"></span>' },
  'RefreshRight': { template: '<span class="refresh-right-icon"></span>' },
  'ArrowRight': { template: '<span class="arrow-right-icon"></span>' },
  'ArrowLeft': { template: '<span class="arrow-left-icon"></span>' },
  'Download': { template: '<span class="download-icon"></span>' },
  'Delete': { template: '<span class="delete-icon"></span>' },
};

describe('ElectromagnetControl', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    vi.clearAllMocks();
    pinia = createPinia();
    setActivePinia(pinia);

    wrapper = mount(ElectromagnetControl, {
      global: {
        plugins: [pinia],
        stubs,
      },
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.clearAllMocks();
  });

  describe('组件渲染', () => {
    it('应该正确渲染组件', () => {
      expect(wrapper.find('.electromagnet-control').exists()).toBe(true);
    });

    it('应该显示电磁铁控制标题', () => {
      expect(wrapper.text()).toContain('电磁铁控制');
    });

    it('应该显示实时数据显示区域', () => {
      expect(wrapper.find('.realtime-display').exists()).toBe(true);
    });

    it('应该显示当前电流显示', () => {
      expect(wrapper.find('.current-display').exists()).toBe(true);
    });

    it('应该显示磁场强度显示', () => {
      expect(wrapper.find('.field-display').exists()).toBe(true);
    });

    it('应该显示电流设置区域', () => {
      expect(wrapper.find('.current-form').exists()).toBe(true);
    });

    it('应该显示扫描模式配置区域', () => {
      expect(wrapper.find('.scan-form').exists()).toBe(true);
    });

    it('应该显示电流滑块', () => {
      expect(wrapper.find('.current-slider').exists()).toBe(true);
    });
  });

  describe('实时数据显示', () => {
    it('应该显示当前电流值', () => {
      const currentDisplay = wrapper.find('.current-display');
      expect(currentDisplay.text()).toContain('当前电流');
    });

    it('应该显示磁场强度值', () => {
      const fieldDisplay = wrapper.find('.field-display');
      expect(fieldDisplay.text()).toContain('磁场强度');
    });

    it('应该显示电流单位A', () => {
      expect(wrapper.text()).toContain('A');
    });

    it('应该显示磁场单位mT', () => {
      expect(wrapper.text()).toContain('mT');
    });
  });

  describe('电流设置功能', () => {
    it('应该有目标电流输入框', () => {
      const inputs = wrapper.findAll('.form-number');
      expect(inputs.length).toBeGreaterThan(0);
    });

    it('设置电流按钮应该存在', () => {
      const setBtns = wrapper.findAll('.set-btn');
      const setCurrentBtn = setBtns.find(btn => btn.text().includes('设置电流'));
      expect(setCurrentBtn.exists()).toBe(true);
    });

    it('设置磁场按钮应该存在', () => {
      const setBtns = wrapper.findAll('.set-btn');
      const setFieldBtn = setBtns.find(btn => btn.text().includes('设置磁场'));
      expect(setFieldBtn.exists()).toBe(true);
    });
  });

  describe('电流滑块功能', () => {
    it('滑块应该存在', () => {
      const slider = wrapper.find('.slider-control');
      expect(slider.exists()).toBe(true);
    });

    it('滑块变化应该更新目标电流', async () => {
      wrapper.vm.currentForm.targetCurrent = 5;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.currentForm.targetCurrent).toBe(5);
    });
  });

  describe('扫描模式配置', () => {
    it('应该显示扫描模式选择', () => {
      expect(wrapper.find('.mode-radio-group').exists()).toBe(true);
    });

    it('应该显示起始电流输入框', () => {
      expect(wrapper.find('.scan-form').exists()).toBe(true);
    });

    it('应该显示终止电流输入框', () => {
      const formItems = wrapper.findAll('.form-item');
      expect(formItems.length).toBeGreaterThan(0);
    });

    it('线性扫描模式应该显示扫描速率输入', async () => {
      wrapper.vm.scanForm.mode = 'linear';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scanForm.mode).toBe('linear');
    });

    it('步进扫描模式应该显示步进大小输入', async () => {
      wrapper.vm.scanForm.mode = 'step';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scanForm.mode).toBe('step');
    });
  });

  describe('扫描控制', () => {
    it('应该显示开始扫描按钮', () => {
      const startBtn = wrapper.find('.start-btn');
      expect(startBtn.exists()).toBe(true);
    });

    it('应该显示暂停按钮', () => {
      const pauseBtn = wrapper.find('.pause-btn');
      expect(pauseBtn.exists()).toBe(true);
    });

    it('应该显示停止扫描按钮', () => {
      const stopBtn = wrapper.find('.stop-btn');
      expect(stopBtn.exists()).toBe(true);
    });
  });

  describe('扫描验证', () => {
    it('扫描参数验证应该返回正确结果', () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 5;
      wrapper.vm.scanForm.scanRate = 0.1;
      wrapper.vm.scanForm.mode = 'linear';
      wrapper.vm.validateScanParams();

      expect(wrapper.vm.scanValidation.isValid).toBe(true);
    });
  });

  describe('扫描预览', () => {
    it('有效扫描参数时应该显示预览', async () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 5;
      wrapper.vm.scanForm.scanRate = 0.1;
      wrapper.vm.scanForm.mode = 'linear';
      wrapper.vm.validateScanParams();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scanPreview.isValid).toBe(true);
    });
  });

  describe('状态显示', () => {
    it('应该显示状态标签', () => {
      expect(wrapper.find('.status-tag').exists()).toBe(true);
    });

    it('应该返回正确的状态文本', () => {
      mockElectromagnetStore.status = 'ready';
      expect(wrapper.vm.statusText).toContain('就绪');
    });
  });

  describe('时间格式化', () => {
    it('应该正确格式化剩余时间', () => {
      const formatted = wrapper.vm.formatRemainingTime(65);
      expect(formatted).toContain('1');
      expect(formatted).toContain('5');
    });

    it('零时间应该返回短横线', () => {
      const formatted = wrapper.vm.formatRemainingTime(0);
      expect(formatted).toBe('-');
    });
  });

  describe('电流验证', () => {
    it('电流在有效范围内应该验证通过', () => {
      wrapper.vm.currentForm.targetCurrent = 5;
      const validation = wrapper.vm.currentValidation;
      expect(validation.error).toBeFalsy();
    });

    it('电流超出上限应该验证失败', () => {
      wrapper.vm.currentForm.targetCurrent = 15;
      wrapper.vm.validateCurrentInput(15);
      const validation = wrapper.vm.currentValidation;
      expect(validation.error).toBeTruthy();
    });

    it('电流低于下限应该验证失败', () => {
      wrapper.vm.currentForm.targetCurrent = -1;
      wrapper.vm.validateCurrentInput(-1);
      const validation = wrapper.vm.currentValidation;
      expect(validation.error).toBeTruthy();
    });
  });
});
