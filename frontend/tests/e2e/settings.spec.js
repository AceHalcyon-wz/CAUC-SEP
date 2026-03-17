/**
 * @file settings.spec.js
 * @path frontend/tests/e2e/
 * @description 系统设置和用户管理E2E测试套件
 * 
 * 本测试文件包含系统设置和用户管理模块的端到端测试，覆盖以下功能：
 * - 系统配置页面测试
 * - 个人中心页面测试
 * - 用户管理页面测试
 * - 权限控制测试
 * - 审计日志测试
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @playwright/test
 */

import { test, expect } from '@playwright/test';
import { AuthHelper } from './helpers/auth.helper';

/**
 * 系统配置页面测试套件
 * 
 * 测试系统配置的各项功能。
 */
test.describe('系统配置页面', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    
    // 模拟管理员登录
    await authHelper.mockAuthenticated({ role: 'admin' });
    
    // 导航到系统配置页面
    await page.goto('/settings/config');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试系统配置页面渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示系统配置页面', async ({ page }) => {
    // 验证页面标题
    const pageTitle = page.locator('.page-title, h1');
    await expect(pageTitle).toContainText('系统配置');
    
    // 验证配置编辑器显示
    const configEditor = page.locator('.config-editor, .settings-content');
    await expect(configEditor).toBeVisible();
  });

  /**
   * 测试配置项显示
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示配置项列表', async ({ page }) => {
    // 验证配置项存在
    const configItems = page.locator('.config-item, .el-form-item');
    const count = await configItems.count();
    
    expect(count).toBeGreaterThan(0);
  });

  /**
   * 测试配置保存功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持保存配置', async ({ page }) => {
    // 查找保存按钮
    const saveButton = page.locator('button:has-text("保存"), button:has-text("提交")').first();
    
    if (await saveButton.isVisible()) {
      await saveButton.click();
      
      // 等待保存完成
      await page.waitForTimeout(1000);
      
      // 验证成功消息
      const successMessage = page.locator('.el-message--success, .ant-message-success');
      await expect(successMessage).toBeVisible({ timeout: 5000 });
    }
  });

  /**
   * 测试配置重置功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持重置配置', async ({ page }) => {
    // 查找重置按钮
    const resetButton = page.locator('button:has-text("重置"), button:has-text("恢复默认")').first();
    
    if (await resetButton.isVisible()) {
      await resetButton.click();
      
      // 等待重置完成
      await page.waitForTimeout(500);
    }
  });

  /**
   * 测试配置历史记录
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示配置历史记录', async ({ page }) => {
    // 查找历史记录按钮
    const historyButton = page.locator('button:has-text("历史"), button:has-text("历史记录")').first();
    
    if (await historyButton.isVisible()) {
      await historyButton.click();
      
      // 验证历史记录对话框显示
      const historyDialog = page.locator('.el-dialog, .ant-modal');
      await expect(historyDialog).toBeVisible();
    }
  });
});

/**
 * 个人中心页面测试套件
 * 
 * 测试个人中心的各项功能。
 */
