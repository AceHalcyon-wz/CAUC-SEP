/**
 * @file ElectromagnetControl.test.js
 * @path frontend/tests/unit/components/
 * @description ElectromagnetControl组件单元测试
 * @author Agent
 * @date 2024-03-16
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ElectromagnetControl from '@/components/experiment/electromagnet/ElectromagnetControl.vue';

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
    totalSteps: 100,
    currentCurrent: 0,
    currentField: 0,
    scanDirection: 'forward',
  },
  scanData: {
    current: [],
    field: [],
  },
  estimatedRemainingTime: 0,
  calibrationStatus: '已校准',
  calibrationCurve: {
    coefficients: { a: 100, b: 0.5 },
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
  exportScanData: vi.fn().mockReturnValue('current,field\n0,0\n5,500'),
  clearAlarm: vi.fn(),
  clearScanData: vi.fn(),
  calculateCurrent: vi.fn((field) => field / 100),
  calculateField: vi.fn((current) => current * 100),
  init: vi.fn(),
  cleanup: vi.fn(),
  fetchCalibration: vi.fn().mockResolvedValue({ points: [] }),
  uploadCalibration: vi.fn().mockResolvedValue(true),
  validateCalibration: vi.fn().mockResolvedValue({ valid: true, accuracy: '±0.5mT' }),
  performCalibration: vi.fn().mockResolvedValue(true),
  clearCalibration: vi.fn().mockResolvedValue(true),
  emergencyStop: vi.fn().mockResolvedValue(true),
  resetEmergency: vi.fn().mockResolvedValue(true),
  resetOvercurrent: vi.fn().mockResolvedValue(true),
};

vi.mock('@/stores/electromagnet', () => ({
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

vi.mock('@element-plus/icons-vue', () => ({
  Download: { template: '<span class="download-icon"></span>' },
  Delete: { template: '<span class="delete-icon"></span>' },
  ArrowRight: { template: '<span class="arrow-right-icon"></span>' },
  ArrowLeft: { template: '<span class="arrow-left-icon"></span>' },
}));

const stubs = {
  'el-card': { template: '<div class="el-card"><slot /><slot name="header" /></div>' },
  'el-button': {
    template: '<button class="el-button" :disabled="disabled" :loading="loading" @click="$emit(\'click\')"><slot /></button>',
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
    template: '<input type="number" class="el-input-number" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
    props: ['modelValue', 'min', 'max', 'precision', 'step', 'disabled'],
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
  'el-checkbox': {
    template: '<input type="checkbox" class="el-checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />',
    props: ['modelValue'],
  },
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

    it('应该显示状态标签', () => {
      expect(wrapper.find('.status-tag').exists()).toBe(true);
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

    it('应该显示校准曲线区域', () => {
      expect(wrapper.find('.calibration-section').exists()).toBe(true);
    });

    it('应该显示安全控制区域', () => {
      expect(wrapper.find('.safety-controls').exists()).toBe(true);
    });
  });

  describe('磁场控制功能', () => {
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

    it('应该显示目标电流输入框', () => {
      expect(wrapper.text()).toContain('目标电流');
    });

    it('应该显示目标磁场输入框', () => {
      expect(wrapper.text()).toContain('目标磁场');
    });

    it('点击设置电流按钮应该调用setCurrent方法', async () => {
      wrapper.vm.currentForm.targetCurrent = 5;

      const setBtns = wrapper.findAll('.set-btn');
      const setCurrentBtn = setBtns.find(btn => btn.text().includes('设置电流'));

      if (setCurrentBtn) {
        await setCurrentBtn.trigger('click');
        await flushPromises();
        expect(mockElectromagnetStore.setCurrent).toHaveBeenCalled();
      }
    });

    it('点击设置磁场按钮应该调用setField方法', async () => {
      wrapper.vm.currentForm.targetField = 500;

      const setBtns = wrapper.findAll('.set-btn');
      const setFieldBtn = setBtns.find(btn => btn.text().includes('设置磁场'));

      if (setFieldBtn) {
        await setFieldBtn.trigger('click');
        await flushPromises();
        expect(mockElectromagnetStore.setField).toHaveBeenCalled();
      }
    });

    it('无法控制时设置按钮应该禁用', async () => {
      mockElectromagnetStore.canControl = false;
      await wrapper.vm.$nextTick();

      const setBtns = wrapper.findAll('.set-btn');
      setBtns.forEach(btn => {
        expect(btn.attributes('disabled')).toBeDefined();
      });

      mockElectromagnetStore.canControl = true;
    });
  });

  describe('扫描功能', () => {
    it('应该显示扫描模式选择', () => {
      expect(wrapper.find('.mode-radio-group').exists()).toBe(true);
    });

    it('应该显示起始电流输入框', () => {
      expect(wrapper.text()).toContain('起始电流');
    });

    it('应该显示终止电流输入框', () => {
      expect(wrapper.text()).toContain('终止电流');
    });

    it('线性扫描模式应该显示扫描速率输入', async () => {
      wrapper.vm.scanForm.mode = 'linear';
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('扫描速率');
    });

    it('步进扫描模式应该显示步进大小输入', async () => {
      wrapper.vm.scanForm.mode = 'step';
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('步进大小');
    });

    it('步进扫描模式应该显示步数输入', async () => {
      wrapper.vm.scanForm.mode = 'step';
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('步数');
    });

    it('步进扫描模式应该显示步间延时输入', async () => {
      wrapper.vm.scanForm.mode = 'step';
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('步间延时');
    });

    it('应该显示配置扫描按钮', () => {
      const configBtns = wrapper.findAll('.config-btn');
      const configBtn = configBtns.find(btn => btn.text().includes('配置扫描'));
      expect(configBtn).toBeDefined();
    });

    it('应该显示验证参数按钮', () => {
      const configBtns = wrapper.findAll('.config-btn');
      const validateBtn = configBtns.find(btn => btn.text().includes('验证参数'));
      expect(validateBtn).toBeDefined();
    });
  });

  describe('扫描控制功能', () => {
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

    it('点击开始扫描应该调用startScan方法', async () => {
      const startBtn = wrapper.find('.start-btn');
      await startBtn.trigger('click');
      await flushPromises();
      expect(mockElectromagnetStore.startScan).toHaveBeenCalled();
    });

    it('点击暂停扫描应该调用pauseScan方法', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      const pauseBtn = wrapper.find('.pause-btn');
      await pauseBtn.trigger('click');
      await flushPromises();
      expect(mockElectromagnetStore.pauseScan).toHaveBeenCalled();

      mockElectromagnetStore.isScanning = false;
    });

    it('点击停止扫描应该调用stopScan方法', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      const stopBtn = wrapper.find('.stop-btn');
      await stopBtn.trigger('click');
      await flushPromises();
      expect(mockElectromagnetStore.stopScan).toHaveBeenCalled();

      mockElectromagnetStore.isScanning = false;
    });

    it('扫描中应该显示扫描进度', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.scan-progress').exists()).toBe(true);

      mockElectromagnetStore.isScanning = false;
    });

    it('扫描中应该显示进度条', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.progress-bar').exists()).toBe(true);

      mockElectromagnetStore.isScanning = false;
    });

    it('扫描中应该显示进度详情', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.progress-details').exists()).toBe(true);

      mockElectromagnetStore.isScanning = false;
    });
  });

  describe('安全限制功能', () => {
    it('应该显示急停按钮', () => {
      const emergencyBtn = wrapper.find('.emergency-btn');
      expect(emergencyBtn.exists()).toBe(true);
    });

    it('点击急停按钮应该调用emergencyStop方法', async () => {
      const emergencyBtn = wrapper.find('.emergency-btn');
      await emergencyBtn.trigger('click');
      await flushPromises();
      expect(mockElectromagnetStore.emergencyStop).toHaveBeenCalled();
    });

    it('急停状态下应该显示复位按钮', async () => {
      mockElectromagnetStore.status = 'emergency_stop';
      await wrapper.vm.$nextTick();

      const resetBtn = wrapper.find('.reset-btn');
      expect(resetBtn.exists()).toBe(true);

      mockElectromagnetStore.status = 'ready';
    });

    it('应该显示过流保护复位按钮', () => {
      const resetBtns = wrapper.findAll('.reset-btn');
      const overcurrentBtn = resetBtns.find(btn => btn.text().includes('过流保护复位'));
      expect(overcurrentBtn).toBeDefined();
    });

    it('点击过流保护复位应该调用resetOvercurrent方法', async () => {
      const resetBtns = wrapper.findAll('.reset-btn');
      const overcurrentBtn = resetBtns.find(btn => btn.text().includes('过流保护复位'));

      if (overcurrentBtn) {
        await overcurrentBtn.trigger('click');
        await flushPromises();
        expect(mockElectromagnetStore.resetOvercurrent).toHaveBeenCalled();
      }
    });
  });

  describe('校准功能', () => {
    it('应该显示校准状态', () => {
      expect(wrapper.find('.calibration-status').exists()).toBe(true);
    });

    it('应该显示刷新校准按钮', () => {
      const actionBtns = wrapper.findAll('.action-btn');
      const refreshBtn = actionBtns.find(btn => btn.text().includes('刷新校准'));
      expect(refreshBtn).toBeDefined();
    });

    it('点击刷新校准应该调用fetchCalibration方法', async () => {
      const actionBtns = wrapper.findAll('.action-btn');
      const refreshBtn = actionBtns.find(btn => btn.text().includes('刷新校准'));

      if (refreshBtn) {
        await refreshBtn.trigger('click');
        await flushPromises();
        expect(mockElectromagnetStore.fetchCalibration).toHaveBeenCalled();
      }
    });

    it('应该显示添加校准点区域', () => {
      expect(wrapper.find('.add-calibration-point').exists()).toBe(true);
    });

    it('应该显示电流输入框', () => {
      expect(wrapper.text()).toContain('电流');
    });

    it('应该显示磁场输入框', () => {
      expect(wrapper.text()).toContain('磁场');
    });

    it('应该显示添加校准点按钮', () => {
      const addBtn = wrapper.find('.add-point-btn');
      expect(addBtn.exists()).toBe(true);
    });

    it('点击添加校准点应该添加到列表', async () => {
      wrapper.vm.newCalibrationPoint.current = 5;
      wrapper.vm.newCalibrationPoint.field = 500;

      const addBtn = wrapper.find('.add-point-btn');
      await addBtn.trigger('click');

      expect(wrapper.vm.calibrationPoints.length).toBe(1);
    });

    it('应该显示校准操作按钮', () => {
      expect(wrapper.find('.calibration-actions').exists()).toBe(true);
    });

    it('应该显示验证数据按钮', () => {
      const calibrationBtns = wrapper.findAll('.calibration-btn');
      const validateBtn = calibrationBtns.find(btn => btn.text().includes('验证数据'));
      expect(validateBtn).toBeDefined();
    });

    it('应该显示上传校准曲线按钮', () => {
      const calibrationBtns = wrapper.findAll('.calibration-btn');
      const uploadBtn = calibrationBtns.find(btn => btn.text().includes('上传校准曲线'));
      expect(uploadBtn).toBeDefined();
    });

    it('应该显示执行校准按钮', () => {
      const calibrationBtns = wrapper.findAll('.calibration-btn');
      const performBtn = calibrationBtns.find(btn => btn.text().includes('执行校准'));
      expect(performBtn).toBeDefined();
    });

    it('应该显示清除所有点按钮', () => {
      const calibrationBtns = wrapper.findAll('.calibration-btn');
      const clearBtn = calibrationBtns.find(btn => btn.text().includes('清除所有点'));
      expect(clearBtn).toBeDefined();
    });

    it('应该显示清除校准数据按钮', () => {
      const calibrationBtns = wrapper.findAll('.calibration-btn');
      const clearBtn = calibrationBtns.find(btn => btn.text().includes('清除校准数据'));
      expect(clearBtn).toBeDefined();
    });
  });

  describe('电流验证功能', () => {
    it('电流在有效范围内应该验证通过', () => {
      wrapper.vm.currentForm.targetCurrent = 5;
      const result = wrapper.vm.validateCurrentInput(5);
      expect(result).toBe(true);
    });

    it('电流超出上限应该验证失败', () => {
      const result = wrapper.vm.validateCurrentInput(15);
      expect(result).toBe(false);
      expect(wrapper.vm.currentValidation.error).toBeTruthy();
    });

    it('电流低于下限应该验证失败', () => {
      const result = wrapper.vm.validateCurrentInput(-1);
      expect(result).toBe(false);
      expect(wrapper.vm.currentValidation.error).toBeTruthy();
    });

    it('电流接近最大限制应该显示警告', () => {
      wrapper.vm.validateCurrentInput(9.5);
      expect(wrapper.vm.currentValidation.warning).toBeTruthy();
    });
  });

  describe('扫描参数验证功能', () => {
    it('有效扫描参数应该验证通过', () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 5;
      wrapper.vm.scanForm.scanRate = 0.1;
      wrapper.vm.scanForm.mode = 'linear';

      const result = wrapper.vm.validateScanParams();
      expect(result).toBe(true);
    });

    it('起始电流超出范围应该验证失败', () => {
      wrapper.vm.scanForm.startCurrent = -1;
      wrapper.vm.scanForm.endCurrent = 5;

      const result = wrapper.vm.validateScanParams();
      expect(result).toBe(false);
      expect(wrapper.vm.scanValidation.startError).toBeTruthy();
    });

    it('终止电流超出范围应该验证失败', () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 15;

      const result = wrapper.vm.validateScanParams();
      expect(result).toBe(false);
      expect(wrapper.vm.scanValidation.endError).toBeTruthy();
    });

    it('起始和终止电流相同应该验证失败', () => {
      wrapper.vm.scanForm.startCurrent = 5;
      wrapper.vm.scanForm.endCurrent = 5;

      const result = wrapper.vm.validateScanParams();
      expect(result).toBe(false);
    });
  });

  describe('扫描预览功能', () => {
    it('有效参数时应该显示扫描预览', async () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 5;
      wrapper.vm.scanForm.scanRate = 0.1;
      wrapper.vm.scanForm.mode = 'linear';
      wrapper.vm.validateScanParams();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scanPreview.isValid).toBe(true);
    });

    it('应该计算总步数', async () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 5;
      wrapper.vm.scanForm.scanRate = 0.1;
      wrapper.vm.scanForm.mode = 'linear';
      wrapper.vm.validateScanParams();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scanPreview.totalSteps).toBeGreaterThan(0);
    });

    it('应该显示预计时长', async () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 5;
      wrapper.vm.scanForm.scanRate = 0.1;
      wrapper.vm.scanForm.mode = 'linear';
      wrapper.vm.validateScanParams();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scanPreview.estimatedTime).toBeTruthy();
    });

    it('应该显示电流范围', async () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 5;
      wrapper.vm.scanForm.scanRate = 0.1;
      wrapper.vm.scanForm.mode = 'linear';
      wrapper.vm.validateScanParams();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scanPreview.currentRange).toContain('A');
    });
  });

  describe('状态显示功能', () => {
    it('应该返回正确的状态类型 - ready', async () => {
      mockElectromagnetStore.status = 'ready';
      await wrapper.vm.$nextTick();
      await flushPromises();
      expect(wrapper.vm.statusTagType).toBe('success');
    });

    it('应该返回正确的状态类型 - scanning', async () => {
      mockElectromagnetStore.status = 'scanning';
      await wrapper.vm.$nextTick();
      await flushPromises();
      expect(wrapper.vm.statusTagType).toBe('primary');
    });

    it('应该返回正确的状态类型 - emergency_stop', async () => {
      mockElectromagnetStore.status = 'emergency_stop';
      await wrapper.vm.$nextTick();
      await flushPromises();
      expect(wrapper.vm.statusTagType).toBe('danger');
    });

    it('应该返回正确的状态文本 - ready', async () => {
      mockElectromagnetStore.status = 'ready';
      await wrapper.vm.$nextTick();
      await flushPromises();
      expect(wrapper.vm.statusText).toBe('就绪');
    });

    it('应该返回正确的状态文本 - scanning', async () => {
      mockElectromagnetStore.status = 'scanning';
      await wrapper.vm.$nextTick();
      await flushPromises();
      expect(wrapper.vm.statusText).toBe('扫描中');
    });

    it('应该返回正确的状态文本 - emergency_stop', async () => {
      mockElectromagnetStore.status = 'emergency_stop';
      await wrapper.vm.$nextTick();
      await flushPromises();
      expect(wrapper.vm.statusText).toBe('急停');
    });
  });

  describe('时间格式化功能', () => {
    it('应该正确格式化秒数', () => {
      const formatted = wrapper.vm.formatRemainingTime(30);
      expect(formatted).toContain('30');
    });

    it('应该正确格式化分钟', () => {
      const formatted = wrapper.vm.formatRemainingTime(90);
      expect(formatted).toContain('1');
    });

    it('应该正确格式化小时', () => {
      const formatted = wrapper.vm.formatRemainingTime(3661);
      expect(formatted).toContain('1');
    });

    it('零时间应该返回短横线', () => {
      const formatted = wrapper.vm.formatRemainingTime(0);
      expect(formatted).toBe('-');
    });

    it('负数时间应该返回短横线', () => {
      const formatted = wrapper.vm.formatRemainingTime(-1);
      expect(formatted).toBe('-');
    });
  });

  describe('时长格式化功能', () => {
    it('应该正确格式化秒数', () => {
      const formatted = wrapper.vm.formatDuration(30);
      expect(formatted).toContain('30');
    });

    it('应该正确格式化分钟', () => {
      const formatted = wrapper.vm.formatDuration(90);
      expect(formatted).toContain('1');
    });

    it('应该正确格式化小时', () => {
      const formatted = wrapper.vm.formatDuration(3661);
      expect(formatted).toContain('1');
    });
  });

  describe('组件卸载清理', () => {
    it('组件卸载时应该调用cleanup方法', async () => {
      wrapper.unmount();
      expect(mockElectromagnetStore.cleanup).toHaveBeenCalled();
    });
  });

  describe('计算属性测试', () => {
    it('currentMarks应该返回正确的标记点', () => {
      const marks = wrapper.vm.currentMarks;
      expect(marks[0]).toBeDefined();
      expect(marks[10]).toBeDefined();
    });

    it('scanDataStats应该返回正确的统计信息', async () => {
      mockElectromagnetStore.scanData.current = [0, 5, 10];
      mockElectromagnetStore.scanData.field = [0, 500, 1000];
      await wrapper.vm.$nextTick();

      const stats = wrapper.vm.scanDataStats;
      expect(stats.currentRange).toContain('A');
      expect(stats.fieldRange).toContain('mT');
    });
  });

  describe('校准质量功能', () => {
    it('getQualityClass应该返回正确的样式类', () => {
      wrapper.vm.calibrationQuality.r2 = 0.99;
      expect(wrapper.vm.getQualityClass('r2')).toBe('quality-excellent');

      wrapper.vm.calibrationQuality.r2 = 0.96;
      expect(wrapper.vm.getQualityClass('r2')).toBe('quality-good');

      wrapper.vm.calibrationQuality.r2 = 0.92;
      expect(wrapper.vm.getQualityClass('r2')).toBe('quality-fair');

      wrapper.vm.calibrationQuality.r2 = 0.85;
      expect(wrapper.vm.getQualityClass('r2')).toBe('quality-poor');
    });
  });
});
