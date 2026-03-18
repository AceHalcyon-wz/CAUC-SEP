# 更新日志

本项目的所有重要更改都将记录在此文件中。

本文件格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.3.5] - 2026-03-18

### 新增

- **桌面应用打包**: 完成 Nuitka + Electron + electron-builder 完整打包流程
  - 生成 Windows 安装包: `CAUC-SEP-3.5.0-x64-setup.exe` (207.47 MB)
  - 解压后大小: 819.80 MB
  - 输出路径: `electron/dist/`

### 变更

- **部署文档重构**: 移除 Docker 部署内容，专注桌面应用部署
  - 更新 `docs/technical-docs/10-部署运维/部署配置.md`
  - 保留生产环境配置、安全加固、数据库维护等内容
- **打包脚本修复**: 修正 Nuitka 输出目录配置
  - Nuitka 根据入口文件名输出 `main.dist` 目录
  - 同步更新 `electron-builder.yml`、`package.json`、`main.js` 路径配置
  - 更新 `backend/scripts/build_exe_standalone.py` 输出目录检查

### 技术细节

- **前端构建**: Vue 3 + Vite 构建，输出到 `electron/resources/frontend/`
- **后端编译**: Nuitka standalone 模式，MSVC 14.5 编译器
- **Electron打包**: electron-builder 24.13.3，NSIS 安装程序
- **打包耗时**: Nuitka 编译约 30 分钟，Electron 打包约 2 分钟

## [0.3.4] - 2026-03-18

### 变更

- **测试目录重整**: 清理冗余测试文件，优化测试结构
  - 删除根目录 `tests/` 临时调试目录（Playwright 调试脚本）
  - 删除 `frontend/tests/e2e/example.spec.js` 框架验证示例
  - 删除 `frontend/tests/e2e/electron.example.spec.js` Electron 测试示例
  - 删除 `frontend/tests/e2e/verify-*.js` 环境验证脚本
  - 删除 `frontend/tests/unit/test_boundary_conditions.js` 重复边界测试
  - 删除 `frontend/tests/unit/test_exception_scenarios.js` 重复异常测试
- **文档更新**: 同步更新测试指南和项目目录结构文档

### 移除

- `tests/` 根目录临时调试测试目录
- `frontend/tests/e2e/example.spec.js` 示例测试文件
- `frontend/tests/e2e/electron.example.spec.js` Electron 示例测试
- `frontend/tests/e2e/verify-config.js` 配置验证脚本
- `frontend/tests/e2e/verify-e2e-tests.js` E2E 验证脚本
- `frontend/tests/e2e/verify-setup.js` 环境验证脚本
- `frontend/tests/unit/test_boundary_conditions.js` 边界条件测试
- `frontend/tests/unit/test_exception_scenarios.js` 异常场景测试

## [0.3.3] - 2026-03-18

### 新增

- **API响应处理工具**: 新增 `unwrapResponse` 工具函数
  - 解决前端组件对 API 响应数据结构的错误访问问题
  - apiRequest 返回格式: `{success: boolean, data?: any, message?: string}`
  - 相关文件: `frontend/src/utils/apiRequest.js`, `frontend/src/utils/request.js`

### 变更

- **前端依赖升级**: Vue 3.5 + Element Plus 兼容性修复
  - Element Plus: 2.9.7 → 2.13.5
  - Element Plus 2.13.0 才正式支持 Vue 3.5
  - 修复 `TabNavRenderer` 渲染错误导致的微电流计页面空白问题

### 修复

- **微电流计页面空白**: 解决 Vue 3.5.13 与 Element Plus 2.9.7 兼容性问题
  - 相关文件: `frontend/src/components/experiment/ammeter/AmmeterControl.vue`
  - 相关文件: `frontend/src/components/experiment/ammeter/AmmeterWaveform.vue`
- **硬件监控实时刷新**: 实现系统资源数据实时更新
  - 添加 1 秒间隔自动刷新定时器
  - 修复 CPU、内存、磁盘使用率显示为 0% 的问题
  - 相关文件: `frontend/src/views/settings/Performance.vue`
- **用户管理页面加载**: 解决用户列表无法加载的问题
  - 使用 `unwrapResponse` 正确解包分页数据
  - 相关文件: `frontend/src/views/settings/UserManagement.vue`
- **ECharts 配置**: 修复 yAxis 回调函数空值访问问题
  - 使用可选链操作符 `?.` 安全访问属性
  - 相关文件: `frontend/src/components/experiment/ammeter/AmmeterWaveform.vue`

## [0.3.2] - 2026-03-15

### 变更

