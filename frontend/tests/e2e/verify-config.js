/**
 * @file verify-config.js
 * @path frontend/tests/e2e/
 * @description E2E测试配置验证脚本
 * 
 * 用于验证Playwright E2E测试框架的配置是否正确，包括：
 * - 依赖包安装检查
 * - 配置文件加载检查
 * - 辅助函数导入检查
 * 
 * @author Agent
 * @date 2024-03-16
 */

import { test, expect } from '@playwright/test';

// 验证配置文件加载
console.log('✓ @playwright/test 导入成功');

// 验证辅助函数导入
try {
  const { testConfig, getTestUser, getTimeout } = await import('./helpers/index.js');
  console.log('✓ 辅助函数模块导入成功');
  
  // 验证配置内容
  console.log('✓ 测试配置:', {
    frontendUrl: testConfig.app.frontendUrl,
    apiBaseUrl: testConfig.app.apiBaseUrl,
    defaultTimeout: testConfig.timeouts.default,
  });
  
  // 验证用户配置
  const adminUser = getTestUser('admin');
  console.log('✓ 管理员用户:', adminUser.username);
  
  // 验证超时配置
  const timeout = getTimeout('default');
  console.log('✓ 默认超时:', timeout, 'ms');
  
} catch (error) {
  console.error('✗ 辅助函数导入失败:', error.message);
  process.exit(1);
}

// 简单的配置验证测试
test('配置验证测试', async ({ page }) => {
  // 验证基础配置
  expect(testConfig).toBeDefined();
  expect(testConfig.app.frontendUrl).toBeTruthy();
  
  console.log('✓ 所有配置验证通过');
});
