/**
 * @file MotorControl.test.js
 * @path frontend/tests/unit/components/
 * @description MotorControl组件单元测试
 * @author Agent
 * @date 2024-03-16
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
    prConfig: false,
    prTrigger: false,
    resetAlarm: false,
    saveParams: false,
    factoryReset: false,
    statusWord: false,
    alarmCode: false,
    smooth: false,
    fit: false,
    hysteresis: false,
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
  statusWord: null,
  alarmCode: null,
  alarmText: '',
  prPaths: {},
  analysisResult: null,
  positionPresets: [],
  movementHistory: [],
  positionHistory: [],
  pathTemplates: [],
  limitStatus: '正常',
  limitStatusType: 'success',
  moveAbsolute: vi.fn().mockResolvedValue(true),
  jog: vi.fn().mockResolvedValue(true),
  emergencyStop: vi.fn().mockResolvedValue(true),
  resetEmergency: vi.fn().mockResolvedValue(true),
  setLimits: vi.fn().mockResolvedValue(true),
  home: vi.fn().mockResolvedValue(true),
  clearAlarm: vi.fn(),
  addMovementRecord: vi.fn(),
  fetchStatus: vi.fn().mockResolvedValue(true),
  connectMotor: vi.fn().mockResolvedValue(true),
  disconnectMotor: vi.fn().mockResolvedValue(true),
  configurePRPath: vi.fn().mockResolvedValue(true),
  triggerPRPath: vi.fn().mockResolvedValue(true),
  resetAlarm: vi.fn().mockResolvedValue(true),
  saveParams: vi.fn().mockResolvedValue(true),
  factoryReset: vi.fn().mockResolvedValue(true),
  readStatusWord: vi.fn().mockResolvedValue({}),
  readAlarmCode: vi.fn().mockResolvedValue({ alarm_code: 0, alarm_text: '' }),
  smoothSignal: vi.fn().mockResolvedValue({}),
  fitCurve: vi.fn().mockResolvedValue({}),
  analyzeHysteresis: vi.fn().mockResolvedValue({}),
  fetchCurrentPosition: vi.fn().mockResolvedValue({}),
  clearPositionHistory: vi.fn(),
  addPositionPreset: vi.fn().mockReturnValue(true),
  updatePositionPreset: vi.fn().mockReturnValue(true),
  deletePositionPreset: vi.fn().mockReturnValue(true),
  applyPositionPreset: vi.fn().mockResolvedValue(true),
  clearMovementHistory: vi.fn(),
  exportMovementHistory: vi.fn().mockReturnValue('[]'),
  loadPathTemplates: vi.fn(),
  addPathTemplate: vi.fn().mockReturnValue(true),
  updatePathTemplate: vi.fn().mockReturnValue(true),
  deletePathTemplate: vi.fn().mockReturnValue(true),
  applyPathTemplate: vi.fn().mockResolvedValue(true),
  exportPathTemplate: vi.fn().mockReturnValue('{}'),
  importPathTemplate: vi.fn().mockReturnValue(true),
  getPathTemplates: vi.fn().mockReturnValue([]),
  duplicatePathTemplate: vi.fn().mockReturnValue(true),
  showError: vi.fn(),
  cleanup: vi.fn(),
};

vi.mock('@/stores/motor', () => ({
  useMotorStore: vi.fn(() => mockMotorStore),
}));

vi.mock('@/utils/validation', () => ({
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

vi.mock('@/config/constants', () => ({
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
    info: vi.fn(),
  },
  ElMessageBox: {
    confirm: vi.fn().mockResolvedValue(true),
    alert: vi.fn(),
  },
}));

vi.mock('@/components/device', () => ({
  PRPathConfig: { template: '<div class="pr-path-config-mock">PRPathConfig</div>' },
}));

vi.mock('./MotorPositionPreset.vue', () => ({
  default: { template: '<div class="motor-position-preset-mock">MotorPositionPreset</div>' },
}));

vi.mock('./MotorTrajectoryPreview.vue', () => ({
  default: { template: '<div class="motor-trajectory-preview-mock">MotorTrajectoryPreview</div>' },
}));

vi.mock('./MotorHistoryPanel.vue', () => ({
  default: { template: '<div class="motor-history-panel-mock">MotorHistoryPanel</div>' },
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
  'el-tag': { template: '<span class="el-tag"><slot /></span>' },
  'el-divider': { template: '<hr class="el-divider"><slot /></hr>' },
  'el-select': { template: '<select class="el-select" :disabled="disabled" @change="$emit(\'change\', $event.target.value)"><slot /></select>' },
  'el-option': { template: '<option class="el-option" :value="value"><slot /></option>' },
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
  'Setting': { template: '<span class="setting-icon"></span>' },
  'Check': { template: '<span class="check-icon"></span>' },
};

describe('MotorControl', () => {
  let wrapper;
  let pinia;

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

    it('应该显示PR路径配置组件', () => {
      expect(wrapper.find('.pr-path-config-mock').exists()).toBe(true);
    });

    it('应该显示位置预设组件', () => {
      expect(wrapper.find('.motor-position-preset-mock').exists()).toBe(true);
    });

    it('应该显示运动历史面板组件', () => {
      expect(wrapper.find('.motor-history-panel-mock').exists()).toBe(true);
    });

    it('应该显示轨迹预览组件', () => {
      expect(wrapper.find('.motor-trajectory-preview-mock').exists()).toBe(true);
    });
  });

  describe('位置控制功能', () => {
    it('应该显示目标位置输入框', () => {
      const positionInput = wrapper.find('.position-input');
      expect(positionInput.exists()).toBe(true);
    });

    it('位置输入框应该有限制范围', () => {
      const positionInput = wrapper.find('.position-input');
      expect(positionInput.attributes('min')).toBeDefined();
      expect(positionInput.attributes('max')).toBeDefined();
    });

    it('应该显示位置单位mm', () => {
      expect(wrapper.text()).toContain('mm');
    });

    it('应该显示限位范围提示', () => {
      expect(wrapper.text()).toContain('限位范围');
    });

    it('位置超出限位应该显示错误样式', async () => {
      wrapper.vm.moveForm.position = 60;
      await wrapper.vm.$nextTick();

      const positionInput = wrapper.find('.position-input');
      expect(positionInput.classes()).toContain('position-error');
    });

    it('位置接近限位应该显示警告样式', async () => {
      wrapper.vm.moveForm.position = 48;
      await wrapper.vm.$nextTick();

      const positionInput = wrapper.find('.position-input');
      expect(positionInput.classes()).toContain('position-warning');
    });

    it('位置在正常范围内不应该显示警告样式', async () => {
      wrapper.vm.moveForm.position = 0;
      await wrapper.vm.$nextTick();

      const positionInput = wrapper.find('.position-input');
      expect(positionInput.classes()).not.toContain('position-error');
      expect(positionInput.classes()).not.toContain('position-warning');
    });
  });

  describe('速度控制功能', () => {
    it('应该显示运动速度输入框', () => {
      const velocityInput = wrapper.find('.velocity-input');
      expect(velocityInput.exists()).toBe(true);
    });

    it('速度输入框应该有限制范围', () => {
      const velocityInput = wrapper.find('.velocity-input');
      expect(velocityInput.attributes('min')).toBeDefined();
      expect(velocityInput.attributes('max')).toBeDefined();
    });

    it('应该显示速度单位mm/s', () => {
      expect(wrapper.text()).toContain('mm/s');
    });

    it('应该显示速度范围提示', () => {
      expect(wrapper.text()).toContain('0.1-100');
    });
  });

  describe('急停功能', () => {
    it('急停按钮应该存在', () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      expect(emergencyBtn.exists()).toBe(true);
    });

    it('点击急停按钮应该调用emergencyStop方法', async () => {
      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      await emergencyBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.emergencyStop).toHaveBeenCalled();
    });

    it('急停状态下应该显示复位急停按钮', async () => {
      mockMotorStore.isEmergencyStopped = true;
      await wrapper.vm.$nextTick();

      const resetBtn = wrapper.find('.reset-emergency-btn');
      expect(resetBtn.exists()).toBe(true);
    });

    it('点击复位急停按钮应该调用resetEmergency方法', async () => {
      mockMotorStore.isEmergencyStopped = true;
      await wrapper.vm.$nextTick();

      const resetBtn = wrapper.find('.reset-emergency-btn');
      await resetBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.resetEmergency).toHaveBeenCalled();
    });

    it('急停状态下应该显示急停警告', async () => {
      mockMotorStore.isEmergencyStopped = true;
      await wrapper.vm.$nextTick();

      const alert = wrapper.find('.emergency-alert');
      expect(alert.exists()).toBe(true);
    });

    it('未连接时急停按钮应该禁用', async () => {
      mockMotorStore.isConnected = false;
      await wrapper.vm.$nextTick();

      const emergencyBtn = wrapper.find('.emergency-stop-btn');
      expect(emergencyBtn.attributes('disabled')).toBeDefined();
    });
  });

  describe('绝对定位功能', () => {
    it('绝对定位按钮应该存在', () => {
      const moveBtn = wrapper.find('.move-btn');
      expect(moveBtn.exists()).toBe(true);
    });

    it('点击绝对定位按钮应该调用moveAbsolute方法', async () => {
      wrapper.vm.moveForm.position = 10;
      wrapper.vm.moveForm.velocity = 20;

      const moveBtn = wrapper.find('.move-btn');
      await moveBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.moveAbsolute).toHaveBeenCalledWith(10, 20);
    });

    it('运动中应该显示加载状态', async () => {
      wrapper.vm.isMoving = true;
      await wrapper.vm.$nextTick();

      const moveBtn = wrapper.find('.move-btn');
      expect(moveBtn.attributes('loading')).toBeDefined();
    });

    it('位置验证失败时不应该调用moveAbsolute', async () => {
      wrapper.vm.moveForm.position = 100; // 超出限位

      const moveBtn = wrapper.find('.move-btn');
      await moveBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.moveAbsolute).not.toHaveBeenCalled();
    });

    it('无法控制时绝对定位按钮应该禁用', async () => {
      mockMotorStore.canControl = false;
      await wrapper.vm.$nextTick();

      const moveBtn = wrapper.find('.move-btn');
      expect(moveBtn.attributes('disabled')).toBeDefined();
    });
  });

  describe('回零功能', () => {
    it('回零按钮应该存在', () => {
      const homeBtn = wrapper.find('.home-btn');
      expect(homeBtn.exists()).toBe(true);
    });

    it('点击回零按钮应该调用home方法', async () => {
      const homeBtn = wrapper.find('.home-btn');
      await homeBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.home).toHaveBeenCalled();
    });

    it('应该显示回零模式选择器', () => {
      const homeModeSelect = wrapper.find('.home-mode-select');
      expect(homeModeSelect.exists()).toBe(true);
    });

    it('应该有10种回零模式选项', () => {
      expect(wrapper.vm.HOME_MODE_OPTIONS.length).toBe(10);
    });

    it('无法控制时回零按钮应该禁用', async () => {
      mockMotorStore.canControl = false;
      await wrapper.vm.$nextTick();

      const homeBtn = wrapper.find('.home-btn');
      expect(homeBtn.attributes('disabled')).toBeDefined();
    });
  });

  describe('JOG功能', () => {
    it('JOG按钮应该存在', () => {
      const jogButtons = wrapper.findAll('.jog-btn');
      expect(jogButtons.length).toBe(2);
    });

    it('应该有JOG-和JOG+两个按钮', () => {
      const jogLeftBtn = wrapper.find('.jog-btn-left');
      const jogRightBtn = wrapper.find('.jog-btn-right');

      expect(jogLeftBtn.exists()).toBe(true);
      expect(jogRightBtn.exists()).toBe(true);
      expect(jogLeftBtn.text()).toContain('JOG-');
      expect(jogRightBtn.text()).toContain('JOG+');
    });

    it('按下JOG按钮应该开始JOG运动', async () => {
      vi.useFakeTimers();
      wrapper.vm.moveForm.velocity = 15;

      const jogLeftBtn = wrapper.find('.jog-btn-left');
      await jogLeftBtn.trigger('mousedown');
      await flushPromises();

      expect(wrapper.vm.jogState.active).toBe(true);
      expect(wrapper.vm.jogState.direction).toBe(-1);

      vi.useRealTimers();
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

    it('JOG运动中应该显示运行中指示器', async () => {
      vi.useFakeTimers();
      wrapper.vm.jogState.active = true;
      wrapper.vm.jogState.direction = -1;
      await wrapper.vm.$nextTick();

      const jogLeftBtn = wrapper.find('.jog-btn-left');
      expect(jogLeftBtn.classes()).toContain('jog-active');

      vi.useRealTimers();
    });

    it('无法控制时JOG按钮应该禁用', async () => {
      mockMotorStore.canControl = false;
      await wrapper.vm.$nextTick();

      const jogButtons = wrapper.findAll('.jog-btn');
      jogButtons.forEach(btn => {
        expect(btn.attributes('disabled')).toBeDefined();
      });
    });
  });

  describe('限位设置功能', () => {
    it('应该显示限位设置表单', () => {
      expect(wrapper.find('.limit-form').exists()).toBe(true);
    });

    it('应该显示正向限位输入框', () => {
      const limitInputs = wrapper.findAll('.limit-input');
      expect(limitInputs.length).toBe(2);
    });

    it('应该显示应用限位按钮', () => {
      const applyBtn = wrapper.find('.apply-limit-btn');
      expect(applyBtn.exists()).toBe(true);
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
      wrapper.vm.limitForm.positive = 30;
      wrapper.vm.limitForm.negative = 40;

      const applyBtn = wrapper.find('.apply-limit-btn');
      await applyBtn.trigger('click');
      await flushPromises();

      expect(mockMotorStore.setLimits).not.toHaveBeenCalled();
    });
  });

  describe('报警处理功能', () => {
    it('有报警消息时应该显示错误提示', async () => {
      mockMotorStore.alarmMessage = '测试报警';
      await wrapper.vm.$nextTick();

      const alert = wrapper.find('.error-alert');
      expect(alert.exists()).toBe(true);
    });

    it('关闭报警提示应该调用clearAlarm方法', async () => {
      mockMotorStore.alarmMessage = '测试报警';
      await wrapper.vm.$nextTick();

      // 模拟关闭报警
      wrapper.vm.motorStore.clearAlarm();
      expect(mockMotorStore.clearAlarm).toHaveBeenCalled();
    });
  });

  describe('状态显示功能', () => {
    it('应该显示限位范围信息', () => {
      const limitAlert = wrapper.find('.limit-alert');
      expect(limitAlert.exists()).toBe(true);
    });

    it('位置接近限位边界时应该显示警告文本', async () => {
      wrapper.vm.moveForm.position = 48;
      await wrapper.vm.$nextTick();

      const warningText = wrapper.find('.limit-warning-text');
      expect(warningText.exists()).toBe(true);
    });

    it('位置超出限位时应该显示错误文本', async () => {
      wrapper.vm.moveForm.position = 60;
      await wrapper.vm.$nextTick();

      const warningText = wrapper.find('.limit-warning-text');
      expect(warningText.exists()).toBe(true);
      expect(warningText.text()).toContain('超出');
    });
  });

  describe('组件卸载清理', () => {
    it('组件卸载时应该停止JOG运动', async () => {
      vi.useFakeTimers();
      wrapper.vm.jogState.active = true;
      wrapper.vm.jogInterval = setInterval(() => {}, 100);

      wrapper.unmount();

      expect(wrapper.vm.jogInterval).toBeNull();
      vi.useRealTimers();
    });
  });

  describe('验证函数测试', () => {
    it('validatePosition应该正确验证位置', () => {
      wrapper.vm.moveForm.position = 0;
      const result = wrapper.vm.validatePosition();
      expect(result).toBe(true);
    });

    it('validatePosition应该拒绝超出限位的位置', () => {
      wrapper.vm.moveForm.position = 100;
      const result = wrapper.vm.validatePosition();
      expect(result).toBe(false);
      expect(wrapper.vm.positionError).not.toBe('');
    });

    it('validateVelocity应该正确验证速度', () => {
      wrapper.vm.moveForm.velocity = 50;
      const result = wrapper.vm.validateVelocity();
      expect(result).toBe(true);
    });

    it('validateVelocity应该拒绝超出范围的速度', () => {
      wrapper.vm.moveForm.velocity = 200;
      const result = wrapper.vm.validateVelocity();
      expect(result).toBe(false);
      expect(wrapper.vm.velocityError).not.toBe('');
    });
  });

  describe('计算属性测试', () => {
    it('positionInputClass应该返回正确的样式类', async () => {
      wrapper.vm.moveForm.position = 0;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.positionInputClass).toBe('');

      wrapper.vm.moveForm.position = 48;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.positionInputClass).toBe('position-warning');

      wrapper.vm.moveForm.position = 60;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.positionInputClass).toBe('position-error');
    });

    it('limitAlertType应该返回正确的类型', async () => {
      wrapper.vm.moveForm.position = 0;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.limitAlertType).toBe('info');

      wrapper.vm.moveForm.position = 48;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.limitAlertType).toBe('warning');

      wrapper.vm.moveForm.position = 60;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.limitAlertType).toBe('error');
    });

    it('limitWarning应该返回正确的警告文本', async () => {
      wrapper.vm.moveForm.position = 0;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.limitWarning).toBe('');

      wrapper.vm.moveForm.position = 48;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.limitWarning).toContain('接近');

      wrapper.vm.moveForm.position = 60;
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.limitWarning).toContain('超出');
    });
  });
});