- **项目结构优化**: 清理废弃的Docker和CI/CD相关文件
  - 移除Docker部署方案（`.dockerignore`, `docker-compose.yml`, `Dockerfile`等）
  - 移除CI/CD配置（`codecov.yml`, `.pre-commit-config.yaml`, `CONTRIBUTING.md`）
  - 清理过时脚本（Docker脚本、lint-check.sh、run-tests.sh）
  - 移除临时文件（`slib`, `nuitka-crash-report.xml`）
- **文档更新**: 同步更新所有README文件和项目目录结构文档
- **保留构建方案**: 本地Nuitka打包 + Electron桌面应用

### 移除

- Docker相关文件（已放弃Docker部署）
- GitHub Actions CI/CD配置（已放弃自动部署）
- Pre-commit钩子配置
- Codecov覆盖率配置

## [0.3.1] - 2026-03-14

### 新增

- 全面更新项目文档注释体系
  - 所有Python模块添加完整的中文docstring（遵循PEP 257规范）
  - 所有Vue组件和TypeScript文件添加完整的JSDoc注释
  - 配置文件（yml、yaml、toml、bat）添加详细中文注释
- 更新CI/CD配置
  - 添加并发控制，避免重复构建
  - 添加超时限制，防止任务无限挂起
  - 新增isort导入排序检查
  - 优化缓存策略，加速构建
- 更新监控配置文档
  - Grafana仪表盘配置说明
  - Prometheus告警规则详细注释
- 更新开发者指南
  - 新增安全加固章节
  - 新增性能优化章节
  - 新增常见问题章节

### 变更

- 统一所有文档版本号为v0.3.0
- 更新项目描述为"CAUC-SEP 自旋电子器件实验平台 - 多设备集成控制系统"
- 优化文档结构，增强可读性

### 项目结构优化

- 更新 backend/core/ 所有模块文档
- 更新 backend/api/ 所有API模块文档
- 更新 backend/drivers/ 驱动模块文档
- 更新 backend/middleware/ 中间件文档
- 更新 backend/models/ 数据模型文档
- 更新 backend/schemas/ Schema文档
- 更新 backend/monitoring/ 监控配置文档
- 更新 backend/tests/ 测试文档
- 更新 frontend/tests/ 前端测试文档
- 更新 docs/ 项目文档
- 更新 scripts/ 脚本文件注释
- 更新 .github/workflows/ CI/CD配置

## [0.3.0] - 2026-03-08

### 新增

- 多设备支持：电磁铁、温度控制器、压电控制器、皮安计
- 所有设备的 WebSocket 端点（/ws/electromagnet、/ws/temperature、/ws/piezo、/ws/ammeter、/ws/devices）
- 安全中间件：速率限制、安全头、审计日志
- 电磁铁功能：恒流模式、扫描模式（正向/反向/三角波）、校准管理、过流保护
- 温度控制器功能：PID 控制、程序温控、保护限值、历史记录管理
- 压电控制器功能：电压/位移控制、校准（线性/多项式/分段）、开环/闭环模式
- 皮安计功能：多通道采集（4 通道）、信噪比计算、数字滤波、缓冲区管理
- 设备注册表，用于集中设备管理
- 统一 WebSocket 消息格式，包含设备类型和消息类型
- 性能监控 API 和链路追踪功能
- 崩溃报告和自动上传机制
- 用户管理和 JWT 认证模块
- Prometheus + Grafana 监控配置
- 进程级驱动架构（drivers/ 目录）
- 前端离线同步和错误处理组合式函数

### 变更

- **破坏性变更**: API 版本前缀更改为 /api/v1/ 用于电机端点
- 改进错误处理，使用标准化错误代码
- 增强所有端点的输入验证
- 更新 CORS 配置以提高安全性
- 重构前端路由为模块化视图结构
- 优化数据库索引性能

### 修复

- 电机驱动连接稳定性问题
- WebSocket 重连处理
- 长时间运行实验中的内存泄漏

### 项目结构优化

- 清理所有 `__pycache__/` 目录和 `.pyc` 编译文件
- 移除备份文件（`.bak`、`.backup`、`.orig` 后缀）
- 清理临时文件和日志文件
- 更新项目文档结构，反映当前实际目录布局

## [0.2.0] - 2024-02-15

### 新增

- PR 路径编程（16 段）
- 数据分析模块：信号平滑（Savitzky-Golay、Butterworth）、磁滞回线分析
- 实验管理：SQLite 存储、CSV 导出
- 使用 ECharts 实时显示位置
- 软件限位保护
- 急停功能

### 变更

- 提高 Modbus 通信稳定性
- 改进错误消息

## [0.1.0] - 2024-01-20

### 新增

- 初始版本发布
- 通过 Modbus RTU 控制 DM2C 步进电机
- 基本运动控制：绝对定位、JOG 模式、回零
- Vue3 + Element Plus 前端
- FastAPI 后端，支持 WebSocket
- 实时状态监控
