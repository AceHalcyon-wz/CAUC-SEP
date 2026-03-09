/**
 * @file connectionTemplates.js
 * @path src/config/
 * @description 连接配置模板定义，提供预定义的设备连接参数模板
 * @author Agent
 * @date 2024-03-07
 */

/**
 * 波特率选项
 * @constant {Array<{label: string, value: number}>}
 */
export const BAUDRATE_OPTIONS = [
  { label: '9600', value: 9600 },
  { label: '19200', value: 19200 },
  { label: '38400', value: 38400 },
  { label: '57600', value: 57600 },
  { label: '115200', value: 115200 },
  { label: '230400', value: 230400 },
  { label: '460800', value: 460800 },
  { label: '921600', value: 921600 }
]

/**
 * 数据位选项
 * @constant {Array<{label: string, value: number}>}
 */
export const DATABITS_OPTIONS = [
  { label: '5位', value: 5 },
  { label: '6位', value: 6 },
  { label: '7位', value: 7 },
  { label: '8位', value: 8 }
]

/**
 * 停止位选项
 * @constant {Array<{label: string, value: number}>}
 */
export const STOPBITS_OPTIONS = [
  { label: '1位', value: 1 },
  { label: '1.5位', value: 1.5 },
  { label: '2位', value: 2 }
]

/**
 * 校验位选项
 * @constant {Array<{label: string, value: string}>}
 */
export const PARITY_OPTIONS = [
  { label: '无校验', value: 'N' },
  { label: '奇校验', value: 'O' },
  { label: '偶校验', value: 'E' },
  { label: '标记', value: 'M' },
  { label: '空格', value: 'S' }
]

/**
 * 流控制选项
 * @constant {Array<{label: string, value: string}>}
 */
export const FLOWCONTROL_OPTIONS = [
  { label: '无', value: 'none' },
  { label: '硬件流控 (RTS/CTS)', value: 'hardware' },
  { label: '软件流控 (XON/XOFF)', value: 'software' }
]

/**
 * 设备类型配置
 * @constant {Object}
 */
export const DEVICE_TYPE_CONFIGS = {
  motor: {
    name: '电机控制器',
    icon: 'Setting',
    defaultConfig: {
      baudrate: 115200,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 1,
      timeout: 1000
    },
    description: '步进电机/伺服电机控制器，支持Modbus RTU通信'
  },
  electromagnet: {
    name: '电磁铁电源',
    icon: 'Lightning',
    defaultConfig: {
      baudrate: 9600,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 2,
      timeout: 1000
    },
    description: '电磁铁电源控制器，用于磁场控制'
  },
  temperature: {
    name: '温控器',
    icon: 'Thermometer',
    defaultConfig: {
      baudrate: 9600,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 3,
      timeout: 1000
    },
    description: '温度控制器，支持PID控温'
  },
  piezo: {
    name: '压电陶瓷驱动',
    icon: 'Odometer',
    defaultConfig: {
      baudrate: 115200,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 4,
      timeout: 1000
    },
    description: '压电陶瓷驱动电源，用于精密位移控制'
  },
  ammeter: {
    name: '微电流计',
    icon: 'Aim',
    defaultConfig: {
      baudrate: 115200,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 5,
      timeout: 1000
    },
    description: '微电流计，用于微弱电流测量'
  }
}

/**
 * 预定义连接模板
 * @constant {Array}
 */
export const CONNECTION_TEMPLATES = [
  {
    id: 'default_motor',
    name: '默认电机配置',
    deviceType: 'motor',
    description: '适用于标准步进电机控制器',
    config: {
      port: 'COM3',
      baudrate: 115200,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 1,
      timeout: 1000
    },
    isDefault: true
  },
  {
    id: 'default_electromagnet',
    name: '默认电磁铁配置',
    deviceType: 'electromagnet',
    description: '适用于标准电磁铁电源',
    config: {
      port: 'COM4',
      baudrate: 9600,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 2,
      timeout: 1000
    },
    isDefault: true
  },
  {
    id: 'default_temperature',
    name: '默认温控器配置',
    deviceType: 'temperature',
    description: '适用于标准温度控制器',
    config: {
      port: 'COM5',
      baudrate: 9600,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 3,
      timeout: 1000
    },
    isDefault: true
  },
  {
    id: 'high_speed_motor',
    name: '高速电机配置',
    deviceType: 'motor',
    description: '高速通信模式，适用于需要快速响应的场景',
    config: {
      port: 'COM3',
      baudrate: 921600,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 1,
      timeout: 500
    },
    isDefault: false
  },
  {
    id: 'reliable_temperature',
    name: '可靠温控配置',
    deviceType: 'temperature',
    description: '增强可靠性配置，适用于长时间温度控制',
    config: {
      port: 'COM5',
      baudrate: 19200,
      databits: 8,
      stopbits: 2,
      parity: 'E',
      flowcontrol: 'hardware',
      slaveId: 3,
      timeout: 2000
    },
    isDefault: false
  }
]

/**
 * 连接诊断信息模板
 * @constant {Object}
 */
