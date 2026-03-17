/**
 * @file test-utils.js
 * @path frontend/tests/unit/helpers/
 * @description 测试工具函数集合
 * 
 * 提供常用的测试辅助函数、mock工厂函数和组件挂载工具
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @vue/test-utils, vitest, pinia
 */

import { mount, createWrapperError } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { vi } from 'vitest';
import { ref, reactive, computed } from 'vue';

/**
 * 创建Pinia store mock工厂函数
 * 
 * @param {Object} initialState - 初始状态
 * @param {Object} actions - mock actions
 * @returns {Object} mock store
 */
export function createMockStore(initialState = {}, actions = {}) {
  const state = reactive({ ...initialState });
  
  const mockActions = Object.keys(actions).reduce((acc, key) => {
    acc[key] = vi.fn(actions[key]);
    return acc;
  }, {});

  return {
    ...state,
    ...mockActions,
    $patch: vi.fn((newState) => Object.assign(state, newState)),
    $reset: vi.fn(),
    $subscribe: vi.fn(),
    $state: state,
  };
}

/**
 * 创建设备store mock
 * 
 * @param {Object} overrides - 覆盖默认状态
 * @returns {Object} mock设备store
 */
export function createMockDeviceStore(overrides = {}) {
  const defaultState = {
    devices: [],
    connectedDevices: [],
    selectedDevice: null,
    isLoading: false,
    error: null,
    ...overrides,
  };

  return createMockStore(defaultState, {
    fetchDevices: vi.fn(),
    connectDevice: vi.fn(),
    disconnectDevice: vi.fn(),
    selectDevice: vi.fn(),
    updateDeviceStatus: vi.fn(),
  });
}

/**
 * 创建电机store mock
 * 
 * @param {Object} overrides - 覆盖默认状态
 * @returns {Object} mock电机store
 */
export function createMockMotorStore(overrides = {}) {
  const defaultState = {
    position: 0,
    targetPosition: 0,
    speed: 0,
    maxSpeed: 1000,
    isRunning: false,
    isConnected: false,
    error: null,
    ...overrides,
  };

  return createMockStore(defaultState, {
    moveTo: vi.fn(),
    stop: vi.fn(),
    emergencyStop: vi.fn(),
    setSpeed: vi.fn(),
    home: vi.fn(),
    jogStart: vi.fn(),
    jogStop: vi.fn(),
  });
}

/**
 * 创建温度store mock
 * 
 * @param {Object} overrides - 覆盖默认状态
 * @returns {Object} mock温度store
 */
export function createMockTemperatureStore(overrides = {}) {
  const defaultState = {
    currentTemp: 293.15,
    targetTemp: 293.15,
    heatingRate: 0,
    isConnected: false,
    isHeating: false,
    pidParams: { kp: 1, ki: 0, kd: 0 },
    error: null,
    ...overrides,
  };

  return createMockStore(defaultState, {
    setTargetTemp: vi.fn(),
    stopHeating: vi.fn(),
    configurePID: vi.fn(),
    validatePID: vi.fn(),
    startPIDControl: vi.fn(),
    emergencyStop: vi.fn(),
    connect: vi.fn(),
    disconnect: vi.fn(),
  });
}

/**
 * 创建压电store mock
 * 
 * @param {Object} overrides - 覆盖默认状态
 * @returns {Object} mock压电store
 */
export function createMockPiezoStore(overrides = {}) {
  const defaultState = {
    voltage: 0,
    targetVoltage: 0,
    position: { x: 0, y: 0, z: 0 },
    isConnected: false,
    isMoving: false,
    error: null,
    ...overrides,
  };

  return createMockStore(defaultState, {
    setVoltage: vi.fn(),
    setPosition: vi.fn(),
    stop: vi.fn(),
    calibrate: vi.fn(),
  });
}

/**
 * 创建电磁铁store mock
 * 
 * @param {Object} overrides - 覆盖默认状态
 * @returns {Object} mock电磁铁store
 */
