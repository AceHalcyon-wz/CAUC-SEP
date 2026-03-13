/**
 * @file errorSolutions.js
 * @path src/utils/
 * @description 错误解决方案库，提供常见错误的智能匹配解决方案
 * @author Agent
 * @date 2024-03-07
 */

/**
 * 错误类型枚举
 */
export const ERROR_TYPES = {
  NETWORK: 'network',
  PERMISSION: 'permission',
  VALIDATION: 'validation',
  DEVICE: 'device',
  WEBSOCKET: 'websocket',
  TIMEOUT: 'timeout',
  DATABASE: 'database',
  STORAGE: 'storage',
  AUTHENTICATION: 'authentication',
  RATE_LIMIT: 'rate_limit',
  HARDWARE: 'hardware',
  COMMUNICATION: 'communication',
  DATA_INTEGRITY: 'data_integrity',
  CONFIGURATION: 'configuration',
  RESOURCE: 'resource',
  UNKNOWN: 'unknown'
}

/**
 * 错误严重程度
 */
export const ERROR_SEVERITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical'
}

/**
 * 错误严重程度权重（用于排序和优先级判断）
 */
export const ERROR_SEVERITY_WEIGHT = {
  [ERROR_SEVERITY.LOW]: 1,
  [ERROR_SEVERITY.MEDIUM]: 2,
  [ERROR_SEVERITY.HIGH]: 3,
  [ERROR_SEVERITY.CRITICAL]: 4
}

/**
 * 解决方案数据库
 */
