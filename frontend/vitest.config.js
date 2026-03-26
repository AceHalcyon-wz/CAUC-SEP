/**
 * @file vitest.config.js
 * @path frontend/
 * @description Vitest测试框架配置文件
 * @version v2.0
 * @author DevOps Engineer Agent
 * @date 2026-03-25
 * @updated 完善覆盖率阈值、测试报告配置
 */

import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  test: {
    // 测试环境
    environment: 'jsdom',
    
    // 全局变量
    globals: true,
    
    // 设置文件
    setupFiles: ['./tests/unit/setup.js'],
    
    // 测试文件匹配
    include: ['src/**/*.{test,spec}.{js,ts}', 'tests/unit/**/*.{test,spec}.{js,ts}'],
    exclude: ['node_modules', 'tests/e2e/**'],
    
    // 测试超时配置
    testTimeout: 10000,
    hookTimeout: 10000,
    
    // 并行执行
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
        minThreads: 1,
        maxThreads: 4,
      },
    },
    
    // 覆盖率配置
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'json', 'json-summary', 'html', 'lcov', 'cobertura'],
      reportsDirectory: './coverage',
      
      // 覆盖率阈值（CI环境强制）
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 65,
        statements: 70,
        'global': {
          lines: 70,
          functions: 70,
          branches: 65,
          statements: 70,
        },
      },
      
      // 排除文件
      exclude: [
        'node_modules/',
        'src/**/*.spec.js',
        'src/**/*.test.js',
        'src/tests/**',
        'tests/**',
        'src/types/generated.ts',
        'src/main.js',
        'src/vite-env.d.ts',
        'src/**/*.d.ts',
        'src/i18n/**',
        'src/styles/**',
        'src/config/**',
        'src/directives/**',
        'src/router/**',
        'src/stores/index.js',
        'src/components/index.js',
        'src/composables/index.js',
        'src/views/**',  // 页面组件覆盖率要求较低
      ],
      
      // 包含所有文件
      all: true,
      
      // 清除缓存
      clean: true,
      cleanOnRerun: true,
      
      // 报告详细程度
      reportOnFailure: true,
      skipFull: true,
    },
    
    // 监听模式配置
    watch: false,
    
    // 失败重试
    retry: 0,
    
    // 报告器配置
    reporters: [
      'default',
      ['junit', { suiteName: 'CAUC-SEP Frontend Tests', outputFile: './test-results/junit.xml' }],
    ],
    
    // 快照配置
    snapshotFormat: {
      escapeString: true,
      printBasicPrototype: true,
    },
    
    // 慢测试阈值
    slowTestThreshold: 300,
  },
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  
  // 定义环境变量
  define: {
    __TEST__: true,
    __DEV__: false,
    __PROD__: false,
  },
});
