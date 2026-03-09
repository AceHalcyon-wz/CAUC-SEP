/**
 * @file .eslintrc.cjs
 * @path frontend/
 * @description ESLint 配置文件 - Vue3 + Vite 项目
 * @author CAUC-SEP Team
 * @date 2024-03-06
 */

module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  plugins: ['vue'],
  rules: {
    // Vue 规则
    'vue/multi-word-component-names': 'off',
    'vue/no-v-html': 'warn',
    'vue/require-default-prop': 'off',
    'vue/require-explicit-emits': 'warn',
    'vue/component-definition-name-casing': ['error', 'PascalCase'],
    'vue/component-name-in-template-casing': ['error', 'PascalCase'],
    'vue/block-lang': [
      'error',
      {
        script: {
          lang: 'js',
        },
      },
    ],

    // JS 规则
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    'no-undef': 'error',
    'prefer-const': 'warn',
    'no-var': 'error',
    eqeqeq: ['error', 'always'],
    curly: ['error', 'multi-line'],
  },
  ignorePatterns: [
    'node_modules/',
    'dist/',
    'coverage/',
    '*.config.js',
    'tests/e2e/',
  ],
  overrides: [
    {
      files: ['**/__tests__/**/*.{j,t}s?(x)', '**/*.test.{j,t}s?(x)'],
      env: {
        jest: true,
      },
      rules: {
        'no-console': 'off',
        'vue/require-default-prop': 'off',
      },
    },
  ],
};