const SOLUTION_DATABASE = [
  // 网络错误
  {
    errorPatterns: [
      'network error',
      'failed to fetch',
      'networkerror',
      'err_connection_refused',
      'err_internet_disconnected',
      'err_name_not_resolved',
      'err_connection_timed_out'
    ],
    type: ERROR_TYPES.NETWORK,
    severity: ERROR_SEVERITY.HIGH,
    title: '网络连接错误',
    description: '无法连接到服务器，可能是网络问题或服务器未启动',
    solutions: [
      {
        step: 1,
        action: '检查网络连接',
        description: '确保您的计算机已连接到网络，可以尝试访问其他网站',
        icon: 'Connection'
      },
      {
        step: 2,
        action: '检查服务器状态',
        description: '确认后端服务是否正常运行，查看服务器日志',
        icon: 'Monitor'
      },
      {
        step: 3,
        action: '检查防火墙设置',
        description: '确保防火墙未阻止应用程序的网络访问',
        icon: 'Lock'
      },
      {
        step: 4,
        action: '检查代理设置',
        description: '如果使用代理，确认代理配置正确',
        icon: 'Setting'
      }
    ],
    relatedDocs: [
      { title: '网络故障排查指南', url: '/docs/network-troubleshooting' },
      { title: '服务器配置说明', url: '/docs/server-config' }
    ],
    autoActions: [
      { label: '重试连接', action: 'retry' },
      { label: '检查服务器', action: 'checkServer' }
    ]
  },

  // WebSocket连接错误
  {
    errorPatterns: [
      'websocket error',
      'websocket connection failed',
      'ws connection closed',
      'socket hang up',
      'websocket is not open'
    ],
    type: ERROR_TYPES.WEBSOCKET,
    severity: ERROR_SEVERITY.HIGH,
    title: 'WebSocket连接错误',
    description: '实时数据连接失败，将无法接收实时更新',
    solutions: [
      {
        step: 1,
        action: '检查WebSocket服务',
        description: '确认WebSocket服务已启动并监听正确端口',
        icon: 'Connection'
      },
      {
        step: 2,
        action: '检查URL配置',
        description: '验证WebSocket地址配置是否正确（ws://或wss://）',
        icon: 'Link'
      },
      {
        step: 3,
        action: '检查网络代理',
        description: '某些代理服务器可能不支持WebSocket，尝试直连',
        icon: 'Warning'
      },
      {
        step: 4,
        action: '刷新页面重连',
        description: '刷新浏览器页面以重新建立WebSocket连接',
        icon: 'Refresh'
      }
    ],
    relatedDocs: [
      { title: 'WebSocket配置说明', url: '/docs/websocket-config' },
      { title: '实时数据推送指南', url: '/docs/realtime-data' }
    ],
    autoActions: [
      { label: '重新连接', action: 'reconnect' },
      { label: '查看连接状态', action: 'checkStatus' }
    ]
  },

  // 设备连接错误
  {
    errorPatterns: [
      'serial port',
      'com port',
      'device not found',
      'port is busy',
      'access denied',
      'permission denied',
      'failed to open port',
      '设备未连接',
      '串口打开失败'
    ],
    type: ERROR_TYPES.DEVICE,
    severity: ERROR_SEVERITY.HIGH,
    title: '设备连接错误',
    description: '无法连接到实验设备，请检查硬件连接和权限',
    solutions: [
      {
        step: 1,
        action: '检查设备连接',
        description: '确保设备已通过USB或串口线正确连接到计算机',
        icon: 'Connection'
      },
      {
        step: 2,
        action: '检查端口占用',
        description: '确认串口未被其他程序占用，关闭可能占用的软件',
        icon: 'Warning'
      },
      {
        step: 3,
        action: '检查驱动程序',
        description: '确保设备驱动已正确安装，在设备管理器中查看',
        icon: 'Download'
      },
      {
        step: 4,
        action: '检查访问权限',
        description: 'Windows: 以管理员身份运行；Linux: 将用户加入dialout组',
        icon: 'Lock'
      },
      {
        step: 5,
        action: '尝试其他端口',
        description: '尝试更换USB端口或使用不同的串口号',
        icon: 'Switch'
      }
    ],
    relatedDocs: [
      { title: '设备连接指南', url: '/docs/device-connection' },
      { title: '驱动安装说明', url: '/docs/driver-installation' }
    ],
    autoActions: [
      { label: '扫描设备', action: 'scanDevices' },
      { label: '重新连接', action: 'reconnectDevice' }
    ]
  },

  // 权限错误
  {
    errorPatterns: [
      'permission denied',
      'access denied',
      'unauthorized',
      'forbidden',
      '403',
      'insufficient permissions',
      '权限不足'
    ],
    type: ERROR_TYPES.PERMISSION,
    severity: ERROR_SEVERITY.HIGH,
    title: '权限错误',
    description: '您没有执行此操作的权限',
    solutions: [
      {
        step: 1,
        action: '检查用户权限',
        description: '确认您的账户具有执行此操作所需的权限',
        icon: 'User'
      },
      {
        step: 2,
        action: '联系管理员',
        description: '如需更高权限，请联系系统管理员',
        icon: 'Phone'
      },
      {
        step: 3,
        action: '重新登录',
        description: '尝试退出登录后重新登录以刷新权限',
        icon: 'Refresh'
      }
    ],
    relatedDocs: [
      { title: '权限管理说明', url: '/docs/permissions' },
      { title: '用户角色说明', url: '/docs/user-roles' }
    ],
    autoActions: [
      { label: '重新登录', action: 'relogin' }
    ]
  },

  // 验证错误
  {
    errorPatterns: [
      'validation error',
      'invalid parameter',
      'invalid input',
      '参数错误',
      '验证失败',
      '格式不正确',
      'out of range',
      'value error'
    ],
    type: ERROR_TYPES.VALIDATION,
    severity: ERROR_SEVERITY.MEDIUM,
    title: '数据验证错误',
    description: '输入的数据不符合要求',
    solutions: [
      {
        step: 1,
        action: '检查输入格式',
        description: '确保输入的数据格式正确（如数字范围、字符类型等）',
        icon: 'Edit'
      },
      {
        step: 2,
        action: '查看错误提示',
        description: '仔细阅读表单下方的错误提示信息',
        icon: 'Warning'
      },
      {
        step: 3,
        action: '重置表单',
        description: '尝试重置表单后重新输入',
        icon: 'Refresh'
      }
    ],
    relatedDocs: [
      { title: '数据格式说明', url: '/docs/data-format' },
      { title: '参数配置指南', url: '/docs/parameters' }
    ],
    autoActions: [
      { label: '重置表单', action: 'resetForm' }
    ]
  },

  // 超时错误
  {
    errorPatterns: [
      'timeout',
      'timed out',
      'request timeout',
      'connection timeout',
      'operation timed out',
      '超时'
    ],
    type: ERROR_TYPES.TIMEOUT,
    severity: ERROR_SEVERITY.MEDIUM,
    title: '操作超时',
    description: '操作耗时过长，可能是网络延迟或服务器响应慢',
    solutions: [
      {
        step: 1,
        action: '检查网络状况',
        description: '网络延迟可能导致超时，尝试改善网络连接',
        icon: 'Connection'
      },
      {
        step: 2,
        action: '减少数据量',
        description: '如果是数据查询，尝试缩小查询范围或时间跨度',
        icon: 'Filter'
      },
      {
        step: 3,
        action: '稍后重试',
        description: '服务器可能暂时过载，稍后再试',
        icon: 'Time'
      },
      {
        step: 4,
        action: '联系管理员',
        description: '如果频繁超时，请联系管理员检查服务器性能',
        icon: 'Phone'
      }
    ],
    relatedDocs: [
      { title: '性能优化指南', url: '/docs/performance' },
      { title: '超时配置说明', url: '/docs/timeout-config' }
    ],
    autoActions: [
      { label: '重试操作', action: 'retry' }
    ]
  },

  // Modbus通信错误
  {
    errorPatterns: [
      'modbus',
      'slave',
      'crc error',
      'illegal function',
      'illegal data address',
      'illegal data value',
      'slave device failure',
      'acknowledge',
      'slave device busy'
    ],
    type: ERROR_TYPES.DEVICE,
    severity: ERROR_SEVERITY.HIGH,
    title: 'Modbus通信错误',
    description: '与设备的Modbus通信失败',
    solutions: [
      {
        step: 1,
        action: '检查从站地址',
        description: '确认配置的从站地址与设备实际地址一致',
        icon: 'Setting'
      },
      {
        step: 2,
        action: '检查波特率',
        description: '确保波特率、数据位、停止位等参数与设备匹配',
        icon: 'Connection'
      },
      {
        step: 3,
        action: '检查寄存器地址',
        description: '验证访问的寄存器地址是否在设备支持范围内',
        icon: 'Document'
      },
      {
        step: 4,
        action: '检查通信线路',
        description: '检查RS485/RS232线路连接是否正常',
        icon: 'Connection'
      },
      {
        step: 5,
        action: '减少通信频率',
        description: '如果设备繁忙，尝试降低查询频率',
        icon: 'Time'
      }
    ],
    relatedDocs: [
      { title: 'Modbus协议说明', url: '/docs/modbus-protocol' },
      { title: '设备通信配置', url: '/docs/device-comm' }
    ],
    autoActions: [
      { label: '重新连接', action: 'reconnectDevice' },
      { label: '测试通信', action: 'testConnection' }
    ]
  },

  // 数据库错误
  {
    errorPatterns: [
      'database',
      'indexeddb',
      'quota exceeded',
      'data error',
      'constraint error',
      'transaction inactive',
      'database version error',
      '数据库错误',
      '存储空间不足'
    ],
    type: ERROR_TYPES.DATABASE,
    severity: ERROR_SEVERITY.HIGH,
    title: '数据库错误',
    description: '本地数据库操作失败，可能是存储空间不足或数据损坏',
    solutions: [
      {
        step: 1,
        action: '清理缓存数据',
        description: '清除浏览器缓存和本地存储数据，释放空间',
        icon: 'Delete'
      },
      {
        step: 2,
        action: '检查存储配额',
        description: '查看浏览器存储使用情况，必要时清理旧数据',
        icon: 'DataAnalysis'
      },
      {
        step: 3,
        action: '刷新页面',
        description: '刷新页面以重新初始化数据库连接',
        icon: 'Refresh'
      },
      {
        step: 4,
        action: '使用隐私模式',
        description: '尝试在浏览器隐私模式下使用，排除扩展干扰',
        icon: 'Lock'
      }
    ],
    relatedDocs: [
      { title: '数据存储说明', url: '/docs/data-storage' },
      { title: '清理缓存指南', url: '/docs/clear-cache' }
    ],
    autoActions: [
      { label: '清理缓存', action: 'clearCache' },
      { label: '刷新页面', action: 'refresh' }
    ]
  },

  // 存储错误
  {
    errorPatterns: [
      'storage',
      'localstorage',
      'sessionstorage',
      'quota',
      'storage full',
      '存储已满',
      'storage quota',
      'not enough space'
    ],
    type: ERROR_TYPES.STORAGE,
    severity: ERROR_SEVERITY.MEDIUM,
    title: '存储空间错误',
    description: '浏览器存储空间不足，无法保存数据',
    solutions: [
      {
        step: 1,
        action: '清理旧数据',
        description: '删除不需要的历史数据和缓存文件',
        icon: 'Delete'
      },
      {
        step: 2,
        action: '导出重要数据',
        description: '将重要数据导出备份后再清理',
        icon: 'Download'
      },
      {
        step: 3,
        action: '检查浏览器设置',
        description: '查看浏览器存储限制和当前使用情况',
        icon: 'Setting'
      }
    ],
    relatedDocs: [
      { title: '存储管理指南', url: '/docs/storage-management' }
    ],
    autoActions: [
      { label: '清理缓存', action: 'clearCache' }
    ]
  },

  // 认证错误
  {
    errorPatterns: [
      'authentication',
      'unauthenticated',
      'not authenticated',
      'invalid token',
      'token expired',
      'session expired',
      'login required',
      '认证失败',
      '登录过期',
      '401'
    ],
    type: ERROR_TYPES.AUTHENTICATION,
    severity: ERROR_SEVERITY.HIGH,
    title: '认证错误',
    description: '身份验证失败或会话已过期',
    solutions: [
      {
        step: 1,
        action: '重新登录',
        description: '您的登录状态已过期，请重新登录',
        icon: 'User'
      },
      {
        step: 2,
        action: '检查账号状态',
        description: '确认账号未被禁用或锁定',
        icon: 'Warning'
      },
      {
        step: 3,
        action: '清除登录信息',
        description: '清除浏览器中的登录缓存后重新登录',
        icon: 'Delete'
      }
    ],
    relatedDocs: [
      { title: '登录问题排查', url: '/docs/login-issues' },
      { title: '账号安全', url: '/docs/account-security' }
    ],
    autoActions: [
      { label: '重新登录', action: 'relogin' }
    ]
  },

  // 速率限制错误
  {
    errorPatterns: [
      'rate limit',
      'too many requests',
      '429',
      '请求过于频繁',
      'throttle',
      'quota exceeded',
      '请求限制'
    ],
    type: ERROR_TYPES.RATE_LIMIT,
    severity: ERROR_SEVERITY.MEDIUM,
    title: '请求频率限制',
    description: '请求过于频繁，已触发服务器限流机制',
    solutions: [
      {
        step: 1,
        action: '等待一段时间',
        description: '请等待几秒或几分钟后重试',
        icon: 'Time'
      },
      {
        step: 2,
        action: '减少请求频率',
        description: '降低操作频率，避免短时间内大量请求',
        icon: 'Warning'
      },
      {
        step: 3,
        action: '使用批量操作',
        description: '尽量使用批量接口代替多次单独请求',
        icon: 'Document'
      }
    ],
    relatedDocs: [
      { title: 'API使用规范', url: '/docs/api-guidelines' },
      { title: '频率限制说明', url: '/docs/rate-limit' }
    ],
    autoActions: [
      { label: '稍后重试', action: 'retry' }
    ]
  },

  // 文件操作错误
  {
    errorPatterns: [
      'file not found',
      'file error',
      'file too large',
      'invalid file type',
      '文件不存在',
      '文件过大',
      '文件类型错误',
      'upload failed',
      'download failed'
    ],
    type: ERROR_TYPES.VALIDATION,
    severity: ERROR_SEVERITY.MEDIUM,
    title: '文件操作错误',
    description: '文件操作失败，可能是文件不存在、格式不支持或大小超限',
    solutions: [
      {
        step: 1,
        action: '检查文件是否存在',
        description: '确认文件路径正确且文件未被删除或移动',
        icon: 'Document'
      },
      {
        step: 2,
        action: '检查文件格式',
        description: '确认文件格式符合要求（如支持的文件类型）',
        icon: 'Warning'
      },
      {
        step: 3,
        action: '检查文件大小',
        description: '确认文件大小未超过限制（通常最大50MB）',
        icon: 'DataAnalysis'
      },
      {
        step: 4,
        action: '重新选择文件',
        description: '尝试重新选择或上传文件',
        icon: 'Upload'
      }
    ],
    relatedDocs: [
      { title: '文件上传说明', url: '/docs/file-upload' },
      { title: '支持的文件格式', url: '/docs/file-formats' }
    ],
    autoActions: [
      { label: '重新选择', action: 'selectFile' }
    ]
  },

  // 配置错误
  {
    errorPatterns: [
      'config',
      'configuration',
      'invalid config',
      'config error',
      '配置错误',
      '配置文件损坏',
      'missing config'
    ],
    type: ERROR_TYPES.CONFIGURATION,
    severity: ERROR_SEVERITY.MEDIUM,
    title: '配置错误',
    description: '系统配置无效或配置文件损坏',
    solutions: [
      {
        step: 1,
        action: '重置配置',
        description: '将配置恢复到默认值',
        icon: 'Refresh'
      },
      {
        step: 2,
        action: '检查配置项',
        description: '确认所有必填配置项已正确填写',
        icon: 'Edit'
      },
      {
        step: 3,
        action: '导入正确配置',
        description: '从备份中导入正确的配置文件',
        icon: 'Upload'
      }
    ],
    relatedDocs: [
      { title: '配置说明', url: '/docs/configuration' },
      { title: '配置备份与恢复', url: '/docs/config-backup' }
    ],
    autoActions: [
      { label: '重置配置', action: 'resetConfig' }
    ]
  },

  // 硬件错误
  {
    errorPatterns: [
      'hardware error',
      'device malfunction',
      'sensor error',
      'actuator error',
      '硬件错误',
      '设备故障',
      '传感器错误',
      '执行器错误',
      'overheating',
      '过热',
      'hardware failure'
    ],
    type: ERROR_TYPES.HARDWARE,
    severity: ERROR_SEVERITY.CRITICAL,
    title: '硬件错误',
    description: '实验设备硬件出现故障或异常',
    solutions: [
      {
        step: 1,
        action: '停止当前操作',
        description: '立即停止当前实验操作，避免进一步损坏',
        icon: 'Warning'
      },
      {
        step: 2,
        action: '检查设备状态',
        description: '检查设备电源、连接线、传感器等硬件状态',
        icon: 'Monitor'
      },
      {
        step: 3,
        action: '查看设备日志',
        description: '检查设备自检日志，定位具体故障部件',
        icon: 'Document'
      },
      {
        step: 4,
        action: '联系技术支持',
        description: '如无法自行解决，联系设备厂商或技术支持',
        icon: 'Phone'
      }
    ],
    relatedDocs: [
      { title: '硬件故障排查指南', url: '/docs/hardware-troubleshooting' },
      { title: '设备维护手册', url: '/docs/device-maintenance' }
    ],
    autoActions: [
      { label: '停止实验', action: 'stopExperiment' },
      { label: '查看设备日志', action: 'viewDeviceLog' }
    ]
  },

  // 通信错误
  {
    errorPatterns: [
      'communication error',
      'communication timeout',
      'protocol error',
      '通信错误',
      '通信超时',
      '协议错误',
      'data corruption',
      'checksum error',
      '校验错误'
    ],
    type: ERROR_TYPES.COMMUNICATION,
    severity: ERROR_SEVERITY.HIGH,
    title: '通信错误',
    description: '设备通信过程中出现数据传输错误',
    solutions: [
      {
        step: 1,
        action: '检查通信线路',
        description: '确认通信线缆连接正常，无松动或损坏',
        icon: 'Connection'
      },
      {
        step: 2,
        action: '检查通信参数',
        description: '验证波特率、数据位、停止位等参数配置正确',
        icon: 'Setting'
      },
      {
        step: 3,
        action: '降低通信速率',
        description: '尝试降低通信速率以提高稳定性',
        icon: 'Time'
      },
      {
        step: 4,
        action: '检查电磁干扰',
        description: '排除附近设备的电磁干扰影响',
        icon: 'Warning'
      }
    ],
    relatedDocs: [
      { title: '通信协议说明', url: '/docs/communication-protocol' },
      { title: '通信故障排查', url: '/docs/communication-troubleshooting' }
    ],
    autoActions: [
      { label: '重新连接', action: 'reconnect' },
      { label: '测试通信', action: 'testConnection' }
    ]
  },

  // 数据完整性错误
  {
    errorPatterns: [
      'data integrity',
      'data corrupted',
      'invalid data',
      '数据完整性',
      '数据损坏',
      '无效数据',
      'checksum mismatch',
      'data validation failed',
      '数据验证失败'
    ],
    type: ERROR_TYPES.DATA_INTEGRITY,
    severity: ERROR_SEVERITY.HIGH,
    title: '数据完整性错误',
    description: '数据在传输或存储过程中发生损坏或验证失败',
    solutions: [
      {
        step: 1,
        action: '重新获取数据',
        description: '尝试重新从源获取数据',
        icon: 'Refresh'
      },
      {
        step: 2,
        action: '检查数据格式',
        description: '验证数据格式是否符合预期规范',
        icon: 'Document'
      },
      {
        step: 3,
        action: '恢复备份数据',
        description: '如有备份，尝试恢复之前的有效数据',
        icon: 'Download'
      },
      {
        step: 4,
        action: '检查存储介质',
        description: '检查存储设备是否存在坏道或损坏',
        icon: 'Monitor'
      }
    ],
    relatedDocs: [
      { title: '数据完整性检查', url: '/docs/data-integrity' },
      { title: '数据恢复指南', url: '/docs/data-recovery' }
    ],
    autoActions: [
      { label: '重新获取', action: 'refetchData' },
      { label: '恢复备份', action: 'restoreBackup' }
    ]
  },

  // 资源错误
  {
    errorPatterns: [
      'out of memory',
      'memory limit',
      'resource exhausted',
      '内存不足',
      '资源耗尽',
      'too many connections',
      'connection limit',
      '连接数超限',
      'cpu limit',
      'CPU限制'
    ],
    type: ERROR_TYPES.RESOURCE,
    severity: ERROR_SEVERITY.HIGH,
    title: '资源不足错误',
    description: '系统资源不足，无法完成操作',
    solutions: [
      {
        step: 1,
        action: '关闭不必要的程序',
        description: '关闭其他占用资源的程序或标签页',
        icon: 'Close'
      },
      {
        step: 2,
        action: '清理缓存数据',
        description: '清除浏览器缓存和临时数据',
        icon: 'Delete'
      },
      {
        step: 3,
        action: '减少数据量',
        description: '减少单次处理的数据量或分批处理',
        icon: 'Filter'
      },
      {
        step: 4,
        action: '重启应用',
        description: '重启应用以释放被占用的资源',
        icon: 'Refresh'
      }
    ],
    relatedDocs: [
      { title: '性能优化指南', url: '/docs/performance-optimization' },
      { title: '资源管理说明', url: '/docs/resource-management' }
    ],
    autoActions: [
      { label: '清理缓存', action: 'clearCache' },
      { label: '刷新页面', action: 'refresh' }
    ]
  },

  // 实验参数错误
  {
    errorPatterns: [
      'parameter out of range',
      'invalid parameter',
      '实验参数错误',
      '参数超出范围',
      'unsafe parameter',
      '危险参数',
      'parameter conflict',
      '参数冲突'
    ],
    type: ERROR_TYPES.VALIDATION,
    severity: ERROR_SEVERITY.MEDIUM,
    title: '实验参数错误',
    description: '设置的实验参数不合法或超出安全范围',
    solutions: [
      {
        step: 1,
        action: '检查参数范围',
        description: '确认参数值在允许的安全范围内',
        icon: 'Warning'
      },
      {
        step: 2,
        action: '查看参数说明',
        description: '参考文档了解各参数的合法取值范围',
        icon: 'Document'
      },
      {
        step: 3,
        action: '使用默认值',
        description: '尝试使用系统推荐的默认参数值',
        icon: 'Refresh'
      },
      {
        step: 4,
        action: '检查参数依赖',
        description: '确认参数之间是否存在冲突或依赖关系',
        icon: 'Link'
      }
    ],
    relatedDocs: [
      { title: '实验参数说明', url: '/docs/experiment-parameters' },
      { title: '安全操作指南', url: '/docs/safety-guidelines' }
    ],
    autoActions: [
      { label: '重置参数', action: 'resetParameters' },
      { label: '使用默认值', action: 'useDefaults' }
    ]
  },

  // 安全错误
  {
    errorPatterns: [
      'safety violation',
      'safety interlock',
      'emergency stop',
      '安全违规',
      '安全联锁',
      '紧急停止',
      'safety limit exceeded',
      '安全限制超限'
    ],
    type: ERROR_TYPES.HARDWARE,
    severity: ERROR_SEVERITY.CRITICAL,
    title: '安全保护触发',
    description: '系统检测到安全风险，已触发保护机制',
    solutions: [
      {
        step: 1,
        action: '确认安全状态',
        description: '检查设备和环境是否处于安全状态',
        icon: 'Warning'
      },
      {
        step: 2,
        action: '排除安全隐患',
        description: '识别并排除导致安全保护触发的因素',
        icon: 'Monitor'
      },
      {
        step: 3,
        action: '重置安全联锁',
        description: '在确认安全后，按照规程重置安全联锁',
        icon: 'Refresh'
      },
      {
        step: 4,
        action: '记录事件',
        description: '记录安全事件详情，便于后续分析',
        icon: 'Document'
      }
    ],
    relatedDocs: [
      { title: '安全操作规程', url: '/docs/safety-procedures' },
      { title: '应急处理指南', url: '/docs/emergency-handling' }
    ],
    autoActions: [
      { label: '查看安全状态', action: 'checkSafetyStatus' },
      { label: '记录事件', action: 'logEvent' }
    ]
  }
]

