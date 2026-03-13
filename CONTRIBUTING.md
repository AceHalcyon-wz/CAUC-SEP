# 贡献指南

感谢您对 CAUC-SEP（自旋电子器件实验平台）项目的关注！本文档将帮助您了解如何参与项目开发。

---

## 目录

- [开发环境搭建](#开发环境搭建)
- [代码风格规范](#代码风格规范)
- [Git 工作流程](#git-工作流程)
- [测试指南](#测试指南)
- [项目结构概览](#项目结构概览)
- [问题反馈](#问题反馈)
- [许可证](#许可证)

---

## 开发环境搭建

### 前置要求

| 工具 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.10+ | 推荐使用 3.11 |
| Node.js | 18+ | 推荐使用 LTS 版本 |
| Git | 最新版 | 版本控制工具 |
| USB-RS485 转换器 | - | 硬件通信（可选，仅硬件测试需要） |

### 后端环境配置

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（推荐）
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 安装开发依赖（测试、代码检查工具）
pip install -r requirements-test.txt
pip install black isort mypy ruff

# 6. 验证安装
python -c "import fastapi; import pymodbus; print('后端依赖安装成功')"
```

### 前端环境配置

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 验证安装
npm run dev
# 访问 http://localhost:5173 确认前端正常运行
```

### IDE 推荐配置

#### VS Code 推荐扩展

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.isort",
    "vue.volar",
    "vue.vscode-typescript-vue-plugin",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode"
  ]
}
```

#### VS Code settings.json 配置

```json
{
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "[vue]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

---

## 代码风格规范

### Python 代码规范

#### 格式化工具

| 工具 | 配置 | 命令 |
|------|------|------|
| Black | line-length: 100 | `black .` |
| isort | profile: black | `isort .` |
| mypy | strict mode | `mypy --strict` |
| ruff | line-length: 100 | `ruff check .` |

#### 命名规范

```python
# 变量/函数: snake_case
user_profile = {}
def fetch_user_data(): ...

# 类: PascalCase
class UserRepository: ...

# 常量: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# 私有成员: 前缀单下划线
_internal_cache = {}
```

#### 注释规范

```python
"""
文件名: user_service.py
路径: backend/services/
功能: 用户业务逻辑层，处理用户CRUD及权限校验
作者: Your Name
创建日期: 2024-03-06
依赖: sqlalchemy, pydantic
"""

from typing import Optional


class UserService:
    """用户服务核心类。

    提供用户数据的增删改查，集成缓存层与事件发布。
    所有方法均为线程安全设计。
    """

    def get_user_by_id(
        self,
        user_id: str,
        *,
        include_deleted: bool = False
    ) -> Optional[dict]:
        """根据ID获取用户信息。

        Args:
            user_id: 用户唯一标识（UUID格式）
            include_deleted: 是否包含已软删除的用户，默认False

        Returns:
            用户信息字典，未找到时返回None

        Raises:
            ValueError: user_id格式非法
            DatabaseError: 数据库连接异常

        Example:
            >>> service = UserService()
            >>> user = service.get_user_by_id("550e8400-e29b-41d4-a716-446655440000")
            >>> print(user["email"] if user else "Not found")
        """
        # 参数校验：确保UUID格式正确
        if not self._is_valid_uuid(user_id):
            raise ValueError(f"Invalid UUID format: {user_id}")

        # 优先从缓存获取（减少DB压力）
        cached = self._cache.get(f"user:{user_id}")
        if cached and not include_deleted:
            return cached

        # 回源查询并回填缓存
        user = self._query_from_db(user_id, include_deleted)
        if user:
            self._cache.set(f"user:{user_id}", user, ttl=300)

        return user
```

#### 标记规范

```python
# TODO: 2024-03-10 添加Redis缓存层 [P1-高]
# FIXME: 当前实现存在N+1查询问题 [P0-紧急]
# HACK: 临时绕过第三方API限制，等待官方修复 [P3-低]
# NOTE: 此处故意使用同步调用，避免异步上下文切换
```

### Vue/JavaScript 代码规范

#### 组件结构规范

```vue
<!-- UserProfile.vue -->
<script setup>
/**
 * @file UserProfile.vue
 * @path frontend/src/components/user/
 * @description 用户资料展示组件，支持编辑模式切换
 * @author Your Name
 * @date 2024-03-06
 */

// 1. 导入顺序：Vue核心 → 第三方 → 本地工具 → 组件
import { ref, computed, watch, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { formatDate } from '@/utils/date';

// 2. Props/Emits 定义
const props = defineProps({
  userId: {
    type: String,
    required: true
  },
  editable: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update', 'error']);

// 3. 组合式函数调用
const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

// 4. 响应式状态（按功能分组）
const userData = ref(null);
const isLoading = ref(false);
const isEditMode = ref(false);

// 5. 计算属性
/** 格式化后的创建时间 */
const formattedJoinDate = computed(() => {
  if (!userData.value?.createdAt) return '-';
  return formatDate(userData.value.createdAt, 'YYYY-MM-DD');
});

// 6. 方法
/**
 * 加载用户数据
 * @param {boolean} forceRefresh - 是否强制刷新缓存
 */
async function loadUserData(forceRefresh = false) {
  if (isLoading.value) return;

  isLoading.value = true;
  try {
    const data = await userStore.fetchUser(props.userId, {
      cache: !forceRefresh
    });
    userData.value = data;
  } catch (err) {
    emit('error', err.message);
    console.error('[UserProfile] Failed to load user:', err);
  } finally {
    isLoading.value = false;
  }
}

// 7. 生命周期
onMounted(() => {
  loadUserData();
});
</script>

<template>
  <div class="user-profile" v-loading="isLoading">
    <header class="profile-header">
      <h2>{{ userData?.name || '未知用户' }}</h2>
    </header>
    <!-- 更多模板内容 -->
  </div>
</template>

<style scoped>
.user-profile {
  padding: 16px;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
```

#### 命名规范

```javascript
// 变量/函数: camelCase
const userProfile = {};
function fetchUserData() {}

// 组件文件: PascalCase.vue
// UserProfile.vue, MotorControl.vue

// 组合式函数: use前缀
function useDevice() {}
function useWebSocket() {}

// 常量: UPPER_SNAKE_CASE
const API_BASE_URL = 'http://localhost:8000';
```

---

## Git 工作流程

### 分支命名规范

| 分支类型 | 命名格式 | 示例 |
|----------|----------|------|
| 功能开发 | `feature/*` | `feature/add-piezo-control` |
| 问题修复 | `fix/*` | `fix/motor-connection-timeout` |
| 文档更新 | `docs/*` | `docs/update-api-reference` |
| 代码重构 | `refactor/*` | `refactor/simplify-state-management` |

### 提交信息格式

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

#### 提交类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(motor): 添加PR路径编程功能` |
| `fix` | 问题修复 | `fix(dm2c): 修复位置读取溢出问题` |
| `docs` | 文档更新 | `docs: 更新API文档` |
| `refactor` | 代码重构 | `refactor(analysis): 优化拟合算法性能` |
| `test` | 测试相关 | `test(motor): 添加限位检查单元测试` |
| `chore` | 构建/工具 | `chore: 更新依赖版本` |

### Pull Request 流程

```bash
# 1. 从 main 分支创建功能分支
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 2. 进行代码修改并提交
git add .
git commit -m "feat(scope): 添加新功能描述"

# 3. 推送到远程仓库
git push origin feature/your-feature-name

# 4. 在 GitHub 上创建 Pull Request
# - 填写 PR 标题和描述
# - 关联相关 Issue（如有）
# - 等待代码审查

# 5. 根据审查意见修改代码
git add .
git commit -m "fix: 根据审查意见修改"
git push origin feature/your-feature-name

# 6. 合并后删除功能分支
git checkout main
git pull origin main
git branch -d feature/your-feature-name
```

### Pull Request 检查清单

- [ ] 代码通过所有测试
- [ ] 新代码有对应的测试用例
- [ ] 代码符合项目风格规范
- [ ] 文档已更新（如需要）
- [ ] 提交信息格式正确

---

## 测试指南

### 运行测试

```bash
# 进入后端目录
cd backend

# 运行所有测试
pytest

# 运行指定测试文件
pytest tests/test_dm2c_driver.py

# 运行指定测试函数
pytest tests/test_dm2c_driver.py::TestLeadshineDM2C::test_connect

# 显示详细输出
pytest -v

# 显示测试覆盖率
pytest --cov=. --cov-report=html

# 排除慢速测试
pytest -m "not slow"

# 仅运行集成测试
pytest -m integration
```

### 测试文件命名规范

| 测试类型 | 文件位置 | 命名格式 |
|----------|----------|----------|
| 单元测试 | `backend/tests/` | `test_*.py` |
| 集成测试 | `backend/tests/integration/` | `test_*.py` |
| 测试类 | - | `Test*` |
| 测试函数 | - | `test_*` |

### 测试覆盖率要求

- 新代码覆盖率目标: **>80%**
- 核心模块覆盖率目标: **>90%**
- 使用 `pytest --cov=. --cov-report=term-missing` 查看未覆盖代码

### 编写测试示例

```python
"""
DM2C驱动器单元测试

测试内容：
- 连接/断开连接
- 位置读取
- 运动控制
- 限位检查
"""

import pytest
from unittest.mock import MagicMock, patch

from core.abstract import DeviceStatus
from core.dm2c_driver import LeadshineDM2C


class TestLeadshineDM2C:
    """DM2C驱动器测试类。"""

    @pytest.fixture
    def dm2c_driver(self):
        """创建DM2C驱动器实例。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(
                device_id="test_motor",
                config={
                    "port": "COM_TEST",
                    "slave_id": 1,
                    "baudrate": 115200,
                    "steps_per_mm": 1600
                }
            )
            yield driver

    def test_initial_status_is_disconnected(self, dm2c_driver):
        """测试初始状态为断开连接。"""
        assert dm2c_driver.status == DeviceStatus.DISCONNECTED

    def test_set_limits_valid(self, dm2c_driver):
        """测试设置有效限位。"""
        dm2c_driver.set_limits(positive=100.0, negative=-100.0)
        assert dm2c_driver.limit_config.positive_limit == 100.0
        assert dm2c_driver.limit_config.negative_limit == -100.0

    def test_check_position_limit_within_range(self, dm2c_driver):
        """测试位置在限位范围内。"""
        dm2c_driver.set_limits(positive=100.0, negative=-100.0)
        assert dm2c_driver.check_position_limit(50.0) is True
        assert dm2c_driver.check_position_limit(-50.0) is True

    def test_check_position_limit_out_of_range(self, dm2c_driver):
        """测试位置超出限位范围。"""
        dm2c_driver.set_limits(positive=100.0, negative=-100.0)
        assert dm2c_driver.check_position_limit(150.0) is False
        assert dm2c_driver.check_position_limit(-150.0) is False
```

---

## 项目结构概览

### 目录结构

```
cauc-sep/
├── .github/                    # GitHub 配置
│   └── workflows/              # CI/CD 工作流
├── backend/                    # Python 后端
│   ├── api/                    # API 路由模块
│   │   ├── motor.py            # 电机控制 API
│   │   ├── device.py           # 设备状态 API
│   │   ├── experiment.py       # 实验管理 API
│   │   ├── analysis.py         # 数据分析 API
│   │   ├── health.py           # 健康检查 API
│   │   ├── performance.py      # 性能监控 API
│   │   ├── tracing.py          # 链路追踪 API
│   │   ├── crash_report.py     # 崩溃报告 API
│   │   ├── update.py           # 更新管理 API
│   │   ├── user.py             # 用户管理 API
│   │   └── schemas.py          # Pydantic 数据模型
│   ├── core/                   # 核心业务逻辑
│   │   ├── abstract.py         # 硬件抽象层基类
│   │   ├── dm2c_driver.py      # DM2C 步进电机驱动
│   │   ├── picoammeter.py      # 皮安计驱动
│   │   ├── piezo_controller.py # 压电控制器驱动
│   │   ├── temperature_controller.py  # 温度控制器驱动
│   │   ├── electromagnet_driver.py    # 电磁铁驱动
│   │   ├── data_storage.py     # 数据存储
│   │   ├── analysis.py         # 物理分析器
│   │   ├── cache.py            # 缓存模块
│   │   ├── tracing.py          # 链路追踪
│   │   ├── metrics.py          # 指标收集
│   │   ├── profiler.py         # 性能分析器
│   │   └── error_recovery.py   # 错误恢复
│   ├── drivers/                # 进程级驱动
│   │   ├── base.py             # 驱动基类
│   │   ├── dm2c_process.py     # DM2C 进程驱动
│   │   ├── electromagnet_process.py # 电磁铁进程驱动
│   │   └── temperature_process.py  # 温控进程驱动
│   ├── middleware/             # 中间件
│   │   ├── audit.py            # 审计日志
│   │   ├── security.py         # 安全中间件
│   │   ├── rate_limit.py       # 速率限制
│   │   ├── cors_config.py      # CORS 配置
│   │   ├── jwt_auth.py         # JWT 认证
│   │   └── validation.py       # 请求验证
│   ├── migrations/             # 数据库迁移
│   │   └── sql/                # SQL 迁移脚本
│   ├── models/                 # 数据库模型
│   ├── monitoring/             # 监控配置
│   │   ├── grafana/            # Grafana 仪表盘
│   │   └── prometheus/         # Prometheus 配置
│   ├── tests/                  # 测试文件
│   │   ├── integration/        # 集成测试
│   │   └── unit/               # 单元测试
│   ├── docs/                   # 后端文档
│   ├── main.py                 # FastAPI 主程序
│   ├── pyproject.toml          # 项目配置
│   ├── pytest.ini              # 测试配置
│   ├── mypy.ini                # 类型检查配置
│   └── requirements.txt        # Python 依赖
├── frontend/                   # Vue3 前端
│   ├── src/
│   │   ├── api/                # API 客户端
│   │   ├── components/         # UI 组件
│   │   │   └── layout/         # 布局组件
│   │   ├── composables/        # 组合式函数
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── views/              # 页面视图
│   │   │   ├── analysis/       # 分析页面
│   │   │   ├── device/         # 设备页面
│   │   │   ├── experiment/     # 实验页面
│   │   │   └── settings/       # 设置页面
│   │   ├── router/             # 路由配置
│   │   ├── config/             # 配置文件
│   │   ├── utils/              # 工具函数
│   │   ├── styles/             # 样式文件
│   │   └── directives/         # Vue 指令
│   ├── e2e/                    # E2E 测试
│   ├── docs/                   # 前端文档
│   ├── package.json            # Node 依赖
│   ├── vite.config.js          # Vite 配置
│   └── vitest.config.js        # Vitest 配置
├── docs/                       # 项目文档
│   ├── api/                    # API 文档
│   └── components/             # 组件文档
├── scripts/                    # 脚本
│   ├── build.bat               # 打包脚本
│   ├── start_dev.bat           # 开发启动脚本
│   ├── docker-build.bat        # Docker 构建
│   └── run-tests.sh            # 测试运行脚本
├── docker-compose.yml          # Docker 编排配置
├── .pre-commit-config.yaml     # Pre-commit 钩子配置
└── README.md                   # 项目说明
```

### 缓存文件清理说明

项目已配置自动清理以下类型的文件，保持代码仓库整洁：

| 文件类型 | 说明 | 清理方式 |
|----------|------|----------|
| `__pycache__/` | Python 字节码缓存目录 | 手动/自动清理 |
| `*.pyc` | Python 编译文件 | 手动/自动清理 |
| `*.bak` | 备份文件 | 手动清理 |
| `*.backup` | 备份文件 | 手动清理 |
| `*.orig` | 合并冲突备份 | 手动清理 |
| `*.log` | 日志文件 | 按需清理 |

建议在提交代码前运行以下命令清理缓存：

```bash
# Windows PowerShell
Get-ChildItem -Path . -Include __pycache__,*.pyc -Recurse -Force | Remove-Item -Force -Recurse

# Linux/macOS
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

项目已配置 `.gitignore` 文件，自动忽略上述缓存文件。

### 添加新功能的位置

| 功能类型 | 添加位置 | 说明 |
|----------|----------|------|
| 新 API 端点 | `backend/api/` | 创建新模块或修改现有模块 |
| 新设备驱动 | `backend/core/` | 继承 `AbstractDevice` 或 `AbstractStepper` |
| 新 UI 组件 | `frontend/src/components/` | 使用 Composition API |
| 新状态管理 | `frontend/src/stores/` | 使用 Pinia |
| 新工具函数 | `frontend/src/utils/` | 可复用的纯函数 |

### 如何添加新设备驱动

1. **创建驱动文件**

在 `backend/core/` 目录下创建新驱动文件，例如 `new_device_driver.py`。

2. **继承抽象基类**

```python
"""
新设备驱动

功能：
- 设备连接管理
- 数据读写
- 状态监控
"""

from typing import Any
from core.abstract import AbstractDevice, DeviceStatus


class NewDeviceDriver(AbstractDevice):
    """新设备驱动类。

    继承自 AbstractDevice，实现所有抽象方法。
    """

    def __init__(self, device_id: str, config: dict[str, Any]):
        """初始化设备驱动。

        Args:
            device_id: 设备唯一标识符
            config: 设备配置字典，包含通信参数等
        """
        super().__init__(device_id, config)
        # 初始化设备特定属性

    async def connect(self) -> bool:
        """建立与设备的连接。

        Returns:
            bool: 连接是否成功
        """
        self.status = DeviceStatus.CONNECTING
        try:
            # 实现连接逻辑
            self.status = DeviceStatus.READY
            return True
        except Exception as e:
            self.set_error(f"连接失败: {str(e)}")
            return False

    async def disconnect(self) -> bool:
        """断开与设备的连接。

        Returns:
            bool: 断开是否成功
        """
        try:
            # 实现断开连接逻辑
            self.status = DeviceStatus.DISCONNECTED
            return True
        except Exception as e:
            self.set_error(f"断开连接失败: {str(e)}")
            return False

    async def read_status(self) -> dict[str, Any]:
        """读取设备完整状态信息。

        Returns:
            dict: 包含设备状态信息的字典
        """
        return {
            "status": self.status.value,
            "connected": self.is_connected,
            # 添加设备特定状态
        }
```

3. **创建 API 路由**

在 `backend/api/` 目录下创建对应的 API 模块。

4. **编写测试**

在 `backend/tests/` 目录下创建 `test_new_device_driver.py`。

5. **注册设备**

在 `backend/core/device_registry.py` 中注册新设备。

---

## 问题反馈

### 使用 GitHub Issues

在提交 Issue 前，请先搜索是否已有类似问题。

#### Issue 模板

```markdown
## 问题描述
简要描述遇到的问题。

## 复现步骤
1. 执行操作 A
2. 执行操作 B
3. 观察到问题

## 期望行为
描述您期望发生的行为。

## 实际行为
描述实际发生的行为。

## 环境信息
- 操作系统: Windows 11
- Python 版本: 3.11.x
- Node.js 版本: 18.x
- 项目版本: v0.2.0
- 硬件: DM2C步进驱动器 / USB-RS485转换器

## 日志/截图
```
粘贴相关日志或截图
```

## 其他信息
其他可能有助于解决问题的信息。
```

### 问题分类标签

| 标签 | 说明 |
|------|------|
| `bug` | 程序错误 |
| `enhancement` | 功能增强请求 |
| `documentation` | 文档问题 |
| `hardware` | 硬件相关问题 |
| `good first issue` | 适合新贡献者 |

---

## 许可证

本项目采用 **Apache License 2.0** 许可证。

### 贡献者协议

通过向本项目提交代码，您同意：

1. 您贡献的代码将按照 Apache License 2.0 许可证授权
2. 您拥有贡献代码的版权或有权进行授权
3. 您的贡献不侵犯任何第三方的知识产权

### 许可证要点

- 允许商业使用
- 允许修改和分发
- 需要保留版权声明
- 需要说明代码的修改部分
- 不提供任何担保

完整许可证文本请参阅项目根目录的 [LICENSE](LICENSE) 文件。

---

## 联系方式

如有问题，请通过以下方式联系：

- **GitHub Issues**: 提交问题或功能请求
- **项目文档**: 查看 `docs/` 目录下的技术文档

---

感谢您的贡献！
