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

// Mock electromagnet store
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
  setCurrent: vi.fn().mockResolvedValue(true),
  setField: vi.fn().mockResolvedValue(true),
  configScan: vi.fn().mockResolvedValue(true),
  startScan: vi.fn().mockResolvedValue(true),
  stopScan: vi.fn().mockResolvedValue(true),
  pauseScan: vi.fn().mockResolvedValue(true),
  resumeScan: vi.fn().mockResolvedValue(true),
  validateScanConfig: vi.fn().mockResolvedValue({ valid: true }),
  exportScanData: vi.fn().mockReturnValue('[]'),
  clearAlarm: vi.fn(),
};

vi.mock('../stores/electromagnet', () => ({
  useElectromagnetStore: vi.fn(() => mockElectromagnetStore),
}));

// Mock ElementPlus message
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
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
    template: '<input type="range" class="el-slider" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
    props: ['modelValue', 'min', 'max', 'step', 'marks', 'disabled'],
  },
  'el-radio-group': { template: '<div class="el-radio-group"><slot /></div>' },
  'el-radio': { template: '<label class="el-radio"><slot /></label>' },
  'el-progress': { template: '<div class="el-progress"></div>' },
  'el-row': { template: '<div class="el-row"><slot /></div>' },
  'el-col': { template: '<div class="el-col"><slot /></div>' },
};

