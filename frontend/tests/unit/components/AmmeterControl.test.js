/**
 * @file AmmeterControl.test.js
 * @path frontend/tests/unit/components/
 * @description AmmeterControl组件单元测试
 * @author Agent
 * @date 2024-03-16
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import AmmeterControl from '@/components/experiment/ammeter/AmmeterControl.vue';

// Mock ammeter store
const mockAmmeterStore = {
  isConnected: true,
  status: 'ready',
  isCollecting: false,
  sampleRate: 1000,
  channelCount: 4,
  channelData: {
    1: 0.0001,
    2: 0.0002,
    3: 0.0003,
    4: 0.0004,
  },
  bufferStatus: {
    size: 100,
    max_size: 10000,
  },
  bufferUsagePercent: 1,
  bufferStatusType: 'success',
  bufferStatusText: '缓冲区正常',
  snrData: {
    1: { snr: 45.5, signal: 0.0001, noise: 0.000001 },
    2: { snr: 42.3, signal: 0.0002, noise: 0.000002 },
    3: { snr: 48.1, signal: 0.0003, noise: 0.000003 },
    4: { snr: 43.7, signal: 0.0004, noise: 0.000004 },
  },
  realtimeData: [],
  collectionStats: {
    samples_collected: 1000,
    data_rate: 1000,
  },
  canControl: true,
  channelConfig: {
    1: { enabled: true, range: 'auto', filter: 'low' },
    2: { enabled: true, range: 'auto', filter: 'low' },
    3: { enabled: true, range: 'auto', filter: 'low' },
    4: { enabled: true, range: 'auto', filter: 'low' },
  },
  collectionTemplates: [],
  activeTemplateId: null,
  snrThresholds: {
    warning: 30,
    critical: 20,
  },
  snrAlarms: {},
  hasSNRAlarm: false,
  bufferConfig: {
    maxSize: 10000,
    warningThreshold: 0.8,
    criticalThreshold: 0.95,
    autoClear: false,
  },
  init: vi.fn(),
  cleanup: vi.fn(),
  startCollection: vi.fn().mockResolvedValue(true),
  stopCollection: vi.fn().mockResolvedValue(true),
  setSampleRate: vi.fn().mockResolvedValue(true),
  clearBuffer: vi.fn().mockResolvedValue(true),
  fetchStatus: vi.fn().mockResolvedValue(true),
  configureChannel: vi.fn().mockResolvedValue(true),
  fetchAllSNR: vi.fn().mockResolvedValue(true),
  clearRealtimeData: vi.fn(),
  saveTemplate: vi.fn().mockReturnValue('template-1'),
  loadTemplate: vi.fn().mockReturnValue(true),
  deleteTemplate: vi.fn().mockReturnValue(true),
  optimizeBufferSize: vi.fn().mockReturnValue({
    currentSize: 10000,
    averageUsage: 25,
    peakUsage: 50,
    recommendation: {
      action: 'maintain',
      reason: '当前缓冲区大小合适',
      suggestedSize: 10000,
    },
  }),
};

vi.mock('@/stores/ammeter', () => ({
  useAmmeterStore: vi.fn(() => mockAmmeterStore),
}));

vi.mock('@/config/constants', () => ({
  AMMETER: {
    MIN_SAMPLE_RATE: 1,
    MAX_SAMPLE_RATE: 10000,
    CHANNEL_COUNT: 4,
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

// Mock child components
vi.mock('./AmmeterWaveform.vue', () => ({
  default: {
    template: '<div class="ammeter-waveform-mock">AmmeterWaveform</div>',
    props: ['data', 'channelConfig', 'channelCount', 'autoUpdate', 'updateInterval'],
  },
}));

vi.mock('./AmmeterChannelConfig.vue', () => ({
  default: {
    template: '<div class="ammeter-channel-config-mock">AmmeterChannelConfig</div>',
    props: ['channelConfig', 'channelCount', 'canControl', 'isCollecting'],
  },
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
  'el-input-number': {
    template: '<input type="number" class="el-input-number" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
    props: ['modelValue', 'min', 'max', 'precision', 'step', 'disabled'],
  },
  'el-input': {
    template: '<input class="el-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
    props: ['modelValue', 'placeholder', 'type'],
  },
  'el-tag': { template: '<span class="el-tag"><slot /></span>' },
  'el-switch': {
    template: '<input type="checkbox" class="el-switch" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />',
    props: ['modelValue', 'disabled', 'active-text', 'inactive-text'],
  },
  'el-select': { template: '<select class="el-select" :disabled="disabled" @change="$emit(\'change\', $event.target.value)"><slot /></select>' },
  'el-option': { template: '<option class="el-option" :value="value"><slot /></option>' },
  'el-row': { template: '<div class="el-row"><slot /></div>' },
  'el-col': { template: '<div class="el-col"><slot /></div>' },
  'el-form': { template: '<form class="el-form"><slot /></form>' },
  'el-form-item': { template: '<div class="el-form-item"><slot /></div>' },
  'el-checkbox': {
    template: '<input type="checkbox" class="el-checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />',
    props: ['modelValue', 'disabled'],
  },
  'el-dialog': {
    template: '<div class="el-dialog" v-if="modelValue"><slot /><slot name="footer" /></div>',
    props: ['modelValue', 'title', 'width'],
  },
  'VideoPlay': { template: '<span class="video-play-icon"></span>' },
  'VideoPause': { template: '<span class="video-pause-icon"></span>' },
  'Delete': { template: '<span class="delete-icon"></span>' },
  'Refresh': { template: '<span class="refresh-icon"></span>' },
  'Plus': { template: '<span class="plus-icon"></span>' },
  'Document': { template: '<span class="document-icon"></span>' },
  'Warning': { template: '<span class="warning-icon"></span>' },
  'Aim': { template: '<span class="aim-icon"></span>' },
};

describe('AmmeterControl', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();

    wrapper = mount(AmmeterControl, {
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
      expect(wrapper.find('.ammeter-control').exists()).toBe(true);
    });

    it('应该显示微电流采集控制标题', () => {
      expect(wrapper.text()).toContain('微电流采集控制');
    });

    it('应该显示连接状态', () => {
      expect(wrapper.find('.connection-status').exists()).toBe(true);
    });

    it('应该显示采集控制标签页', () => {
      expect(wrapper.find('.collection-control').exists()).toBe(true);
    });

    it('应该显示通道配置标签页', () => {
      const tabPanes = wrapper.findAll('.el-tab-pane');
      expect(tabPanes.length).toBeGreaterThan(1);
    });

    it('应该显示实时数据标签页', () => {
      const tabPanes = wrapper.findAll('.el-tab-pane');
      expect(tabPanes.length).toBeGreaterThan(2);
    });

    it('应该显示数据图表标签页', () => {
      const tabPanes = wrapper.findAll('.el-tab-pane');
      expect(tabPanes.length).toBeGreaterThan(3);
    });
  });

  describe('电流测量功能', () => {
    it('应该显示采样率设置区域', () => {
      expect(wrapper.find('.sample-rate-section').exists()).toBe(true);
    });

    it('应该显示采样率滑块', () => {
      expect(wrapper.find('.rate-slider').exists()).toBe(true);
    });

    it('应该显示当前采样率值', () => {
      const rateDisplay = wrapper.find('.rate-display');
      expect(rateDisplay.exists()).toBe(true);
    });

    it('应该显示采样率单位Hz', () => {
      expect(wrapper.text()).toContain('Hz');
    });

    it('应该显示通道数据', () => {
      expect(wrapper.find('.channel-data-section').exists()).toBe(true);
    });

    it('应该显示4个通道的数据卡片', () => {
      const channelCards = wrapper.findAll('.data-channel-card');
      expect(channelCards.length).toBe(4);
    });
  });

  describe('量程切换功能', () => {
    it('应该显示通道配置面板', () => {
      expect(wrapper.find('.channel-config-panel').exists()).toBe(true);
    });

    it('应该显示量程选择器', () => {
      const selects = wrapper.findAll('.el-select');
      expect(selects.length).toBeGreaterThan(0);
    });

    it('应该显示滤波选择器', () => {
      const selects = wrapper.findAll('.el-select');
      expect(selects.length).toBeGreaterThan(0);
    });

    it('应该显示通道启用开关', () => {
      const switches = wrapper.findAll('.el-switch');
      expect(switches.length).toBe(4);
    });
  });

  describe('数据显示功能', () => {
    it('应该显示缓冲区状态', () => {
      expect(wrapper.find('.buffer-status-section').exists()).toBe(true);
    });

    it('应该显示缓冲区使用率', () => {
      expect(wrapper.find('.buffer-percent').exists()).toBe(true);
    });

    it('应该显示缓冲区进度条', () => {
      expect(wrapper.find('.buffer-bar').exists()).toBe(true);
    });

    it('应该显示采集统计信息', () => {
      expect(wrapper.find('.stats-section').exists()).toBe(true);
    });

    it('应该显示已采集样本数', () => {
      expect(wrapper.text()).toContain('已采集样本');
    });

    it('应该显示数据速率', () => {
      expect(wrapper.text()).toContain('数据速率');
    });

    it('应该显示信噪比监控区域', () => {
      expect(wrapper.find('.snr-section').exists()).toBe(true);
    });

    it('应该显示SNR数据', () => {
      const snrCards = wrapper.findAll('.snr-card');
      expect(snrCards.length).toBe(4);
    });
  });

  describe('采集控制功能', () => {
    it('应该显示开始采集按钮', () => {
      const actionBtns = wrapper.findAll('.action-btn');
      const startBtn = actionBtns.find(btn => btn.text().includes('开始采集'));
      expect(startBtn).toBeDefined();
    });

    it('应该显示清空缓冲区按钮', () => {
      const actionBtns = wrapper.findAll('.action-btn');
      const clearBtn = actionBtns.find(btn => btn.text().includes('清空缓冲区'));
      expect(clearBtn).toBeDefined();
    });

    it('应该显示刷新状态按钮', () => {
      const actionBtns = wrapper.findAll('.action-btn');
      const refreshBtn = actionBtns.find(btn => btn.text().includes('刷新状态'));
      expect(refreshBtn).toBeDefined();
    });

    it('点击开始采集按钮应该调用startCollection方法', async () => {
      const actionBtns = wrapper.findAll('.action-btn');
      const startBtn = actionBtns.find(btn => btn.text().includes('开始采集'));
      
      if (startBtn) {
        await startBtn.trigger('click');
        await flushPromises();
        expect(mockAmmeterStore.startCollection).toHaveBeenCalled();
      }
    });

    it('点击清空缓冲区按钮应该调用clearBuffer方法', async () => {
      const actionBtns = wrapper.findAll('.action-btn');
      const clearBtn = actionBtns.find(btn => btn.text().includes('清空缓冲区'));
      
      if (clearBtn) {
        await clearBtn.trigger('click');
        await flushPromises();
        expect(mockAmmeterStore.clearBuffer).toHaveBeenCalled();
      }
    });

    it('点击刷新状态按钮应该调用fetchStatus方法', async () => {
      const actionBtns = wrapper.findAll('.action-btn');
      const refreshBtn = actionBtns.find(btn => btn.text().includes('刷新状态'));
      
      if (refreshBtn) {
        await refreshBtn.trigger('click');
        await flushPromises();
        expect(mockAmmeterStore.fetchStatus).toHaveBeenCalled();
      }
    });
  });

  describe('采样率设置功能', () => {
    it('应该显示快捷采样率按钮', () => {
      const quickBtns = wrapper.findAll('.quick-btn');
      expect(quickBtns.length).toBe(6); // [1, 10, 100, 1000, 5000, 10000]
    });

    it('点击快捷采样率按钮应该设置采样率', async () => {
      const quickBtns = wrapper.findAll('.quick-btn');
      const btn100Hz = quickBtns[2]; // 100 Hz
      
      if (btn100Hz) {
        await btn100Hz.trigger('click');
        await flushPromises();
        expect(mockAmmeterStore.setSampleRate).toHaveBeenCalled();
      }
    });

    it('采样率滑块变化应该调用setSampleRate方法', async () => {
      const slider = wrapper.find('.rate-slider');
      await slider.setValue(2000);
      await slider.trigger('change', 2000);
      await flushPromises();
      expect(mockAmmeterStore.setSampleRate).toHaveBeenCalled();
    });
  });

  describe('通道配置功能', () => {
    it('应该显示通道启用开关', () => {
      const switches = wrapper.findAll('.el-switch');
      expect(switches.length).toBe(4);
    });

    it('切换通道启用状态应该调用configureChannel方法', async () => {
      const switches = wrapper.findAll('.el-switch');
      const firstSwitch = switches[0];
      
      if (firstSwitch) {
        await firstSwitch.trigger('change', false);
        await flushPromises();
        expect(mockAmmeterStore.configureChannel).toHaveBeenCalled();
      }
    });

    it('应该显示量程选择器', () => {
      const selects = wrapper.findAll('.el-select');
      expect(selects.length).toBeGreaterThan(0);
    });
  });

  describe('缓冲区状态显示', () => {
    it('应该显示缓冲区使用率百分比', () => {
      const percent = wrapper.find('.buffer-percent');
      expect(percent.exists()).toBe(true);
    });

    it('应该显示缓冲区进度条', () => {
      const bar = wrapper.find('.buffer-bar');
      expect(bar.exists()).toBe(true);
    });

    it('应该显示缓冲区详情', () => {
      const details = wrapper.find('.buffer-details');
      expect(details.exists()).toBe(true);
    });
  });

  describe('SNR监控功能', () => {
    it('应该显示SNR刷新按钮', () => {
      const snrBtn = wrapper.find('.snr-btn');
      expect(snrBtn.exists()).toBe(true);
    });

    it('点击刷新SNR按钮应该调用fetchAllSNR方法', async () => {
      const snrBtn = wrapper.find('.snr-btn');
      await snrBtn.trigger('click');
      await flushPromises();
      expect(mockAmmeterStore.fetchAllSNR).toHaveBeenCalled();
    });

    it('应该显示各通道SNR数据', () => {
      const snrCards = wrapper.findAll('.snr-card');
      expect(snrCards.length).toBe(4);
    });
  });

  describe('模板管理功能', () => {
    it('应该显示模板管理标签页', () => {
      const tabPanes = wrapper.findAll('.el-tab-pane');
      expect(tabPanes.length).toBeGreaterThan(4);
    });

    it('应该显示保存模板按钮', () => {
      expect(wrapper.text()).toContain('保存当前配置为模板');
    });

    it('应该显示SNR阈值配置区域', () => {
      expect(wrapper.find('.snr-config-section').exists()).toBe(true);
    });

    it('应该显示缓冲区配置区域', () => {
      expect(wrapper.find('.buffer-config-section').exists()).toBe(true);
    });
  });

  describe('连接状态显示', () => {
    it('连接状态下应该显示已连接样式', async () => {
      mockAmmeterStore.isConnected = true;
      await wrapper.vm.$nextTick();

      const statusDiv = wrapper.find('.connection-status');
      expect(statusDiv.classes()).toContain('connected');
    });

    it('断开状态下应该显示未连接样式', async () => {
      mockAmmeterStore.isConnected = false;
      await wrapper.vm.$nextTick();

      const statusDiv = wrapper.find('.connection-status');
      expect(statusDiv.classes()).toContain('disconnected');
    });
  });

  describe('采集状态显示', () => {
    it('采集中应该显示正确状态', async () => {
      mockAmmeterStore.isCollecting = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('采集中');
    });

    it('空闲时应该显示正确状态', async () => {
      mockAmmeterStore.isCollecting = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('空闲');
    });
  });

  describe('格式化函数测试', () => {
    it('应该正确格式化采样率', () => {
      expect(wrapper.vm.formatRate(1000)).toBe('1000 Hz');
      expect(wrapper.vm.formatRate(5000)).toBe('5.0 kHz');
    });

    it('应该正确格式化电流值', () => {
      expect(wrapper.vm.formatCurrent(0.0001)).toBe('0.0001 μA');
      expect(wrapper.vm.formatCurrent(0.000001)).toBe('1.000 nA');
      expect(wrapper.vm.formatCurrent(1000)).toBe('1.000 mA');
    });
  });

  describe('组件卸载清理', () => {
    it('组件卸载时应该调用cleanup方法', async () => {
      wrapper.unmount();
      expect(mockAmmeterStore.cleanup).toHaveBeenCalled();
    });
  });
});
