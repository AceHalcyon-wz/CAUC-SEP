# 更新日志

本项目的所有重要更改都将记录在此文件中。

本文件格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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