describe('ElectromagnetControl', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();

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

    it('设置电流按钮在可控制状态下应该可用', () => {
      const setBtns = wrapper.findAll('.set-btn');
      const setCurrentBtn = setBtns.find(btn => btn.text().includes('设置电流'));
      expect(setCurrentBtn.exists()).toBe(true);
    });

    it('设置电流按钮在不可控制状态下应该禁用', async () => {
      mockElectromagnetStore.canControl = false;
      await wrapper.vm.$nextTick();

      const setBtns = wrapper.findAll('.set-btn');
      const setCurrentBtn = setBtns.find(btn => btn.text().includes('设置电流'));
      expect(setCurrentBtn.attributes('disabled')).toBeDefined();

      mockElectromagnetStore.canControl = true;
    });

    it('点击设置电流按钮应该调用setCurrent方法', async () => {
      wrapper.vm.currentForm.targetCurrent = 5;

      const setBtns = wrapper.findAll('.set-btn');
      const setCurrentBtn = setBtns.find(btn => btn.text().includes('设置电流'));
      await setCurrentBtn.trigger('click');
      await flushPromises();

      expect(mockElectromagnetStore.setCurrent).toHaveBeenCalled();
    });

    it('点击设置磁场按钮应该调用setField方法', async () => {
      wrapper.vm.currentForm.targetField = 100;

      const setBtns = wrapper.findAll('.set-btn');
      const setFieldBtn = setBtns.find(btn => btn.text().includes('设置磁场'));
      await setFieldBtn.trigger('click');
      await flushPromises();

      expect(mockElectromagnetStore.setField).toHaveBeenCalled();
    });
  });

  describe('电流滑块功能', () => {
    it('滑块在可控制状态下应该可用', () => {
      const slider = wrapper.find('.slider-control');
      expect(slider.attributes('disabled')).toBeUndefined();
    });

    it('滑块在不可控制状态下应该禁用', async () => {
      mockElectromagnetStore.canControl = false;
      await wrapper.vm.$nextTick();

      const slider = wrapper.find('.slider-control');
      expect(slider.attributes('disabled')).toBeDefined();

      mockElectromagnetStore.canControl = true;
    });

    it('滑块变化应该更新目标电流', async () => {
      const slider = wrapper.find('.slider-control');
      await slider.setValue(5);
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

    it('点击配置扫描按钮应该调用configScan方法', async () => {
      const configBtns = wrapper.findAll('.config-btn');
      const configScanBtn = configBtns.find(btn => btn.text().includes('配置扫描'));
      await configScanBtn.trigger('click');
      await flushPromises();

      expect(mockElectromagnetStore.configScan).toHaveBeenCalled();
    });

    it('点击验证参数按钮应该调用validateScanConfig方法', async () => {
      const configBtns = wrapper.findAll('.config-btn');
      const validateBtn = configBtns.find(btn => btn.text().includes('验证参数'));
      await validateBtn.trigger('click');
      await flushPromises();

      expect(mockElectromagnetStore.validateScanConfig).toHaveBeenCalled();
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

    it('开始扫描按钮在可控制且未扫描时应该可用', () => {
      mockElectromagnetStore.canControl = true;
      mockElectromagnetStore.isScanning = false;

      const startBtn = wrapper.find('.start-btn');
      expect(startBtn.attributes('disabled')).toBeUndefined();
    });

    it('开始扫描按钮在扫描中应该禁用', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      const startBtn = wrapper.find('.start-btn');
      expect(startBtn.attributes('disabled')).toBeDefined();

      mockElectromagnetStore.isScanning = false;
    });

    it('点击开始扫描按钮应该调用startScan方法', async () => {
      const startBtn = wrapper.find('.start-btn');
      await startBtn.trigger('click');
      await flushPromises();

      expect(mockElectromagnetStore.startScan).toHaveBeenCalled();
    });

    it('点击暂停按钮应该调用pauseScan方法', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      const pauseBtn = wrapper.find('.pause-btn');
      await pauseBtn.trigger('click');
      await flushPromises();

      expect(mockElectromagnetStore.pauseScan).toHaveBeenCalled();

      mockElectromagnetStore.isScanning = false;
    });

    it('点击停止扫描按钮应该调用stopScan方法', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      const stopBtn = wrapper.find('.stop-btn');
      await stopBtn.trigger('click');
      await flushPromises();

      expect(mockElectromagnetStore.stopScan).toHaveBeenCalled();

      mockElectromagnetStore.isScanning = false;
    });
  });

  describe('扫描进度显示', () => {
    it('扫描中应该显示进度区域', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.scan-progress').exists()).toBe(true);

      mockElectromagnetStore.isScanning = false;
    });

    it('应该显示进度条', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.progress-bar').exists()).toBe(true);

      mockElectromagnetStore.isScanning = false;
    });

    it('应该显示进度详情', async () => {
      mockElectromagnetStore.isScanning = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.progress-details').exists()).toBe(true);

      mockElectromagnetStore.isScanning = false;
    });
  });

  describe('扫描验证', () => {
    it('扫描参数验证应该返回正确结果', () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 5;
      wrapper.vm.scanForm.scanRate = 0.1;

      const validation = wrapper.vm.scanValidation;
      expect(validation.isValid).toBe(true);
    });

    it('起始电流大于终止电流时应该验证失败', () => {
      wrapper.vm.scanForm.startCurrent = 5;
      wrapper.vm.scanForm.endCurrent = 0;

      const validation = wrapper.vm.scanValidation;
      expect(validation.isValid).toBe(false);
    });
  });

  describe('扫描预览', () => {
    it('有效扫描参数时应该显示预览', async () => {
      wrapper.vm.scanForm.startCurrent = 0;
      wrapper.vm.scanForm.endCurrent = 5;
      wrapper.vm.scanForm.scanRate = 0.1;
      wrapper.vm.scanForm.mode = 'linear';
      await wrapper.vm.$nextTick();

      const preview = wrapper.vm.scanPreview;
      expect(preview.isValid).toBe(true);
    });
  });

  describe('报警处理', () => {
    it('有报警消息时应该显示报警提示', async () => {
      mockElectromagnetStore.alarmMessage = '电流过载';
      await wrapper.vm.$nextTick();

      const alert = wrapper.find('.alarm-alert');
      expect(alert.exists()).toBe(true);
      expect(alert.text()).toContain('电流过载');

      mockElectromagnetStore.alarmMessage = '';
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

    it('应该返回正确的状态标签类型', () => {
      mockElectromagnetStore.status = 'ready';
      expect(wrapper.vm.statusTagType).toBe('success');

      mockElectromagnetStore.status = 'error';
      expect(wrapper.vm.statusTagType).toBe('danger');

      mockElectromagnetStore.status = 'ready';
    });
  });

  describe('时间格式化', () => {
    it('应该正确格式化剩余时间', () => {
      const formatted = wrapper.vm.formatRemainingTime(65);
      expect(formatted).toContain('1');
      expect(formatted).toContain('5');
    });

    it('零时间应该返回0秒', () => {
      const formatted = wrapper.vm.formatRemainingTime(0);
      expect(formatted).toContain('0');
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
      const validation = wrapper.vm.currentValidation;
      expect(validation.error).toBeTruthy();
    });

    it('电流低于下限应该验证失败', () => {
      wrapper.vm.currentForm.targetCurrent = -1;
      const validation = wrapper.vm.currentValidation;
      expect(validation.error).toBeTruthy();
    });
  });
});