/**
 * 智能匹配错误解决方案
 *
 * @param {Error|string} error - 错误对象或错误消息
 * @returns {Object|null} 匹配的解决方案对象，未找到返回null
 *
 * @example
 * ```javascript
 * const solution = matchSolution(new Error('network error'))
 * console.log(solution.title) // '网络连接错误'
 * ```
 */
export function matchSolution(error) {
  const errorMessage = error?.message || error?.toString() || ''
  const lowerMessage = errorMessage.toLowerCase()

  // 遍历解决方案数据库进行匹配
  for (const solution of SOLUTION_DATABASE) {
    for (const pattern of solution.errorPatterns) {
      if (lowerMessage.includes(pattern.toLowerCase())) {
        return {
          ...solution,
          matchedPattern: pattern,
          timestamp: new Date().toISOString()
        }
      }
    }
  }

  // 未找到匹配，返回通用解决方案
  return {
    type: ERROR_TYPES.UNKNOWN,
    severity: ERROR_SEVERITY.MEDIUM,
    title: '未知错误',
    description: '发生了未知错误，请查看错误详情',
    solutions: [
      {
        step: 1,
        action: '查看错误详情',
        description: '展开错误堆栈以了解详细错误信息',
        icon: 'Document'
      },
      {
        step: 2,
        action: '刷新页面',
        description: '尝试刷新页面以解决临时性问题',
        icon: 'Refresh'
      },
      {
        step: 3,
        action: '联系技术支持',
        description: '如果问题持续存在，请联系技术支持并提供错误详情',
        icon: 'Phone'
      }
    ],
    relatedDocs: [
      { title: '常见问题解答', url: '/docs/faq' },
      { title: '技术支持', url: '/docs/support' }
    ],
    autoActions: [
      { label: '刷新页面', action: 'refresh' },
      { label: '导出错误报告', action: 'exportReport' }
    ],
    timestamp: new Date().toISOString()
  }
}

