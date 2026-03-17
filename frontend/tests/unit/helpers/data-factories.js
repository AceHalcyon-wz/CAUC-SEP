/**
 * @file data-factories.js
 * @path frontend/tests/unit/helpers/
 * @description 测试数据工厂函数集合
 * 
 * 提供统一的测试数据生成方法，避免硬编码
 * 
 * @author Agent
 * @date 2024-03-16
 */

/**
 * 创建电机状态数据
 * 
 * @param {Object} overrides - 覆盖默认值
 * @returns {Object} 电机状态对象
 */
export function createMotorStatus(overrides = {}) {
  const defaults = {
    device_id: 'test_motor',
    status: 'ready',
    position_steps: 0,
    position_mm: 0.0,
    velocity_mm_s: 0.0,
    alarm_code: 0,
    alarm_text: '无报警',
    status_word: {
      fault: false,
      enabled: true,
      running: false,
      cmd_complete: true,
      path_complete: true,
      home_complete: true,
      raw_value: 0x72,
    },
    limit_positive: 100.0,
    limit_negative: -100.0,
    connected: true,
    simulation: true,
  };

  return { ...defaults, ...overrides };
}

/**
 * 创建压电陶瓷状态数据
 * 
 * @param {Object} overrides - 覆盖默认值
 * @returns {Object} 压电陶瓷状态对象
 */
export function createPiezoStatus(overrides = {}) {
  const defaults = {
    device_id: 'test_piezo',
    status: 'ready',
    control_mode: 'open_loop',
    current_voltage_v: 0.0,
    current_displacement_um: 0.0,
    target_displacement_um: 0.0,
    calibration_valid: false,
    calibration_points: 0,
    max_voltage_v: 150.0,
    max_displacement_um: 100.0,
    connected: true,
    simulation: true,
  };

  return { ...defaults, ...overrides };
}

/**
 * 创建电磁铁状态数据
 * 
 * @param {Object} overrides - 覆盖默认值
 * @returns {Object} 电磁铁状态对象
 */
export function createElectromagnetStatus(overrides = {}) {
  const defaults = {
    device_id: 'test_electromagnet',
    electromagnet_status: 'ready',
    current_value: 0.0,
    field_value: 0.0,
    scan_progress: 0.0,
    max_current_limit: 10.0,
    connected: true,
    simulation: true,
  };

  return { ...defaults, ...overrides };
}

/**
 * 创建温控状态数据
 * 
 * @param {Object} overrides - 覆盖默认值
 * @returns {Object} 温控状态对象
 */
export function createTemperatureStatus(overrides = {}) {
  const defaults = {
    device_id: 'test_temp_controller',
    status: 'ready',
    current_temperature: 300.0,
    current_output: 0.0,
    setpoint: 300.0,
    mode: 'PID',
    pid_running: false,
    connected: true,
    simulation: true,
    program: { running: false, progress: 0.0 },
    protection: { triggered: false, type: null },
  };

  return { ...defaults, ...overrides };
}

/**
 * 创建微电流计状态数据
 * 
 * @param {Object} overrides - 覆盖默认值
 * @returns {Object} 微电流计状态对象
 */
export function createAmmeterStatus(overrides = {}) {
  const defaults = {
    device_id: 'test_ammeter',
    status: 'ready',
    sample_rate: 100.0,
    num_channels: 4,
    acquiring: false,
    buffer_size: 1000,
    connected: true,
    simulation: true,
  };

  return { ...defaults, ...overrides };
}

/**
 * 创建设备列表数据
 * 
 * @param {number} count - 设备数量
 * @returns {Object} 设备列表响应对象
 */
export function createDeviceListResponse(count = 3) {
  const devices = [];
  const deviceTypes = ['stepper_motor', 'piezo', 'electromagnet', 'temperature', 'ammeter'];

  for (let i = 0; i < count; i++) {
    devices.push({
      device_id: `device_${i + 1}`,
      device_type: deviceTypes[i % deviceTypes.length],
      device_name: `测试设备 ${i + 1}`,
      status: 'ready',
    });
  }

  return {
    count: devices.length,
    devices,
  };
}

/**
 * 创建运动历史数据
 * 
 * @param {number} count - 记录数量
 * @returns {Array} 运动历史数组
 */
export function createMovementHistory(count = 5) {
  const history = [];
  const now = Date.now();

  for (let i = 0; i < count; i++) {
    history.push({
      id: i + 1,
      type: i % 2 === 0 ? 'absolute' : 'jog',
      position: i * 10,
      velocity: 20,
      timestamp: new Date(now - i * 60000).toISOString(),
      success: true,
    });
  }

  return history;
}

/**
 * 创建位置预设数据
 * 
 * @param {number} count - 预设数量
 * @returns {Array} 位置预设数组
 */
export function createPositionPresets(count = 3) {
  const presets = [];

  for (let i = 0; i < count; i++) {
    presets.push({
      id: i + 1,
      name: `预设位置 ${i + 1}`,
      position: i * 20,
      description: `测试预设位置 ${i + 1}`,
    });
  }

  return presets;
}

/**
 * 创建PR路径配置数据
 * 
 * @param {number} pathNumber - 路径编号
 * @returns {Object} PR路径配置对象
 */
export function createPRPathConfig(pathNumber = 0) {
  return {
    path_number: pathNumber,
    mode: 1,
    position_mm: pathNumber * 10,
    velocity_mm_s: 1000,
    accel_time: 100,
    decel_time: 100,
    dwell_time: 0,
    special_param: 0,
  };
}

/**
 * 创建校准数据
 * 
 * @param {number} pointCount - 校准点数量
 * @returns {Object} 校准数据对象
 */
export function createCalibrationData(pointCount = 3) {
  const points = [];
  for (let i = 0; i < pointCount; i++) {
    points.push({
      voltage_v: i * 50,
      displacement_um: i * 33.33,
    });
  }

  return {
    valid: true,
    type: 'polynomial',
    points,
    coefficients: [0, 0.667, 0],
    point_count: pointCount,
  };
}

/**
 * 创建分析结果数据
 * 
 * @param {string} type - 分析类型
 * @returns {Object} 分析结果对象
 */
export function createAnalysisResult(type = 'hysteresis') {
  if (type === 'hysteresis') {
    return {
      type: 'hysteresis',
      coercivity: 200.0,
      remanence: 0.5,
      saturation: 1.0,
      squareness: 0.8,
      area: 150.5,
      quality: 'good',
    };
  }

  return {
    type: 'general',
    peak_count: 2,
    mean: 0.5,
    std: 0.1,
    min: 0.0,
    max: 1.0,
  };
}

export default {
  createMotorStatus,
  createPiezoStatus,
  createElectromagnetStatus,
  createTemperatureStatus,
  createAmmeterStatus,
  createDeviceListResponse,
  createMovementHistory,
  createPositionPresets,
  createPRPathConfig,
  createCalibrationData,
  createAnalysisResult,
};
