/**
 * @file vitest.config.js
 * @path frontend/
 * @description Vitest测试框架配置文件
 * @author Agent
 * @date 2024-03-07
 * @updated 2026-03-16 添加覆盖率阈值配置
 */

import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
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
      ],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 70,
        statements: 70,
      },
      all: true,
    },
    globals: true,
    setupFiles: ['./tests/unit/setup.js'],
    include: ['src/**/*.{test,spec}.{js,ts}', 'tests/unit/**/*.{test,spec}.{js,ts}'],
    exclude: ['node_modules', 'e2e/**'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
