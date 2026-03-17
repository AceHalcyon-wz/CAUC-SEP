# E2E测试套件文档

## 概述

本测试套件为CAUC-SEP自旋电子器件实验平台提供全面的端到端测试覆盖，确保应用在各种使用场景下的稳定性和可靠性。

## 测试文件结构

```
frontend/tests/e2e/
├── auth.spec.js              # 用户认证流程测试
├── settings.spec.js          # 系统设置和用户管理测试
├── cross-browser.spec.js     # 跨浏览器兼容性测试
├── navigation.spec.js        # 导航和布局测试（已存在）
├── analysis.spec.js          # 数据分析功能测试（已存在）
├── device.spec.js            # 设备控制功能测试（已存在）
├── helpers/                  # 测试辅助工具
│   ├── auth.helper.js        # 认证辅助函数
│   ├── device.helper.js      # 设备辅助函数
│   ├── test.config.js        # 测试配置
│   └── index.js              # 辅助函数导出
├── playwright.config.js      # Playwright配置
└── run-e2e-tests.bat         # Windows测试运行脚本
```

## 测试覆盖范围

### 1. 用户认证流程测试 (auth.spec.js)

#### 登录页面测试
- ✅ 登录页面基础渲染
- ✅ 登录模式切换（快速登录、账号密码登录、访客模式）
- ✅ 快速登录功能
- ✅ 账号密码登录功能
- ✅ 访客模式登录
- ✅ 登录加载状态显示
- ✅ 登录成功后的重定向
- ✅ 登录页面响应式设计

#### 登出功能测试
- ✅ 成功登出
- ✅ 登出后清除Token

#### Token管理测试
- ✅ 登录后Token存储
- ✅ Token过期处理
- ✅ 模拟认证状态

#### 权限控制测试
- ✅ 未登录访问受保护页面
- ✅ 管理员权限验证
- ✅ 普通用户权限限制
- ✅ 权限检查功能

#### 登录错误处理测试
- ✅ 网络错误处理
- ✅ 服务器错误处理

#### 会话管理测试
- ✅ 会话持久化
- ✅ 多标签页会话共享
- ✅ 会话超时处理

### 2. 系统设置和用户管理测试 (settings.spec.js)

#### 系统配置页面测试
- ✅ 系统配置页面渲染
- ✅ 配置项显示
- ✅ 配置保存功能
- ✅ 配置重置功能
- ✅ 配置历史记录

#### 个人中心页面测试
- ✅ 个人中心页面渲染
- ✅ 个人信息标签页
- ✅ 编辑个人信息功能
- ✅ 修改密码功能
- ✅ 偏好设置标签页
- ✅ 操作历史标签页
- ✅ 头像上传功能
- ✅ 响应式设计

#### 用户管理页面测试
- ✅ 用户管理页面渲染
- ✅ 用户列表显示
- ✅ 添加用户功能
- ✅ 编辑用户功能
- ✅ 删除用户功能
- ✅ 用户搜索功能
- ✅ 用户筛选功能
- ✅ 权限设置功能
- ✅ 批量操作功能
- ✅ 分页功能
- ✅ 刷新功能

#### 审计日志页面测试
- ✅ 审计日志页面渲染
- ✅ 日志筛选功能
- ✅ 日志导出功能
- ✅ 日志详情查看

#### 关于系统页面测试
- ✅ 关于系统页面渲染
- ✅ 系统版本信息显示
- ✅ 技术栈信息显示

#### 性能监控页面测试
- ✅ 性能监控页面渲染
- ✅ 性能指标显示

#### 帮助文档页面测试
- ✅ 帮助文档页面渲染
- ✅ 文档搜索功能

#### 设置页面权限控制测试
- ✅ 普通用户访问限制
- ✅ 管理员完全访问权限

### 3. 跨浏览器兼容性测试 (cross-browser.spec.js)

#### 跨浏览器基础功能测试
- ✅ 登录页面在各浏览器正确渲染
- ✅ 快速登录功能在各浏览器一致性
- ✅ 设备状态页面在各浏览器渲染
- ✅ 电机控制页面在各浏览器一致性
- ✅ 数据分析页面在各浏览器一致性

#### CSS和样式兼容性测试
- ✅ Flexbox布局兼容性
- ✅ CSS Grid布局兼容性
- ✅ CSS变量兼容性
- ✅ 渐变背景兼容性
- ✅ 阴影效果兼容性
- ✅ 圆角效果兼容性

#### JavaScript API兼容性测试
- ✅ LocalStorage兼容性
- ✅ Fetch API兼容性
- ✅ Promise兼容性
- ✅ async/await兼容性
- ✅ WebSocket兼容性

#### 表单输入兼容性测试
- ✅ 文本输入兼容性
- ✅ 下拉选择兼容性
- ✅ 复选框兼容性
- ✅ 开关兼容性
- ✅ 日期选择器兼容性

#### 图表渲染兼容性测试
- ✅ Canvas渲染兼容性
- ✅ SVG渲染兼容性
- ✅ 图表交互兼容性

#### 响应式设计兼容性测试
- ✅ 桌面端布局
- ✅ 平板端布局
- ✅ 移动端布局
- ✅ 媒体查询兼容性

#### 性能兼容性测试
- ✅ 页面加载性能
- ✅ 交互响应性能
- ✅ 内存使用