/**
 * 获取错误类型图标
 *
 * @param {string} type - 错误类型
 * @returns {string} 图标名称
 */
export function getErrorIcon(type) {
  const iconMap = {
    [ERROR_TYPES.NETWORK]: 'Connection',
    [ERROR_TYPES.PERMISSION]: 'Lock',
    [ERROR_TYPES.VALIDATION]: 'Warning',
    [ERROR_TYPES.DEVICE]: 'Monitor',
    [ERROR_TYPES.WEBSOCKET]: 'Connection',
    [ERROR_TYPES.TIMEOUT]: 'Time',
    [ERROR_TYPES.DATABASE]: 'CoinCollection',
    [ERROR_TYPES.STORAGE]: 'FolderOpened',
    [ERROR_TYPES.AUTHENTICATION]: 'User',
    [ERROR_TYPES.RATE_LIMIT]: 'Timer',
    [ERROR_TYPES.HARDWARE]: 'Cpu',
    [ERROR_TYPES.COMMUNICATION]: 'Connection',
    [ERROR_TYPES.DATA_INTEGRITY]: 'DocumentChecked',
    [ERROR_TYPES.CONFIGURATION]: 'Setting',
    [ERROR_TYPES.RESOURCE]: 'DataAnalysis',
    [ERROR_TYPES.UNKNOWN]: 'Warning'
  }
  return iconMap[type] || 'Warning'
}

