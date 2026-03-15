/**
 * @file test-login-improvement.js
 * @path scripts/verification/
 * @description 测试新的登录系统改进方案
 * @author Agent
 * @date 2026-03-15
 * @version 1.0.0
 */

const fs = require('fs')
const path = require('path')

/**
 * 测试颜色
 */
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
}

/**
 * 日志工具
 */
function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`)
}

/**
 * 检查文件是否存在
 */
function checkFileExists(filePath, description) {
  const fullPath = path.join(__dirname, '..', '..', filePath)
  const exists = fs.existsSync(fullPath)
  
  if (exists) {
    log(`✓ ${description}: ${filePath}`, 'green')
    return true
  } else {
    log(`✗ ${description}: ${filePath} - 文件不存在`, 'red')
    return false
  }
}

/**
 * 检查文件内容
 */
function checkFileContent(filePath, patterns, description) {
  const fullPath = path.join(__dirname, '..', '..', filePath)
  
  try {
    const content = fs.readFileSync(fullPath, 'utf-8')
    let allMatch = true
    
    patterns.forEach(pattern => {
      const regex = new RegExp(pattern)
      if (!regex.test(content)) {
        log(`✗ ${description}: 未找到模式 "${pattern}"`, 'red')
        allMatch = false
      }
    })
    
    if (allMatch) {
      log(`✓ ${description}: 内容验证通过`, 'green')
    }
    
    return allMatch
  } catch (error) {
    log(`✗ ${description}: 读取失败 - ${error.message}`, 'red')
    return false
  }
}

/**
 * 主测试函数
 */
async function runTests() {
  log('\n========================================', 'cyan')
  log('登录系统改进方案测试', 'cyan')
  log('========================================\n', 'cyan')
  
  let passed = 0
  let failed = 0
  
  // 测试 1: 检查新增文件
  log('测试 1: 检查新增文件', 'blue')
  log('----------------------------------------', 'yellow')
  
  const files = [
    'frontend/src/config/loginConfig.js',
    'frontend/src/utils/tokenAuth.js',
    'frontend/src/utils/healthCheck.js',
    'docs/LOGIN_IMPROVEMENT.md'
  ]
  
  files.forEach(file => {
    if (checkFileExists(file, '新增文件')) {
      passed++
    } else {
      failed++
    }
  })
  
  // 测试 2: 检查 Login.vue 更新
  log('\n测试 2: 检查 Login.vue 更新', 'blue')
  log('----------------------------------------', 'yellow')
  
  const loginPatterns = [
    'LoginMode',
    'quickLogin',
    'guestLogin',
    'handleQuickLogin',
    'handleTraditionalLogin',
    'handleGuestLogin',
    'switchMode'
  ]
  
  if (checkFileContent('frontend/src/views/Login.vue', loginPatterns, 'Login.vue')) {
    passed++
  } else {
    failed++
  }
  
  // 测试 3: 检查 loginConfig.js 导出
  log('\n测试 3: 检查 loginConfig.js 导出', 'blue')
  log('----------------------------------------', 'yellow')
  
  const configPatterns = [
    'export const LoginMode',
    'export const PRESET_ACCOUNTS',
    'export const LOGIN_CONFIG',
    'export function getAccountConfig',
    'export function verifyTempToken'
  ]
  
  if (checkFileContent('frontend/src/config/loginConfig.js', configPatterns, 'loginConfig.js')) {
    passed++
  } else {
    failed++
  }
  
  // 测试 4: 检查 tokenAuth.js 导出
  log('\n测试 4: 检查 tokenAuth.js 导出', 'blue')
  log('----------------------------------------', 'yellow')
  
  const tokenAuthPatterns = [
    'export const TokenType',
    'export function quickLogin',
    'export function guestLogin',
    'export function saveToken',
    'export function validateToken',
    'export function getCurrentUser'
  ]
  
  if (checkFileContent('frontend/src/utils/tokenAuth.js', tokenAuthPatterns, 'tokenAuth.js')) {
    passed++
  } else {
    failed++
  }
  
  // 测试 5: 检查 healthCheck.js 导出
  log('\n测试 5: 检查 healthCheck.js 导出', 'blue')
  log('----------------------------------------', 'yellow')
  
  const healthCheckPatterns = [
    'export const HealthStatus',
    'export async function checkHealth',
    'export async function quickCheck',
    'export async function shouldUseQuickLogin'
  ]
  
  if (checkFileContent('frontend/src/utils/healthCheck.js', healthCheckPatterns, 'healthCheck.js')) {
    passed++
  } else {
    failed++
  }
  
  // 测试 6: 检查文档
  log('\n测试 6: 检查文档', 'blue')
  log('----------------------------------------', 'yellow')
  
  const docPatterns = [
    '# 登录系统改进方案',
    '## 📋 概述',
    '## 🚀 使用方式',
    '## 🔐 安全机制'
  ]
  
  if (checkFileContent('docs/LOGIN_IMPROVEMENT.md', docPatterns, 'LOGIN_IMPROVEMENT.md')) {
    passed++
  } else {
    failed++
  }
  
  // 测试结果
  log('\n========================================', 'cyan')
  log(`测试结果：${passed} 通过，${failed} 失败`, passed === files.length + 4 ? 'green' : 'yellow')
  log('========================================\n', 'cyan')
  
  if (failed > 0) {
    process.exit(1)
  }
}

// 运行测试
runTests().catch(error => {
  log(`\n测试失败：${error.message}`, 'red')
  process.exit(1)
})
