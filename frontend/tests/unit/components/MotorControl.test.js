/**
 * @file MotorControl.test.js
 * @path frontend/src/components/__tests__/
 * @description MotorControl组件单元测试
 * @author Agent
 * @date 2024-03-08
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import MotorControl from '@/components/experiment/motor/MotorControl.vue';

const mockMotorStore = {
  isConnected: true,
  isConnecting: false,
  status: 'ready',
  alarmMessage: '',
  wsConnected: true,
  loading: {
    emergencyStop: false,
    resetEmergency: false,
    home: false,
    moveAbsolute: false,
    jog: false,
  },
  canControl: true,
  isEmergencyStopped: false,
  limits: {
    positive_mm: 50,
    negative_mm: -50,
    positive_steps: 80000,
    negative_steps: -80000,
  },
  positionSteps: 0,
  positionMm: 0,
  velocity: 0,
  moveAbsolute: vi.fn().mockResolvedValue(true),
  jog: vi.fn().mockResolvedValue(true),
  emergencyStop: vi.fn().mockResolvedValue(true),
  resetEmergency: vi.fn().mockResolvedValue(true),
  setLimits: vi.fn().mockResolvedValue(true),
  home: vi.fn().mockResolvedValue(true),
  clearAlarm: vi.fn(),
  addMovementRecord: vi.fn(),
};

vi.mock('../../stores/motor', () => ({
  useMotorStore: vi.fn(() => mockMotorStore),
}));

vi.mock('../../utils/validation', () => ({
  validatePosition: vi.fn((value, min, max) => {
    if (value < min || value > max) {
      return { valid: false, message: '位置超出限位范围' };
    }
    return { valid: true, message: '' };
  }),
  validateVelocity: vi.fn((value, min, max) => {
    if (value < min || value > max) {
      return { valid: false, message: '速度超出有效范围' };
    }
    return { valid: true, message: '' };
  }),
}));

vi.mock('../../config/constants', () => ({
  MOTOR: {
    MIN_VELOCITY: 0.1,
    MAX_VELOCITY: 100,
  },
}));

vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock('../PRPathConfig.vue', () => ({
  default: { template: '<div class="pr-path-config-mock">PRPathConfig</div>' },
}));

vi.mock('../MotorPositionPreset.vue', () => ({
  default: { template: '<div class="motor-position-preset-mock">MotorPositionPreset</div>' },
}));

vi.mock('../MotorTrajectoryPreview.vue', () => ({
  default: { template: '<div class="motor-trajectory-preview-mock">MotorTrajectoryPreview</div>' },
}));

vi.mock('../MotorHistoryPanel.vue', () => ({
  default: { template: '<div class="motor-history-panel-mock">MotorHistoryPanel</div>' },
}));

describe('MotorControl', () => {
  let wrapper;
  let pinia;

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
      template: '<input type="number" class="el-input-number" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
      props: ['modelValue', 'min', 'max', 'precision', 'step'],
    },
    'el-tag': { template: '<span class="el-tag"><slot /></span>' },
    'el-divider': { template: '<hr class="el-divider"><slot /></hr>' },
    'el-select': { template: '<select class="el-select"><slot /></select>' },
    'el-option': { template: '<option class="el-option"><slot /></option>' },
    'el-tooltip': { template: '<div class="el-tooltip"><slot /></div>' },
    'WarningFilled': { template: '<span class="warning-filled-icon"></span>' },
    'RefreshRight': { template: '<span class="refresh-right-icon"></span>' },
    'SetUp': { template: '<span class="setup-icon"></span>' },
    'InfoFilled': { template: '<span class="info-filled-icon"></span>' },
    'Warning': { template: '<span class="warning-icon"></span>' },
    'Position': { template: '<span class="position-icon"></span>' },
    'HomeFilled': { template: '<span class="home-filled-icon"></span>' },
    'ArrowLeft': { template: '<span class="arrow-left-icon"></span>' },
    'ArrowRight': { template: '<span class="arrow-right-icon"></span>' },
    'QuestionFilled': { template: '<span class="question-filled-icon"></span>' },
  };

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();

    wrapper = mount(MotorControl, {
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
      expect(wrapper.find('.motor-control-wrapper').exists()).toBe(true);
    });

    it('应该显示急停按钮', () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      expect(emergencyBtn.exists()).toBe(true);
      expect(emergencyBtn.text()).toContain('急停');
    });

    it('应该显示运动控制卡片', () => {
      expect(wrapper.find('.motor-control').exists()).toBe(true);
    });

    it('应该显示位置输入框', () => {
      expect(wrapper.find('.position-input').exists()).toBe(true);
    });

    it('应该显示速度输入框', () => {
      expect(wrapper.find('.velocity-input').exists()).toBe(true);
    });

    it('应该显示绝对定位按钮', () => {
      const moveBtn = wrapper.find('.move-btn');
      expect(moveBtn.exists()).toBe(true);
      expect(moveBtn.text()).toContain('绝对定位');
    });

    it('应该显示回零按钮', () => {
      const homeBtn = wrapper.find('.home-btn');
      expect(homeBtn.exists()).toBe(true);
      expect(homeBtn.text()).toContain('回零');
    });

    it('应该显示JOG按钮', () => {
      const jogButtons = wrapper.findAll('.jog-btn');
      expect(jogButtons.length).toBe(2);
    });
  });

  describe('急停功能', () => {
    it('急停按钮应该存在', () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      expect(emergencyBtn.exists()).toBe(true);
    });
  });

  describe('绝对定位功能', () => {
    it('绝对定位按钮应该存在', () => {
      const moveBtn = wrapper.find('.move-btn');
      expect(moveBtn.exists()).toBe(true);
    });

    it('运动中应该显示加载状态', async () => {
      wrapper.vm.isMoving = true;
      await wrapper.vm.$nextTick();

      const moveBtn = wrapper.find('.move-btn');
      expect(moveBtn.attributes('loading')).toBeDefined();
    });
  });

  describe('JOG功能', () => {
    it('JOG按钮应该存在', () => {
      const jogButtons = wrapper.findAll('.jog-btn');
      expect(jogButtons.length).toBe(2);
    });

    it('释放JOG按钮应该停止JOG运动', async () => {
      vi.useFakeTimers();
      wrapper.vm.moveForm.velocity = 15;

      const jogLeftBtn = wrapper.find('.jog-btn-left');
      await jogLeftBtn.trigger('mousedown');
      await jogLeftBtn.trigger('mouseup');
      await flushPromises();

      expect(wrapper.vm.jogState.active).toBe(false);

      vi.useRealTimers();
    });
  });
});