/**
 * 获取错误严重程度颜色
 *
 * @param {string} severity - 严重程度
 * @returns {string} CSS变量名
 */
export function getSeverityColor(severity) {
  const colorMap = {
    [ERROR_SEVERITY.LOW]: 'var(--color-success)',
    [ERROR_SEVERITY.MEDIUM]: 'var(--color-warning)',
    [ERROR_SEVERITY.HIGH]: 'var(--color-error)',
    [ERROR_SEVERITY.CRITICAL]: 'var(--color-error-dark)'
  }
  return colorMap[severity] || 'var(--color-warning)'
}

/**
 * 获取错误类型标签
 *
 * @param {string} type - 错误类型
 * @returns {string} 类型标签文本
 */
export function getErrorTypeLabel(type) {
  const labelMap = {
    [ERROR_TYPES.NETWORK]: '网络错误',
    [ERROR_TYPES.PERMISSION]: '权限错误',
    [ERROR_TYPES.VALIDATION]: '验证错误',
    [ERROR_TYPES.DEVICE]: '设备错误',
    [ERROR_TYPES.WEBSOCKET]: 'WebSocket错误',
    [ERROR_TYPES.TIMEOUT]: '超时错误',
    [ERROR_TYPES.DATABASE]: '数据库错误',
    [ERROR_TYPES.STORAGE]: '存储错误',
    [ERROR_TYPES.AUTHENTICATION]: '认证错误',
    [ERROR_TYPES.RATE_LIMIT]: '频率限制',
    [ERROR_TYPES.HARDWARE]: '硬件错误',
    [ERROR_TYPES.COMMUNICATION]: '通信错误',
    [ERROR_TYPES.DATA_INTEGRITY]: '数据完整性错误',
    [ERROR_TYPES.CONFIGURATION]: '配置错误',
    [ERROR_TYPES.RESOURCE]: '资源错误',
    [ERROR_TYPES.UNKNOWN]: '未知错误'
  }
  return labelMap[type] || '未知错误'
}