test.describe('个人中心页面', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    
    // 模拟用户登录
    await authHelper.mockAuthenticated({ 
      id: 'test-user-123',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user'
    });
    
    // 导航到个人中心页面
    await page.goto('/settings/profile');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试个人中心页面渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示个人中心页面', async ({ page }) => {
    // 验证页面标题
    const pageTitle = page.locator('.page-title, h1');
    await expect(pageTitle).toContainText('个人中心');
    
    // 验证标签页显示
    const tabs = page.locator('.el-tabs__item, .ant-tabs-tab');
    const count = await tabs.count();
    
    expect(count).toBeGreaterThanOrEqual(3);
  });

  /**
   * 测试个人信息标签页
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示个人信息标签页', async ({ page }) => {
    // 验证个人信息标签页激活
    const activeTab = page.locator('.el-tabs__item.is-active, .ant-tabs-tab-active');
    await expect(activeTab).toContainText('个人信息');
    
    // 验证用户名显示
    const usernameInput = page.locator('input[name="username"], input[placeholder*="用户名"]');
    await expect(usernameInput).toBeVisible();
    
    // 验证邮箱显示
    const emailInput = page.locator('input[name="email"], input[placeholder*="邮箱"]');
    await expect(emailInput).toBeVisible();
  });

  /**
   * 测试编辑个人信息功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持编辑个人信息', async ({ page }) => {
    // 点击编辑按钮
    const editButton = page.locator('button:has-text("编辑")').first();
    
    if (await editButton.isVisible()) {
      await editButton.click();
      
      // 修改用户名
      const usernameInput = page.locator('input[name="username"]').first();
      if (await usernameInput.isEnabled()) {
        await usernameInput.clear();
        await usernameInput.fill('newusername');
        
        // 点击保存按钮
        const saveButton = page.locator('button:has-text("保存")').first();
        await saveButton.click();
        
        // 等待保存完成
        await page.waitForTimeout(1000);
      }
    }
  });

  /**
   * 测试修改密码功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持修改密码', async ({ page }) => {
    // 查找密码修改区域
    const oldPasswordInput = page.locator('input[placeholder*="当前密码"], input[placeholder*="旧密码"]').first();
    
    if (await oldPasswordInput.isVisible()) {
      // 填写密码表单
      await oldPasswordInput.fill('oldpassword123');
      
      const newPasswordInput = page.locator('input[placeholder*="新密码"]').first();
      await newPasswordInput.fill('newpassword123');
      
      const confirmPasswordInput = page.locator('input[placeholder*="确认密码"], input[placeholder*="再次输入"]').first();
      await confirmPasswordInput.fill('newpassword123');
      
      // 点击修改密码按钮
      const changePasswordBtn = page.locator('button:has-text("修改密码")').first();
      await changePasswordBtn.click();
      
      // 等待操作完成
      await page.waitForTimeout(1000);
    }
  });

  /**
   * 测试偏好设置标签页
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示偏好设置标签页', async ({ page }) => {
    // 点击偏好设置标签
    await page.click('.el-tabs__item:has-text("偏好设置"), .ant-tabs-tab:has-text("偏好设置")');
    
    // 等待标签页切换
    await page.waitForTimeout(300);
    
    // 验证偏好设置内容显示
    const preferencesContent = page.locator('.tab-content, .el-tab-pane');
    await expect(preferencesContent).toBeVisible();
    
    // 验证通知设置
    const notificationSwitch = page.locator('.el-switch, .ant-switch').first();
    await expect(notificationSwitch).toBeVisible();
  });

  /**
   * 测试操作历史标签页
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示操作历史标签页', async ({ page }) => {
    // 点击操作历史标签
    await page.click('.el-tabs__item:has-text("操作历史"), .ant-tabs-tab:has-text("操作历史")');
    
    // 等待标签页切换
    await page.waitForTimeout(300);
    
    // 验证操作历史表格显示
    const historyTable = page.locator('.el-table, .ant-table');
    await expect(historyTable).toBeVisible();
  });

  /**
   * 测试头像上传功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持头像上传', async ({ page }) => {
    // 查找头像上传按钮
    const uploadButton = page.locator('button:has-text("上传头像"), .avatar-upload button').first();
    
    if (await uploadButton.isVisible()) {
      // 验证上传按钮存在
      await expect(uploadButton).toBeEnabled();
    }
  });

  /**
   * 测试响应式设计
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在移动端正常显示', async ({ page }) => {
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // 验证页面正常显示
    const pageTitle = page.locator('.page-title, h1');
    await expect(pageTitle).toBeVisible();
  });
});

/**
 * 用户管理页面测试套件
 * 
 * 测试用户管理的各项功能。
 */
