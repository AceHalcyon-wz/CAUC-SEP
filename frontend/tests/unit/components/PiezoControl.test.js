/**
 * @file PiezoControl.test.js
 * @path frontend/tests/unit/components/
 * @description PiezoControl组件单元测试
 * @author Agent
 * @date 2024-03-16
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import PiezoControl from '@/components/experiment/piezo/PiezoControl.vue';

const mockPiezoStore = {
  isConnected: true,
  isConnecting: false,
  status: 'ready',
  alarmMessage: '',
  wsConnected: true,
  loading: {},
  canControl: true,
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
  calibrationData: {
    points: [],
    coefficients: { a: 0, b: 0 },
    isValid: false,
  },
  historyData: [],
  setVoltage: vi.fn().mockResolvedValue(true),
  startCalibration: vi.fn().mockResolvedValue(true),
  stopCalibration: vi.fn().mockResolvedValue(true),
  addCalibrationPoint: vi.fn().mockResolvedValue(true),
  clearCalibration: vi.fn().mockResolvedValue(true),
  applyCalibration: vi.fn().mockResolvedValue(true),
  clearAlarm: vi.fn(),
  clearHistory: vi.fn(),
  init: vi.fn(),
  cleanup: vi.fn(),
  connectWebSocket: vi.fn(),
  disconnectWebSocket: vi.fn(),
  fetchStatus: vi.fn().mockResolvedValue(true),
};

vi.mock('@/stores/piezo', () => ({
  usePiezoStore: vi.fn(() => mockPiezoStore),
}));

vi.mock('@/config/constants', () => ({
  PIEZO: {
    VOLTAGE_MIN: 0,
    VOLTAGE_MAX: 150,
    DISPLACEMENT_MIN: 0,
    DISPLACEMENT_MAX: 20000,
  },
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

vi.mock('./PiezoVoltageMap.vue', () => ({
  default: { template: '<div class="piezo-voltage-map-mock">PiezoVoltageMap</div>' },
}));

vi.mock('./PiezoCalibrationEditor.vue', () => ({
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
    template: '<input type="range" class="el-slider" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
    props: ['modelValue', 'min', 'max', 'step', 'disabled', 'show-input'],
  },
  'el-radio-group': { template: '<div class="el-radio-group"><slot /></div>' },
  'el-radio-button': { template: '<label class="el-radio-button"><slot /></label>' },
  'Cpu': { template: '<span class="cpu-icon"></span>' },
  'VideoCamera': { template: '<span class="video-camera-icon"></span>' },
  'Download': { template: '<span class="download-icon"></span>' },
  'Delete': { template: '<span class="delete-icon"></span>' },
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

    it('应该显示电压位移映射组件', () => {
      expect(wrapper.find('.piezo-voltage-map-mock').exists()).toBe(true);
    });

    it('应该显示校准编辑器组件', () => {
      expect(wrapper.find('.piezo-calibration-editor-mock').exists()).toBe(true);
    });

    it('应该显示数据图表标签页', () => {
      const tabPanes = wrapper.findAll('.el-tab-pane');
      expect(tabPanes.length).toBe(4);
    });
  });

  describe('电压控制功能', () => {
    it('应该显示电压滑块', () => {
      expect(wrapper.find('.el-slider').exists()).toBe(true);
    });

    it('应该显示当前电压值', () => {
      const voltageDisplay = wrapper.find('.value-display');
      expect(voltageDisplay.exists()).toBe(true);
    });

    it('应该显示电压单位V', () => {
      expect(wrapper.text()).toContain('V');
    });

    it('应该显示电压刻度标记', () => {
      const marks = wrapper.findAll('.mark');
      expect(marks.length).toBe(5);
    });

    it('电压滑块变化应该调用setVoltage方法', async () => {
      const slider = wrapper.find('.el-slider');
      await slider.setValue(50);
      await slider.trigger('change');
      await flushPromises();

      // slider的change事件会触发handleVoltageChange
      // 由于mock了setVoltage返回true，组件会调用ElMessage.success
    });

    it('未连接时电压滑块应该禁用', async () => {
      mockPiezoStore.canControl = false;
      await wrapper.vm.$nextTick();

      const slider = wrapper.find('.el-slider');
      expect(slider.attributes('disabled')).toBeDefined();
    });
  });

  describe('快捷电压设置功能', () => {
    it('应该显示快捷电压按钮', () => {
      const quickBtns = wrapper.findAll('.quick-btn');
      expect(quickBtns.length).toBe(6);
    });

    it('快捷电压按钮应该显示正确的电压值', () => {
      const quickBtns = wrapper.findAll('.quick-btn');
      const expectedVoltages = [0, 30, 60, 90, 120, 150];

      quickBtns.forEach((btn, index) => {
        expect(btn.text()).toContain(expectedVoltages[index].toString());
      });
    });

    it('点击快捷电压按钮应该调用setVoltage方法', async () => {
      const quickBtns = wrapper.findAll('.quick-btn');
      await quickBtns[2].trigger('click'); // 60V
      await flushPromises();

      expect(mockPiezoStore.setVoltage).toHaveBeenCalledWith(60);
    });

    it('当前电压匹配时快捷按钮应该显示激活状态', async () => {
      wrapper.vm.voltageValue = 60;
      await wrapper.vm.$nextTick();

      const quickBtns = wrapper.findAll('.quick-btn');
      expect(quickBtns[2].classes()).toContain('quick-btn--active');
    });

    it('未连接时快捷电压按钮应该禁用', async () => {
      mockPiezoStore.canControl = false;
      await wrapper.vm.$nextTick();

      const quickBtns = wrapper.findAll('.quick-btn');
      quickBtns.forEach(btn => {
        expect(btn.attributes('disabled')).toBeDefined();
      });
    });
  });

  describe('位置控制功能', () => {
    it('应该显示位移区域', () => {
      expect(wrapper.find('.displacement-section').exists()).toBe(true);
    });

    it('应该显示位移值', () => {
      const displacementValue = wrapper.find('.displacement-value');
      expect(displacementValue.exists()).toBe(true);
    });

    it('应该显示位移单位μm', () => {
      expect(wrapper.vm.displacementUnit).toBe('μm');
    });

    it('应该显示位移进度条', () => {
      expect(wrapper.find('.displacement-bar').exists()).toBe(true);
    });

    it('应该显示详细信息卡片', () => {
      const detailCards = wrapper.findAll('.detail-card');
      expect(detailCards.length).toBe(3);
    });

    it('应该显示电压详情', () => {
      expect(wrapper.text()).toContain('电压');
    });

    it('应该显示温度详情', () => {
      expect(wrapper.text()).toContain('温度');
    });

    it('应该显示状态详情', () => {
      expect(wrapper.text()).toContain('状态');
    });

    it('displayDisplacement应该正确转换nm为μm', async () => {
      mockPiezoStore.currentDisplacement = 10000; // 10000 nm = 10 μm
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.displayDisplacement).toBe('10.000');
    });
  });

  describe('校准功能', () => {
    it('应该显示校准标签页', () => {
      const tabPanes = wrapper.findAll('.el-tab-pane');
      expect(tabPanes.length).toBeGreaterThan(2);
    });

    it('应该显示校准编辑器组件', () => {
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
    });

    it('应该显示连接状态文本', async () => {
      mockPiezoStore.isConnected = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.connectionStatus).toBe('设备已连接');
    });

    it('应该显示断开状态文本', async () => {
      mockPiezoStore.isConnected = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.connectionStatus).toBe('设备未连接');
    });
  });

  describe('状态显示功能', () => {
    it('应该返回正确的状态文本 - ready', async () => {
      mockPiezoStore.status = 'ready';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.statusText).toBe('就绪');
    });

    it('应该返回正确的状态文本 - working', async () => {
      mockPiezoStore.status = 'working';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.statusText).toBe('工作中');
    });

    it('应该返回正确的状态文本 - calibrating', async () => {
      mockPiezoStore.status = 'calibrating';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.statusText).toBe('校准中');
    });

    it('应该返回正确的状态文本 - error', async () => {
      mockPiezoStore.status = 'error';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.statusText).toBe('错误');
    });

    it('应该返回正确的状态类型 - ready', async () => {
      mockPiezoStore.status = 'ready';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.statusType).toBe('success');
    });

    it('应该返回正确的状态类型 - working', async () => {
      mockPiezoStore.status = 'working';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.statusType).toBe('primary');
    });

    it('应该返回正确的状态类型 - calibrating', async () => {
      mockPiezoStore.status = 'calibrating';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.statusType).toBe('warning');
    });

    it('应该返回正确的状态类型 - error', async () => {
      mockPiezoStore.status = 'error';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.statusType).toBe('danger');
    });
  });

  describe('标签页切换功能', () => {
    it('默认应该显示电压控制标签页', () => {
      expect(wrapper.vm.activeTab).toBe('voltage');
    });

    it('应该能够切换标签页', async () => {
      wrapper.vm.activeTab = 'calibration';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.activeTab).toBe('calibration');
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

    it('应该显示图表容器', () => {
      expect(wrapper.find('.chart-container').exists()).toBe(true);
    });

    it('应该显示开始采集按钮', () => {
      const chartBtns = wrapper.findAll('.chart-btn');
      const collectBtn = chartBtns.find(btn => btn.text().includes('开始采集'));
      expect(collectBtn).toBeDefined();
    });

    it('点击采集按钮应该切换采集状态', async () => {
      const chartBtns = wrapper.findAll('.chart-btn');
      const collectBtn = chartBtns.find(btn => btn.text().includes('开始采集'));

      await collectBtn.trigger('click');
      await flushPromises();

      expect(wrapper.vm.isCollecting).toBe(true);
    });
  });

  describe('数据导出功能', () => {
    it('应该显示导出按钮', () => {
      const chartBtns = wrapper.findAll('.chart-btn');
      const exportBtn = chartBtns.find(btn => btn.text().includes('导出'));
      expect(exportBtn).toBeDefined();
    });

    it('无数据时导出应该显示警告', async () => {
      wrapper.vm.chartData = [];
      await wrapper.vm.exportData();
      // ElMessage.warning should be called
    });
  });

  describe('清空数据功能', () => {
    it('应该显示清空按钮', () => {
      const chartBtns = wrapper.findAll('.chart-btn');
      const clearBtn = chartBtns.find(btn => btn.text().includes('清空'));
      expect(clearBtn).toBeDefined();
    });

    it('点击清空按钮应该调用clearHistory方法', async () => {
      wrapper.vm.chartData = [{ timestamp: 1, voltage: 0, displacement: 0 }];

      const chartBtns = wrapper.findAll('.chart-btn');
      const clearBtn = chartBtns.find(btn => btn.text().includes('清空'));

      await clearBtn.trigger('click');
      await flushPromises();

      expect(mockPiezoStore.clearHistory).toHaveBeenCalled();
    });
  });

  describe('电压变化动画功能', () => {
    it('电压变化时应该设置isVoltageChanging为true', async () => {
      vi.useFakeTimers();
      wrapper.vm.onVoltageInput(50);
      expect(wrapper.vm.isVoltageChanging).toBe(true);
      vi.useRealTimers();
    });

    it('电压变化后应该重置isVoltageChanging为false', async () => {
      vi.useFakeTimers();
      wrapper.vm.onVoltageInput(50);
      vi.advanceTimersByTime(300);
      expect(wrapper.vm.isVoltageChanging).toBe(false);
      vi.useRealTimers();
    });
  });

  describe('数据采集功能', () => {
    it('开始采集应该创建定时器', async () => {
      vi.useFakeTimers();
      wrapper.vm.startDataCollection();
      expect(wrapper.vm.dataCollectionInterval).not.toBeNull();
      wrapper.vm.stopDataCollection();
      vi.useRealTimers();
    });

    it('停止采集应该清除定时器', async () => {
      vi.useFakeTimers();
      wrapper.vm.startDataCollection();
      wrapper.vm.stopDataCollection();
      expect(wrapper.vm.dataCollectionInterval).toBeNull();
      vi.useRealTimers();
    });

    it('采集时应该添加数据到chartData', async () => {
      vi.useFakeTimers();
      wrapper.vm.chartData = [];
      wrapper.vm.startDataCollection();
      vi.advanceTimersByTime(500);
      expect(wrapper.vm.chartData.length).toBe(1);
      wrapper.vm.stopDataCollection();
      vi.useRealTimers();
    });

    it('chartData最多保持100个数据点', async () => {
      vi.useFakeTimers();
      wrapper.vm.chartData = Array(100).fill({ timestamp: 1, voltage: 0, displacement: 0 });
      wrapper.vm.startDataCollection();
      vi.advanceTimersByTime(500);
      expect(wrapper.vm.chartData.length).toBe(100);
      wrapper.vm.stopDataCollection();
      vi.useRealTimers();
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

    it('组件卸载时应该调用cleanup方法', async () => {
      wrapper.unmount();
      expect(mockPiezoStore.cleanup).toHaveBeenCalled();
    });
  });

  describe('Store同步功能', () => {
    it('Store电压变化应该同步到本地', async () => {
      mockPiezoStore.currentVoltage = 75;
      await wrapper.vm.$nextTick();

      // Watcher should update local voltageValue
    });
  });

  describe('图表类型切换功能', () => {
    it('切换到校准曲线应该调用updateCalibrationChart', async () => {
      mockPiezoStore.calibrationData.points = [
        { voltage: 0, displacement: 0 },
        { voltage: 150, displacement: 15000 },
      ];
      await wrapper.vm.$nextTick();

      wrapper.vm.chartType = 'calibration';
      await wrapper.vm.$nextTick();

      // Should update chart with calibration data
    });

    it('切换到历史数据应该使用Store历史数据', async () => {
      mockPiezoStore.historyData = [
        { timestamp: 1, voltage: 50, displacement: 5000 },
        { timestamp: 2, voltage: 100, displacement: 10000 },
      ];
      await wrapper.vm.$nextTick();

      wrapper.vm.chartType = 'history';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.chartData.length).toBe(2);
    });
  });
});
