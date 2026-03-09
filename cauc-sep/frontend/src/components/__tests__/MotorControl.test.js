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
import MotorControl from '../MotorControl.vue';

// Mock motor store
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

vi.mock('../stores/motor', () => ({
  useMotorStore: vi.fn(() => mockMotorStore),
}));

// Mock validation utils
vi.mock('../utils/validation', () => ({
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

// Mock constants
vi.mock('../config/constants', () => ({
  MOTOR: {
    MIN_VELOCITY: 0.1,
    MAX_VELOCITY: 100,
  },
}));

// Mock ElementPlus message
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// Mock child components
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
    'el-card': { template: '<div class="el-card"><slot /></div>' },
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
      template: '<input type="number" class="el-input-number" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" @change="$emit(\'change\', Number($event.target.value))" />',
      props: ['modelValue', 'min', 'max', 'precision', 'step'],
    },
    'el-tag': { template: '<span class="el-tag"><slot /></span>' },
    'el-divider': { template: '<hr class="el-divider"><slot /></hr>' },
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

    it('应该显示限位设置区域', () => {
      expect(wrapper.find('.limit-form').exists()).toBe(true);
    });

    it('应该显示子组件', () => {
      expect(wrapper.find('.pr-path-config-mock').exists()).toBe(true);
      expect(wrapper.find('.motor-position-preset-mock').exists()).toBe(true);
      expect(wrapper.find('.motor-history-panel-mock').exists()).toBe(true);
    });
  });

  describe('急停功能', () => {
    it('急停按钮在连接状态下应该可用', () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      expect(emergencyBtn.attributes('disabled')).toBeUndefined();
    });

    it('急停按钮在断开状态下应该禁用', async () => {
      mockMotorStore.isConnected = false;
      await wrapper.vm.$nextTick();

      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      expect(emergencyBtn.attributes('disabled')).toBeDefined();

      mockMotorStore.isConnected = true;
    });

    it('点击急停按钮应该调用emergencyStop方法', async () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      await emergencyBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.emergencyStop).toHaveBeenCalled();
    });

    it('急停状态下应该显示复位按钮', async () => {
      mockMotorStore.isEmergencyStopped = true;
      mockMotorStore.status = 'emergency_stop';
      await wrapper.vm.$nextTick();

      const resetBtn = wrapper.find('.reset-emergency-btn');
      expect(resetBtn.exists()).toBe(true);

      mockMotorStore.isEmergencyStopped = false;
      mockMotorStore.status = 'ready';
    });

    it('点击复位按钮应该调用resetEmergency方法', async () => {
      mockMotorStore.isEmergencyStopped = true;
      mockMotorStore.status = 'emergency_stop';
      await wrapper.vm.$nextTick();

      const resetBtn = wrapper.find('.reset-emergency-btn');
      await resetBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.resetEmergency).toHaveBeenCalled();

      mockMotorStore.isEmergencyStopped = false;
      mockMotorStore.status = 'ready';
    });
  });

  describe('绝对定位功能', () => {
    it('绝对定位按钮在可控制状态下应该可用', () => {
      const moveBtn = wrapper.find('.move-btn');
      expect(moveBtn.attributes('disabled')).toBeUndefined();
    });

    it('绝对定位按钮在不可控制状态下应该禁用', async () => {
      mockMotorStore.canControl = false;
      await wrapper.vm.$nextTick();

      const moveBtn = wrapper.find('.move-btn');
      expect(moveBtn.attributes('disabled')).toBeDefined();

      mockMotorStore.canControl = true;
    });

    it('点击绝对定位按钮应该调用moveAbsolute方法', async () => {
      wrapper.vm.moveForm.position = 10;
      wrapper.vm.moveForm.velocity = 20;

      const moveBtn = wrapper.find('.move-btn');
      await moveBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.moveAbsolute).toHaveBeenCalledWith(10, 20);
      expect(mockMotorStore.addMovementRecord).toHaveBeenCalled();
    });

    it('运动中应该显示加载状态', async () => {
      wrapper.vm.isMoving = true;
      await wrapper.vm.$nextTick();

      const moveBtn = wrapper.find('.move-btn');
      expect(moveBtn.attributes('loading')).toBe('true');
    });
  });

  describe('回零功能', () => {
    it('点击回零按钮应该调用home方法', async () => {
      const homeBtn = wrapper.find('.home-btn');
      await homeBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.home).toHaveBeenCalledWith(0);
    });
  });

  describe('JOG功能', () => {
    it('JOG按钮在可控制状态下应该可用', () => {
      const jogButtons = wrapper.findAll('.jog-btn');
      jogButtons.forEach(btn => {
        expect(btn.attributes('disabled')).toBeUndefined();
      });
    });

    it('JOG按钮在不可控制状态下应该禁用', async () => {
      mockMotorStore.canControl = false;
      await wrapper.vm.$nextTick();

      const jogButtons = wrapper.findAll('.jog-btn');
      jogButtons.forEach(btn => {
        expect(btn.attributes('disabled')).toBeDefined();
      });

      mockMotorStore.canControl = true;
    });

    it('按下JOG-按钮应该启动负向JOG运动', async () => {
      vi.useFakeTimers();
      wrapper.vm.moveForm.velocity = 15;

      const jogLeftBtn = wrapper.find('.jog-btn-left');
      await jogLeftBtn.trigger('mousedown');
      await flushPromises();

      expect(mockMotorStore.jog).toHaveBeenCalledWith(-1, 15);

      vi.useRealTimers();
      wrapper.vm.stopJog();
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

  describe('限位设置功能', () => {
    it('应该显示正向限位输入框', () => {
      const limitInputs = wrapper.findAll('.limit-input');
      expect(limitInputs.length).toBe(2);
    });

    it('点击应用限位按钮应该调用setLimits方法', async () => {
      wrapper.vm.limitForm.positive = 40;
      wrapper.vm.limitForm.negative = -40;

      const applyBtn = wrapper.find('.apply-limit-btn');
      await applyBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.setLimits).toHaveBeenCalledWith(40, -40);
    });

    it('负向限位大于等于正向限位时应该显示错误', async () => {
      const { ElMessage } = await import('element-plus');

      wrapper.vm.limitForm.positive = 30;
      wrapper.vm.limitForm.negative = 40;

      await wrapper.vm.handleSetLimits();

      expect(ElMessage.error).toHaveBeenCalledWith('负向限位必须小于正向限位');
    });
  });

  describe('限位警告', () => {
    it('位置在限位范围内时应该显示info类型', () => {
      wrapper.vm.moveForm.position = 0;
      expect(wrapper.vm.limitAlertType).toBe('info');
    });

    it('位置超出正向限位时应该显示error类型', () => {
      wrapper.vm.moveForm.position = 60;
      expect(wrapper.vm.limitAlertType).toBe('error');
    });

    it('位置超出负向限位时应该显示error类型', () => {
      wrapper.vm.moveForm.position = -60;
      expect(wrapper.vm.limitAlertType).toBe('error');
    });

    it('位置接近限位边界时应该显示warning类型', () => {
      wrapper.vm.moveForm.position = 48;
      expect(wrapper.vm.limitAlertType).toBe('warning');
    });

    it('超出正向限位时应该显示警告文本', () => {
      wrapper.vm.moveForm.position = 60;
      expect(wrapper.vm.limitWarning).toBe('目标位置超出正向限位！');
    });

    it('超出负向限位时应该显示警告文本', () => {
      wrapper.vm.moveForm.position = -60;
      expect(wrapper.vm.limitWarning).toBe('目标位置超出负向限位！');
    });
  });

  describe('位置输入样式', () => {
    it('位置在范围内时不应有警告样式', () => {
      wrapper.vm.moveForm.position = 0;
      expect(wrapper.vm.positionInputClass).toBe('');
    });

    it('位置超出限位时应该有error样式', () => {
      wrapper.vm.moveForm.position = 60;
      expect(wrapper.vm.positionInputClass).toBe('position-error');
    });

    it('位置接近限位边界时应该有warning样式', () => {
      wrapper.vm.moveForm.position = 48;
      expect(wrapper.vm.positionInputClass).toBe('position-warning');
    });
  });

  describe('报警处理', () => {
    it('有报警消息时应该显示报警提示', async () => {
      mockMotorStore.alarmMessage = '测试报警';
      await wrapper.vm.$nextTick();

      const alert = wrapper.find('.error-alert');
      expect(alert.exists()).toBe(true);
      expect(alert.text()).toContain('测试报警');

      mockMotorStore.alarmMessage = '';
    });

    it('关闭报警提示应该调用clearAlarm方法', async () => {
      mockMotorStore.alarmMessage = '测试报警';
      await wrapper.vm.$nextTick();

      const alert = wrapper.find('.error-alert');
      // 模拟关闭事件
      await alert.vm.$emit('close');

      expect(mockMotorStore.clearAlarm).toHaveBeenCalled();

      mockMotorStore.alarmMessage = '';
    });
  });

  describe('验证功能', () => {
    it('验证位置应该返回正确结果', () => {
      wrapper.vm.moveForm.position = 30;
      const result = wrapper.vm.validatePosition();
      expect(result).toBe(true);
      expect(wrapper.vm.positionError).toBe('');
    });

    it('验证速度应该返回正确结果', () => {
      wrapper.vm.moveForm.velocity = 50;
      const result = wrapper.vm.validateVelocity();
      expect(result).toBe(true);
      expect(wrapper.vm.velocityError).toBe('');
    });
  });

  describe('组件卸载清理', () => {
    it('组件卸载时应该清理JOG定时器', async () => {
      vi.useFakeTimers();
      wrapper.vm.jogInterval = setInterval(() => {}, 100);

      wrapper.unmount();

      // 定时器应该被清除
      expect(wrapper.vm.jogInterval).toBeUndefined();

      vi.useRealTimers();
    });
  });
});