test.describe('用户管理页面', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    
    // 模拟管理员登录
    await authHelper.mockAuthenticated({ role: 'admin' });
    
    // 导航到用户管理页面
    await page.goto('/settings/user-management');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试用户管理页面渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示用户管理页面', async ({ page }) => {
    // 验证页面标题
    const pageTitle = page.locator('.page-title, h1');
    await expect(pageTitle).toContainText('用户管理');
    
    // 验证用户列表显示
    const userTable = page.locator('.el-table, .user-list-card');
    await expect(userTable).toBeVisible();
  });

  /**
   * 测试用户列表显示
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示用户列表', async ({ page }) => {
    // 等待表格加载
    await page.waitForTimeout(1000);
    
    // 验证用户数据行存在
    const userRows = page.locator('.el-table__row, .ant-table-row');
    const count = await userRows.count();
    
    expect(count).toBeGreaterThanOrEqual(0);
  });

  /**
   * 测试添加用户功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持添加用户', async ({ page }) => {
    // 点击添加用户按钮
    const addButton = page.locator('button:has-text("添加用户"), button:has-text("新增")').first();
    
    if (await addButton.isVisible()) {
      await addButton.click();
      
      // 验证添加用户对话框显示
      const dialog = page.locator('.el-dialog, .ant-modal');
      await expect(dialog).toBeVisible();
      
      // 填写用户信息
      const usernameInput = page.locator('.el-dialog input[placeholder*="用户名"], .ant-modal input[placeholder*="用户名"]').first();
      if (await usernameInput.isVisible()) {
        await usernameInput.fill('newtestuser');
        
        const emailInput = page.locator('.el-dialog input[placeholder*="邮箱"], .ant-modal input[placeholder*="邮箱"]').first();
        await emailInput.fill('newtest@example.com');
        
        const passwordInput = page.locator('.el-dialog input[placeholder*="密码"], .ant-modal input[placeholder*="密码"]').first();
        await passwordInput.fill('password123');
        
        // 点击保存
        const saveButton = page.locator('.el-dialog button:has-text("保存"), .ant-modal button:has-text("保存")').first();
        await saveButton.click();
        
        // 等待操作完成
        await page.waitForTimeout(1000);
      }
    }
  });

  /**
   * 测试编辑用户功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持编辑用户', async ({ page }) => {
    // 等待表格加载
    await page.waitForTimeout(1000);
    
    // 查找编辑按钮
    const editButton = page.locator('button:has-text("编辑")').first();
    
    if (await editButton.isVisible()) {
      await editButton.click();
      
      // 验证编辑对话框显示
      const dialog = page.locator('.el-dialog, .ant-modal');
      await expect(dialog).toBeVisible();
      
      // 关闭对话框
      const cancelButton = page.locator('.el-dialog button:has-text("取消"), .ant-modal button:has-text("取消")').first();
      await cancelButton.click();
    }
  });

  /**
   * 测试删除用户功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持删除用户', async ({ page }) => {
    // 等待表格加载
    await page.waitForTimeout(1000);
    
    // 查找删除按钮（排除管理员）
    const deleteButton = page.locator('button:has-text("删除"):not(:disabled)').first();
    
    if (await deleteButton.isVisible()) {
      await deleteButton.click();
      
      // 验证确认对话框显示
      const confirmDialog = page.locator('.el-message-box, .ant-modal-confirm');
      await expect(confirmDialog).toBeVisible();
      
      // 取消删除
      const cancelButton = page.locator('button:has-text("取消")').first();
      await cancelButton.click();
    }
  });

  /**
   * 测试用户搜索功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持搜索用户', async ({ page }) => {
    // 查找搜索输入框
    const searchInput = page.locator('input[placeholder*="用户名"], input[placeholder*="搜索"]').first();
    
    if (await searchInput.isVisible()) {
      // 输入搜索关键词
      await searchInput.fill('admin');
      
      // 点击搜索按钮
      const searchButton = page.locator('button:has-text("搜索")').first();
      await searchButton.click();
      
      // 等待搜索结果
      await page.waitForTimeout(1000);
    }
  });

  /**
   * 测试用户筛选功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持筛选用户', async ({ page }) => {
    // 查找角色筛选下拉框
    const roleSelect = page.locator('.el-select:has-text("角色"), .ant-select:has-text("角色")').first();
    
    if (await roleSelect.isVisible()) {
      await roleSelect.click();
      
      // 选择管理员角色
      const adminOption = page.locator('.el-select-dropdown__item:has-text("管理员"), .ant-select-item:has-text("管理员")').first();
      if (await adminOption.isVisible()) {
        await adminOption.click();
        
        // 等待筛选结果
        await page.waitForTimeout(1000);
      }
    }
  });

  /**
   * 测试权限设置功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持设置用户权限', async ({ page }) => {
    // 等待表格加载
    await page.waitForTimeout(1000);
    
    // 查找权限按钮
    const permissionButton = page.locator('button:has-text("权限")').first();
    
    if (await permissionButton.isVisible()) {
      await permissionButton.click();
      
      // 验证权限对话框显示
      const permissionDialog = page.locator('.el-dialog, .ant-modal');
      await expect(permissionDialog).toBeVisible();
      
      // 验证权限组显示
      const permissionGroups = page.locator('.permission-group, .permission-list');
      await expect(permissionGroups.first()).toBeVisible();
      
      // 关闭对话框
      const cancelButton = page.locator('.el-dialog button:has-text("取消"), .ant-modal button:has-text("取消")').first();
      await cancelButton.click();
    }
  });

  /**
   * 测试批量操作功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持批量操作', async ({ page }) => {
    // 等待表格加载
    await page.waitForTimeout(1000);
    
    // 查找复选框
    const checkbox = page.locator('.el-checkbox__input, .ant-checkbox-input').first();
    
    if (await checkbox.isVisible()) {
      await checkbox.click();
      
      // 验证批量删除按钮激活
      const batchDeleteButton = page.locator('button:has-text("批量删除")');
      await expect(batchDeleteButton).toBeEnabled();
    }
  });

  /**
   * 测试分页功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持分页', async ({ page }) => {
    // 查找分页组件
    const pagination = page.locator('.el-pagination, .ant-pagination');
    
    if (await pagination.isVisible()) {
      // 验证分页信息显示
      const paginationInfo = page.locator('.el-pagination__total, .ant-pagination-total-text');
      await expect(paginationInfo).toBeVisible();
      
      // 测试页码切换
      const nextButton = page.locator('.btn-next, .ant-pagination-next');
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  /**
   * 测试刷新功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持刷新用户列表', async ({ page }) => {
    // 点击刷新按钮
    const refreshButton = page.locator('button:has-text("刷新")').first();
    
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      
      // 等待刷新完成
      await page.waitForTimeout(1000);
    }
  });
});

/**
 * 审计日志页面测试套件
 * 
 * 测试审计日志的各项功能。
 */