#### 特定浏览器测试
- ✅ Firefox特定功能测试
- ✅ Chromium特定功能测试
- ✅ WebKit特定功能测试

## 运行测试

### 方式一：使用NPM脚本

```bash
# 运行所有E2E测试
npm run test:e2e

# 打开Playwright UI界面
npm run test:e2e:ui

# 运行所有测试（单元测试 + E2E测试）
npm run test:all
```

### 方式二：使用测试脚本（Windows）

```bash
# 运行所有测试
tests\e2e\run-e2e-tests.bat

# 仅运行认证测试
tests\e2e\run-e2e-tests.bat --auth

# 仅运行设置测试
tests\e2e\run-e2e-tests.bat --settings

# 仅运行跨浏览器测试
tests\e2e\run-e2e-tests.bat --cross-browser

# 打开UI界面
tests\e2e\run-e2e-tests.bat --ui

# 调试模式
tests\e2e\run-e2e-tests.bat --debug
```

### 方式三：直接使用Playwright CLI

```bash
# 运行所有测试
npx playwright test

# 运行特定测试文件
npx playwright test auth.spec.js

# 运行特定浏览器
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit

# 运行特定测试用例
npx playwright test -g "应该支持快速登录"

# 查看测试报告
npx playwright show-report

# 调试模式
npx playwright test --debug

# UI模式
npx playwright test --ui
```

## 测试配置

### 浏览器配置

测试支持以下浏览器：
- **Chromium**: Chrome、Edge等Chromium内核浏览器
- **Firefox**: Firefox浏览器
- **WebKit**: Safari等WebKit内核浏览器
- **Mobile Chrome**: 移动端Chrome（iPhone 8尺寸）

### 测试环境

测试环境配置位于 `helpers/test.config.js`，包括：
- 应用URL配置
- 测试用户账号
- 设备配置
- 超时设置
- API端点配置

### 环境变量

可以通过环境变量覆盖测试配置：

```bash
# 设置前端URL
export FRONTEND_URL=http://localhost:5173

# 设置后端API URL
export API_BASE_URL=http://localhost:8000

# 设置测试用户
export TEST_ADMIN_USERNAME=admin
export TEST_ADMIN_PASSWORD=admin123

# 启用CI模式
export CI=true
```

## 测试最佳实践

### 1. 测试隔离
- 每个测试用例独立运行
- 使用 `beforeEach` 和 `afterEach` 进行状态重置
- 避免测试间的依赖关系

### 2. 选择器策略
- 优先使用语义化选择器（如 `getByRole`、`getByText`）
- 使用 `data-testid` 属性进行精确定位
- 避免使用脆弱的CSS选择器

### 3. 等待策略
- 使用 `waitForLoadState` 等待页面加载
- 使用 `waitForSelector` 等待元素出现
- 避免使用固定的 `waitForTimeout`

### 4. 断言最佳实践
- 使用明确的断言消息
- 验证关键业务逻辑
- 检查用户可见的状态变化

### 5. 错误处理
- 捕获并验证错误消息
- 测试异常场景
- 验证错误恢复机制

## 测试报告

### HTML报告
测试完成后会自动生成HTML报告：
- 位置：`playwright-report/index.html`
- 包含：测试结果、截图、视频、追踪信息

### 控制台输出
测试运行时会在控制台输出详细日志：
- 测试用例执行状态
- 失败原因和堆栈信息
- 性能指标

### 截图和视频
- 失败时自动截图
- 失败时保留视频录制
- 重试时记录追踪信息

## 持续集成

### GitHub Actions配置示例

```yaml
name: E2E Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Install Playwright browsers
        run: npx playwright install --with-deps
      
      - name: Run E2E tests
        run: npm run test:e2e
        env:
          CI: true
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

## 故障排查

### 常见问题

1. **测试超时**
   - 增加超时时间：`test.setTimeout(60000)`
   - 检查网络连接
   - 验证开发服务器是否运行

2. **元素未找到**
   - 检查选择器是否正确
   - 增加等待时间
   - 验证页面是否完全加载

3. **浏览器启动失败**
   - 安装浏览器：`npx playwright install`
   - 检查系统依赖
   - 验证浏览器路径

4. **权限错误**
   - 检查用户权限配置
   - 验证认证状态
   - 确认测试用户存在

### 调试技巧

1. **使用UI模式**
   ```bash
   npx playwright test --ui
   ```

2. **使用调试模式**
   ```bash
   npx playwright test --debug
   ```

3. **查看追踪信息**
   ```bash
   npx playwright show-trace trace.zip
   ```

4. **打印页面内容**
   ```javascript
   console.log(await page.content());
   console.log(await page.screenshot({ path: 'debug.png' }));
   ```

## 维护指南

### 添加新测试

1. 在相应的测试文件中添加新的测试用例
2. 遵循现有的命名规范和结构
3. 添加必要的注释和文档
4. 确保测试独立性和可重复性

### 更新测试

1. 当UI或功能变更时，更新相应的测试
2. 保持测试与实际应用的一致性
3. 定期审查和优化测试用例

### 删除测试

1. 移除过时或不再需要的测试
2. 更新相关文档
3. 确保测试覆盖率不受影响

## 联系方式

如有问题或建议，请联系开发团队：
- 项目地址：D:\cauc-sep
- 测试目录：D:\cauc-sep\frontend\tests\e2e
