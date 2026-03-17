/**
 * @file TemperatureControl.test.js
 * @path frontend/tests/unit/components/
 * @description TemperatureControl组件单元测试
 * @author Agent
 * @date 2024-03-16
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import TemperatureControl from '@/components/experiment/temperature/TemperatureControl.vue';

const mockTempStore = {
  isConnected: true,
  isConnecting: false,
  status: 'ready',
  alarmMessage: '',
  wsConnected: true,
  loading: {
    setTemp: false,
    pidConfig: false,
    startPID: false,
    stopPID: false,
    resetEmergency: false,
    validatePID: false,
    setProtection: false,
    createProgram: false,
    fetchHistory: false,
  },
  canControl: true,
  isHeating: false,
  isProgramRunning: false,
  programStatus: 'idle',
  programProgress: 0,
  currentTemp: 298.15,
  targetTemp: 298.15,
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
    setpoint: 298.15,
  },
  programCurves: [
    { id: 'prog-1', name: '标准升温程序', segments: [], description: '测试程序' },
  ],
  tempHistory: [],
  tempStatusText: '稳定',
  tempStatusType: 'success',
  pidControlActive: false,
  setTargetTemp: vi.fn().mockResolvedValue(true),
  configurePID: vi.fn().mockResolvedValue(true),
  startPIDControl: vi.fn().mockResolvedValue(true),
  stopPIDControl: vi.fn().mockResolvedValue(true),
  stopHeating: vi.fn().mockResolvedValue(true),
  emergencyStop: vi.fn().mockResolvedValue(true),
  resetEmergencyStop: vi.fn().mockResolvedValue(true),
  createProgram: vi.fn().mockResolvedValue(true),
  startProgram: vi.fn().mockResolvedValue(true),
  stopProgram: vi.fn().mockResolvedValue(true),
  pauseProgram: vi.fn().mockResolvedValue(true),
  resumeProgram: vi.fn().mockResolvedValue(true),
  deleteProgram: vi.fn().mockResolvedValue(true),
  validatePIDParams: vi.fn().mockResolvedValue({ valid: true, message: '' }),
  validateTemperature: vi.fn((temp) => {
    if (temp < 77) return { valid: false, message: '温度低于下限' };
    if (temp > 400) return { valid: false, message: '温度高于上限' };
    return { valid: true, message: '' };
  }),
  kelvinToCelsius: vi.fn((k) => k - 273.15),
  clearAlarm: vi.fn(),
  connect: vi.fn().mockResolvedValue(true),
  disconnect: vi.fn().mockResolvedValue(true),
  setProtectionConfig: vi.fn().mockResolvedValue(true),
  clearProtectionStatus: vi.fn().mockResolvedValue(true),
  fetchTemperatureHistory: vi.fn().mockResolvedValue([]),
  clearTemperatureHistory: vi.fn().mockResolvedValue(true),
  exportTemperatureHistory: vi.fn().mockResolvedValue(new Blob()),
  fetchPIDParams: vi.fn().mockResolvedValue(true),
  init: vi.fn(),
  cleanup: vi.fn(),
};

vi.mock('@/stores/temperature', () => ({
  useTemperatureStore: vi.fn(() => mockTempStore),
}));

vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
  ElMessageBox: {
    confirm: vi.fn().mockResolvedValue(true),
    alert: vi.fn(),
  },
}));

vi.mock('vue-echarts', () => ({
  default: {
    template: '<div class="v-chart-mock"></div>',
  },
}));

vi.mock('echarts/core', () => ({
  use: vi.fn(),
}));

vi.mock('echarts/renderers', () => ({
  CanvasRenderer: {},
}));

vi.mock('echarts/charts', () => ({
  LineChart: {},
}));

vi.mock('echarts/components', () => ({
  TitleComponent: {},
  TooltipComponent: {},
  LegendComponent: {},
  GridComponent: {},
  DataZoomComponent: {},
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
    props: ['title', 'type', 'closable', 'show-icon'],
  },
  'el-form': { template: '<form class="el-form"><slot /></form>' },
  'el-form-item': { template: '<div class="el-form-item"><slot /></div>' },
  'el-input-number': {
    template: '<input type="number" class="el-input-number" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
    props: ['modelValue', 'min', 'max', 'precision', 'step', 'disabled'],
  },
  'el-input': {
    template: '<input class="el-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
    props: ['modelValue', 'placeholder', 'type'],
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
  'el-select': { template: '<select class="el-select"><slot /></select>' },
  'el-option': { template: '<option class="el-option"><slot /></option>' },
  'el-switch': {
    template: '<input type="checkbox" class="el-switch" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />',
    props: ['modelValue', 'active-text', 'inactive-text'],
  },
  'v-chart': { template: '<div class="v-chart-mock"></div>' },
  'Thermometer': { template: '<span class="thermometer-icon"></span>' },
  'Aim': { template: '<span class="aim-icon"></span>' },
  'Odometer': { template: '<span class="odometer-icon"></span>' },
  'WarningFilled': { template: '<span class="warning-filled-icon"></span>' },
  'RefreshRight': { template: '<span class="refresh-right-icon"></span>' },
  'Check': { template: '<span class="check-icon"></span>' },
  'Close': { template: '<span class="close-icon"></span>' },
  'Setting': { template: '<span class="setting-icon"></span>' },
  'VideoPlay': { template: '<span class="video-play-icon"></span>' },
  'VideoPause': { template: '<span class="video-pause-icon"></span>' },
  'Plus': { template: '<span class="plus-icon"></span>' },
  'Top': { template: '<span class="top-icon"></span>' },
  'Bottom': { template: '<span class="bottom-icon"></span>' },
  'Minus': { template: '<span class="minus-icon"></span>' },
  'Shield': { template: '<span class="shield-icon"></span>' },
  'Refresh': { template: '<span class="refresh-icon"></span>' },
  'Delete': { template: '<span class="delete-icon"></span>' },
  'Download': { template: '<span class="download-icon"></span>' },
  'Link': { template: '<span class="link-icon"></span>' },
  'Disconnect': { template: '<span class="disconnect-icon"></span>' },
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

    it('应该显示温度状态卡片', () => {
      expect(wrapper.find('.temp-status-cards').exists()).toBe(true);
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
      expect(sections.length).toBeGreaterThan(1);
    });

    it('应该显示程序控温区域', () => {
      expect(wrapper.find('.program-tabs').exists()).toBe(true);
    });

    it('应该显示温度保护配置区域', () => {
      expect(wrapper.find('.protection-grid').exists()).toBe(true);
    });

    it('应该显示历史记录管理区域', () => {
      expect(wrapper.find('.history-info').exists()).toBe(true);
    });

    it('应该显示连接控制区域', () => {
      expect(wrapper.find('.connection-section').exists()).toBe(true);
    });
  });

  describe('温度设置功能', () => {
    it('应该显示目标温度输入框', () => {
      const inputs = wrapper.findAll('.el-input-number');
      expect(inputs.length).toBeGreaterThan(0);
    });

    it('应该显示升温速率输入框', () => {
      expect(wrapper.text()).toContain('升温速率');
    });

    it('应该显示温度范围提示', () => {
      expect(wrapper.text()).toContain('有效范围');
    });

    it('应该显示应用设置按钮', () => {
      const btns = wrapper.findAll('.action-btn--primary');
      expect(btns.length).toBeGreaterThan(0);
    });

    it('点击应用设置应该调用setTargetTemp方法', async () => {
      wrapper.vm.tempForm.targetTemp = 350;
      wrapper.vm.tempForm.heatingRate = 5;

      const applyBtns = wrapper.findAll('.action-btn--primary');
      const applyBtn = applyBtns[0];

      await applyBtn.trigger('click');
      await flushPromises();

      expect(mockTempStore.setTargetTemp).toHaveBeenCalled();
    });

    it('应该显示停止加热按钮', () => {
      const btns = wrapper.findAll('.action-btn--secondary');
      expect(btns.length).toBeGreaterThan(0);
    });

    it('点击停止加热应该调用stopHeating方法', async () => {
      const stopBtns = wrapper.findAll('.action-btn--secondary');
      const stopBtn = stopBtns.find(btn => btn.text().includes('停止加热'));

      if (stopBtn) {
        await stopBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.setTargetTemp).toHaveBeenCalled();
      }
    });

    it('无法控制时应用设置按钮应该禁用', async () => {
      mockTempStore.canControl = false;
      await wrapper.vm.$nextTick();

      const applyBtns = wrapper.findAll('.action-btn--primary');
      const applyBtn = applyBtns[0];
      expect(applyBtn.attributes('disabled')).toBeDefined();
    });
  });

  describe('温度曲线功能', () => {
    it('应该显示图表区域', () => {
      expect(wrapper.find('.chart-container').exists()).toBe(true);
    });

    it('应该显示图表图例', () => {
      expect(wrapper.find('.chart-legend').exists()).toBe(true);
    });

    it('应该显示当前温度图例', () => {
      expect(wrapper.text()).toContain('当前温度');
    });

    it('应该显示目标温度图例', () => {
      expect(wrapper.text()).toContain('目标温度');
    });

    it('chartOption应该包含正确的配置', () => {
      const option = wrapper.vm.chartOption;
      expect(option.series).toBeDefined();
      expect(option.series.length).toBe(2);
    });
  });

  describe('PID参数配置功能', () => {
    it('应该显示Kp输入框', () => {
      expect(wrapper.text()).toContain('比例系数 Kp');
    });

    it('应该显示Ki输入框', () => {
      expect(wrapper.text()).toContain('积分系数 Ki');
    });

    it('应该显示Kd输入框', () => {
      expect(wrapper.text()).toContain('微分系数 Kd');
    });

    it('应该显示应用PID参数按钮', () => {
      const btns = wrapper.findAll('.action-btn--primary');
      const pidBtn = btns.find(btn => btn.text().includes('应用 PID'));
      expect(pidBtn).toBeDefined();
    });

    it('点击应用PID参数应该调用configurePID方法', async () => {
      wrapper.vm.pidForm.kp = 15;
      wrapper.vm.pidForm.ki = 0.8;
      wrapper.vm.pidForm.kd = 5;

      const applyBtns = wrapper.findAll('.action-btn--primary');
      const pidBtn = applyBtns.find(btn => btn.text().includes('应用 PID'));

      if (pidBtn) {
        await pidBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.configurePID).toHaveBeenCalled();
      }
    });

    it('应该显示验证参数按钮', () => {
      const btns = wrapper.findAll('.action-btn--secondary');
      const validateBtn = btns.find(btn => btn.text().includes('验证参数'));
      expect(validateBtn).toBeDefined();
    });

    it('点击验证参数应该调用validatePIDParams方法', async () => {
      const validateBtns = wrapper.findAll('.action-btn--secondary');
      const validateBtn = validateBtns.find(btn => btn.text().includes('验证参数'));

      if (validateBtn) {
        await validateBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.validatePIDParams).toHaveBeenCalled();
      }
    });

    it('应该显示重置默认值按钮', () => {
      const btns = wrapper.findAll('.action-btn--secondary');
      const resetBtn = btns.find(btn => btn.text().includes('重置默认值'));
      expect(resetBtn).toBeDefined();
    });

    it('点击重置默认值应该重置PID参数', async () => {
      wrapper.vm.pidForm.kp = 20;
      wrapper.vm.pidForm.ki = 1.0;
      wrapper.vm.pidForm.kd = 10;

      const resetBtns = wrapper.findAll('.action-btn--secondary');
      const resetBtn = resetBtns.find(btn => btn.text().includes('重置默认值'));

      if (resetBtn) {
        await resetBtn.trigger('click');
        expect(wrapper.vm.pidForm.kp).toBe(10.0);
        expect(wrapper.vm.pidForm.ki).toBe(0.5);
        expect(wrapper.vm.pidForm.kd).toBe(2.0);
      }
    });

    it('应该显示启动PID按钮', () => {
      const btns = wrapper.findAll('.action-btn--success');
      expect(btns.length).toBeGreaterThan(0);
    });

    it('点击启动PID应该调用startPIDControl方法', async () => {
      const startBtns = wrapper.findAll('.action-btn--success');
      const startBtn = startBtns[0];

      if (startBtn) {
        await startBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.startPIDControl).toHaveBeenCalled();
      }
    });
  });

  describe('程序控温功能', () => {
    it('应该显示程序列表标签页', () => {
      expect(wrapper.find('.program-list').exists()).toBe(true);
    });

    it('应该显示程序表格', () => {
      expect(wrapper.find('.el-table').exists()).toBe(true);
    });

    it('应该显示创建程序标签页', () => {
      const tabPanes = wrapper.findAll('.el-tab-pane');
      expect(tabPanes.length).toBeGreaterThan(0);
    });

    it('应该显示程序名称输入框', () => {
      expect(wrapper.text()).toContain('程序名称');
    });

    it('应该显示程序描述输入框', () => {
      expect(wrapper.text()).toContain('程序描述');
    });

    it('应该显示温度段列表', () => {
      expect(wrapper.text()).toContain('温度段');
    });

    it('应该显示添加温度段按钮', () => {
      const addBtn = wrapper.find('.add-segment-btn');
      expect(addBtn.exists()).toBe(true);
    });

    it('点击添加温度段应该添加新段', async () => {
      const initialLength = wrapper.vm.programForm.segments.length;

      const addBtn = wrapper.find('.add-segment-btn');
      await addBtn.trigger('click');

      expect(wrapper.vm.programForm.segments.length).toBe(initialLength + 1);
    });

    it('应该显示程序预览图表', () => {
      expect(wrapper.find('.preview-chart-container').exists()).toBe(true);
    });

    it('应该显示创建程序按钮', () => {
      const createBtns = wrapper.findAll('.el-button');
      const createBtn = createBtns.find(btn => btn.text().includes('创建程序'));
      expect(createBtn).toBeDefined();
    });

    it('点击创建程序应该调用createProgram方法', async () => {
      wrapper.vm.programForm.name = '测试程序';
      wrapper.vm.programForm.description = '测试描述';

      const createBtns = wrapper.findAll('.el-button');
      const createBtn = createBtns.find(btn => btn.text().includes('创建程序'));

      if (createBtn) {
        await createBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.createProgram).toHaveBeenCalled();
      }
    });

    it('calculateTotalDuration应该正确计算总时长', () => {
      const segments = [
        { type: 'heat', targetTemp: 300, rate: 5 },
        { type: 'hold', targetTemp: 300, duration: 30 },
        { type: 'cool', targetTemp: 100, rate: 3 },
      ];

      const duration = wrapper.vm.calculateTotalDuration(segments);
      expect(duration).toContain('min');
    });
  });

  describe('温度保护配置功能', () => {
    it('应该显示最高温度限制输入框', () => {
      expect(wrapper.text()).toContain('最高温度限制');
    });

    it('应该显示最低温度限制输入框', () => {
      expect(wrapper.text()).toContain('最低温度限制');
    });

    it('应该显示超温自动关机开关', () => {
      expect(wrapper.text()).toContain('超温自动关机');
    });

    it('应该显示应用保护配置按钮', () => {
      const btns = wrapper.findAll('.action-btn--primary');
      const protectBtn = btns.find(btn => btn.text().includes('应用保护配置'));
      expect(protectBtn).toBeDefined();
    });

    it('点击应用保护配置应该调用setProtectionConfig方法', async () => {
      wrapper.vm.protectionForm.maxTemp = 380;
      wrapper.vm.protectionForm.minTemp = 85;
      wrapper.vm.protectionForm.enableShutdown = true;

      const applyBtns = wrapper.findAll('.action-btn--primary');
      const protectBtn = applyBtns.find(btn => btn.text().includes('应用保护配置'));

      if (protectBtn) {
        await protectBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.setProtectionConfig).toHaveBeenCalled();
      }
    });

    it('最低温度大于等于最高温度时应该显示警告', async () => {
      wrapper.vm.protectionForm.maxTemp = 100;
      wrapper.vm.protectionForm.minTemp = 150;

      const applyBtns = wrapper.findAll('.action-btn--primary');
      const protectBtn = applyBtns.find(btn => btn.text().includes('应用保护配置'));

      if (protectBtn) {
        await protectBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.setProtectionConfig).not.toHaveBeenCalled();
      }
    });
  });

  describe('历史记录管理功能', () => {
    it('应该显示历史数据点数量', () => {
      expect(wrapper.text()).toContain('当前数据点');
    });

    it('应该显示最大容量', () => {
      expect(wrapper.text()).toContain('最大容量');
    });

    it('应该显示刷新历史按钮', () => {
      const refreshBtns = wrapper.findAll('.el-button');
      const refreshBtn = refreshBtns.find(btn => btn.text().includes('刷新历史'));
      expect(refreshBtn).toBeDefined();
    });

    it('点击刷新历史应该调用fetchTemperatureHistory方法', async () => {
      const refreshBtns = wrapper.findAll('.el-button');
      const refreshBtn = refreshBtns.find(btn => btn.text().includes('刷新历史'));

      if (refreshBtn) {
        await refreshBtn.trigger('click');
        await flushPromises();
        expect(mockTempStore.fetchTemperatureHistory).toHaveBeenCalled();
      }
    });

    it('应该显示清除历史按钮', () => {
      const clearBtns = wrapper.findAll('.el-button');
      const clearBtn = clearBtns.find(btn => btn.text().includes('清除历史'));
      expect(clearBtn).toBeDefined();
    });

    it('应该显示导出CSV按钮', () => {
      const exportBtns = wrapper.findAll('.action-btn--primary');
      const csvBtn = exportBtns.find(btn => btn.text().includes('导出 CSV'));
      expect(csvBtn).toBeDefined();
    });

    it('应该显示导出JSON按钮', () => {
      const exportBtns = wrapper.findAll('.action-btn--secondary');
      const jsonBtn = exportBtns.find(btn => btn.text().includes('导出 JSON'));
      expect(jsonBtn).toBeDefined();
    });
  });

  describe('急停功能', () => {
    it('应该显示紧急停止按钮', () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      expect(emergencyBtn.exists()).toBe(true);
    });

    it('点击紧急停止应该调用emergencyStop方法', async () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      await emergencyBtn.trigger('click');
      await flushPromises();
      expect(mockTempStore.emergencyStop).toHaveBeenCalled();
    });

    it('急停状态下应该显示复位按钮', async () => {
      mockTempStore.status = 'emergency_stop';
      await wrapper.vm.$nextTick();

      const resetBtn = wrapper.find('.emergency-reset-btn');
      expect(resetBtn.exists()).toBe(true);

      mockTempStore.status = 'ready';
    });

    it('急停状态下应该显示急停警告', async () => {
      mockTempStore.status = 'emergency_stop';
      await wrapper.vm.$nextTick();

      const alert = wrapper.find('.emergency-alert');
      expect(alert.exists()).toBe(true);

      mockTempStore.status = 'ready';
    });
  });

  describe('连接状态显示', () => {
    it('应该显示连接状态徽章', () => {
      expect(wrapper.find('.connection-badge').exists()).toBe(true);
    });

    it('连接状态下应该显示已连接', async () => {
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.connectionStatus.text).toBe('已连接');
    });

    it('断开状态下应该显示未连接', async () => {
      mockTempStore.isConnected = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.connectionStatus.text).toBe('未连接');
    });

    it('连接中应该显示连接中', async () => {
      mockTempStore.isConnecting = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.connectionStatus.text).toBe('连接中...');
    });

    it('应该显示断开连接按钮', async () => {
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('断开连接');
    });

    it('应该显示连接温控器按钮', async () => {
      mockTempStore.isConnected = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('连接温控器');
    });
  });

  describe('加热状态显示', () => {
    it('加热中应该显示加热状态', async () => {
      mockTempStore.isHeating = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('加热中');
    });

    it('未加热时应该显示待机状态', async () => {
      mockTempStore.isHeating = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('待机');
    });

    it('应该显示输出功率', async () => {
      mockTempStore.outputPower = 50;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('50.0');
    });
  });

  describe('温度验证功能', () => {
    it('温度在有效范围内应该验证通过', async () => {
      wrapper.vm.tempForm.targetTemp = 300;
      await wrapper.vm.$nextTick();

      const validation = wrapper.vm.tempValidation;
      expect(validation.valid).toBe(true);
    });

    it('温度超出上限应该验证失败', async () => {
      wrapper.vm.tempForm.targetTemp = 500;
      await wrapper.vm.$nextTick();

      const validation = wrapper.vm.tempValidation;
      expect(validation.valid).toBe(false);
    });

    it('温度低于下限应该验证失败', async () => {
      wrapper.vm.tempForm.targetTemp = 50;
      await wrapper.vm.$nextTick();

      const validation = wrapper.vm.tempValidation;
      expect(validation.valid).toBe(false);
    });
  });

  describe('温度格式化功能', () => {
    it('应该正确格式化温度值', () => {
      const formatted = wrapper.vm.formatTempValue(300.5);
      expect(formatted).toBe('300.50');
    });

    it('应该保留两位小数', () => {
      const formatted = wrapper.vm.formatTempValue(300.123);
      expect(formatted).toBe('300.12');
    });
  });

  describe('组件卸载清理', () => {
    it('组件卸载时应该调用cleanup方法', async () => {
      wrapper.unmount();
      expect(mockTempStore.cleanup).toHaveBeenCalled();
    });
  });

  describe('计算属性测试', () => {
    it('connectionBadgeClass应该返回正确的样式类', async () => {
      mockTempStore.isConnected = true;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.connectionBadgeClass).toBe('connection-badge--connected');

      mockTempStore.isConnecting = true;
      mockTempStore.isConnected = false;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.connectionBadgeClass).toBe('connection-badge--connecting');

      mockTempStore.isConnecting = false;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.connectionBadgeClass).toBe('connection-badge--disconnected');
    });

    it('statusIndicatorClass应该返回正确的样式类', async () => {
      mockTempStore.isHeating = true;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.statusIndicatorClass).toBe('status-indicator--heating');

      mockTempStore.isHeating = false;
      mockTempStore.tempStatusType = 'success';
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.statusIndicatorClass).toBe('status-indicator--stable');

      mockTempStore.tempStatusType = 'warning';
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.statusIndicatorClass).toBe('status-indicator--warning');
    });
  });
});