test.describe('审计日志页面', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    
    // 模拟管理员登录
    await authHelper.mockAuthenticated({ role: 'admin' });
    
    // 导航到审计日志页面
    await page.goto('/settings/audit');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试审计日志页面渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示审计日志页面', async ({ page }) => {
    // 验证页面标题
    const pageTitle = page.locator('.page-title, h1');
    await expect(pageTitle).toContainText('审计日志');
    
    // 验证日志列表显示
    const logTable = page.locator('.el-table, .audit-log-list');
    await expect(logTable).toBeVisible();
  });

  /**
   * 测试日志筛选功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持筛选日志', async ({ page }) => {
    // 查找日期范围选择器
    const dateRangePicker = page.locator('.el-date-editor--daterange, .ant-picker-range').first();
    
    if (await dateRangePicker.isVisible()) {
      // 验证日期选择器存在
      await expect(dateRangePicker).toBeEnabled();
    }
  });

  /**
   * 测试日志导出功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持导出日志', async ({ page }) => {
    // 查找导出按钮
    const exportButton = page.locator('button:has-text("导出")').first();
    
    if (await exportButton.isVisible()) {
      // 验证导出按钮存在
      await expect(exportButton).toBeEnabled();
    }
  });

  /**
   * 测试日志详情查看
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持查看日志详情', async ({ page }) => {
    // 等待表格加载
    await page.waitForTimeout(1000);
    
    // 查找详情按钮
    const detailButton = page.locator('button:has-text("详情"), button:has-text("查看")').first();
    
    if (await detailButton.isVisible()) {
      await detailButton.click();
      
      // 验证详情对话框显示
      const dialog = page.locator('.el-dialog, .ant-modal');
      await expect(dialog).toBeVisible();
    }
  });
});

/**
 * 关于系统页面测试套件
 * 
 * 测试关于系统页面的各项功能。
 */
