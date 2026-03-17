/**
 * @file verify-setup.js
 * @path frontend/tests/e2e/
 * @description E2E测试框架配置验证脚本（ES Module）
 * 
 * 用于验证Playwright E2E测试框架的配置是否正确，包括：
 * - 依赖包安装检查
 * - 配置文件加载检查
 * - 辅助函数导入检查
 * 
 * @author Agent
 * @date 2024-03-16
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('========================================');
console.log('E2E测试框架配置验证');
console.log('========================================\n');

// 1. 检查依赖包
console.log('1. 检查依赖包安装情况...');
const packageJsonPath = path.join(__dirname, '../../package.json');
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));

const requiredDeps = ['@playwright/test'];
const requiredDevDeps = ['@playwright/test', 'playwright-electron'];

let allDepsInstalled = true;

requiredDeps.forEach(dep => {
  if (packageJson.dependencies && packageJson.dependencies[dep]) {
    console.log(`  ✓ ${dep}: ${packageJson.dependencies[dep]}`);
  } else {
    console.log(`  ✗ ${dep}: 未安装`);
    allDepsInstalled = false;
  }
});

requiredDevDeps.forEach(dep => {
  if (packageJson.devDependencies && packageJson.devDependencies[dep]) {
    console.log(`  ✓ ${dep}: ${packageJson.devDependencies[dep]}`);
  } else {
    console.log(`  ✗ ${dep}: 未安装`);
    allDepsInstalled = false;
  }
});

if (!allDepsInstalled) {
  console.log('\n  警告: 部分依赖未安装，请运行: npm install');
}

// 2. 检查配置文件
console.log('\n2. 检查配置文件...');
const configFiles = [
  'playwright.config.js',
  'helpers/test.config.js',
  'helpers/electron.helper.js',
  'helpers/auth.helper.js',
  'helpers/device.helper.js',
  'helpers/index.js',
];

configFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  if (fs.existsSync(filePath)) {
    console.log(`  ✓ ${file}`);
  } else {
    console.log(`  ✗ ${file}: 不存在`);
  }
});

// 3. 检查测试文件
console.log('\n3. 检查测试文件...');
const testFiles = [
  'example.spec.js',
  'electron.example.spec.js',
  'navigation.spec.js',
  'device.spec.js',
  'analysis.spec.js',
];

testFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  if (fs.existsSync(filePath)) {
    console.log(`  ✓ ${file}`);
  } else {
    console.log(`  ✗ ${file}: 不存在`);
  }
});

// 4. 检查helpers目录结构
console.log('\n4. 检查helpers目录结构...');
const helpersDir = path.join(__dirname, 'helpers');
if (fs.existsSync(helpersDir)) {
  const files = fs.readdirSync(helpersDir);
  console.log(`  ✓ helpers目录存在，包含 ${files.length} 个文件:`);
  files.forEach(file => {
    console.log(`    - ${file}`);
  });
} else {
  console.log('  ✗ helpers目录不存在');
}

// 5. 验证配置文件内容
console.log('\n5. 验证配置文件内容...');
try {
  const configModule = await import('./helpers/test.config.js');
  const config = configModule.testConfig;
  
  if (config) {
    console.log('  ✓ test.config.js 加载成功');
    console.log(`    - 前端URL: ${config.app.frontendUrl}`);
    console.log(`    - API URL: ${config.app.apiBaseUrl}`);
    console.log(`    - 默认超时: ${config.timeouts.default}ms`);
    console.log(`    - 浏览器: ${config.browser.defaultBrowser}`);
  }
} catch (error) {
  console.log('  ✗ 配置验证失败:', error.message);
}

// 6. 检查Electron支持
console.log('\n6. 检查Electron测试支持...');
const electronPath = path.join(__dirname, '../../../electron');
if (fs.existsSync(electronPath)) {
  console.log('  ✓ Electron应用目录存在');
  
  const electronPackageJson = path.join(electronPath, 'package.json');
  if (fs.existsSync(electronPackageJson)) {
    const pkg = JSON.parse(fs.readFileSync(electronPackageJson, 'utf-8'));
    console.log(`    - Electron版本: ${pkg.devDependencies?.electron || '未知'}`);
    console.log(`    - 应用名称: ${pkg.productName || pkg.name}`);
  }
} else {
  console.log('  ✗ Electron应用目录不存在');
}

// 7. 总结
console.log('\n========================================');
console.log('验证完成！');
console.log('========================================');
console.log('\n运行测试命令:');
console.log('  npm run test:e2e              # 运行所有E2E测试');
console.log('  npm run test:e2e:ui            # 以UI模式运行测试');
console.log('  npx playwright test --ui       # 使用Playwright UI');
console.log('\nElectron测试:');
console.log('  ELECTRON_TEST=true npm run test:e2e  # 运行Electron测试');
console.log('========================================\n');
