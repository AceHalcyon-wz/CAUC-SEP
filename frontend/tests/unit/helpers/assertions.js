/**
 * @file assertions.js
 * @path frontend/tests/unit/helpers/
 * @description 语义化断言工具函数集合
 * 
 * 提供可读性强的断言函数，提高测试代码可维护性
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies vitest
 */

import { expect } from 'vitest';

/**
 * 断言元素存在
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} selector - CSS选择器
 * @param {string} message - 自定义错误消息
 */
export function assertElementExists(wrapper, selector, message = '') {
  const element = wrapper.find(selector);
  expect(element.exists(), `元素 ${selector} 应该存在。${message}`).toBe(true);
}

/**
 * 断言元素不存在
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} selector - CSS选择器
 * @param {string} message - 自定义错误消息
 */
export function assertElementNotExists(wrapper, selector, message = '') {
  const element = wrapper.find(selector);
  expect(element.exists(), `元素 ${selector} 不应该存在。${message}`).toBe(false);
}

/**
 * 断言文本包含
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} text - 期望包含的文本
 * @param {string} message - 自定义错误消息
 */
export function assertTextContains(wrapper, text, message = '') {
  expect(wrapper.text(), `应该包含文本 "${text}"。${message}`).toContain(text);
}

/**
 * 断言文本不包含
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} text - 期望不包含的文本
 * @param {string} message - 自定义错误消息
 */
export function assertTextNotContains(wrapper, text, message = '') {
  expect(wrapper.text(), `不应该包含文本 "${text}"。${message}`).not.toContain(text);
}

/**
 * 断言元素可见
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} selector - CSS选择器
 * @param {string} message - 自定义错误消息
 */
export function assertElementVisible(wrapper, selector, message = '') {
  const element = wrapper.find(selector);
  expect(element.exists(), `元素 ${selector} 应该存在。${message}`).toBe(true);
  expect(element.isVisible(), `元素 ${selector} 应该可见。${message}`).toBe(true);
}

/**
 * 断言元素隐藏
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} selector - CSS选择器
 * @param {string} message - 自定义错误消息
 */
export function assertElementHidden(wrapper, selector, message = '') {
  const element = wrapper.find(selector);
  expect(element.exists(), `元素 ${selector} 应该存在。${message}`).toBe(true);
  expect(element.isVisible(), `元素 ${selector} 应该隐藏。${message}`).toBe(false);
}

/**
 * 断言按钮禁用
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} selector - CSS选择器
 * @param {string} message - 自定义错误消息
 */
export function assertButtonDisabled(wrapper, selector, message = '') {
  const button = wrapper.find(selector);
  expect(button.exists(), `按钮 ${selector} 应该存在。${message}`).toBe(true);
  expect(button.attributes('disabled'), `按钮 ${selector} 应该被禁用。${message}`).toBeDefined();
}

/**
 * 断言按钮启用
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} selector - CSS选择器
 * @param {string} message - 自定义错误消息
 */
export function assertButtonEnabled(wrapper, selector, message = '') {
  const button = wrapper.find(selector);
  expect(button.exists(), `按钮 ${selector} 应该存在。${message}`).toBe(true);
  expect(button.attributes('disabled'), `按钮 ${selector} 应该启用。${message}`).toBeUndefined();
}

/**
 * 断言输入框值
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} selector - CSS选择器
 * @param {string|number} expectedValue - 期望值
 * @param {string} message - 自定义错误消息
 */
export function assertInputValue(wrapper, selector, expectedValue, message = '') {
  const input = wrapper.find(selector);
  expect(input.exists(), `输入框 ${selector} 应该存在。${message}`).toBe(true);
  expect(input.element.value, `输入框值应该为 ${expectedValue}。${message}`).toBe(String(expectedValue));
}

/**
 * 断言组件属性
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} propName - 属性名
 * @param {*} expectedValue - 期望值
 * @param {string} message - 自定义错误消息
 */
export function assertProp(wrapper, propName, expectedValue, message = '') {
  expect(wrapper.props(propName), `属性 ${propName} 应该为 ${expectedValue}。${message}`).toBe(expectedValue);
}

/**
 * 断言组件属性存在
 * 
 * @param {Object} wrapper - Vue Test Utils wrapper
 * @param {string} propName - 属性名
 * @param {string} message - 自定义错误消息
 */
export function assertPropExists(wrapper, propName, message = '') {
  expect(wrapper.props(propName), `属性 ${propName} 应该存在。${message}`).toBeDefined();
}

/**
 * 断言Store状态
 * 
 * @param {Object} store - Pinia store
 * @param {string} stateKey - 状态键
 * @param {*} expectedValue - 期望值
 * @param {string} message - 自定义错误消息
 */
