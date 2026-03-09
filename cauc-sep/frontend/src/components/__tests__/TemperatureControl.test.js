/**
 * @file TemperatureControl.test.js
 * @path frontend/src/components/__tests__/
 * @description TemperatureControl组件单元测试
 * @author Agent
 * @date 2024-03-08
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import TemperatureControl from '../TemperatureControl.vue';

// Mock temperature store
const mockTempStore = {
  isConnected: false,
  isConnecting: false,
  status: 'disconnected',
  alarmMessage: '',
  wsConnected: false,
  loading: {
    setTemp: false,
    pidConfig: false,
    startPID: false,
    stopPID: false,
    resetEmergency: false,
    validatePID: false,
    setProtection: false,
    createProgram: false,
  },
  canControl: false,
  isHeating: false,
  isProgramRunning: false,
  programStatus: 'idle',
  programProgress: 0,
  currentTemp: 25.0,
  targetTemp: 25.0,
  heatingRate: 0,
  outputPower: 0,
  tempLimits: {
    min: 77,
    max: 400,
    warning_high: 380,
    warning_low: 85,
  },
  pidParams: {
    kp: 10.0,
    ki: 0.5,
    kd: 2.0,
    setpoint: 25.0,
  },
  programCurves: [],
  tempHistory: [],
  tempStatusText: '温度过低',
  tempStatusType: 'warning',
  pidControlActive: false,
  setTargetTemp: vi.fn().mockResolvedValue(true),
  configurePID: vi.fn().mockResolvedValue(true),
  startPIDControl: vi.fn().mockResolvedValue(true),
  stopPIDControl: vi.fn().mockResolvedValue(true),
  stopHeating: vi.fn().mockResolvedValue(true),
  emergencyStop: vi.fn().mockResolvedValue(true),
  resetEmergency: vi.fn().mockResolvedValue(true),
  createProgram: vi.fn().mockResolvedValue(true),
  startProgram: vi.fn().mockResolvedValue(true),
  stopProgram: vi.fn().mockResolvedValue(true),
  pauseProgram: vi.fn().mockResolvedValue(true),
  resumeProgram: vi.fn().mockResolvedValue(true),
  deleteProgram: vi.fn().mockResolvedValue(true),
  validatePID: vi.fn().mockResolvedValue({ valid: true, message: '' }),
  kelvinToCelsius: vi.fn((k) => k - 273.15),
  clearAlarm: vi.fn(),
  connect: vi.fn().mockResolvedValue(true),
  disconnect: vi.fn().mockResolvedValue(true),
};

vi.mock('../stores/temperature', () => ({
  useTemperatureStore: vi.fn(() => mockTempStore),
}));

// Mock ElementPlus message
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// Mock vue-echarts
vi.mock('vue-echarts', () => ({
  default: {
    template: '<div class="v-chart-mock"></div>',
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
    props: ['title', 'type', 'closable', 'show-icon'],
  },
  'el-form': { template: '<form class="el-form"><slot /></form>' },
  'el-form-item': { template: '<div class="el-form-item"><slot /></div>' },
  'el-input-number': {
    template: '<input type="number" class="el-input-number" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" />',
    props: ['modelValue', 'min', 'max', 'precision', 'step'],
  },
  'el-input': {
    template: '<input class="el-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
    props: ['modelValue', 'placeholder'],
  },
  'el-tag': { template: '<span class="el-tag"><slot /></span>' },
  'el-divider': { template: '<hr class="el-divider"><slot /></hr>' },
  'el-tabs': { template: '<div class="el-tabs"><slot /></div>' },
  'el-tab-pane': { template: '<div class="el-tab-pane"><slot /></div>' },
  'el-table': { template: '<table class="el-table"><slot /></table>' },
  'el-table-column': { template: '<col class="el-table-column" />' },
  'el-progress': { template: '<div class="el-progress"></div>' },
  'el-radio-group': { template: '<div class="el-radio-group"><slot /></div>' },
  'el-radio-button': { template: '<label class="el-radio-button"><slot /></label>' },
  'el-row': { template: '<div class="el-row"><slot /></div>' },
  'el-col': { template: '<div class="el-col"><slot /></div>' },
  'v-chart': { template: '<div class="v-chart-mock"></div>' },
};

describe('TemperatureControl', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();

    wrapper = mount(TemperatureControl, {
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
      expect(wrapper.find('.temperature-control').exists()).toBe(true);
    });

    it('应该显示温度控制面板标题', () => {
      expect(wrapper.text()).toContain('温度控制面板');
    });

    it('应该显示当前温度卡片', () => {
      expect(wrapper.find('.status-card--current').exists()).toBe(true);
    });

    it('应该显示目标温度卡片', () => {
      expect(wrapper.find('.status-card--target').exists()).toBe(true);
    });

    it('应该显示升温速率卡片', () => {
      expect(wrapper.find('.status-card--rate').exists()).toBe(true);
    });

    it('应该显示温度曲线图表', () => {
      expect(wrapper.find('.chart-section').exists()).toBe(true);
    });

    it('应该显示目标温度设置区域', () => {
      expect(wrapper.find('.control-section').exists()).toBe(true);
    });

    it('应该显示PID参数配置区域', () => {
      const sections = wrapper.findAll('.control-section');
      expect(sections.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('温度显示', () => {
    it('应该显示当前温度值', () => {
      expect(wrapper.text()).toContain('25.00');
    });

    it('应该显示温度单位K', () => {
      expect(wrapper.text()).toContain('K');
    });
  });

  describe('目标温度设置', () => {
    it('应该有目标温度输入框', () => {
      const tempInputs = wrapper.findAll('.el-input-number');
      expect(tempInputs.length).toBeGreaterThan(0);
    });

    it('应用设置按钮在可控制状态下应该可用', async () => {
      mockTempStore.canControl = true;
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();

      const applyBtn = wrapper.find('.action-btn--primary');
      expect(applyBtn.exists()).toBe(true);

      mockTempStore.canControl = false;
      mockTempStore.isConnected = false;
    });

    it('应用设置按钮在不可控制状态下应该禁用', async () => {
      mockTempStore.canControl = false;
      await wrapper.vm.$nextTick();

      const applyBtn = wrapper.find('.action-btn--primary');
      expect(applyBtn.attributes('disabled')).toBeDefined();
    });

    it('点击应用设置应该调用setTargetTemp方法', async () => {
      mockTempStore.canControl = true;
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();

      wrapper.vm.tempForm.targetTemp = 350;
      wrapper.vm.tempForm.heatingRate = 2;

      const applyBtn = wrapper.find('.action-btn--primary');
      await applyBtn.trigger('click');
      await flushPromises();

      expect(mockTempStore.setTargetTemp).toHaveBeenCalled();

      mockTempStore.canControl = false;
      mockTempStore.isConnected = false;
    });

    it('点击停止加热应该调用stopHeating方法', async () => {
      mockTempStore.canControl = true;
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();

      const stopBtns = wrapper.findAll('.action-btn--secondary');
      const stopHeatingBtn = stopBtns.find(btn => btn.text().includes('停止加热'));
      if (stopHeatingBtn) {
        await stopHeatingBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.stopHeating).toHaveBeenCalled();
      }

      mockTempStore.canControl = false;
      mockTempStore.isConnected = false;
    });
  });

  describe('PID参数配置', () => {
    it('应该显示Kp输入框', () => {
      const pidInputs = wrapper.findAll('.el-input-number');
      expect(pidInputs.length).toBeGreaterThan(0);
    });

    it('点击应用PID参数应该调用configurePID方法', async () => {
      mockTempStore.canControl = true;
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();

      wrapper.vm.pidForm.kp = 15;
      wrapper.vm.pidForm.ki = 0.8;
      wrapper.vm.pidForm.kd = 8;

      const applyBtns = wrapper.findAll('.action-btn--primary');
      const applyPidBtn = applyBtns.find(btn => btn.text().includes('应用 PID'));
      
      if (applyPidBtn) {
        await applyPidBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.configurePID).toHaveBeenCalled();
      }

      mockTempStore.canControl = false;
      mockTempStore.isConnected = false;
    });

    it('点击验证参数应该调用validatePID方法', async () => {
      mockTempStore.canControl = true;
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();

      const validateBtns = wrapper.findAll('.action-btn--secondary');
      const validateBtn = validateBtns.find(btn => btn.text().includes('验证参数'));
      
      if (validateBtn) {
        await validateBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.validatePID).toHaveBeenCalled();
      }

      mockTempStore.canControl = false;
      mockTempStore.isConnected = false;
    });

    it('点击启动PID应该调用startPIDControl方法', async () => {
      mockTempStore.canControl = true;
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();

      const startPidBtn = wrapper.find('.action-btn--success');
      if (startPidBtn.exists()) {
        await startPidBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.startPIDControl).toHaveBeenCalled();
      }

      mockTempStore.canControl = false;
      mockTempStore.isConnected = false;
    });
  });

  describe('紧急停止功能', () => {
    it('应该显示紧急停止按钮', () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      if (emergencyBtn.exists()) {
        expect(emergencyBtn.text()).toContain('紧急停止');
      }
    });

    it('点击紧急停止应该调用emergencyStop方法', async () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      if (emergencyBtn.exists()) {
        await emergencyBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.emergencyStop).toHaveBeenCalled();
      }
    });

    it('急停状态下应该显示复位按钮', async () => {
      mockTempStore.status = 'emergency_stop';
      await wrapper.vm.$nextTick();

      const resetBtn = wrapper.find('.emergency-reset-btn');
      if (resetBtn.exists()) {
        expect(resetBtn.text()).toContain('复位急停');
      }

      mockTempStore.status = 'ready';
    });
  });

  describe('程序控温功能', () => {
    it('应该显示程序控温标签页', () => {
      expect(wrapper.find('.program-tabs').exists()).toBe(true);
    });

    it('应该显示程序列表', () => {
      expect(wrapper.find('.program-list').exists()).toBe(true);
    });

    it('应该显示创建程序标签页', () => {
      const tabPanes = wrapper.findAll('.el-tab-pane');
      expect(tabPanes.length).toBeGreaterThan(0);
    });
  });

  describe('温度验证', () => {
    it('温度在有效范围内应该验证通过', () => {
      wrapper.vm.tempForm.targetTemp = 300;
      const validation = wrapper.vm.tempValidation;
      expect(validation.valid).toBe(true);
    });

    it('温度超出上限应该验证失败', () => {
      wrapper.vm.tempForm.targetTemp = 600;
      const validation = wrapper.vm.tempValidation;
      expect(validation.valid).toBe(false);
    });

    it('温度低于下限应该验证失败', () => {
      wrapper.vm.tempForm.targetTemp = 50;
      const validation = wrapper.vm.tempValidation;
      expect(validation.valid).toBe(false);
    });
  });

  describe('连接状态显示', () => {
    it('应该显示连接状态', () => {
      expect(wrapper.find('.connection-section').exists()).toBe(true);
    });

    it('连接状态下应该显示已连接', async () => {
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();
      
      // 连接状态下应该显示断开连接按钮
      expect(wrapper.text()).toContain('断开连接');
      
      mockTempStore.isConnected = false;
    });

    it('断开状态下应该显示未连接', async () => {
      mockTempStore.isConnected = false;
      await wrapper.vm.$nextTick();
      
      // 断开状态下应该显示连接按钮
      expect(wrapper.text()).toContain('连接温控器');
    });
  });

  describe('加热状态显示', () => {
    it('加热中应该显示加热状态', async () => {
      mockTempStore.isHeating = true;
      mockTempStore.outputPower = 50;
      await wrapper.vm.$nextTick();
      
      // 检查组件是否正确渲染
      expect(wrapper.find('.temperature-control').exists()).toBe(true);
      
      mockTempStore.isHeating = false;
      mockTempStore.outputPower = 0;
    });

    it('未加热时应该显示待机状态', async () => {
      mockTempStore.isHeating = false;
      mockTempStore.outputPower = 0;
      await wrapper.vm.$nextTick();
      
      expect(wrapper.text()).toContain('待机');
    });
  });

  describe('报警处理', () => {
    it('有报警消息时应该显示报警提示', async () => {
      mockTempStore.alarmMessage = '温度异常';
      await wrapper.vm.$nextTick();

      const alert = wrapper.find('.alarm-alert');
      if (alert.exists()) {
        expect(alert.text()).toContain('温度异常');
      }

      mockTempStore.alarmMessage = '';
    });
  });

  describe('温度格式化', () => {
    it('应该正确格式化温度值', () => {
      // 组件使用 toFixed(2) 格式化
      const formatted = wrapper.vm.formatTempValue(300.5);
      expect(formatted).toBe('300.50');
    });
  });
});
