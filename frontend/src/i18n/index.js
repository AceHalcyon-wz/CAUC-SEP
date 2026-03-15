/**
 * @file index.js
 * @path src/i18n/
 * @description 国际化配置 - 仅中文
 * @author Agent
 * @date 2024-03-15
 * @version 3.5.1
 */

import { createI18n } from 'vue-i18n'

// 中文翻译
const zhCN = {
  nav: {
    device: '设备状态',
    experiment: '实验控制',
    motor: '电机控制',
    electromagnet: '电磁铁',
    temperature: '温度控制',
    piezo: '压电陶瓷',
    ammeter: '微电流计',
    analysis: '数据分析',
    settings: '系统设置'
  },
  status: {
    connected: '在线',
    disconnected: '离线',
    reconnecting: '重连中',
    connecting: '连接中',
    error: '错误',
    warning: '警告',
    normal: '正常'
  },
  action: {
    switchLanguage: '切换语言',
    fullscreen: '全屏显示',
    exitFullscreen: '退出全屏',
    collapseSidebar: '收起侧边栏',
    expandSidebar: '展开侧边栏',
    openMenu: '打开菜单',
    collapse: '收起',
    expand: '展开',
    refresh: '刷新',
    save: '保存',
    cancel: '取消',
    confirm: '确认',
    delete: '删除',
    edit: '编辑',
    add: '添加',
    search: '搜索',
    filter: '筛选',
    export: '导出',
    import: '导入',
    print: '打印',
    download: '下载',
    upload: '上传',
    close: '关闭',
    back: '返回',
    next: '下一步',
    previous: '上一步',
    finish: '完成',
    submit: '提交',
    reset: '重置',
    clear: '清空',
    apply: '应用',
    connect: '连接',
    disconnect: '断开',
    start: '开始',
    stop: '停止',
    pause: '暂停',
    resume: '继续',
    emergencyStop: '急停'
  },
  user: {
    admin: '管理员',
    profile: '个人资料',
    settings: '用户设置',
    logout: '退出登录',
    login: '登录',
    register: '注册',
    username: '用户名',
    password: '密码',
    email: '邮箱',
    phone: '电话',
    role: '角色',
    department: '部门'
  },
  notification: {
    empty: '暂无通知',
    title: '通知中心',
    markAllRead: '全部已读',
    clearAll: '清空通知',
    newMessage: '新消息',
    system: '系统通知',
    warning: '警告通知',
    error: '错误通知',
    success: '成功通知'
  },
  device: {
    title: '设备管理',
    status: '设备状态',
    connect: '连接设备',
    disconnect: '断开设备',
    reconnect: '重新连接',
    testing: '测试连接',
    config: '设备配置',
    properties: '设备属性',
    logs: '设备日志',
    alarms: '设备告警',
    noDevice: '暂无设备',
    connecting: '连接中...',
    connected: '已连接',
    disconnected: '已断开',
    error: '连接错误',
    timeout: '连接超时',
    notFound: '设备未找到'
  },
  experiment: {
    title: '实验控制',
    start: '开始实验',
    stop: '停止实验',
    pause: '暂停实验',
    resume: '继续实验',
    reset: '重置实验',
    save: '保存实验',
    load: '加载实验',
    new: '新建实验',
    history: '实验历史',
    current: '当前实验',
    parameters: '实验参数',
    results: '实验结果',
    notes: '实验备注'
  },
  chart: {
    title: '数据图表',
    realtime: '实时数据',
    history: '历史数据',
    zoom: '缩放',
    pan: '平移',
    reset: '重置视图',
    export: '导出图表',
    save: '保存图表',
    print: '打印图表'
  },
  common: {
    loading: '加载中...',
    processing: '处理中...',
    saving: '保存中...',
    deleting: '删除中...',
    uploading: '上传中...',
    downloading: '下载中...',
    success: '操作成功',
    failed: '操作失败',
    error: '发生错误',
    warning: '警告',
    info: '提示',
    confirm: '请确认',
    cancel: '已取消',
    retry: '重试',
    close: '关闭',
    more: '更多',
    less: '收起',
    all: '全部',
    none: '无',
    select: '请选择',
    input: '请输入',
    search: '搜索...',
    noData: '暂无数据',
    noResult: '无搜索结果',
    loadingError: '加载失败',
    networkError: '网络错误',
    serverError: '服务器错误',
    timeoutError: '请求超时',
    unknownError: '未知错误'
  }
}

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN
  }
})

export default i18n