export function assertStoreState(store, stateKey, expectedValue, message = '') {
  expect(store[stateKey], `Store状态 ${stateKey} 应该为 ${expectedValue}。${message}`).toBe(expectedValue);
}

/**
 * 断言Store action被调用
 * 
 * @param {Object} store - Pinia store
 * @param {string} actionName - action名称
 * @param {Array} expectedArgs - 期望参数
 * @param {string} message - 自定义错误消息
 */
export function assertStoreActionCalled(store, actionName, expectedArgs = null, message = '') {
  expect(store[actionName], `Store action ${actionName} 应该被调用。${message}`).toHaveBeenCalled();
  if (expectedArgs) {
    expect(store[actionName], `Store action ${actionName} 参数应该匹配。${message}`).toHaveBeenCalledWith(...expectedArgs);
  }
}

/**
 * 断言Store action未被调用
 * 
 * @param {Object} store - Pinia store
 * @param {string} actionName - action名称
 * @param {string} message - 自定义错误消息
 */
export function assertStoreActionNotCalled(store, actionName, message = '') {
  expect(store[actionName], `Store action ${actionName} 不应该被调用。${message}`).not.toHaveBeenCalled();
}

/**
 * 断言API响应成功
 * 
 * @param {Object} response - API响应
 * @param {string} message - 自定义错误消息
 */
export function assertApiSuccess(response, message = '') {
  expect(response.status, `API响应状态应该为200。${message}`).toBe(200);
  if (response.data && 'success' in response.data) {
    expect(response.data.success, `API响应应该成功。${message}`).toBe(true);
  }
}

/**
 * 断言API响应错误
 * 
 * @param {Object} response - API响应
 * @param {number} expectedStatus - 期望状态码
 * @param {string} message - 自定义错误消息
 */
export function assertApiError(response, expectedStatus, message = '') {
  expect(response.status, `API响应状态应该为 ${expectedStatus}。${message}`).toBe(expectedStatus);
}

/**
 * 断言WebSocket连接状态
 * 
 * @param {Object} ws - WebSocket composable
 * @param {string} expectedState - 期望状态
 * @param {string} message - 自定义错误消息
 */
export function assertWebSocketState(ws, expectedState, message = '') {
  expect(ws.connectionState.value, `WebSocket状态应该为 ${expectedState}。${message}`).toBe(expectedState);
}

/**
 * 断言数组长度
 * 
 * @param {Array} array - 数组
 * @param {number} expectedLength - 期望长度
 * @param {string} message - 自定义错误消息
 */
export function assertArrayLength(array, expectedLength, message = '') {
  expect(array.length, `数组长度应该为 ${expectedLength}。${message}`).toBe(expectedLength);
}

/**
 * 断言对象包含属性
 * 
 * @param {Object} obj - 对象
 * @param {Array<string>} props - 属性名数组
 * @param {string} message - 自定义错误消息
 */
export function assertObjectHasProps(obj, props, message = '') {
  props.forEach(prop => {
    expect(obj, `对象应该包含属性 ${prop}。${message}`).toHaveProperty(prop);
  });
}

/**
 * 断言数值在范围内
 * 
 * @param {number} value - 数值
 * @param {number} min - 最小值
 * @param {number} max - 最大值
 * @param {string} message - 自定义错误消息
 */
export function assertInRange(value, min, max, message = '') {
  expect(value, `值 ${value} 应该在范围 [${min}, ${max}] 内。${message}`).toBeGreaterThanOrEqual(min);
  expect(value, `值 ${value} 应该在范围 [${min}, ${max}] 内。${message}`).toBeLessThanOrEqual(max);
}

/**
 * 断言数值接近
 * 
 * @param {number} actual - 实际值
 * @param {number} expected - 期望值
 * @param {number} precision - 精度
 * @param {string} message - 自定义错误消息
 */
export function assertApproximately(actual, expected, precision = 0.001, message = '') {
  expect(actual, `值应该接近 ${expected}（精度 ${precision}）。${message}`).toBeCloseTo(expected, precision);
}

export default {
  assertElementExists,
  assertElementNotExists,
  assertTextContains,
  assertTextNotContains,
  assertElementVisible,
  assertElementHidden,
  assertButtonDisabled,
  assertButtonEnabled,
  assertInputValue,
  assertProp,
  assertPropExists,
  assertStoreState,
  assertStoreActionCalled,
  assertStoreActionNotCalled,
  assertApiSuccess,
  assertApiError,
  assertWebSocketState,
  assertArrayLength,
  assertObjectHasProps,
  assertInRange,
  assertApproximately,
};