export const DIAGNOSTIC_MESSAGES = {
  port_not_found: {
    level: 'error',
    title: '串口未找到',
    description: '指定的串口不存在或已被占用',
    suggestions: [
      '检查设备是否正确连接到计算机',
      '在设备管理器中确认串口号',
      '关闭可能占用串口的其他应用程序',
      '尝试重新插拔USB设备'
    ]
  },
  permission_denied: {
    level: 'error',
    title: '权限被拒绝',
    description: '无法访问串口，权限不足',
    suggestions: [
      '以管理员身份运行应用程序',
      '检查当前用户是否有串口访问权限',
      '在Linux/Mac系统下，将用户添加到dialout组'
    ]
  },
  baudrate_mismatch: {
    level: 'warning',
    title: '波特率不匹配',
    description: '设备波特率与配置不匹配',
    suggestions: [
      '确认设备的实际波特率设置',
      '尝试使用自动波特率检测功能',
      '参考设备手册确认默认波特率'
    ]
  },
  timeout: {
    level: 'warning',
    title: '通信超时',
    description: '设备响应超时',
    suggestions: [
      '检查设备是否正常供电',
      '确认通信线路连接正常',
      '增加超时时间设置',
      '检查设备是否处于正常工作状态'
    ]
  },
  frame_error: {
    level: 'error',
    title: '帧错误',
    description: '数据帧格式错误',
    suggestions: [
      '检查数据位、停止位、校验位配置',
      '确认通信线路质量',
      '检查是否存在电磁干扰'
    ]
  },
  parity_error: {
    level: 'error',
    title: '校验错误',
    description: '数据校验失败',
    suggestions: [
      '检查校验位配置是否正确',
      '检查通信线路质量',
      '尝试关闭校验位进行测试'
    ]
  },
  buffer_overflow: {
    level: 'warning',
    title: '缓冲区溢出',
    description: '接收缓冲区已满',
    suggestions: [
      '降低数据采样率',
      '增加读取频率',
      '检查程序处理数据的速度'
    ]
  },
  device_busy: {
    level: 'warning',
    title: '设备忙',
    description: '设备正在处理其他请求',
    suggestions: [
      '等待当前操作完成',
      '检查是否存在死锁',
      '重启设备'
    ]
  }
}

/**
 * 创建新的连接配置
 *
 * @param {string} deviceType - 设备类型
 * @param {Object} customConfig - 自定义配置
 * @returns {Object} 完整的连接配置
 */
export function createConnectionConfig(deviceType, customConfig = {}) {
  const deviceConfig = DEVICE_TYPE_CONFIGS[deviceType]
  if (!deviceConfig) {
    throw new Error(`Unknown device type: ${deviceType}`)
  }

  return {
    deviceType,
    name: deviceConfig.name,
    ...deviceConfig.defaultConfig,
    ...customConfig,
    createdAt: Date.now(),
    updatedAt: Date.now()
  }
}

/**
 * 验证连接配置
 *
 * @param {Object} config - 连接配置
 * @returns {{valid: boolean, errors: Array<string>}} 验证结果
 */
export function validateConnectionConfig(config) {
  const errors = []

  if (!config.port || typeof config.port !== 'string') {
    errors.push('串口号不能为空')
  }

  if (!BAUDRATE_OPTIONS.find(opt => opt.value === config.baudrate)) {
    errors.push('无效的波特率设置')
  }

  if (!DATABITS_OPTIONS.find(opt => opt.value === config.databits)) {
    errors.push('无效的数据位设置')
  }

  if (!STOPBITS_OPTIONS.find(opt => opt.value === config.stopbits)) {
    errors.push('无效的停止位设置')
  }

  if (!PARITY_OPTIONS.find(opt => opt.value === config.parity)) {
    errors.push('无效的校验位设置')
  }

  if (config.slaveId < 1 || config.slaveId > 247) {
    errors.push('从站地址必须在1-247之间')
  }

  if (config.timeout < 100 || config.timeout > 10000) {
    errors.push('超时时间必须在100-10000ms之间')
  }

  return {
    valid: errors.length === 0,
    errors
  }
}

/**
 * 导出配置为JSON
 *
 * @param {Object} config - 连接配置
 * @returns {string} JSON字符串
 */
export function exportConfigToJSON(config) {
  return JSON.stringify(config, null, 2)
}

/**
 * 从JSON导入配置
 *
 * @param {string} jsonString - JSON字符串
 * @returns {Object} 配置对象
 */
export function importConfigFromJSON(jsonString) {
  try {
    const config = JSON.parse(jsonString)
    const validation = validateConnectionConfig(config)
    if (!validation.valid) {
      throw new Error(`配置验证失败: ${validation.errors.join(', ')}`)
    }
    return config
  } catch (error) {
    throw new Error(`配置导入失败: ${error.message}`)
  }
}

export default {
  BAUDRATE_OPTIONS,
  DATABITS_OPTIONS,
  STOPBITS_OPTIONS,
  PARITY_OPTIONS,
  FLOWCONTROL_OPTIONS,
  DEVICE_TYPE_CONFIGS,
  CONNECTION_TEMPLATES,
  DIAGNOSTIC_MESSAGES,
  createConnectionConfig,
  validateConnectionConfig,
  exportConfigToJSON,
  importConfigFromJSON
}