/**
 * 获取所有错误类型
 *
 * @returns {Array} 错误类型列表
 */
export function getAllErrorTypes() {
  return Object.values(ERROR_TYPES).map(type => ({
    value: type,
    label: getErrorTypeLabel(type),
    icon: getErrorIcon(type)
  }))
}

/**
 * 根据错误消息智能判断错误类型
 *
 * @param {string} message - 错误消息
 * @returns {string} 错误类型
 */
export function inferErrorType(message) {
  if (!message) return ERROR_TYPES.UNKNOWN
  
  const lowerMessage = message.toLowerCase()
  
  // 按优先级匹配
  if (lowerMessage.includes('network') || lowerMessage.includes('fetch')) {
    return ERROR_TYPES.NETWORK
  }
  if (lowerMessage.includes('permission') || lowerMessage.includes('unauthorized')) {
    return ERROR_TYPES.PERMISSION
  }
  if (lowerMessage.includes('timeout')) {
    return ERROR_TYPES.TIMEOUT
  }
  if (lowerMessage.includes('device') || lowerMessage.includes('serial')) {
    return ERROR_TYPES.DEVICE
  }
  if (lowerMessage.includes('websocket')) {
    return ERROR_TYPES.WEBSOCKET
  }
  if (lowerMessage.includes('database') || lowerMessage.includes('indexeddb')) {
    return ERROR_TYPES.DATABASE
  }
  if (lowerMessage.includes('storage') || lowerMessage.includes('quota')) {
    return ERROR_TYPES.STORAGE
  }
  if (lowerMessage.includes('auth') || lowerMessage.includes('token')) {
    return ERROR_TYPES.AUTHENTICATION
  }
  if (lowerMessage.includes('rate') || lowerMessage.includes('limit')) {
    return ERROR_TYPES.RATE_LIMIT
  }
  if (lowerMessage.includes('hardware') || lowerMessage.includes('sensor')) {
    return ERROR_TYPES.HARDWARE
  }
  if (lowerMessage.includes('communication') || lowerMessage.includes('protocol')) {
    return ERROR_TYPES.COMMUNICATION
  }
  if (lowerMessage.includes('data') || lowerMessage.includes('integrity')) {
    return ERROR_TYPES.DATA_INTEGRITY
  }
  if (lowerMessage.includes('config')) {
    return ERROR_TYPES.CONFIGURATION
  }
  if (lowerMessage.includes('memory') || lowerMessage.includes('resource')) {
    return ERROR_TYPES.RESOURCE
  }
  if (lowerMessage.includes('validation') || lowerMessage.includes('invalid')) {
    return ERROR_TYPES.VALIDATION
  }
  
  return ERROR_TYPES.UNKNOWN
}

