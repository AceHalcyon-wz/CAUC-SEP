# 测试指南

## 概述

本项目包含完整的单元测试和E2E测试套件，使用 Vitest 进行单元测试，使用 Playwright 进行E2E测试。

## 测试结构

```
frontend/
├── src/
│   ├── components/
│   │   └── __tests__/
│   │       └── DataAnalysis.test.js    # 组件单元测试
│   ├── composables/
│   │   └── __tests__/
│   │       ├── useProgress.test.js     # 组合式函数测试
│   │       └── useOnlineStatus.test.js
│   ├── utils/
│   │   └── __tests__/
│   │       └── chartUtils.test.js      # 工具函数测试
│   └── test/
│       └── setup.js                     # 测试环境设置
├── e2e/
│   ├── playwright.config.js             # Playwright配置
│   ├── analysis.spec.js                 # 数据分析E2E测试
│   ├── navigation.spec.js               # 导航E2E测试
│   └── device.spec.js                   # 设备控制E2E测试
└── vitest.config.js                     # Vitest配置
```

## 安装依赖

```bash
# 安装项目依赖
npm install

# 安装Playwright浏览器
npx playwright install
```

## 运行测试

### 单元测试

```bash
# 运行所有单元测试（监听模式）
npm run test

# 运行所有单元测试（单次运行）
npm run test:run

# 运行测试并生成覆盖率报告
npm run test:coverage

# 使用UI界面运行测试
npm run test:ui
```

### E2E测试

```bash
# 运行所有E2E测试
npm run test:e2e

# 使用UI界面运行E2E测试
npm run test:e2e:ui

# 调试模式运行E2E测试
npm run test:e2e:debug

# 查看E2E测试报告
npm run test:e2e:report
```

### 运行所有测试

```bash
# 运行单元测试和E2E测试
npm run test:all
```

## 测试覆盖范围

### 单元测试

#### 组件测试 (DataAnalysis.test.js)
- 组件渲染测试
- 多模型对比功能测试
- 报告生成和导出测试
- 历史记录管理测试
- 标注功能测试
- 大数据量优化测试

#### 组合式函数测试
- **useProgress.test.js**
  - 初始化状态测试
  - 操作生命周期测试（开始、更新、完成、失败、取消）
  - 暂停和恢复测试
  - 计算属性测试
  - 快照功能测试

- **useOnlineStatus.test.js**
  - 在线/离线状态检测测试
  - 事件监听测试
  - 离线持续时间计算测试
  - 网络质量评估测试
  - 健康检查测试

#### 工具函数测试 (chartUtils.test.js)
- 数据采样算法测试（smartSampling、downsampleData）
- 数据特征检测测试
- 自适应采样策略测试
- 图表配置生成测试
- 数据导出功能测试
- 性能监控工具测试

### E2E测试

#### 数据分析功能测试 (analysis.spec.js)
- 页面渲染测试
- 标签页切换测试
- 信号平滑功能测试
- 磁滞回线分析测试
- 多模型对比测试
- 报告生成和导出测试
- 历史记录管理测试
- 标注功能测试
- 响应式设计测试
- 性能测试

#### 导航和布局测试 (navigation.spec.js)
- 侧边栏和顶部栏测试
- 页面路由测试
- 键盘快捷键测试
- 可访问性测试

#### 设备控制测试 (device.spec.js)
- 设备连接测试
- 电机控制测试
- 温度控制测试
- 电磁铁控制测试
- 压电控制测试
- 安培计控制测试
- 设备状态监控测试

## 测试最佳实践

### 单元测试

1. **测试命名**
   ```javascript
   describe('功能模块', () => {
     it('应该正确执行某操作', () => {
       // 测试代码
     });
   });
   ```

2. **测试结构**
   ```javascript
   it('测试描述', () => {
     // Arrange - 准备测试数据
     const input = 'test';
     
     // Act - 执行测试操作
     const result = functionUnderTest(input);
     
     // Assert - 验证结果
     expect(result).toBe('expected');
   });
   ```

3. **Mock外部依赖**
   ```javascript
   vi.mock('../api/analysis', () => ({
     multiModelFit: vi.fn(),
   }));
   ```

### E2E测试

1. **使用有意义的定位器**
   ```javascript
   // 推荐
   await page.click('button:has-text("提交")');
   await page.locator('.submit-button').click();
   
   // 不推荐
   await page.click('button:nth-child(3)');
   ```

2. **等待策略**
   ```javascript
   // 等待元素可见
   await expect(page.locator('.result')).toBeVisible();
   
   // 等待网络空闲
   await page.waitForLoadState('networkidle');
   ```

3. **测试隔离**
   ```javascript
   test.beforeEach(async ({ page }) => {
     // 每个测试前的准备工作
     await page.goto('/');
   });
   ```

## 测试覆盖率目标

- **语句覆盖率**: >= 80%
- **分支覆盖率**: >= 75%
- **函数覆盖率**: >= 80%
- **行覆盖率**: >= 80%

## 持续集成

测试会在以下情况自动运行：
- 提交代码到主分支
- 创建Pull Request
- 定期夜间构建

## 故障排查

### 单元测试失败

1. 检查Mock是否正确配置
2. 验证测试数据是否符合预期
3. 确认组件依赖是否正确注入

### E2E测试失败

1. 检查开发服务器是否正常运行
2. 验证测试环境配置
3. 查看测试截图和视频
4. 使用调试模式逐步排查

## 常见问题

**Q: 如何跳过某个测试？**
```javascript
it.skip('暂时跳过的测试', () => {
  // 测试代码
});
```

**Q: 如何只运行特定测试？**
```javascript
it.only('只运行这个测试', () => {
  // 测试代码
});
```

**Q: 如何调试E2E测试？**
```bash
npm run test:e2e:debug
```

**Q: 如何查看测试覆盖率报告？**
```bash
npm run test:coverage
# 报告会生成在 coverage/ 目录
```

## 相关文档

- [Vitest 官方文档](https://vitest.dev/)
- [Vue Test Utils 文档](https://test-utils.vuejs.org/)
- [Playwright 文档](https://playwright.dev/)
- [测试最佳实践](https://testingjavascript.com/)

---

**更新日期**: 2026-03-08  
**维护者**: Agent
