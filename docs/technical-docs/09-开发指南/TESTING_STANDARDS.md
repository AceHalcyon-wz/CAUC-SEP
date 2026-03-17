# CAUC-SEP 测试规范文档

> 版本: 1.0.0  
> 更新日期: 2026-03-16  
> 作者: CAUC-SEP Team

## 目录

1. [概述](#概述)
2. [测试文件命名规范](#测试文件命名规范)
3. [测试函数命名规范](#测试函数命名规范)
4. [测试数据命名规范](#测试数据命名规范)
5. [测试组织结构](#测试组织结构)
6. [测试代码风格](#测试代码风格)
7. [断言规范](#断言规范)
8. [Mock和Fixture规范](#mock和fixture规范)
9. [测试覆盖率要求](#测试覆盖率要求)
10. [最佳实践](#最佳实践)

---

## 概述

本文档定义了 CAUC-SEP 项目的测试规范，旨在：

- 提高测试代码的可读性和可维护性
- 确保测试命名的一致性
- 规范测试数据的组织方式
- 提升测试质量和覆盖率

---

## 测试文件命名规范

### 后端 (Python/pytest)

| 测试类型 | 文件命名 | 示例 |
|---------|---------|------|
| 单元测试 | `test_{模块名}.py` | `test_motor.py`, `test_piezo_controller.py` |
| 集成测试 | `test_{功能名}_{场景}.py` | `test_motor_workflow.py` |
| API测试 | `test_api_{模块名}.py` | `test_api_motor.py`, `test_api_device.py` |
| 性能测试 | `test_performance_{描述}.py` | `test_performance_query.py` |

**目录结构：**

```
backend/tests/
├── conftest.py              # 共享fixtures
├── factories.py             # 测试数据工厂
├── helpers/                 # 测试辅助工具
│   ├── __init__.py
│   ├── assertions.py        # 语义化断言
│   ├── mock_factories.py    # Mock工厂
│   └── test_data.py         # 测试数据生成
├── unit/                    # 单元测试
│   ├── test_api/
│   ├── test_core/
│   └── test_schemas/
├── integration/             # 集成测试
│   └── test_*.py
└── test_*.py               # 根级测试文件
```

### 前端 (Vue/Vitest)

| 测试类型 | 文件命名 | 示例 |
|---------|---------|------|
| 单元测试 | `{组件名}.test.js` | `MotorControl.test.js` |
| 单元测试 (TypeScript) | `{组件名}.test.ts` | `useWebSocket.test.ts` |
| 集成测试 | `{功能名}.spec.js` | `auth-flow.spec.js` |
| E2E测试 | `{功能名}.spec.js` | `device-flow.spec.js` |

**目录结构：**

```
frontend/tests/
├── unit/                    # 单元测试
│   ├── components/          # 组件测试
│   ├── composables/         # 组合式函数测试
│   ├── utils/               # 工具函数测试
│   ├── helpers/             # 测试辅助工具
│   │   ├── test-utils.js
│   │   ├── assertions.js
│   │   └── data-factories.js
│   └── setup.js             # 测试环境设置
└── e2e/                     # E2E测试
    ├── helpers/             # 测试辅助函数
    └── *.spec.js
```

---

## 测试函数命名规范

### 命名模式

采用 `test_{功能描述}_{场景描述}` 的命名模式：

```python
# Python 示例
def test_connect_motor_success():
    """测试成功连接电机。"""
    pass

def test_connect_motor_failure():
    """测试连接电机失败。"""
    pass

def test_move_motor_position_out_of_range():
    """测试电机定位超出范围。"""
    pass
```

```javascript
// JavaScript 示例
describe('MotorControl', () => {
  describe('连接功能', () => {
    it('应该成功连接电机', () => {
      // ...
    });

    it('连接失败时应该显示错误消息', () => {
      // ...
    });
  });

  describe('位置控制', () => {
    it('位置超出范围时应该拒绝移动', () => {
      // ...
    });
  });
});
```

### 测试类命名 (Python)

使用 `Test{功能名称}` 模式：

```python
class TestMotorConnectionEndpoints:
    """测试电机连接端点。"""
    pass

class TestMotorMoveEndpoints:
    """测试电机运动端点。"""
    pass

class TestPiezoCalibration:
    """测试压电陶瓷校准功能。"""
    pass
```

### 测试描述规范

| 场景 | 描述模式 | 示例 |
|-----|---------|------|
| 成功场景 | `test_{功能}_success` | `test_connect_motor_success` |
| 失败场景 | `test_{功能}_failure` | `test_connect_motor_failure` |
| 边界条件 | `test_{功能}_{边界描述}` | `test_set_voltage_maximum` |
| 异常处理 | `test_{功能}_{异常描述}` | `test_move_motor_disconnected` |
| 验证测试 | `test_{功能}_validation` | `test_move_request_validation` |

---

## 测试数据命名规范

### Fixture命名

| 类型 | 命名模式 | 示例 |
|-----|---------|------|
| 数据库fixture | `fixture_{描述}` | `fixture_temp_db`, `fixture_test_session` |
| Mock对象 | `mock_{描述}` | `mock_motor`, `mock_piezo_controller` |
| 测试数据 | `{描述}_data` | `sample_hysteresis_data`, `sample_signal_data` |
| 配置对象 | `test_{描述}_config` | `test_motor_config` |

### Python Fixture示例

```python
@pytest.fixture
def mock_motor():
    """创建Mock电机控制器实例。"""
    controller = MagicMock()
    controller.device_id = "test_motor"
    controller.status = DeviceStatus.READY
    return controller

@pytest.fixture
def sample_hysteresis_data():
    """生成模拟磁滞回线数据。"""
    h_field = np.linspace(-1000, 1000, 200)
    moment = np.tanh(h_field / 200)
    return h_field, moment

@pytest.fixture
def temp_storage():
    """创建临时数据存储。"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    storage = DataStorage(db_path)
    yield storage
    storage.engine.dispose()
    os.remove(db_path)
```

### JavaScript Mock示例

```javascript
// Mock Store
export function createMockMotorStore(overrides = {}) {
  const defaultState = {
    position: 0,
    targetPosition: 0,
    isConnected: false,
    ...overrides,
  };

  return createMockStore(defaultState, {
    moveTo: vi.fn(),
    stop: vi.fn(),
    emergencyStop: vi.fn(),
  });
}

// Mock 数据
export function createMotorStatus(overrides = {}) {
  const defaults = {
    device_id: 'test_motor',
    status: 'ready',
    position_mm: 0.0,
    connected: true,
  };

  return { ...defaults, ...overrides };
}
```

---

## 测试组织结构

### AAA模式 (Arrange-Act-Assert)

```python
def test_motor_move_success(client_with_motor, mock_motor):
    """测试成功执行绝对定位。"""
    # Arrange - 准备测试数据
    mock_motor.status = DeviceStatus.READY
    mock_motor.move_abs = AsyncMock(return_value=True)
    request_data = {"position_mm": 10.0, "velocity_mm_s": 5.0}

    # Act - 执行测试操作
    response = client_with_motor.post("/api/v1/motor/move", json=request_data)

    # Assert - 验证结果
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["target_position_mm"] == 10.0
```

### Given-When-Then模式 (BDD风格)

```javascript
describe('MotorControl', () => {
  it('应该在连接成功后启用控制按钮', async () => {
    // Given - 给定初始状态
    const wrapper = mount(MotorControl, {
      global: { plugins: [pinia] },
    });
    mockMotorStore.isConnected = false;

    // When - 当执行操作
    mockMotorStore.isConnected = true;
    await wrapper.vm.$nextTick();

    // Then - 那么验证结果
    const moveButton = wrapper.find('.move-btn');
    expect(moveButton.attributes('disabled')).toBeUndefined();
  });
});
```

---

## 测试代码风格

### 文档字符串规范

```python
def test_set_voltage_success(client_with_piezo, mock_piezo):
    """测试成功设置电压。

    Args:
        client_with_piezo: 带Mock压电陶瓷的测试客户端
        mock_piezo: Mock压电陶瓷控制器

    验证:
        - 响应状态码为200
        - 返回success=True
        - 当前电压值正确更新
    """
    pass
```

### 注释规范

```python
def test_complex_workflow():
    """测试复杂工作流。"""
    # 步骤1: 初始化设备
    device = create_test_device()

    # 步骤2: 执行校准
    calibration_result = device.calibrate()

    # 步骤3: 验证结果
    assert calibration_result.success is True
```

---

## 断言规范

### 使用语义化断言

**推荐：**

```python
from tests.helpers import assert_response_success, assert_device_status

def test_motor_status(client_with_motor, mock_motor):
    """测试获取电机状态。"""
    response = client_with_motor.get("/api/v1/motor/status")

    assert_response_success(response)
    assert_device_status(response, "ready")
```

**不推荐：**

```python
def test_motor_status(client_with_motor, mock_motor):
    """测试获取电机状态。"""
    response = client_with_motor.get("/api/v1/motor/status")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
```

### 断言消息

为复杂断言添加描述性消息：

```python
assert response.status_code == 200, (
    f"期望状态码200，实际为{response.status_code}。"
    f"响应内容: {response.json()}"
)
```

---

## Mock和Fixture规范

### Mock原则

1. **只Mock外部依赖**：数据库、网络、硬件设备
2. **不Mock被测对象**：测试真实行为
3. **Mock行为而非实现**：关注接口契约

### Fixture作用域

| 作用域 | 使用场景 | 示例 |
|-------|---------|------|
| `function` | 每个测试独立数据 | 测试数据库会话 |
| `class` | 类中所有测试共享 | Mock设备实例 |
| `module` | 模块内共享 | 测试配置 |
| `session` | 全局共享 | 数据库引擎 |

```python
@pytest.fixture(scope="function")
def test_db_session():
    """每个测试使用独立的事务。"""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="session")
def event_loop():
    """会话级别事件循环。"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

---

## 测试覆盖率要求

### 覆盖率目标

| 模块类型 | 最低覆盖率 | 推荐覆盖率 |
|---------|-----------|-----------|
| 核心业务逻辑 | 90% | 95% |
| API端点 | 85% | 90% |
| 工具函数 | 80% | 85% |
| UI组件 | 70% | 80% |

### 覆盖率报告

```bash
# Python
pytest --cov=backend --cov-report=html --cov-report=term

# JavaScript
vitest run --coverage
```

---

## 最佳实践

### 1. 测试独立性

每个测试应该独立运行，不依赖其他测试的结果：

```python
# 推荐
def test_create_user(temp_db):
    """测试创建用户。"""
    user = create_user(temp_db, username="test")
    assert user.id is not None

def test_delete_user(temp_db):
    """测试删除用户。"""
    user = create_user(temp_db, username="test")  # 独立创建
    delete_user(temp_db, user.id)
    assert get_user(temp_db, user.id) is None

# 不推荐
created_user_id = None

def test_create_user(temp_db):
    """测试创建用户。"""
    global created_user_id
    user = create_user(temp_db, username="test")
    created_user_id = user.id  # 依赖全局状态

def test_delete_user(temp_db):
    """测试删除用户。"""
    delete_user(temp_db, created_user_id)  # 依赖其他测试
```

### 2. 测试数据工厂

使用工厂函数生成测试数据：

```python
# 推荐
from tests.factories import UserDictFactory, DeviceStatusDictFactory

def test_user_creation():
    user_data = UserDictFactory.create(username="test_user")
    assert user_data["username"] == "test_user"

def test_motor_status():
    status = DeviceStatusDictFactory.create_motor_status(position_mm=10.0)
    assert status["position_mm"] == 10.0

# 不推荐
def test_user_creation():
    user_data = {
        "username": "test_user",
        "password_hash": "hash123",
        "role": "operator",
        # ... 大量硬编码字段
    }
```

### 3. 参数化测试

使用参数化减少重复代码：

```python
@pytest.mark.parametrize("position,expected_valid", [
    (0.0, True),
    (50.0, True),
    (100.0, True),
    (-50.0, True),
    (150.0, False),  # 超出范围
    (-150.0, False),  # 超出范围
])
def test_position_validation(position, expected_valid):
    """测试位置验证。"""
    result = validate_position(position, min_pos=-100, max_pos=100)
    assert result.valid == expected_valid
```

### 4. 测试异常

正确测试异常情况：

```python
# 推荐
def test_connect_failure():
    """测试连接失败抛出异常。"""
    with pytest.raises(ConnectionError, match="连接超时"):
        device.connect(timeout=1)

# 不推荐
def test_connect_failure():
    """测试连接失败。"""
    try:
        device.connect(timeout=1)
        assert False, "应该抛出异常"
    except ConnectionError:
        pass
```

### 5. 清理测试资源

确保测试后清理资源：

```python
@pytest.fixture
def temp_file():
    """创建临时文件。"""
    path = tempfile.mktemp()
    yield path
    if os.path.exists(path):
        os.remove(path)
```

---

## 附录

### 测试命令速查

```bash
# 运行所有测试
pytest

# 运行指定测试文件
pytest tests/test_api_motor.py

# 运行指定测试类
pytest tests/test_api_motor.py::TestMotorConnectionEndpoints

# 运行指定测试函数
pytest tests/test_api_motor.py::TestMotorConnectionEndpoints::test_connect_motor_success

# 运行带标记的测试
pytest -m "not slow"
pytest -m integration

# 显示详细输出
pytest -v

# 显示打印输出
pytest -s

# 生成覆盖率报告
pytest --cov=backend --cov-report=html
```

### 参考资源

- [pytest 官方文档](https://docs.pytest.org/)
- [Vitest 官方文档](https://vitest.dev/)
- [Vue Test Utils 文档](https://test-utils.vuejs.org/)
- [Playwright 文档](https://playwright.dev/)