/**
 * 根据错误上下文推断错误严重程度
 *
 * @param {Object} error - 错误对象
 * @param {Object} context - 错误上下文
 * @returns {string} 严重程度
 */
export function inferErrorSeverity(error, context = {}) {
  // 如果错误已指定严重程度，直接返回
  if (error?.severity) return error.severity
  
  // 根据错误类型推断
  const type = error?.type || inferErrorType(error?.message)
  
  // 关键系统错误
  if (type === ERROR_TYPES.HARDWARE || type === ERROR_TYPES.AUTHENTICATION) {
    return ERROR_SEVERITY.CRITICAL
  }
  
  // 高优先级错误
  if (type === ERROR_TYPES.NETWORK || 
      type === ERROR_TYPES.DEVICE || 
      type === ERROR_TYPES.DATABASE ||
      type === ERROR_TYPES.COMMUNICATION ||
      type === ERROR_TYPES.DATA_INTEGRITY ||
      type === ERROR_TYPES.RESOURCE) {
    return ERROR_SEVERITY.HIGH
  }
  
  // 中等优先级错误
  if (type === ERROR_TYPES.WEBSOCKET || 
      type === ERROR_TYPES.TIMEOUT ||
      type === ERROR_TYPES.PERMISSION ||
      type === ERROR_TYPES.RATE_LIMIT ||
      type === ERROR_TYPES.CONFIGURATION ||
      type === ERROR_TYPES.VALIDATION) {
    return ERROR_SEVERITY.MEDIUM
  }
  
  // 低优先级错误
  if (type === ERROR_TYPES.STORAGE) {
    return ERROR_SEVERITY.LOW
  }
  
  return ERROR_SEVERITY.MEDIUM
}