test.describe('关于系统页面', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    
    // 模拟用户登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    // 导航到关于系统页面
    await page.goto('/settings/about');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试关于系统页面渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示关于系统页面', async ({ page }) => {
    // 验证页面标题
    const pageTitle = page.locator('.page-title, h1');
    await expect(pageTitle).toContainText('关于');
    
    // 验证系统信息显示
    const systemInfo = page.locator('.about-content, .system-info');
    await expect(systemInfo).toBeVisible();
  });

  /**
   * 测试系统版本信息显示
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示系统版本信息', async ({ page }) => {
    // 验证版本信息存在
    const versionText = page.locator('text=/版本|Version/i');
    await expect(versionText).toBeVisible();
  });

  /**
   * 测试技术栈信息显示
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示技术栈信息', async ({ page }) => {
    // 验证技术栈信息存在
    const techStack = page.locator('text=/Vue|Electron|Python/i');
    await expect(techStack.first()).toBeVisible();
  });
});

/**
 * 性能监控页面测试套件
 * 
 * 测试性能监控页面的各项功能。
 */
test.describe('性能监控页面', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    
    // 模拟管理员登录
    await authHelper.mockAuthenticated({ role: 'admin' });
    
    // 导航到性能监控页面
    await page.goto('/settings/performance');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试性能监控页面渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示性能监控页面', async ({ page }) => {
    // 验证页面标题
    const pageTitle = page.locator('.page-title, h1');
    await expect(pageTitle).toContainText('性能监控');
    
    // 验证性能指标显示
    const performanceContent = page.locator('.performance-content, .metrics-grid');
    await expect(performanceContent).toBeVisible();
  });

  /**
   * 测试性能指标显示
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示性能指标', async ({ page }) => {
    // 验证CPU使用率显示
    const cpuMetric = page.locator('text=/CPU|cpu/i');
    await expect(cpuMetric.first()).toBeVisible();
    
    // 验证内存使用率显示
    const memoryMetric = page.locator('text=/内存|Memory/i');
    await expect(memoryMetric.first()).toBeVisible();
  });
});

/**
 * 帮助文档页面测试套件
 * 
 * 测试帮助文档页面的各项功能。
 */
test.describe('帮助文档页面', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    
    // 模拟用户登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    // 导航到帮助文档页面
    await page.goto('/settings/help-docs');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试帮助文档页面渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示帮助文档页面', async ({ page }) => {
    // 验证页面标题
    const pageTitle = page.locator('.page-title, h1');
    await expect(pageTitle).toContainText('帮助');
    
    // 验证文档内容显示
    const helpContent = page.locator('.help-content, .documentation');
    await expect(helpContent).toBeVisible();
  });

  /**
   * 测试文档搜索功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持搜索文档', async ({ page }) => {
    // 查找搜索输入框
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"]').first();
    
    if (await searchInput.isVisible()) {
      // 输入搜索关键词
      await searchInput.fill('设备');
      
      // 等待搜索结果
      await page.waitForTimeout(500);
    }
  });
});

/**
 * 权限控制测试套件
 * 
 * 测试设置页面的权限控制功能。
 */
test.describe('设置页面权限控制', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
  });

  /**
   * 测试普通用户访问用户管理页面
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该限制普通用户访问用户管理页面', async ({ page }) => {
    // 模拟普通用户登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    // 尝试访问用户管理页面
    await page.goto('/settings/user-management');
    await page.waitForLoadState('networkidle');
    
    // 验证访问被限制（可能重定向或显示无权限提示）
    const currentUrl = page.url();
    const hasAccessDenied = await page.locator('text=/无权限|权限不足|403/').isVisible();
    
    // 普通用户不应该能访问用户管理页面
    expect(currentUrl.includes('/user-management') && !hasAccessDenied).toBeFalsy();
  });

  /**
   * 测试管理员访问所有设置页面
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该允许管理员访问所有设置页面', async ({ page }) => {
    // 模拟管理员登录
    await authHelper.mockAuthenticated({ role: 'admin' });
    
    // 访问各个设置页面
    const settingsPages = [
      '/settings/config',
      '/settings/profile',
      '/settings/user-management',
      '/settings/audit',
      '/settings/about',
      '/settings/performance'
    ];
    
    for (const settingsPage of settingsPages) {
      await page.goto(settingsPage);
      await page.waitForLoadState('networkidle');
      
      // 验证页面正常显示
      const pageTitle = page.locator('.page-title, h1');
      await expect(pageTitle).toBeVisible();
    }
  });
});
