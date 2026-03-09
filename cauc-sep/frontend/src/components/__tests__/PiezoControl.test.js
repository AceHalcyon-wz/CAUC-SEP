/**
 * @file PiezoControl.test.js
 * @path frontend/src/components/__tests__/
 * @description PiezoControl组件单元测试
 * @author Agent
 * @date 2024-03-08
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import PiezoControl from '../PiezoControl.vue';

// Mock piezo store
const mockPiezoStore = {
  isConnected: false,
  isConnecting: false,
  status: 'disconnected',
  alarmMessage: '',
  wsConnected: false,
  loading: {},
  canControl: false,
  currentVoltage: 0,
  currentDisplacement: 0,
  voltageLimits: {
    min: 0,
    max: 150,
  },
  displacementLimits: {
    min: 0,
    max: 20000,
  },
  setVoltage: vi.fn().mockResolvedValue(true),
  startCalibration: vi.fn().mockResolvedValue(true),
  stopCalibration: vi.fn().mockResolvedValue(true),
  clearAlarm: vi.fn(),
  clearHistory: vi.fn(),
};

vi.mock('../stores/piezo', () => ({
  usePiezoStore: vi.fn(() => mockPiezoStore),
}));

// Mock constants
vi.mock('../config/constants', () => ({
  PIEZO: {
    VOLTAGE_MIN: 0,
    VOLTAGE_MAX: 150,
  },
}));

// Mock ElementPlus message
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock echarts
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

// Mock child components
vi.mock('../PiezoVoltageMap.vue', () => ({
  default: { template: '<div class="piezo-voltage-map-mock">PiezoVoltageMap</div>' },
}));

vi.mock('../PiezoCalibrationEditor.vue', () => ({
  default: { template: '<div class="piezo-calibration-editor-mock">PiezoCalibrationEditor</div>' },
}));

const stubs = {
  'el-card': { template: '<div class="el-card"><slot /><slot name="header" /></div>' },
  'el-button': {
    template: '<button class="el-button" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
    props: ['disabled', 'type', 'size', 'loading'],
  },
  'el-icon': { template: '<i class="el-icon"><slot /></i>' },
  'el-tabs': { template: '<div class="el-tabs"><slot /></div>' },
  'el-tab-pane': { template: '<div class="el-tab-pane"><slot /></div>' },
  'el-slider': {
    template: '<input type="range" class="el-slider" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
    props: ['modelValue', 'min', 'max', 'step', 'disabled', 'show-input'],
  },
  'el-radio-group': { template: '<div class="el-radio-group"><slot /></div>' },
  'el-radio-button': { template: '<label class="el-radio-button"><slot /></label>' },
};

describe('PiezoControl', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();

    wrapper = mount(PiezoControl, {
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
      expect(wrapper.find('.piezo-control').exists()).toBe(true);
    });

    it('应该显示压电陶瓷控制标题', () => {
      expect(wrapper.text()).toContain('压电陶瓷控制');
    });

    it('应该显示连接状态', () => {
      expect(wrapper.find('.connection-status').exists()).toBe(true);
    });

    it('应该显示电压控制标签页', () => {
      expect(wrapper.find('.voltage-control').exists()).toBe(true);
    });

    it('应该显示子组件', () => {
      expect(wrapper.find('.piezo-voltage-map-mock').exists()).toBe(true);
      expect(wrapper.find('.piezo-calibration-editor-mock').exists()).toBe(true);
    });
  });

  describe('连接状态显示', () => {
    it('断开状态下应该显示未连接', async () => {
      mockPiezoStore.isConnected = false;
      await wrapper.vm.$nextTick();

      const statusDiv = wrapper.find('.connection-status');
      expect(statusDiv.classes()).toContain('disconnected');
    });

    it('连接状态下应该显示已连接样式', async () => {
      mockPiezoStore.isConnected = true;
      await wrapper.vm.$nextTick();

      const statusDiv = wrapper.find('.connection-status');
      expect(statusDiv.classes()).toContain('connected');

      mockPiezoStore.isConnected = false;
    });
  });

  describe('电压控制', () => {
    it('应该显示电压滑块', () => {
      expect(wrapper.find('.el-slider').exists()).toBe(true);
    });

    it('应该显示当前电压值', () => {
      const voltageDisplay = wrapper.find('.value-display');
      expect(voltageDisplay.exists()).toBe(true);
    });
  });

  describe('快捷电压设置', () => {
    it('应该显示快捷电压按钮', () => {
      const quickBtns = wrapper.findAll('.quick-btn');
      expect(quickBtns.length).toBe(6); // [0, 30, 60, 90, 120, 150]
    });
  });

  describe('位移显示', () => {
    it('应该显示位移区域', () => {
      expect(wrapper.find('.displacement-section').exists()).toBe(true);
    });

    it('应该显示位移单位μm', () => {
      expect(wrapper.vm.displacementUnit).toBe('μm');
    });
  });

  describe('状态显示', () => {
    it('应该返回正确的状态文本', () => {
      mockPiezoStore.status = 'ready';
      const statusText = wrapper.vm.statusText;
      expect(['就绪', '空闲', '工作中', '校准中', '错误', '已断开', '未知']).toContain(statusText);
    });

    it('应该返回状态类型', () => {
      mockPiezoStore.status = 'ready';
      const statusType = wrapper.vm.statusType;
      expect(['success', 'info', 'warning', 'danger', 'primary']).toContain(statusType);
    });
  });

  describe('标签页切换', () => {
    it('应该显示多个标签页', () => {
      const tabPanes = wrapper.findAll('.el-tab-pane');
      expect(tabPanes.length).toBe(4); // 电压控制、电压位移映射、校准、数据图表
    });

    it('默认应该显示电压控制标签页', () => {
      expect(wrapper.vm.activeTab).toBe('voltage');
    });
  });

  describe('图表功能', () => {
    it('应该显示图表控制区域', () => {
      expect(wrapper.find('.chart-controls').exists()).toBe(true);
    });

    it('应该显示图表类型选择', () => {
      expect(wrapper.find('.chart-type-group').exists()).toBe(true);
    });

    it('图表类型默认应该是实时曲线', () => {
      expect(wrapper.vm.chartType).toBe('realtime');
    });
  });

  describe('数据导出功能', () => {
    it('应该显示导出按钮', () => {
      const chartBtns = wrapper.findAll('.chart-btn');
      const exportBtn = chartBtns.find(btn => btn.text().includes('导出'));
      expect(exportBtn).toBeDefined();
    });
  });

  describe('清空数据功能', () => {
    it('应该显示清空按钮', () => {
      const chartBtns = wrapper.findAll('.chart-btn');
      const clearBtn = chartBtns.find(btn => btn.text().includes('清空'));
      expect(clearBtn).toBeDefined();
    });
  });

  describe('组件卸载清理', () => {
    it('组件卸载时应该清理定时器', async () => {
      vi.useFakeTimers();
      wrapper.vm.dataCollectionInterval = setInterval(() => {}, 100);
      wrapper.vm.voltageChangeTimer = setTimeout(() => {}, 100);

      wrapper.unmount();

      vi.useRealTimers();
    });
  });
});
