/**
 * @file verify-e2e-tests.js
 * @path frontend/tests/e2e/
 * @description E2E测试环境验证脚本
 * 
 * 验证测试环境是否正确配置，包括：
 * - 依赖安装检查
 * - 测试文件完整性检查
 * - 测试配置验证
 * 
 * @author Agent
 * @date 2024-03-16
 */

import { execSync } from 'child_process';
import { existsSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * 验证结果
 */
const results = {
  passed: [],
  failed: [],
  warnings: [],
};

/**
 * 检查项
 */
const checks = {
  /**
   * 检查依赖安装
   */
  checkDependencies() {
    console.log('\n📦 检查依赖安装...');
    
    const requiredDeps = [
      '@playwright/test',
      'playwright-electron',
    ];
    
    const packageJsonPath = join(__dirname, '../../package.json');
    
    if (existsSync(packageJsonPath)) {
      const packageJson = JSON.parse(
        execSync(`cat "${packageJsonPath}"`, { encoding: 'utf-8' })
      );
      
      const allDeps = {
        ...packageJson.dependencies,
        ...packageJson.devDependencies,
      };
      
      requiredDeps.forEach(dep => {
        if (allDeps[dep]) {
          results.passed.push(`依赖 ${dep} 已安装 (${allDeps[dep]})`);
        } else {
          results.failed.push(`依赖 ${dep} 未安装`);
        }
      });
    } else {
      results.failed.push('package.json 文件不存在');
    }
  },

  /**
   * 检查测试文件
   */
  checkTestFiles() {
    console.log('\n📄 检查测试文件...');
    
    const requiredFiles = [
      'app-launch.spec.js',
      'auth-flow.spec.js',
      'device-flow.spec.js',
      'experiment-flow.spec.js',
      'playwright.config.js',
    ];
    
    requiredFiles.forEach(file => {
      const filePath = join(__dirname, file);
      if (existsSync(filePath)) {
        results.passed.push(`测试文件 ${file} 存在`);
      } else {
        results.failed.push(`测试文件 ${file} 不存在`);
      }
    });
  },

  /**
   * 检查helper文件
   */
  checkHelperFiles() {
    console.log('\n🔧 检查辅助文件...');
    
    const helperFiles = [
      'helpers/electron.helper.js',
      'helpers/auth.helper.js',
      'helpers/device.helper.js',
      'helpers/test.config.js',
      'helpers/index.js',
    ];
    
    helperFiles.forEach(file => {
      const filePath = join(__dirname, file);
      if (existsSync(filePath)) {
        results.passed.push(`辅助文件 ${file} 存在`);
      } else {
        results.failed.push(`辅助文件 ${file} 不存在`);
      }
    });
  },

  /**
   * 检查测试配置
   */
  checkTestConfig() {
    console.log('\n⚙️  检查测试配置...');
    
    const configPath = join(__dirname, 'playwright.config.js');
    
    if (existsSync(configPath)) {
      results.passed.push('playwright.config.js 存在');
      
      try {
        // 检查配置是否可以导入
        import(configPath).then(config => {
          if (config.default) {
            results.passed.push('playwright.config.js 可以正常导入');
          }
        }).catch(err => {
          results.warnings.push(`playwright.config.js 导入警告: ${err.message}`);
        });
      } catch (err) {
        results.warnings.push(`playwright.config.js 检查警告: ${err.message}`);
      }
    }
  },

  /**
   * 检查Electron应用
   */
  checkElectronApp() {
    console.log('\n🖥️  检查Electron应用...');
    
    const electronPath = join(__dirname, '../../../electron');
    
    if (existsSync(electronPath)) {
      results.passed.push('Electron目录存在');
      
      const mainPath = join(electronPath, 'src/main.js');
      if (existsSync(mainPath)) {
        results.passed.push('Electron主进程文件存在');
      } else {
        results.failed.push('Electron主进程文件不存在');
      }
      
      const packageJsonPath = join(electronPath, 'package.json');
      if (existsSync(packageJsonPath)) {
        results.passed.push('Electron package.json存在');
      } else {
        results.warnings.push('Electron package.json不存在');
      }
    } else {
      results.warnings.push('Electron目录不存在（Electron测试将被跳过）');
    }
  },

  /**
   * 检查前端构建
   */
  checkFrontendBuild() {
    console.log('\n🎨 检查前端构建...');
    
    const distPath = join(__dirname, '../../dist');
    
    if (existsSync(distPath)) {
      results.passed.push('前端构建产物存在');
      
      const indexPath = join(distPath, 'index.html');
      if (existsSync(indexPath)) {
        results.passed.push('前端index.html存在');
      } else {
        results.failed.push('前端index.html不存在');
      }
    } else {
      results.warnings.push('前端构建产物不存在（需要运行 npm run build）');
    }
  },

  /**
   * 检查后端服务
   */
  checkBackendService() {
    console.log('\n🔌 检查后端服务...');
    
    try {
      // 尝试访问后端健康检查端点
      const response = execSync(
        'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health',
        { encoding: 'utf-8', timeout: 5000 }
      ).trim();
      
      if (response === '200') {
        results.passed.push('后端服务运行正常');
      } else {
        results.warnings.push(`后端服务响应异常 (HTTP ${response})`);
      }
    } catch (err) {
      results.warnings.push('后端服务未运行（某些测试可能失败）');
    }
  },
};

/**
 * 打印结果
 */
function printResults() {
  console.log('\n' + '='.repeat(60));
  console.log('📊 验证结果');
  console.log('='.repeat(60));
  
  if (results.passed.length > 0) {
    console.log('\n✅ 通过的检查:');
    results.passed.forEach(item => console.log(`   ✓ ${item}`));
  }
  
  if (results.failed.length > 0) {
    console.log('\n❌ 失败的检查:');
    results.failed.forEach(item => console.log(`   ✗ ${item}`));
  }
  
  if (results.warnings.length > 0) {
    console.log('\n⚠️  警告:');
    results.warnings.forEach(item => console.log(`   ! ${item}`));
  }
  
  console.log('\n' + '='.repeat(60));
  console.log(`总计: ${results.passed.length} 通过, ${results.failed.length} 失败, ${results.warnings.length} 警告`);
  console.log('='.repeat(60));
  
  // 返回退出码
  process.exit(results.failed.length > 0 ? 1 : 0);
}

/**
 * 主函数
 */
async function main() {
  console.log('🔍 E2E测试环境验证');
  console.log('='.repeat(60));
  
  // 执行所有检查
  Object.values(checks).forEach(check => check());
  
  // 打印结果
  printResults();
}

// 运行验证
main().catch(err => {
  console.error('验证过程出错:', err);
  process.exit(1);
});