export function createMockElectromagnetStore(overrides = {}) {
  const defaultState = {
    current: 0,
    targetCurrent: 0,
    fieldStrength: 0,
    isConnected: false,
    isEnergized: false,
    status: 'disconnected',
    error: null,
    ...overrides,
  };

  return createMockStore(defaultState, {
    setCurrent: vi.fn(),
    energize: vi.fn(),
    deEnergize: vi.fn(),
    stop: vi.fn(),
  });
}

/**
 * 创建用户store mock
 * 
 * @param {Object} overrides - 覆盖默认状态
 * @returns {Object} mock用户store
 */
export function createMockUserStore(overrides = {}) {
  const defaultState = {
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    ...overrides,
  };

  return createMockStore(defaultState, {
    login: vi.fn(),
    logout: vi.fn(),
    fetchUser: vi.fn(),
    updateUser: vi.fn(),
  });
}

/**
 * 创建全局Pinia实例并注册mock stores
 * 
 * @param {Object} stores - store配置对象 { storeName: mockStore }
 * @returns {Object} Pinia实例
 */
export function setupMockPinia(stores = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);

  // 注册mock stores到全局
  Object.entries(stores).forEach(([name, store]) => {
    pinia._s.set(name, store);
  });

  return pinia;
}

/**
 * 挂载组件的便捷方法
 * 
 * @param {Object} component - Vue组件
 * @param {Object} options - 挂载选项
 * @returns {Object} wrapper
 */
export function mountComponent(component, options = {}) {
  const {
    props = {},
    slots = {},
    global = {},
    mocks = {},
    stores = {},
    ...restOptions
  } = options;

  // 设置Pinia
  const pinia = setupMockPinia(stores);

  // 合并全局配置
  const globalConfig = {
    plugins: [pinia, ...(global.plugins || [])],
    mocks: {
      $router: createMockRouter(),
      $route: createMockRoute(),
      ...mocks,
    },
    ...global,
  };

  return mount(component, {
    props,
    slots,
    global: globalConfig,
    ...restOptions,
  });
}

/**
 * 创建mock router
 * 
 * @returns {Object} mock router
 */
export function createMockRouter() {
  return {
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    beforeEach: vi.fn(),
    afterEach: vi.fn(),
    currentRoute: ref({ path: '/', params: {}, query: {} }),
  };
}

/**
 * 创建mock route
 * 
 * @param {Object} overrides - 覆盖默认路由状态
 * @returns {Object} mock route
 */
export function createMockRoute(overrides = {}) {
  return reactive({
    path: '/',
    params: {},
    query: {},
    hash: '',
    name: null,
    meta: {},
    ...overrides,
  });
}

/**
 * 创建mock WebSocket
 * 
 * @returns {Object} mock WebSocket实例
 */
export function createMockWebSocket() {
  const ws = {
    readyState: WebSocket.CONNECTING,
    send: vi.fn(),
    close: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    url: 'ws://localhost:8000/ws',
    binaryType: 'blob',
    CONNECTING: WebSocket.CONNECTING,
    OPEN: WebSocket.OPEN,
    CLOSING: WebSocket.CLOSING,
    CLOSED: WebSocket.CLOSED,
  };

  return ws;
}

/**
 * 创建mock fetch响应
 * 
 * @param {Object} data - 响应数据
 * @param {Object} options - 响应选项
 * @returns {Object} mock Response
 */
export function createMockFetchResponse(data, options = {}) {
  const { status = 200, statusText = 'OK', headers = {} } = options;

  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    headers: new Headers(headers),
    json: vi.fn().mockResolvedValue(data),
    text: vi.fn().mockResolvedValue(JSON.stringify(data)),
    blob: vi.fn().mockResolvedValue(new Blob([JSON.stringify(data)])),
    arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(0)),
  };
}

/**
 * 等待Vue更新完成
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @returns {Promise} 
 */
export async function flushPromises(wrapper = null) {
  await new Promise(resolve => setTimeout(resolve, 0));
  if (wrapper) {
    await wrapper.vm.$nextTick();
  }
}

/**
 * 等待条件满足
 * 
 * @param {Function} condition - 条件函数
 * @param {Object} options - 选项
 * @returns {Promise}
 */
export async function waitFor(condition, options = {}) {
  const { timeout = 5000, interval = 50 } = options;
  const start = Date.now();

  while (!condition()) {
    if (Date.now() - start > timeout) {
      throw new Error('waitFor timeout exceeded');
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }
}

/**
 * 创建mock localStorage
 * 
 * @param {Object} initialData - 初始数据
 * @returns {Object} mock localStorage
 */
export function createMockLocalStorage(initialData = {}) {
  const store = { ...initialData };

  return {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      Object.keys(store).forEach(key => delete store[key]);
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index) => Object.keys(store)[index] || null),
  };
}

/**
 * 创建mock sessionStorage
 * 
 * @param {Object} initialData - 初始数据
 * @returns {Object} mock sessionStorage
 */
export function createMockSessionStorage(initialData = {}) {
  return createMockLocalStorage(initialData);
}

/**
 * 模拟时间流逝
 * 
 * @param {number} ms - 毫秒数
 * @returns {Promise}
 */
export async function advanceTimers(ms) {
  vi.advanceTimersByTime(ms);
  await flushPromises();
}

/**
 * 创建响应式ref的便捷方法
 * 
 * @param {*} value - 初始值
 * @returns {Object} ref对象
 */
export function createRef(value) {
  return ref(value);
}

/**
 * 创建响应式computed的便捷方法
 * 
 * @param {Function} getter - 计算函数
 * @returns {Object} computed对象
 */
export function createComputed(getter) {
  return computed(getter);
}

/**
 * 断言wrapper包含指定文本
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} text - 期望包含的文本
 */
export function assertTextContains(wrapper, text) {
  expect(wrapper.text()).toContain(text);
}

/**
 * 断言wrapper不包含指定文本
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} text - 期望不包含的文本
 */
export function assertTextNotContains(wrapper, text) {
  expect(wrapper.text()).not.toContain(text);
}

/**
 * 断言元素存在
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} selector - 选择器
 */
export function assertElementExists(wrapper, selector) {
  expect(wrapper.find(selector).exists()).toBe(true);
}

/**
 * 断言元素不存在
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} selector - 选择器
 */
export function assertElementNotExists(wrapper, selector) {
  expect(wrapper.find(selector).exists()).toBe(false);
}

/**
 * 触发DOM事件并等待更新
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} event - 事件名
 * @param {Object} options - 事件选项
 */
export async function triggerAndWait(wrapper, event, options = {}) {
  await wrapper.trigger(event, options);
  await flushPromises(wrapper);
}

/**
 * 创建mock axios实例
 * 
 * @returns {Object} mock axios
 */
export function createMockAxios() {
  return {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
    request: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn(),
        eject: vi.fn(),
      },
      response: {
        use: vi.fn(),
        eject: vi.fn(),
      },
    },
    defaults: {
      baseURL: '',
      headers: {},
    },
  };
}

/**
 * 创建mock ECharts实例
 * 
 * @returns {Object} mock ECharts
 */
export function createMockECharts() {
  return {
    setOption: vi.fn(),
    getOption: vi.fn(() => ({})),
    resize: vi.fn(),
    dispose: vi.fn(),
    clear: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    dispatchAction: vi.fn(),
    getDataURL: vi.fn(() => 'data:image/png;base64,mock'),
    getWidth: vi.fn(() => 800),
    getHeight: vi.fn(() => 600),
  };
}

/**
 * 测试工具导出
 */
export default {
  createMockStore,
  createMockDeviceStore,
  createMockMotorStore,
  createMockTemperatureStore,
  createMockPiezoStore,
  createMockElectromagnetStore,
  createMockUserStore,
  setupMockPinia,
  mountComponent,
  createMockRouter,
  createMockRoute,
  createMockWebSocket,
  createMockFetchResponse,
  flushPromises,
  waitFor,
  createMockLocalStorage,
  createMockSessionStorage,
  advanceTimers,
  createRef,
  createComputed,
  assertTextContains,
  assertTextNotContains,
  assertElementExists,
  assertElementNotExists,
  triggerAndWait,
  createMockAxios,
  createMockECharts,
};
