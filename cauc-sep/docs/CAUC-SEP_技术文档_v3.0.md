# CAUC-SEP 自旋电子器件实验平台技术文档 v3.2

**版本**: v3.2  
**更新日期**: 2026-03-08  
**适用对象**: 材料物理专业实验研究  
**开发模式**: AI Agent 辅助开发

---

## 目录

1. [项目概述](#1-项目概述)
2. [快速开始](#2-快速开始)
3. [系统架构](#3-系统架构)
4. [核心模块详解](#4-核心模块详解)
5. [数据库设计](#5-数据库设计)
6. [通信协议设计](#6-通信协议设计)
7. [API参考](#7-api参考)
8. [前端组件指南](#8-前端组件指南)
9. [开发指南](#9-开发指南)
10. [打包与部署](#10-打包与部署)
11. [测试清单](#11-测试清单)
12. [故障排除](#12-故障排除)
13. [数据分析模块增强设计](#13-数据分析模块增强设计)
14. [技术架构改进建议](#14-技术架构改进建议)
15. [附录](#15-附录)

---

## 1. 项目概述

### 1.1 项目背景

本项目旨在开发一套完整的自旋电子器件/材料特性采集与分析实验平台，用于材料物理专业的实验研究。项目参考VCP（Virtual Control Platform）项目的前后分离架构设计理念，采用Python技术栈实现，以替代传统的LabVIEW开发方案。

平台将接入雷赛（Leadshine）DM2C系列驱控一体型步进驱动器作为核心运动控制设备，通过RS-485接口基于Modbus RTU协议进行通信。同时集成电磁铁控制、温控系统、压电陶瓷控制、微电流采集等多个硬件模块，形成完整的实验测量体系。

项目发起人是一名大二材料物理专业学生，导师最初要求使用LabVIEW开发该实验平台。经过技术调研，决定采用Python技术栈实现，并参考VCP项目的架构设计理念。该方案具有开发效率高、代码可维护性强、社区支持丰富等优势。

### 1.2 设计目标

#### 1.2.1 功能目标

- 实现步进电机的PR模式精确定位控制，支持16段位置表编程
- 提供电磁铁励磁电流的恒流/扫描模式控制
- 实现液氮釜温度的PID闭环控制与程序控温
- 支持压电陶瓷纳米级位移精密控制
- 实现pA级微弱电流信号的多通道采集
- 提供可视化实验流程编排与实时数据看板

#### 1.2.2 技术目标

- 采用前后端分离架构，前端Vue3+Element Plus，后端FastAPI
- 支持WebSocket实时数据流与REST API控制指令
- 打包为单一可执行文件（.exe），支持Windows 10/11 64位
- 关键控制回路响应时间<10ms
- 目标文件体积<200MB

### 1.3 核心特性

- **多设备统一管理**: 集成步进电机、电磁铁、温度控制器、压电控制器、皮安装培计
- **实时数据推送**: WebSocket 实时数据流，支持推送频率控制
- **高级运动控制**: 16段PR路径编程、软件限位保护、回零操作
- **数据分析引擎**: Savitzky-Golay滤波、Langevin函数拟合、磁滞回线分析
- **安全机制**: 速率限制、审计日志、安全响应头、过流保护

### 1.4 支持设备

| 设备 | 型号/类型 | 通信协议 | 主要功能 |
|------|----------|----------|----------|
| 步进电机 | 雷赛 DM2C-RS556 | Modbus RTU | 精密位置控制、PR路径编程 |
| 电磁铁 | 可编程电流源 | Serial | 磁场扫描、校准管理 |
| 温度控制器 | PID温控系统 | Serial | 程序控温、保护限值 |
| 压电控制器 | 电压/位移控制 | Serial | 开闭环模式、校准 |
| 皮安装培计 | 微电流测量 | Serial | 多通道采集、SNR分析 |

### 1.5 技术栈

#### 后端技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.109+ | Web框架、REST API |
| PyModbus | 3.5+ | Modbus RTU通信 |
| NumPy | 2.0+ | 数值计算、矩阵运算 |
| SciPy | 1.10+ | 科学计算、信号处理、曲线拟合 |
| lmfit | 1.2+ | 非线性最小二乘拟合、参数优化 |
| SQLAlchemy | 2.0+ | ORM、数据持久化 |
| Pydantic | 2.5+ | 数据验证 |
| h5py | 3.10+ | HDF5大数据存储 |
| python-jose | 3.3+ | JWT认证 |
| passlib | 1.7+ | 密码哈希 |

**数据分析专用库**：

| 组件 | 版本 | 用途 |
|------|------|------|
| NumPy | 2.0+ | 数组运算、数值计算基础 |
| SciPy.signal | 1.10+ | Savitzky-Golay滤波、巴特沃斯滤波 |
| SciPy.optimize | 1.10+ | curve_fit曲线拟合、参数优化 |
| lmfit | 1.2+ | 高级非线性拟合、模型管理 |

#### 前端技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4+ | 前端框架（Composition API） |
| Element Plus | 2.5+ | UI组件库 |
| Pinia | 2.1+ | 状态管理 |
| ECharts | 5.4+ | 数据可视化 |
| Vue Router | 4.2+ | 路由管理 |
| Axios | 1.6+ | HTTP客户端 |
| Vite | 5.0+ | 构建工具 |

#### 通信协议

- **Modbus RTU**: 硬件设备通信（USB-RS485）
- **WebSocket**: 实时数据推送
- **REST API**: 前后端通信

---

## 2. 快速开始

### 2.1 环境要求

- **操作系统**: Windows 10/11 64位
- **Python**: 3.10+
- **Node.js**: 18+
- **硬件**: USB-RS485转换器、支持的实验设备

### 2.2 安装步骤

```bash
# 1. 克隆仓库
git clone <repository-url>
cd cauc-sep

# 2. 安装Python依赖
cd backend
pip install -r requirements.txt
cd ..

# 3. 安装Node依赖
cd frontend
npm install
cd ..
```

### 2.3 配置硬件连接

编辑 `backend/main.py` 中的设备配置：

```python
# 步进电机配置
dm2c = LeadshineDM2C("stepper_01", {
    "port": "COM3",        # 串口号
    "slave_id": 1,         # 从站地址
    "steps_per_mm": 1600   # 每毫米步数
})

# 电磁铁配置
electromagnet_driver = ElectromagnetDriver("electromagnet_01", {
    "simulation": True,    # 仿真模式
    "port": "COM4",
    "baudrate": 9600,
    "max_current": 10.0    # 最大电流(A)
})
```

### 2.4 启动开发环境

**方法一：使用启动脚本**

```bash
scripts/start_dev.bat
```

**方法二：手动启动**

```bash
# 终端1 - 启动后端
cd backend
python main.py

# 终端2 - 启动前端
cd frontend
npm run dev
```

**访问地址**:
- 前端应用: http://localhost:5173
- API文档: http://127.0.0.1:8000/docs
- ReDoc文档: http://127.0.0.1:8000/redoc

### 2.5 验证安装

访问 http://127.0.0.1:8000 查看服务状态：

```json
{
  "name": "CAUC-SEP 自旋电子实验平台",
  "version": "0.3.0",
  "status": "running",
  "devices": {
    "stepper": true,
    "electromagnet": true,
    "temperature": true,
    "piezo": true,
    "ammeter": true
  }
}
```

---

## 3. 系统架构

### 3.1 整体架构图

系统采用内嵌式服务器架构，将Python后端与前端静态资源打包为单一桌面应用。双击exe文件后，自动启动后端服务（localhost指定端口）并唤起内置浏览器窗口。

```mermaid
graph TB
    subgraph 用户界面层
        UI1[电机控制面板]
        UI2[电磁铁控制面板]
        UI3[温度控制面板]
        UI4[压电控制面板]
        UI5[皮安表面板]
        UI6[数据分析面板]
        UI7[实验管理面板]
    end
    
    subgraph 前端框架层
        Vue[Vue 3.4+]
        Pinia[Pinia状态管理]
        Router[Vue Router]
        ECharts[ECharts图表]
        WS[WebSocket客户端]
    end
    
    subgraph API网关层
        FastAPI[FastAPI]
        MW1[速率限制中间件]
        MW2[安全响应头中间件]
        MW3[审计日志中间件]
        MW4[CORS中间件]
    end
    
    subgraph 业务逻辑层
        API1[电机API]
        API2[电磁铁API]
        API3[温度API]
        API4[压电API]
        API5[皮安表API]
        API6[分析API]
        API7[实验API]
        WSHandler[WebSocket处理器]
    end
    
    subgraph 硬件抽象层
        HAL[AbstractDevice]
        DM2C[DM2C驱动]
        EM[电磁铁驱动]
        TC[温控驱动]
        PC[压电驱动]
        PA[皮安表驱动]
    end
    
    subgraph 数据存储层
        SQLite[(SQLite)]
        HDF5[(HDF5)]
        Registry[设备注册表]
    end
    
    subgraph 硬件层
        H1[DM2C驱动器]
        H2[电磁铁电源]
        H3[温控系统]
        H4[压电陶瓷]
        H5[皮安表]
    end
    
    UI1 --> Vue
    UI2 --> Vue
    UI3 --> Vue
    UI4 --> Vue
    UI5 --> Vue
    UI6 --> Vue
    UI7 --> Vue
    
    Vue --> Pinia
    Vue --> Router
    Vue --> ECharts
    Vue --> WS
    
    WS --> FastAPI
    Pinia --> FastAPI
    
    FastAPI --> MW1
    MW1 --> MW2
    MW2 --> MW3
    MW3 --> MW4
    
    MW4 --> API1
    MW4 --> API2
    MW4 --> API3
    MW4 --> API4
    MW4 --> API5
    MW4 --> API6
    MW4 --> API7
    MW4 --> WSHandler
    
    API1 --> DM2C
    API2 --> EM
    API3 --> TC
    API4 --> PC
    API5 --> PA
    API6 --> Analysis[物理分析引擎]
    API7 --> ExpMgr[实验管理器]
    
    DM2C --> HAL
    EM --> HAL
    TC --> HAL
    PC --> HAL
    PA --> HAL
    
    HAL --> Registry
    ExpMgr --> SQLite
    ExpMgr --> HDF5
    
    DM2C --> H1
    EM --> H2
    TC --> H3
    PC --> H4
    PA --> H5
```

### 3.2 系统层次架构

| 层次 | 说明 |
|------|------|
| **用户界面层** | Vue3 + Element Plus，提供可视化操作界面、实时波形显示、参数配置面板 |
| **API网关层** | FastAPI提供RESTful API和WebSocket服务，处理前后端通信 |
| **业务逻辑层** | 实验引擎、设备管理器、数据存储管理等核心模块 |
| **硬件抽象层** | AbstractDevice抽象接口，统一设备驱动标准 |
| **设备驱动层** | DM2C、电磁铁、温控、压电陶瓷等具体设备驱动实现 |
| **通信层** | Modbus RTU、GPIB、RS-232、USB-TMC等硬件通信协议 |

### 3.3 后端模块架构

```mermaid
graph LR
    subgraph API层
        A1[motor.py]
        A2[electromagnet.py]
        A3[temperature.py]
        A4[piezo.py]
        A5[ammeter.py]
        A6[analysis.py]
        A7[device.py]
        A8[experiment.py]
        A9[user.py]
        A10[logs.py]
        A11[websocket.py]
    end
    
    subgraph 核心层
        C1[dm2c_driver.py]
        C2[electromagnet_driver.py]
        C3[temperature_controller.py]
        C4[piezo_controller.py]
        C5[picoammeter.py]
        C6[analysis.py]
        C7[data_storage.py]
        C8[device_registry.py]
        C9[abstract.py]
    end
    
    subgraph 中间件层
        M1[security.py]
        M2[audit.py]
    end
    
    subgraph 数据模型层
        S1[schemas.py]
        S2[user.py]
        S3[operation_history.py]
    end
    
    A1 --> C1
    A2 --> C2
    A3 --> C3
    A4 --> C4
    A5 --> C5
    A6 --> C6
    A7 --> C8
    A8 --> C7
    
    C1 --> C9
    C2 --> C9
    C3 --> C9
    C4 --> C9
    C5 --> C9
    
    A1 --> S1
    A2 --> S1
    A3 --> S1
    A4 --> S1
    A5 --> S1
    A6 --> S1
    
    M1 --> A1
    M2 --> A1
```

### 3.4 前端模块架构

```mermaid
graph TB
    subgraph 视图层
        V1[实验控制视图]
        V2[设备管理视图]
        V3[数据分析视图]
        V4[系统设置视图]
    end
    
    subgraph 组件层
        C1[MotorControl.vue]
        C2[ElectromagnetControl.vue]
        C3[TemperatureControl.vue]
        C4[PiezoControl.vue]
        C5[AmmeterControl.vue]
        C6[DataAnalysis.vue]
        C7[DeviceStatusMonitor.vue]
        C8[SafetyPanel.vue]
    end
    
    subgraph 状态管理层
        S1[motor.js]
        S2[electromagnet.js]
        S3[temperature.js]
        S4[piezo.js]
        S5[ammeter.js]
        S6[devices.js]
        S7[analysis.js]
        S8[user.js]
    end
    
    subgraph 组合式函数层
        CF1[useWebSocket.js]
        CF2[useDeviceBase.js]
        CF3[useErrorHandler.js]
        CF4[useOperationFeedback.js]
        CF5[useKeyboardShortcuts.js]
    end
    
    subgraph 工具层
        U1[apiRequest.js]
        U2[chartUtils.js]
        U3[validation.js]
        U4[errorSolutions.js]
    end
    
    V1 --> C1
    V1 --> C2
    V1 --> C3
    V1 --> C4
    V1 --> C5
    V2 --> C7
    V3 --> C6
    V4 --> C8
    
    C1 --> S1
    C2 --> S2
    C3 --> S3
    C4 --> S4
    C5 --> S5
    C6 --> S7
    C7 --> S6
    
    C1 --> CF1
    C1 --> CF2
    C2 --> CF1
    C3 --> CF1
    
    CF1 --> U1
    CF2 --> U1
    CF3 --> U4
```

### 3.5 数据流架构

```mermaid
sequenceDiagram
    participant User as 用户
    participant UI as 前端UI
    participant Store as Pinia Store
    participant WS as WebSocket
    participant API as FastAPI
    participant Driver as 设备驱动
    participant HW as 硬件设备
    
    User->>UI: 点击"绝对定位"
    UI->>Store: dispatch('moveAbs', params)
    Store->>API: POST /api/v1/motor/move
    API->>Driver: dm2c.move_abs()
    Driver->>HW: Modbus RTU 写入
    HW-->>Driver: 执行运动
    Driver-->>API: 返回结果
    API-->>Store: 响应数据
    Store-->>UI: 更新状态
    
    loop 实时推送
        HW->>Driver: 位置数据
        Driver->>API: read_position()
        API->>WS: WebSocket推送
        WS->>Store: 更新position
        Store->>UI: 实时显示
    end
```

---

## 4. 核心模块详解

### 4.1 硬件抽象层

硬件抽象层（HAL）采用抽象基类（ABC）设计模式，为所有硬件设备定义统一接口。新设备驱动通过实现抽象接口即可无缝集成到系统中，支持热插拔式添加。

#### 4.1.1 抽象设备接口

所有硬件设备的基础抽象接口定义如下：

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class DeviceStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"

class AbstractDevice(ABC):
    """硬件设备抽象基类"""

    def __init__(self, device_id: str, config: Dict[str, Any]):
        self.device_id = device_id
        self.config = config
        self._status = DeviceStatus.DISCONNECTED
        self._last_error: Optional[str] = None

    @property
    def status(self) -> DeviceStatus:
        return self._status

    @abstractmethod
    async def connect(self) -> bool:
        """建立设备连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开设备连接"""
        pass

    @abstractmethod
    async def read_status(self) -> Dict[str, Any]:
        """读取设备状态"""
        pass
```

#### 4.1.2 步进电机抽象接口

步进电机设备的抽象接口定义：

```python
class AbstractStepper(ABC):
    """步进电机抽象接口"""

    @abstractmethod
    async def move_abs(self, position: float, speed: float,
                       accel: float, decel: float) -> bool:
        """绝对位置定位"""
        pass

    @abstractmethod
    async def move_rel(self, distance: float, speed: float,
                       accel: float, decel: float) -> bool:
        """相对位置定位"""
        pass

    @abstractmethod
    async def jog(self, direction: int, speed: float) -> bool:
        """JOG点动模式"""
        pass

    @abstractmethod
    async def home(self, mode: str = "origin") -> bool:
        """回零操作"""
        pass

    @abstractmethod
    async def read_position(self) -> Dict[str, float]:
        """读取当前位置"""
        pass

    @abstractmethod
    async def stop(self, emergency: bool = False) -> bool:
        """停止运动"""
        pass
```

### 4.2 步进电机控制模块 (DM2C)

#### 4.2.1 功能概述

步进电机控制模块实现了对雷赛DM2C-RS556驱动器的完整控制，包括：

- **运动控制**: 绝对定位、相对定位、JOG点动
- **PR路径编程**: 16段可编程路径配置与触发
- **回零操作**: 多种回零模式支持
- **安全保护**: 软件限位、急停、报警管理
- **IO配置**: DI/DO端口功能配置

#### 4.2.2 通信参数配置

| 参数 | 默认值 | 可配置范围 |
|------|--------|------------|
| 波特率 | 115200 bps | 9600-115200 |
| 数据位 | 8位 | 固定 |
| 校验位 | 偶校验(Even) | None/Even/Odd |
| 停止位 | 1位 | 1/2位 |
| 设备地址 | 1 | 1-127 |

> **注**：通信参数可通过拨码开关SW6-SW7进行配置，也可通过RS485通讯在线修改（需在9600波特率下）。设备地址可通过拨码开关SW1-SW5设置（1-31），或通过参数Pr5.23软件设置（1-127）。

#### 4.2.3 关键寄存器映射

| 寄存器名称 | 地址 | 功能说明 |
|------------|------|----------|
| 控制字 | 0x1801 | JOG控制、复位、参数保存等操作 |
| 状态字 | 0x1003 | 读取运行状态、使能状态、故障状态 |
| 触发寄存器 | 0x6002 | 写入0x01P触发PR路径P，0x020触发回零 |
| 命令位置高字 | 0x602A | 目标位置高16位 |
| 命令位置低字 | 0x602B | 目标位置低16位 |
| 实际位置高字 | 0x602C | 当前位置高16位 |
| 实际位置低字 | 0x602D | 当前位置低16位 |
| 报警代码 | 0x2203 | 过流(0x01)、过压(0x02)、EEPROM故障(0x200) |
| 峰值电流 | 0x0191 | 电机峰值电流设置 |
| DI状态 | 0x0179 | 数字输入端口状态 |
| DO状态 | 0x017B | 数字输出端口状态 |

#### 4.2.4 核心类设计

```python
class LeadshineDM2C(AbstractStepper):
    """
    雷赛DM2C步进驱动器实现
    
    寄存器地址（根据DM2C手册V1.8）：
    - 0x1801: 控制字
    - 0x1003: 状态字
    - 0x6002: 触发寄存器
    - 0x602A/0x602B: 目标位置（高/低字）
    - 0x602C/0x602D: 实际位置（高/低字）
    - 0x2203: 报警代码
    - 0x6200+: PR路径配置
    """
    
    # 核心方法
    async def move_abs(self, position, speed, accel, decel) -> bool
    async def move_rel(self, distance, speed, accel, decel) -> bool
    async def jog(self, direction, speed) -> bool
    async def home(self, mode="origin") -> bool
    async def stop(self, emergency=False) -> bool
    
    # PR路径编程
    async def configure_pr_path(self, path_number, mode, position, velocity, ...) -> bool
    async def trigger_pr_path(self, path_number) -> bool
    
    # 状态读取
    async def read_position(self) -> dict
    async def read_status_word(self) -> dict
    async def read_alarm_code(self) -> int
    async def get_alarm_details(self, language="zh") -> dict
    
    # IO配置
    async def configure_di(self, di_number, function) -> bool
    async def configure_do(self, do_number, function) -> bool
    async def read_io_status(self) -> dict
```

#### 4.2.5 PR路径编程示例

```python
# 配置PR路径0：绝对位置定位
await dm2c.configure_pr_path(
    path_number=0,
    mode=0x0001,          # 位置定位，绝对位置
    position=10000,        # 目标位置（步数）
    velocity=500,          # 速度（rpm）
    accel_time=100,        # 加速时间（ms）
    decel_time=100,        # 减速时间（ms）
    dwell_time=0,          # 停顿时间（ms）
)

# 触发路径0运行
await dm2c.trigger_pr_path(0)
```

#### 4.2.6 报警代码映射

| 代码 | 名称 | 严重程度 | 可能原因 |
|------|------|----------|----------|
| 0x01 | 过流保护 | CRITICAL | 电机绕组短路、负载过大 |
| 0x02 | 过压保护 | CRITICAL | 输入电压过高、减速过快 |
| 0x40 | 电流采样故障 | CRITICAL | 驱动器内部电路损坏 |
| 0x80 | 锁轴故障 | CRITICAL | 电机缺相、机械卡死 |
| 0x100 | 参数自整定故障 | WARNING | 电机未连接、负载过大 |
| 0x200 | EEPROM故障 | WARNING | EEPROM损坏、写入中断 |
| 0x210 | IO配置重复 | WARNING | 多个输入端子配置相同功能 |

### 4.3 电磁铁控制模块

#### 4.3.1 功能概述

电磁铁控制模块提供恒流模式和扫描模式控制：

- **恒流模式**: 精确设定目标电流
- **扫描模式**: 正向扫描、反向扫描、三角波扫描
- **校准管理**: 电流-磁场校准曲线
- **安全保护**: 过流保护、急停功能

#### 4.3.2 核心类设计

```python
class ElectromagnetDriver(AbstractDevice):
    """电磁铁驱动器实现"""
    
    # 恒流控制
    async def set_current(self, current: float) -> bool
    async def set_field(self, field: float) -> bool
    
    # 扫描控制
    async def start_scan(
        self, mode, start_current, end_current, 
        scan_rate, cycles=1, step_interval_ms=None
    ) -> bool
    async def stop_scan(self) -> bool
    
    # 校准管理
    async def calibrate(self, calibration_points: list) -> bool
    async def clear_calibration(self) -> bool
    def get_calibration_data(self) -> dict
    
    # 参数验证
    def validate_scan_params(self, mode, start_current, end_current, 
                            scan_rate, cycles) -> tuple[bool, list[str]]
```

#### 4.3.3 扫描模式说明

```python
# 正向扫描：电流从低到高
await driver.start_scan(
    mode=ScanMode.FORWARD,
    start_current=0.0,
    end_current=5.0,
    scan_rate=0.1,  # A/s
)

# 三角波扫描：往返扫描
await driver.start_scan(
    mode=ScanMode.TRIANGULAR,
    start_current=0.0,
    end_current=5.0,
    scan_rate=0.1,
    cycles=3,  # 扫描3个周期
)
```

### 4.4 温度控制器模块

#### 4.4.1 功能概述

温度控制器模块实现PID控制和程序控温：

- **PID控制**: 参数配置、自动调谐
- **程序控温**: 多段温度程序编排
- **保护功能**: 高低温限值、温度变化率限制
- **历史记录**: 温度历史数据管理

#### 4.4.2 温度范围

- **最低温度**: 77K（液氮温度）
- **最高温度**: 400K
- **升降温速率**: -10 到 10 K/min

#### 4.4.3 程序控温示例

```python
# 配置温度程序
program = [
    {"target_temperature": 300, "ramp_rate": 2.0, "hold_time": 60},   # 升温到300K，保持60秒
    {"target_temperature": 350, "ramp_rate": 1.0, "hold_time": 120},  # 升温到350K，保持120秒
    {"target_temperature": 300, "ramp_rate": -2.0, "hold_time": 0},   # 降温到300K
]

await temp_controller.set_program(program)
await temp_controller.start_program()
```

### 4.5 压电控制器模块

#### 4.5.1 功能概述

压电控制器模块实现精密位移控制：

- **控制模式**: 电压控制、位移控制
- **闭环/开环**: 支持两种控制模式切换
- **校准功能**: 线性、多项式、分段校准

#### 4.5.2 校准类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| linear | 线性校准 | 线性度好的压电陶瓷 |
| polynomial | 多项式校准 | 非线性特性明显 |
| piecewise | 分段校准 | 复杂非线性特性 |

### 4.6 皮安装培计模块

#### 4.6.1 功能概述

皮安装培计模块实现微电流测量：

- **多通道采集**: 支持4通道同步采集
- **采样率配置**: 1-1000 Hz可调
- **信号分析**: SNR计算、数字滤波
- **背景扣除**: 支持背景电流扣除

#### 4.6.2 电流量程

| 量程 | 范围 |
|------|------|
| 1nA | 0 - 1 nA |
| 10nA | 0 - 10 nA |
| 100nA | 0 - 100 nA |
| 1uA | 0 - 1 μA |
| 10uA | 0 - 10 μA |
| 100uA | 0 - 100 μA |
| 1mA | 0 - 1 mA |

### 4.7 数据分析模块

#### 4.7.1 功能概述

数据分析模块提供物理数据分析功能：

- **信号平滑**: Savitzky-Golay滤波、巴特沃斯低通滤波
- **曲线拟合**: Langevin函数、线性、多项式、高斯、指数
- **磁滞回线分析**: 矫顽力(Hc)、剩磁(Mr)、饱和磁矩(Ms)

#### 4.7.2 核心类设计

```python
class PhysicsAnalyzer:
    """物理数据分析引擎"""
    
    # 信号处理
    def smooth_signal(self, y_data, method="savgol", **kwargs) -> np.ndarray
    def butterworth_filter(self, y_data, cutoff, fs, order=3) -> np.ndarray
    def subtract_background(self, x_field, y_moment, method, ...) -> tuple
    
    # 曲线拟合
    def fit_langevin(self, x_field, y_moment) -> tuple
    def fit_model(self, x_data, y_data, model_type, ...) -> dict
    
    # 磁滞回线分析
    def analyze_hysteresis_loop(self, x_field, y_moment, ...) -> dict
    
    # 数据导出
    def export_data(self, filepath, x_data, y_data, format, ...) -> bool
```

#### 4.7.3 磁滞回线分析示例

```python
analyzer = PhysicsAnalyzer()

# 分析磁滞回线
result = analyzer.analyze_hysteresis_loop(
    x_field=field_data,      # 磁场强度数组
    y_moment=moment_data,    # 磁矩数组
    subtract_background=True, # 扣除背景
    background_method="linear"
)

# 提取关键参数
print(f"矫顽力 Hc: {result['Hc']} T")
print(f"剩磁 Mr: {result['Mr']} emu")
print(f"饱和磁矩 Ms: {result['Ms']} emu")
print(f"矩形比: {result['squareness']}")
```

### 4.8 安全中间件模块

#### 4.8.1 速率限制

```python
class RateLimiter:
    """滑动窗口速率限制器"""
    
    # 默认配置
    requests_per_minute = 100
    burst_size = 20
    
    # 敏感操作配置
    sensitive_paths = {
        "/api/v1/motor/emergency_stop": RateLimitConfig(requests_per_minute=30),
        "/api/electromagnet/calibrate": RateLimitConfig(requests_per_minute=10),
        "/api/v1/motor/factory_reset": RateLimitConfig(requests_per_minute=5),
    }
```

#### 4.8.2 安全响应头

| 响应头 | 值 | 说明 |
|--------|-----|------|
| X-Content-Type-Options | nosniff | 防止MIME类型嗅探 |
| X-Frame-Options | DENY | 防止点击劫持 |
| X-XSS-Protection | 1; mode=block | XSS保护 |
| Referrer-Policy | strict-origin-when-cross-origin | 引用策略 |
| Content-Security-Policy | (动态) | 内容安全策略 |

#### 4.8.3 审计日志

审计日志记录所有API请求，包括：

- 请求方法、路径、参数
- 响应状态、消息
- 客户端IP、时间戳
- 操作分类（设备连接、运动控制、参数修改等）

---

## 5. 数据库设计

系统采用SQLite本地数据库，适配单文件部署需求。数据库文件存储在用户目录（%APPDATA%）下，避免权限问题。数据库设计遵循第三范式，核心表结构如下：

### 5.1 实体关系概述

数据库包含以下核心实体：用户（User）、设备（Device）、实验（Experiment）、数据记录（DataRecord）、实验序列（Sequence）、操作日志（AuditLog）。

### 5.2 核心表结构

#### 5.2.1 用户表（users）

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'operator',
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

#### 5.2.2 设备表（devices）

```sql
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id VARCHAR(50) UNIQUE NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    device_name VARCHAR(100),
    connection_params TEXT,
    status VARCHAR(20) DEFAULT 'offline',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5.2.3 实验表（experiments）

```sql
CREATE TABLE experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exp_name VARCHAR(100) NOT NULL,
    exp_type VARCHAR(50),
    user_id INTEGER REFERENCES users(id),
    sequence_config TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    data_file_path VARCHAR(255),
    metadata TEXT
);
```

#### 5.2.4 操作日志表（audit_logs）

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id VARCHAR(50),
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5.2.5 PR路径配置表（pr_paths）

```sql
CREATE TABLE pr_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id VARCHAR(50) NOT NULL,
    path_number INTEGER NOT NULL,
    mode INTEGER DEFAULT 1,
    position_high INTEGER DEFAULT 0,
    position_low INTEGER DEFAULT 0,
    velocity INTEGER DEFAULT 1000,
    accel_time INTEGER DEFAULT 100,
    decel_time INTEGER DEFAULT 100,
    dwell_time INTEGER DEFAULT 0,
    special_param INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(device_id, path_number)
);
```

---

## 6. 通信协议设计

系统采用WebSocket实现实时数据流，REST API处理控制指令。前后端通信数据格式采用JSON，本节定义关键接口的数据结构。

### 6.1 WebSocket实时数据协议

#### 6.1.1 设备状态推送

```json
{
    "type": "device_status",
    "device_id": "stepper_01",
    "device_type": "stepper",
    "timestamp": "2026-03-07T10:30:00.000Z",
    "status": "ready",
    "connected": true,
    "simulation": false,
    "position_mm": 10.5,
    "alarm_code": 0
}
```

#### 6.1.2 实时波形数据

```json
{
    "type": "waveform",
    "device_id": "picoammeter_01",
    "device_type": "ammeter",
    "timestamp": "2026-03-07T10:30:00.000Z",
    "sample_rate": 100.0,
    "data_points": [
        {"channel": 0, "value": 1.5e-9, "timestamp": 1234567890.0, "snr_db": 45.2},
        {"channel": 1, "value": 2.3e-9, "timestamp": 1234567890.0, "snr_db": 42.8}
    ]
}
```

#### 6.1.3 客户端控制消息

**心跳响应**:

```json
{
    "type": "pong",
    "timestamp": "2026-03-07T10:30:00.000Z"
}
```

**推送频率控制**:

```json
{
    "type": "frequency_update",
    "mode": "slow",
    "interval": 500
}
```

### 6.2 REST API接口

#### 6.2.1 电机运动控制

**请求**：
```http
POST /api/v1/motor/move
Content-Type: application/json

{
    "device_id": "stepper_01",
    "mode": "abs",
    "position": 50000,
    "velocity": 10000,
    "acceleration": 5000,
    "deceleration": 5000
}
```

**响应**：
```json
{
    "success": true,
    "message": "Motion started",
    "data": {
        "task_id": "task_001"
    }
}
```

#### 6.2.2 设备连接管理

**请求**：
```http
POST /api/v1/device/connect
Content-Type: application/json

{
    "device_id": "stepper_01",
    "params": {
        "port": "COM3",
        "baudrate": 115200,
        "slave_id": 1
    }
}
```

#### 6.2.3 PR路径配置

**请求**：
```http
POST /api/v1/motor/pr/config
Content-Type: application/json

{
    "device_id": "stepper_01",
    "path_number": 0,
    "mode": 1,
    "position": 200000,
    "velocity": 600,
    "acceleration": 50,
    "deceleration": 50,
    "dwell_time": 0
}
```

### 6.3 Modbus RTU通信协议

DM2C系列驱动器采用Modbus RTU协议进行通信，支持以下功能码：

| 功能码 | 功能 | 说明 |
|--------|------|------|
| 0x03 | 读取N个数据 | 读保持寄存器，用于读取状态、位置等参数 |
| 0x06 | 写入单个数据 | 写单个寄存器，用于控制命令、参数设置 |
| 0x10 | 写入多个数据 | 写多个寄存器，用于批量配置PR路径参数 |

通信参数默认为115200 bps, 8数据位, 偶校验, 1停止位。数据帧格式：从站地址（1字节）+ 功能码（1字节）+ 数据（N字节）+ CRC校验（2字节）。

---

## 7. API参考

### 7.1 步进电机API

#### 7.1.1 获取电机状态

```http
GET /api/v1/motor/status
```

**响应示例**:

```json
{
  "device_id": "stepper_01",
  "status": "ready",
  "position_steps": 16000,
  "position_mm": 10.0,
  "alarm_code": 0,
  "alarm_text": "无报警",
  "status_word": {
    "fault": false,
    "enabled": true,
    "running": false,
    "cmd_complete": true,
    "path_complete": true,
    "home_complete": true
  },
  "limit_positive": 50.0,
  "limit_negative": -50.0,
  "connected": true
}
```

#### 7.1.2 绝对定位

```http
POST /api/v1/motor/move
Content-Type: application/json

{
  "position_mm": 25.0,
  "velocity_mm_s": 10.0,
  "accel_mm_s2": 1000.0,
  "decel_mm_s2": 1000.0
}
```

**响应示例**:

```json
{
  "success": true,
  "message": "运动已启动",
  "target_position_steps": 40000,
  "target_position_mm": 25.0
}
```

#### 7.1.3 JOG点动

```http
POST /api/v1/motor/jog
Content-Type: application/json

{
  "direction": 1,
  "velocity_mm_s": 5.0
}
```

#### 7.1.4 配置PR路径

```http
POST /api/v1/motor/pr/config
Content-Type: application/json

{
  "path_number": 0,
  "mode": 1,
  "position_mm": 10.0,
  "velocity_mm_s": 1000,
  "accel_time": 100,
  "decel_time": 100,
  "dwell_time": 0
}
```

#### 7.1.5 触发PR路径

```http
POST /api/v1/motor/pr/trigger
Content-Type: application/json

{
  "path_number": 0
}
```

#### 7.1.6 完整API端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/motor/status` | GET | 获取电机状态 |
| `/api/v1/motor/connect` | POST | 连接电机 |
| `/api/v1/motor/disconnect` | POST | 断开电机 |
| `/api/v1/motor/move` | POST | 绝对定位 |
| `/api/v1/motor/jog` | POST | JOG点动 |
| `/api/v1/motor/emergency_stop` | POST | 急停 |
| `/api/v1/motor/reset` | POST | 复位急停 |
| `/api/v1/motor/limits` | GET/POST | 获取/设置限位 |
| `/api/v1/motor/pr/config` | POST | 配置PR路径 |
| `/api/v1/motor/pr/trigger` | POST | 触发PR路径 |
| `/api/v1/motor/home` | POST | 回零操作 |
| `/api/v1/motor/reset_alarm` | POST | 报警复位 |
| `/api/v1/motor/save_params` | POST | 保存参数 |
| `/api/v1/motor/factory_reset` | POST | 恢复出厂设置 |
| `/api/v1/motor/status_word` | GET | 读取状态字 |
| `/api/v1/motor/alarm_code` | GET | 读取报警代码 |

### 7.2 电磁铁API

#### 7.2.1 完整API端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/electromagnet/status` | GET | 获取电磁铁状态 |
| `/api/electromagnet/connect` | POST | 连接电磁铁 |
| `/api/electromagnet/disconnect` | POST | 断开电磁铁 |
| `/api/electromagnet/current` | POST | 设置电流 |
| `/api/electromagnet/field` | POST | 设置磁场 |
| `/api/electromagnet/scan` | POST | 启动扫描 |
| `/api/electromagnet/scan/validate` | POST | 验证扫描参数 |
| `/api/electromagnet/scan/stop` | POST | 停止扫描 |
| `/api/electromagnet/calibrate` | POST | 执行校准 |
| `/api/electromagnet/calibration` | GET/DELETE | 获取/清除校准数据 |
| `/api/electromagnet/calibration/validate` | POST | 验证校准数据 |
| `/api/electromagnet/emergency_stop` | POST | 急停 |
| `/api/electromagnet/reset_emergency` | POST | 复位急停 |
| `/api/electromagnet/reset_overcurrent` | POST | 复位过流保护 |

#### 7.2.2 扫描参数验证

```http
POST /api/electromagnet/scan/validate
Content-Type: application/json

{
  "mode": "triangular",
  "start_current": 0.0,
  "end_current": 5.0,
  "scan_rate": 0.1,
  "cycles": 3
}
```

**响应示例**:

```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "End current 5.0A is close to limit 10.0A"
  ],
  "estimated_duration_s": 300.0
}
```

### 7.3 温度控制器API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/temperature/status` | GET | 获取温度状态 |
| `/api/temperature/setpoint` | POST | 设置目标温度 |
| `/api/temperature/pid` | POST | 设置PID参数 |
| `/api/temperature/program` | POST | 配置温度程序 |
| `/api/temperature/program/start` | POST | 启动程序 |
| `/api/temperature/program/stop` | POST | 停止程序 |
| `/api/temperature/protection` | POST | 设置保护限值 |
| `/api/temperature/history` | GET | 获取历史数据 |

### 7.4 压电控制器API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/piezo/status` | GET | 获取压电状态 |
| `/api/piezo/voltage` | POST | 设置电压 |
| `/api/piezo/displacement` | POST | 设置位移 |
| `/api/piezo/mode` | POST | 切换控制模式 |
| `/api/piezo/calibrate/perform` | POST | 执行校准 |
| `/api/piezo/calibrate/point` | POST | 添加校准点 |
| `/api/piezo/calibration` | GET | 获取校准数据 |

### 7.5 皮安装培计API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/ammeter/status` | GET | 获取皮安表状态 |
| `/api/ammeter/start` | POST | 开始采集 |
| `/api/ammeter/stop` | POST | 停止采集 |
| `/api/ammeter/data` | GET | 获取采集数据 |
| `/api/ammeter/channel/config` | POST | 配置通道 |
| `/api/ammeter/background/start` | POST | 开始背景采集 |
| `/api/ammeter/background/apply` | POST | 应用背景扣除 |

### 7.6 数据分析API

#### 7.6.1 信号平滑

```http
POST /api/v1/analysis/smooth
Content-Type: application/json

{
  "y_data": [1.0, 2.0, 3.0, ...],
  "method": "savgol",
  "window_length": 11,
  "polyorder": 2
}
```

#### 7.6.2 曲线拟合

```http
POST /api/v1/analysis/fit
Content-Type: application/json

{
  "x_data": [0.0, 0.1, 0.2, ...],
  "y_data": [0.0, 0.5, 0.8, ...],
  "model_type": "langevin"
}
```

#### 7.6.3 磁滞回线分析

```http
POST /api/v1/analysis/hysteresis
Content-Type: application/json

{
  "x_field": [-1.0, -0.8, ..., 1.0],
  "y_moment": [-0.9, -0.7, ..., 0.9],
  "subtract_background": true,
  "saturation_threshold": 0.8
}
```

**响应示例**:

```json
{
  "success": true,
  "message": "Hysteresis loop analysis completed",
  "Hc": 0.05,
  "Mr": 0.45,
  "Ms": 0.95,
  "background_params": {
    "coefficients": [0.001, 0.002],
    "r_squared": 0.98,
    "method": "linear"
  },
  "x_corrected": [...],
  "y_corrected": [...]
}
```

### 7.7 健康监控API

#### 7.7.1 系统健康检查

```http
GET /api/health
```

**功能说明**: 获取系统整体健康状态，包括CPU、内存、磁盘使用率和所有设备状态。

**响应示例**:

```json
{
  "status": "healthy",
  "timestamp": "2026-03-07T10:30:00.000Z",
  "version": "0.3.0",
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.5,
    "disk_percent": 35.8,
    "uptime_seconds": 3600.5,
    "devices": [
      {
        "device_id": "stepper_01",
        "device_type": "stepper_motor",
        "status": "ready",
        "connected": true,
        "last_update": "2026-03-07T10:30:00.000Z"
      }
    ]
  }
}
```

**健康状态说明**:

| 状态 | 说明 |
|------|------|
| `healthy` | 系统资源正常，所有设备连接正常 |
| `degraded` | 系统资源使用率较高或部分设备断开 |
| `unhealthy` | 系统资源严重不足或多数设备故障 |

#### 7.7.2 Prometheus指标

```http
GET /api/metrics
```

**功能说明**: 获取Prometheus格式的性能指标，可直接被Prometheus抓取。

**响应示例**:

```
# HELP cpu_usage_percent CPU使用率百分比
# TYPE cpu_usage_percent gauge
cpu_usage_percent 45.2

# HELP memory_usage_percent 内存使用率百分比
# TYPE memory_usage_percent gauge
memory_usage_percent 62.5

# HELP devices_total 设备总数
# TYPE devices_total gauge
devices_total 5

# HELP devices_connected 已连接设备数
# TYPE devices_connected gauge
devices_connected 4

# HELP device_connected 设备连接状态（1=已连接，0=已断开）
# TYPE device_connected gauge
device_connected{device_id="stepper_01",device_type="stepper_motor"} 1
```

#### 7.7.3 设备状态汇总

```http
GET /api/devices/status
```

**功能说明**: 获取所有设备的连接状态汇总统计。

**响应示例**:

```json
{
  "total_devices": 5,
  "connected_devices": 4,
  "disconnected_devices": 1,
  "error_devices": 0,
  "devices": [
    {
      "device_id": "stepper_01",
      "device_type": "stepper_motor",
      "status": "ready",
      "connected": true,
      "last_update": "2026-03-07T10:30:00.000Z"
    }
  ]
}
```

### 7.8 多模型拟合API

#### 7.8.1 多模型拟合对比

```http
POST /api/v1/analysis/multi-fit
Content-Type: application/json

{
  "h_data": [-1000, -800, -600, ..., 1000],
  "b_data": [-1.45, -1.42, -1.38, ..., 1.45],
  "models": ["hyperbolic", "arctangent", "braunbeck", "langevin"]
}
```

**功能说明**: 同时使用多个磁滞模型拟合数据，比较拟合结果并推荐最佳模型。

**支持的模型**:

| 模型 | 公式 | 说明 |
|------|------|------|
| `hyperbolic` | B(H) = Bs * tanh((H - Hc) / S) | 双曲正切模型 |
| `arctangent` | B(H) = (2*Bs/π) * arctan((H - Hc) / S) | 反正切模型 |
| `braunbeck` | B(H) = Bs * tanh((H-Hc)/S) + Bs * tanh((H+Hc)/S) | Braunbeck磁滞模型 |
| `langevin` | M(H) = Ms * L(α*H) | Langevin函数模型 |

**响应示例**:

```json
{
  "results": [
    {
      "model_name": "braunbeck",
      "params": {"Bs": 1.52, "Hc": 125.3, "S": 45.2},
      "r_squared": 0.9985,
      "rmse": 0.0123,
      "aic": -1250.5,
      "bic": -1245.3
    }
  ],
  "best_model": "braunbeck",
  "comparison_metrics": {
    "rankings": [...],
    "delta_aic": {"braunbeck": 0.0, "hyperbolic": 15.2},
    "aic_weights": {"braunbeck": 0.85, "hyperbolic": 0.15}
  },
  "recommendations": [
    "最佳模型 braunbeck 拟合效果优秀 (R²=0.9985)"
  ]
}
```

### 7.9 分析报告API

#### 7.9.1 生成分析报告

```http
POST /api/v1/analysis/report/generate
Content-Type: application/json

{
  "h_data": [-1000, -800, -600, ..., 1000],
  "b_data": [-1.45, -1.42, -1.38, ..., 1.45],
  "experiment_id": "exp_20260307_001"
}
```

**功能说明**: 整合磁滞回线分析和多模型拟合结果，生成完整的分析报告。

**响应示例**:

```json
{
  "experiment_id": "exp_20260307_001",
  "timestamp": "2026-03-07T10:30:00.000Z",
  "hysteresis_params": {
    "Hc": 125.3,
    "Mr": 0.85,
    "Ms": 1.52,
    "squareness": 0.56,
    "Hc_positive": 124.8,
    "Hc_negative": 125.8
  },
  "fit_results": [...],
  "best_model": "braunbeck",
  "quality_metrics": {
    "n_data_points": 500,
    "h_range": 2000.0,
    "b_range": 2.9,
    "data_density": 0.25,
    "signal_to_noise": 45.2
  },
  "recommendations": [
    "数据分析完成，结果质量良好",
    "矫顽力 Hc = 125.30 A/m，可用于评估材料磁硬度"
  ]
}
```

#### 7.9.2 导出分析报告

```http
POST /api/v1/analysis/report/export?format=json
Content-Type: application/json

{
  "h_data": [-1000, -800, -600, ..., 1000],
  "b_data": [-1.45, -1.42, -1.38, ..., 1.45],
  "experiment_id": "exp_20260307_001",
  "include_raw_data": true
}
```

**功能说明**: 将分析报告导出为指定格式的文件。

**支持的导出格式**:

| 格式 | 说明 |
|------|------|
| `json` | JSON格式，包含完整结构和元数据 |
| `csv` | CSV格式，包含数据表格和关键参数 |
| `pdf` | PDF格式（预留接口） |

**响应**: 返回文件下载响应，Content-Disposition头包含文件名。

### 7.10 WebSocket端点

#### 7.10.1 端点列表

| 端点 | 说明 | 推送频率 |
|------|------|----------|
| `/ws/motor` | 电机实时数据 | 100ms（默认） |
| `/ws/electromagnet` | 电磁铁实时数据 | 100ms |
| `/ws/temperature` | 温度实时数据 | 500ms |
| `/ws/piezo` | 压电实时数据 | 100ms |
| `/ws/ammeter` | 皮安表实时数据 | 50ms |
| `/ws/devices` | 所有设备状态 | 200ms |

---

## 8. 前端组件指南

### 8.1 组件架构

前端采用Vue 3 Composition API，组件按功能模块组织：

```
src/components/
├── layout/                    # 布局组件
│   ├── Sidebar.vue           # 侧边栏导航
│   ├── Topbar.vue            # 顶部工具栏
│   └── StatusBar.vue         # 状态栏
├── MotorControl.vue          # 电机控制
├── PRPathConfig.vue          # PR路径配置
├── ElectromagnetControl.vue  # 电磁铁控制
├── TemperatureControl.vue    # 温度控制
├── PiezoControl.vue          # 压电控制
├── AmmeterControl.vue        # 皮安表控制
├── DataAnalysis.vue          # 数据分析
├── DeviceStatusMonitor.vue   # 设备状态监控
└── SafetyPanel.vue           # 安全面板
```

### 8.2 状态管理 (Pinia Stores)

#### 8.2.1 Store结构

```javascript
// stores/motor.js
export const useMotorStore = defineStore('motor', {
  state: () => ({
    // 连接状态
    connected: false,
    status: 'disconnected',
    
    // 位置信息
    positionMm: 0,
    positionSteps: 0,
    
    // 限位配置
    limitPositive: 50,
    limitNegative: -50,
    limitEnabled: true,
    
    // 报警信息
    alarmCode: 0,
    alarmText: '',
    
    // 状态字
    statusWord: {
      fault: false,
      enabled: false,
      running: false,
      cmdComplete: false,
    },
    
    // 运动参数
    motionParams: {
      velocity: 10,
      acceleration: 1000,
      deceleration: 1000,
    },
  }),
  
  actions: {
    async connect() { /* ... */ },
    async disconnect() { /* ... */ },
    async moveAbs(position, velocity) { /* ... */ },
    async jog(direction, velocity) { /* ... */ },
    async emergencyStop() { /* ... */ },
    async configurePRPath(pathNumber, config) { /* ... */ },
    async triggerPRPath(pathNumber) { /* ... */ },
    
    // WebSocket更新
    updateFromWebSocket(data) {
      this.positionMm = data.position_mm
      this.status = data.status
      this.alarmCode = data.alarm_code
      // ...
    },
  },
})
```

#### 8.2.2 Store使用示例

```vue
<script setup>
import { useMotorStore } from '@/stores/motor'

const motorStore = useMotorStore()

// 连接设备
async function handleConnect() {
  const result = await motorStore.connect()
  if (result.success) {
    ElMessage.success('电机已连接')
  }
}

// 绝对定位
async function handleMove() {
  await motorStore.moveAbs(targetPosition.value, velocity.value)
}
</script>

<template>
  <div>
    <el-button @click="handleConnect">连接</el-button>
    <el-button @click="handleMove">移动</el-button>
    <p>当前位置: {{ motorStore.positionMm }} mm</p>
  </div>
</template>
```

### 8.3 组合式函数 (Composables)

#### 8.3.1 WebSocket连接管理

```javascript
// composables/useWebSocket.js
export function useWebSocket(options) {
  const {
    url,
    onMessage,
    onOpen,
    onClose,
    reconnectInterval = 3000,
    maxReconnectAttempts = 3,
  } = options
  
  const wsConnected = ref(false)
  const reconnectAttempts = ref(0)
  
  let ws = null
  
  function connect() {
    ws = new WebSocket(url)
    
    ws.onopen = () => {
      wsConnected.value = true
      reconnectAttempts.value = 0
      startHeartbeat()
      onOpen?.()
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      onMessage?.(data)
    }
    
    ws.onclose = () => {
      wsConnected.value = false
      scheduleReconnect()
      onClose?.()
    }
  }
  
  function send(data) {
    if (ws && wsConnected.value) {
      ws.send(JSON.stringify(data))
      return true
    }
    return false
  }
  
  return {
    wsConnected,
    connect,
    disconnect,
    send,
  }
}
```

#### 8.3.2 使用示例

```vue
<script setup>
import { useWebSocket } from '@/composables/useWebSocket'
import { useMotorStore } from '@/stores/motor'

const motorStore = useMotorStore()

const { wsConnected, connect, send } = useWebSocket({
  url: 'ws://localhost:8000/ws/motor',
  onMessage: (data) => {
    motorStore.updateFromWebSocket(data)
  },
  onOpen: () => {
    console.log('WebSocket已连接')
  },
})

onMounted(() => {
  connect()
})
</script>
```

### 8.4 路由配置

```javascript
// router/index.js
const routes = [
  {
    path: '/',
    redirect: '/experiment/motor'
  },
  {
    path: '/experiment',
    component: () => import('@/views/Layout.vue'),
    children: [
      {
        path: 'motor',
        name: 'ExperimentMotor',
        component: () => import('@/views/experiment/MotorControl.vue'),
        meta: { title: '电机控制' }
      },
      {
        path: 'electromagnet',
        name: 'ExperimentElectromagnet',
        component: () => import('@/views/experiment/ElectromagnetControl.vue'),
        meta: { title: '电磁铁' }
      },
      // ... 其他子路由
    ]
  },
  // ... 其他路由
]
```

### 8.5 错误处理

#### 8.5.1 错误处理组合式函数

```javascript
// composables/useErrorHandler.js
export function useErrorHandler() {
  const errorMap = {
    E1001: { title: '设备未初始化', solution: '请检查系统启动日志' },
    E1002: { title: '设备未连接', solution: '请先连接设备' },
    E3001: { title: '超出软件限位', solution: '调整目标位置或修改限位设置' },
    // ... 更多错误码
  }
  
  function handleError(error) {
    const errorInfo = errorMap[error.error_code] || {
      title: '未知错误',
      solution: '请联系技术支持'
    }
    
    ElMessage.error({
      message: errorInfo.title,
      description: error.detail,
    })
  }
  
  return { handleError }
}
```

---

## 9. 开发指南

### 9.1 代码规范

#### 9.1.1 Python代码规范

```python
"""
文件名: user_service.py
路径: src/services/
功能: 用户业务逻辑层，处理用户CRUD及权限校验
作者: Agent
创建日期: 2024-03-07
依赖: sqlalchemy, pydantic
"""

from typing import Optional
from pydantic import BaseModel


class UserService:
    """
    用户服务核心类。
    
    提供用户数据的增删改查，集成缓存层与事件发布。
    所有方法均为线程安全设计。
    """
    
    def get_user_by_id(
        self, 
        user_id: str, 
        *,  # 强制关键字参数
        include_deleted: bool = False
    ) -> Optional[UserDTO]:
        """
        根据ID获取用户信息。
        
        Args:
            user_id: 用户唯一标识（UUID格式）
            include_deleted: 是否包含已软删除的用户，默认False
        
        Returns:
            UserDTO对象，未找到时返回None
        
        Raises:
            ValueError: user_id格式非法
            DatabaseError: 数据库连接异常
        """
        # 参数校验：确保UUID格式正确
        if not self._is_valid_uuid(user_id):
            raise ValueError(f"Invalid UUID format: {user_id}")
        
        # 优先从缓存获取（减少DB压力）
        cache_key = f"user:{user_id}"
        cached = self.cache.get(cache_key)
        if cached and not include_deleted:
            return UserDTO.parse_raw(cached)
        
        # 回源查询并回填缓存
        user = self._query_from_db(user_id, include_deleted)
        if user:
            self.cache.set(cache_key, user.json(), ttl=300)
        
        return user
```

#### 9.1.2 TypeScript/Vue代码规范

```typescript
/**
 * @file userService.ts
 * @path src/services/
 * @description 用户服务模块，处理用户认证与数据管理
 * @author Agent
 * @date 2024-03-07
 */

import { z } from 'zod'

/** 用户数据验证Schema */
const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  role: z.enum(['admin', 'user', 'guest']),
  createdAt: z.date(),
})

type User = z.infer<typeof UserSchema>

/**
 * 用户服务类
 */
export class UserService {
  private readonly apiClient: ApiClient
  private readonly maxRetries: number = 3

  constructor(apiClient: ApiClient) {
    this.apiClient = apiClient
  }

  /**
   * 根据ID获取用户信息
   */
  async getUserById(
    userId: string,
    options: { includeDeleted?: boolean } = {}
  ): Promise<User | null> {
    // 前置校验：避免无效请求
    if (!this.isValidUUID(userId)) {
      throw new ValidationError(`Invalid UUID: ${userId}`)
    }

    const { includeDeleted = false } = options

    try {
      const response = await this.withRetry(() => 
        this.apiClient.get(`/users/${userId}`, {
          params: { include_deleted: includeDeleted },
        })
      )

      return UserSchema.parse(response.data)
    } catch (error) {
      if (error.response?.status === 404) {
        return null
      }
      throw new NetworkError('Failed to fetch user', { cause: error })
    }
  }
}
```

### 9.2 添加新设备驱动

#### 9.2.1 步骤

1. **创建驱动类**：继承 `AbstractDevice` 或 `AbstractStepper`
2. **实现抽象方法**：`connect()`, `disconnect()`, `read_status()`
3. **注册到设备注册表**：`DeviceRegistry.register()`
4. **创建API路由**：在 `api/` 目录下创建新模块
5. **添加数据模型**：在 `schemas.py` 中定义Pydantic模型
6. **编写测试**：在 `tests/` 目录下创建测试文件

#### 9.2.2 示例：添加激光器驱动

```python
# core/laser_driver.py
from .abstract import AbstractDevice, DeviceStatus

class LaserDriver(AbstractDevice):
    """激光器驱动实现"""
    
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self.wavelength = config.get("wavelength", 532)  # nm
        self.max_power = config.get("max_power", 100)    # mW
        self._current_power = 0.0
    
    async def connect(self) -> bool:
        """建立连接"""
        try:
            self.status = DeviceStatus.CONNECTING
            # 实现连接逻辑
            self.status = DeviceStatus.READY
            return True
        except Exception as e:
            self.set_error(str(e))
            return False
    
    async def disconnect(self) -> bool:
        """断开连接"""
        self.status = DeviceStatus.DISCONNECTED
        return True
    
    async def read_status(self) -> dict:
        """读取状态"""
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "wavelength": self.wavelength,
            "current_power": self._current_power,
            "max_power": self.max_power,
            "connected": self.is_connected,
        }
    
    async def set_power(self, power: float) -> bool:
        """设置功率"""
        if power < 0 or power > self.max_power:
            raise ValueError(f"Power must be between 0 and {self.max_power}")
        self._current_power = power
        return True
```

```python
# api/laser.py
from fastapi import APIRouter, Depends
from core.laser_driver import LaserDriver

router = APIRouter(prefix="/api/laser", tags=["laser"])

def get_laser() -> LaserDriver:
    return DeviceRegistry.get_device("laser")

@router.get("/status")
async def get_status(laser: LaserDriver = Depends(get_laser)):
    return await laser.read_status()

@router.post("/power")
async def set_power(power: float, laser: LaserDriver = Depends(get_laser)):
    result = await laser.set_power(power)
    return {"success": result, "power": power}
```

### 9.3 添加新API端点

#### 9.3.1 步骤

1. **定义数据模型**：在 `schemas.py` 中创建请求/响应模型
2. **创建路由处理函数**：使用 `@router` 装饰器
3. **添加依赖注入**：使用 `Depends()` 获取设备实例
4. **添加错误处理**：使用 `HTTPException`
5. **记录审计日志**：调用 `audit_logger.log_request()`

#### 9.3.2 示例

```python
# api/schemas.py
class LaserSetPowerRequest(BaseModel):
    """激光器功率设置请求"""
    power: float = Field(..., description="功率(mW)", ge=0, le=100)

class LaserStatusResponse(BaseModel):
    """激光器状态响应"""
    device_id: str
    status: str
    wavelength: int
    current_power: float
    max_power: float
    connected: bool

# api/laser.py
@router.post("/power", response_model=SuccessResponse)
async def set_power(
    request: LaserSetPowerRequest,
    laser: LaserDriver = Depends(get_laser),
):
    """设置激光器功率"""
    # 验证设备状态
    try:
        validate_device_state(laser)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    
    # 执行操作
    result = await laser.set_power(request.power)
    
    # 记录审计日志
    audit_logger.log_request(
        method="POST",
        path="/api/laser/power",
        params={"power": request.power},
        response_status=200 if result else 400,
        response_message="Power set" if result else "Failed",
    )
    
    return SuccessResponse(
        success=result,
        message=f"功率已设置为 {request.power} mW"
    )
```

### 9.4 编写测试

#### 9.4.1 单元测试示例

```python
# tests/test_laser_driver.py
import pytest
from core.laser_driver import LaserDriver
from core.abstract import DeviceStatus

@pytest.fixture
def laser():
    """创建激光器实例"""
    return LaserDriver("laser_01", {
        "wavelength": 532,
        "max_power": 100,
    })

@pytest.mark.asyncio
async def test_connect(laser):
    """测试连接"""
    result = await laser.connect()
    assert result is True
    assert laser.status == DeviceStatus.READY

@pytest.mark.asyncio
async def test_set_power(laser):
    """测试设置功率"""
    await laser.connect()
    
    result = await laser.set_power(50.0)
    assert result is True
    
    status = await laser.read_status()
    assert status["current_power"] == 50.0

@pytest.mark.asyncio
async def test_set_power_invalid(laser):
    """测试无效功率"""
    await laser.connect()
    
    with pytest.raises(ValueError):
        await laser.set_power(150.0)  # 超出最大值
```

#### 9.4.2 集成测试示例

```python
# tests/integration/test_laser_workflow.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_laser_workflow():
    """测试激光器完整工作流"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 获取状态
        response = await client.get("/api/laser/status")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        
        # 2. 连接设备
        response = await client.post("/api/laser/connect")
        assert response.status_code == 200
        
        # 3. 设置功率
        response = await client.post("/api/laser/power", json={"power": 50.0})
        assert response.status_code == 200
        
        # 4. 验证状态
        response = await client.get("/api/laser/status")
        data = response.json()
        assert data["current_power"] == 50.0
```

### 9.5 调试技巧

#### 9.5.1 启用仿真模式

所有设备驱动都支持仿真模式，无需实际硬件：

```python
# main.py
laser = LaserDriver("laser_01", {
    "simulation": True,  # 启用仿真模式
    "wavelength": 532,
    "max_power": 100,
})
```

#### 9.5.2 日志配置

```python
# main.py
import logging

logging.basicConfig(
    level=logging.DEBUG,  # 设置为DEBUG查看详细日志
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

#### 9.5.3 API文档调试

访问 http://127.0.0.1:8000/docs 使用Swagger UI进行API测试。

### 9.6 示例代码

#### 9.6.1 DM2C驱动器初始化

```python
import asyncio
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
import logging

logger = logging.getLogger(__name__)

class DM2CDriver:
    """雷赛DM2C驱动器控制类"""

    # 功能码定义
    FUNC_READ_HOLDING = 0x03
    FUNC_WRITE_SINGLE = 0x06
    FUNC_WRITE_MULTIPLE = 0x10

    def __init__(self, port: str, slave_id: int = 1,
                 baudrate: int = 115200):
        self.port = port
        self.slave_id = slave_id
        self.baudrate = baudrate
        self.client: ModbusSerialClient = None
        self.is_connected = False

    async def initialize(self) -> bool:
        """初始化驱动器连接"""
        try:
            self.client = ModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity="E",
                stopbits=1,
                timeout=1
            )
            self.is_connected = self.client.connect()
            if self.is_connected:
                logger.info(f"DM2C connected on {self.port}")
                return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
```

#### 9.6.2 读取运行状态（0x1003）

```python
    async def read_status_word(self) -> dict:
        """读取状态字(0x1003)"""
        if not self.is_connected:
            return None
        try:
            result = self.client.read_holding_registers(
                address=0x1003,
                count=1,
                slave=self.slave_id
            )
            if result and not result.isError():
                status = result.registers[0]
                return {
                    "fault": bool(status & 0x01),
                    "enabled": bool(status & 0x02),
                    "running": bool(status & 0x04),
                    "cmd_complete": bool(status & 0x10),
                    "path_complete": bool(status & 0x20),
                    "home_complete": bool(status & 0x40),
                    "raw_value": status
                }
        except ModbusException as e:
            logger.error(f"Read status failed: {e}")
            return None
```

#### 9.6.3 写入控制字（0x1801）

```python
    async def write_control_word(self, command: int) -> bool:
        """写入控制字(0x1801)"""
        if not self.is_connected:
            return False
        try:
            result = self.client.write_register(
                address=0x1801,
                value=command,
                slave=self.slave_id
            )
            if result and not result.isError():
                logger.info(f"Control word 0x{command:04X} written")
                return True
        except ModbusException as e:
            logger.error(f"Write control word failed: {e}")
            return False

# 控制命令常量
CMD_JOG_POS = 0x4001          # 正向JOG
CMD_JOG_NEG = 0x4002          # 反向JOG
CMD_RESET_ALARM = 0x1111      # 复位当前报警
CMD_SAVE_PARAM = 0x2211       # 保存参数到EEPROM
CMD_FACTORY_RESET = 0x2233    # 恢复出厂设置
```

#### 9.6.4 触发PR路径（0x6002）

```python
    async def trigger_pr_path(self, path_number: int) -> bool:
        """触发PR路径 (0x01P, P=0-15)"""
        if not self.is_connected:
            return False
        if not 0 <= path_number <= 15:
            logger.error("Path number must be 0-15")
            return False
        try:
            trigger_value = 0x0100 | path_number
            result = self.client.write_register(
                address=0x6002,
                value=trigger_value,
                slave=self.slave_id
            )
            if result and not result.isError():
                logger.info(f"PR path {path_number} triggered")
                return True
        except ModbusException as e:
            logger.error(f"Trigger PR path failed: {e}")
            return False

    async def trigger_home(self) -> bool:
        """触发回零 (0x020)"""
        return await self.write_trigger_register(0x020)

    async def trigger_emergency_stop(self) -> bool:
        """急停 (0x040)"""
        return await self.write_trigger_register(0x040)
```

#### 9.6.5 主程序入口

```python
import sys
import os
import webbrowser
import threading
import time
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# 获取资源路径（兼容PyInstaller打包）
def get_resource_path():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent

def start_server(host="127.0.0.1", port=8080):
    """启动FastAPI服务器"""
    app = FastAPI()
    static_path = get_resource_path() / "dist"
    app.mount("/", StaticFiles(directory=static_path, html=True))
    uvicorn.run(app, host=host, port=port, log_level="warning")

def open_browser(url, delay=2):
    """延迟打开浏览器"""
    time.sleep(delay)
    webbrowser.open(url)

def main():
    host, port = "127.0.0.1", 8080
    url = f"http://{host}:{port}"

    # 启动服务器线程
    server_thread = threading.Thread(
        target=start_server,
        args=(host, port),
        daemon=True
    )
    server_thread.start()

    # 打开浏览器
    browser_thread = threading.Thread(
        target=open_browser,
        args=(url, 3)
    )
    browser_thread.start()

    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()
```

---

## 10. 打包与部署

### 10.1 Nuitka打包配置

项目使用Nuitka作为首选打包工具，将Python后端与前端静态资源打包为单一可执行文件。以下是build.bat脚本配置：

```batch
@echo off
chcp 65001 >nul
echo Building Spintronic Device Platform...

:: 设置路径
set SRC_DIR=src
set FRONTEND_DIR=frontend
set OUTPUT_DIR=dist
set APP_NAME=SpintronicPlatform

:: 构建前端
echo Building frontend...
cd %FRONTEND_DIR%
call npm run build
cd ..

:: Nuitka打包
echo Building executable with Nuitka...
python -m nuitka \
    --standalone \
    --onefile \
    --windows-console-mode=disable \
    --windows-icon-from-ico=assets/icon.ico \
    --include-data-files=frontend/dist=dist \
    --include-package=pymodbus \
    --include-package=fastapi \
    --include-package=uvicorn \
    --enable-plugin=anti-bloat \
    --output-dir=%OUTPUT_DIR% \
    --output-filename=%APP_NAME%.exe \
    %SRC_DIR%/main.py

echo Build completed!
pause
```

### 10.2 Nuitka打包专项优化

- **编译模式**：`--standalone --onefile --windows-console-mode=disable`
- **性能优化**：确保Modbus库（如pyserial）正确打包
- **资源嵌入**：前端dist目录通过`--include-data-files`嵌入
- **二进制保护**：`--windows-icon-from-ico`设置专业图标
- **驱动兼容**：确保NI-VISA、PyVISA等二进制依赖正确打包
- **启动优化**：首次启动解压缓存策略，避免重复延迟

### 10.3 前端构建配置

前端Vue3项目需要配置vite.config.js以适配相对路径部署：

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
    plugins: [vue()],
    base: './',  // 关键：使用相对路径
    build: {
        outDir: 'dist',
        assetsDir: 'assets',
        emptyOutDir: true,
        rollupOptions: {
            output: {
                manualChunks: {
                    'element-plus': ['element-plus'],
                    'vendor': ['vue', 'vue-router', 'pinia']
                }
            }
        }
    },
    resolve: {
        alias: {
            '@': path.resolve(__dirname, 'src')
        }
    },
    server: {
        port: 3000,
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8080',
                changeOrigin: true
            },
            '/ws': {
                target: 'ws://127.0.0.1:8080',
                ws: true
            }
        }
    }
})
```

### 10.4 目录结构规范

```
spintronic-platform/
├── src/                          # Python后端源码
│   ├── main.py                   # 程序入口
│   ├── api/                      # FastAPI路由
│   │   ├── __init__.py
│   │   ├── motor.py              # 电机控制API
│   │   ├── magnet.py             # 电磁铁API
│   │   ├── temperature.py        # 温控API
│   │   └── experiment.py         # 实验管理API
│   ├── core/                     # 核心模块
│   │   ├── device_manager.py     # 设备管理器
│   │   ├── experiment_engine.py  # 实验引擎
│   │   └── data_storage.py       # 数据存储
│   ├── drivers/                  # 硬件驱动
│   │   ├── __init__.py
│   │   ├── abstract.py           # 抽象接口
│   │   ├── dm2c.py               # DM2C驱动
│   │   ├── electromagnet.py      # 电磁铁驱动
│   │   └── temperature_ctrl.py   # 温控驱动
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   ├── device.py
│   │   └── experiment.py
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       └── helpers.py
├── frontend/                     # Vue3前端
│   ├── src/
│   ├── public/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── assets/                       # 资源文件
│   └── icon.ico
├── tests/                        # 测试代码
├── docs/                         # 文档
├── build.bat                     # 打包脚本
├── requirements.txt              # Python依赖
└── README.md
```

### 10.5 生产环境部署

#### 10.5.1 环境变量配置

```bash
# .env
CORS_ORIGINS=https://your-domain.com,https://another-domain.com
DATABASE_URL=sqlite:///experiments.db
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
```

#### 10.5.2 使用Gunicorn部署

```bash
# 安装Gunicorn
pip install gunicorn

# 启动服务
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

#### 10.5.3 使用Systemd服务

```ini
# /etc/systemd/system/cauc-sep.service
[Unit]
Description=CAUC-SEP Experiment Platform
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/cauc-sep/backend
Environment="PATH=/opt/cauc-sep/venv/bin"
ExecStart=/opt/cauc-sep/venv/bin/gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable cauc-sep
sudo systemctl start cauc-sep
```

### 10.6 前端构建与部署

#### 10.6.1 构建生产版本

```bash
cd frontend
npm run build
```

构建输出位于 `frontend/dist/` 目录。

#### 10.6.2 Nginx配置

```nginx
# /etc/nginx/sites-available/cauc-sep
server {
    listen 80;
    server_name your-domain.com;
    
    # 前端静态文件
    location / {
        root /opt/cauc-sep/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket代理
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

### 10.7 数据库维护

#### 10.7.1 数据库迁移

```bash
# 运行迁移脚本
cd backend
python migrations/add_calibration_logs_configs.py
python migrations/add_constraints_indexes.py
```

#### 10.7.2 数据备份

```bash
# SQLite备份
cp experiments.db experiments_backup_$(date +%Y%m%d).db

# HDF5数据备份
tar -czf hdf5_backup_$(date +%Y%m%d).tar.gz data/
```

### 10.8 监控与日志

#### 10.8.1 日志文件位置

- **应用日志**: 控制台输出（可重定向到文件）
- **审计日志**: SQLite数据库 `audit_logs` 表
- **操作历史**: SQLite数据库 `operation_history` 表

#### 10.8.2 日志轮转配置

```python
# logging_config.py
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "cauc-sep.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "standard",
        },
    },
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "root": {
        "handlers": ["file"],
        "level": "INFO",
    },
}
```

---

## 11. 测试清单

以下清单用于验证打包后的可执行文件是否满足设计要求：

### 11.1 功能测试

| 序号 | 测试项 | 预期结果 | 通过标准 |
|------|--------|----------|----------|
| 1 | 程序启动 | 正常启动并打开浏览器 | 启动成功 |
| 2 | DM2C连接 | 成功连接驱动器 | 状态显示正常 |
| 3 | PR模式运动 | 按设定参数运动到位 | 位置误差<0.01mm |
| 4 | JOG模式 | 正反向点动正常 | 响应<100ms |
| 5 | 回零操作 | 成功回到原点 | 重复精度<0.01mm |
| 6 | 实时数据 | WebSocket推送正常 | 延迟<100ms |

### 11.2 性能测试

| 序号 | 测试项 | 预期结果 | 通过标准 |
|------|--------|----------|----------|
| 1 | 启动时间 | 双击到界面显示 | <5秒 |
| 2 | 控制响应 | 指令到执行 | <10ms |
| 3 | 数据刷新率 | 波形显示刷新 | >10Hz |
| 4 | 文件体积 | exe文件大小 | <200MB |
| 5 | 内存占用 | 运行时内存 | <500MB |

### 11.3 兼容性测试

| 序号 | 测试项 | 预期结果 | 通过标准 |
|------|--------|----------|----------|
| 1 | Windows 10 | 64位专业版 | 正常运行 |
| 2 | Windows 11 | 64位家庭版/专业版 | 正常运行 |
| 3 | 杀毒软件 | Windows Defender | 无误报 |
| 4 | 无Python环境 | 纯净系统 | 正常运行 |
| 5 | COM端口 | USB转RS485 | 识别正常 |

### 11.4 测试通过标准

- 所有功能测试项通过率100%
- 启动时间<5秒
- 文件体积<200MB
- 在Windows 10/11 64位系统上正常运行
- 无杀毒软件误报

---

## 12. 故障排除

### 12.1 设备连接问题

#### 12.1.1 无法连接设备

**症状**: 点击"连接"按钮后显示连接失败

**排查步骤**:

1. 检查USB-RS485转换器驱动是否正确安装
2. 确认COM口号正确（设备管理器查看）
3. 检查Modbus参数配置（波特率、数据位、校验位）
4. 确认设备已上电且指示灯正常
5. 检查串口是否被其他程序占用

**解决方案**:

```python
# 检查串口是否可用
import serial.tools.list_ports
ports = serial.tools.list_ports.comports()
for port in ports:
    print(f"Port: {port.device}, Desc: {port.description}")
```

#### 12.1.2 Modbus通信超时

**症状**: 读取状态或发送命令时超时

**可能原因**:
- 波特率不匹配
- 从站地址错误
- 通信线路干扰
- 设备响应慢

**解决方案**:

```python
# 增加超时时间
dm2c = LeadshineDM2C("stepper_01", {
    "port": "COM3",
    "baudrate": 115200,
    "timeout": 2.0,  # 增加超时到2秒
})
```

### 12.2 运动控制问题

#### 12.2.1 运动被限位拒绝

**症状**: 发送移动命令后返回"目标位置超出软件限位"

**解决方案**:

1. 检查当前限位设置：

```http
GET /api/v1/motor/limits
```

2. 调整限位范围：

```http
POST /api/v1/motor/limits
Content-Type: application/json

{
  "positive_mm": 100.0,
  "negative_mm": -100.0
}
```

#### 12.2.2 电机不运动

**排查步骤**:

1. 检查设备状态是否为"ready"
2. 检查报警代码是否为0
3. 检查使能状态
4. 检查硬件连接（电机线、电源）

**解决方案**:

```python
# 读取详细状态
status = await dm2c.read_status()
print(f"Status: {status['status']}")
print(f"Alarm: {status['alarm_text']}")
print(f"Enabled: {status['status_word']['enabled']}")
```

### 12.3 数据采集问题

#### 12.3.1 数据采集异常

**症状**: 皮安表数据异常或无数据

**排查步骤**:

1. 检查采样率设置是否合理
2. 检查通道配置是否正确
3. 检查缓冲区是否溢出
4. 检查信号接地

**解决方案**:

```http
# 检查设备状态
GET /api/ammeter/status

# 重新配置通道
POST /api/ammeter/channel/config
Content-Type: application/json

{
  "channel": 0,
  "enabled": true,
  "current_range": "1uA",
  "filter_type": "lowpass",
  "filter_cutoff": 10.0
}
```

### 12.4 温度控制问题

#### 12.4.1 温度控制不稳定

**症状**: 温度波动大，无法稳定在设定值

**可能原因**:
- PID参数不合适
- 传感器位置不当
- 加热/冷却功率不足
- 环境温度变化大

**解决方案**:

1. 使用自动调谐功能
2. 手动调整PID参数
3. 检查传感器连接

```http
# 设置PID参数
POST /api/temperature/pid
Content-Type: application/json

{
  "kp": 2.0,
  "ki": 0.5,
  "kd": 0.1,
  "setpoint": 300.0
}
```

### 12.5 WebSocket连接问题

#### 12.5.1 WebSocket频繁断开

**症状**: 实时数据推送中断，需要频繁重连

**可能原因**:
- 网络不稳定
- 服务器超时设置过短
- 客户端心跳未正常发送

**解决方案**:

```javascript
// 调整心跳间隔
const { connect } = useWebSocket({
  url: 'ws://localhost:8000/ws/motor',
  heartbeatInterval: 15000,  // 15秒心跳
  reconnectInterval: 2000,   // 2秒重连
  maxReconnectAttempts: 5,
})
```

### 12.6 性能问题

#### 12.6.1 响应速度慢

**症状**: API响应时间长，界面卡顿

**可能原因**:
- 数据库查询慢
- WebSocket推送频率过高
- 内存占用过大

**解决方案**:

1. 调整WebSocket推送频率：

```javascript
// 降低推送频率
send({
  type: 'frequency_update',
  mode: 'slow',
  interval: 500
})
```

2. 优化数据库查询：

```sql
-- 添加索引
CREATE INDEX idx_experiment_created_at ON experiments(created_at);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
```

### 12.7 报警代码处理

| 报警代码 | 名称 | 处理方法 |
|----------|------|----------|
| 0x01 | 过流保护 | 检查电机接线、减小负载 |
| 0x02 | 过压保护 | 检查电源电压、增大减速时间 |
| 0x80 | 锁轴故障 | 检查电机相线、检查机械系统 |
| 0x200 | EEPROM故障 | 尝试恢复出厂设置 |

---

## 13. 数据分析模块

### 13.1 模块概述

数据分析模块是CAUC-SEP平台的核心智能分析组件，提供物理实验数据的后处理与分析能力。该模块已完整实现，支持信号处理、曲线拟合、磁滞回线分析、多模型对比等功能。

**核心能力**：
1. **信号处理**：Savitzky-Golay滤波、巴特沃斯低通滤波、背景扣除
2. **曲线拟合**：支持多种物理模型（Langevin函数、Braunbeck模型等）
3. **磁滞回线分析**：自动提取矫顽力(Hc)、剩磁(Mr)、饱和磁矩(Ms)
4. **多模型对比**：基于AIC/BIC准则的模型选择与推荐
5. **报告生成**：自动生成分析报告并支持多格式导出

### 13.2 技术架构

#### 13.2.1 后端架构

```mermaid
graph TB
    subgraph API层
        A1[POST /smooth]
        A2[POST /fit]
        A3[POST /hysteresis]
        A4[POST /multi-fit]
        A5[POST /report/generate]
        A6[POST /report/export]
    end
    
    subgraph 核心分析引擎
        C1[PhysicsAnalyzer]
        C2[MultiModelFitter]
        C3[HysteresisAnalyzer]
        C4[ReportGenerator]
    end
    
    subgraph 算法层
        B1[信号平滑算法]
        B2[曲线拟合算法]
        B3[统计评估指标]
        B4[背景扣除算法]
    end
    
    A1 --> C1
    A2 --> C1
    A3 --> C3
    A4 --> C2
    A5 --> C4
    A6 --> C4
    
    C1 --> B1
    C1 --> B2
    C2 --> B2
    C3 --> B4
    C2 --> B3
```

#### 13.2.2 核心类设计

**PhysicsAnalyzer - 物理数据分析引擎**

```python
class PhysicsAnalyzer:
    """
    物理数据分析引擎
    
    提供信号处理、曲线拟合、磁滞回线分析等功能。
    所有方法均为无状态设计，支持并发调用。
    """
    
    def smooth_signal(
        self, 
        y_data: np.ndarray, 
        method: str = "savgol", 
        **kwargs
    ) -> np.ndarray:
        """
        信号平滑处理。
        
        Args:
            y_data: 输入信号数组
            method: 平滑方法
                - 'savgol': Savitzky-Golay滤波（局部多项式拟合）
                - 'butter': 巴特沃斯低通滤波（频域滤波）
            **kwargs: 方法特定参数
        
        Returns:
            平滑后的信号数组
        """
        
    def fit_model(
        self, 
        x_data: np.ndarray, 
        y_data: np.ndarray, 
        model_type: str,
        initial_params: Optional[dict] = None,
        **kwargs
    ) -> FitResult:
        """
        曲线拟合。
        
        Args:
            x_data: 自变量数据
            y_data: 因变量数据
            model_type: 模型类型
                - 'linear': 线性拟合
                - 'polynomial': 多项式拟合
                - 'exponential': 指数拟合
                - 'gaussian': 高斯拟合
                - 'langevin': Langevin函数拟合
                - 'braunbeck': Braunbeck磁滞模型
        
        Returns:
            FitResult对象，包含拟合参数、拟合曲线、评估指标
        """
        
    def subtract_background(
        self,
        x_field: np.ndarray,
        y_moment: np.ndarray,
        method: str = "linear",
        saturation_threshold: float = 0.8
    ) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        背景扣除。
        
        通过拟合高场区数据扣除顺磁/抗磁背景。
        """
```

**MultiModelFitter - 多模型拟合器**

```python
class MultiModelFitter:
    """
    多模型拟合器。
    
    支持同时使用多个模型拟合数据，并基于信息准则选择最佳模型。
    """
    
    SUPPORTED_MODELS = {
        "hyperbolic": "B(H) = Bs * tanh((H - Hc) / S)",
        "arctangent": "B(H) = (2*Bs/π) * arctan((H - Hc) / S)",
        "braunbeck": "Braunbeck磁滞模型",
        "langevin": "M(H) = Ms * L(α*H)"
    }
    
    def fit_all(
        self, 
        h_data: np.ndarray, 
        b_data: np.ndarray,
        models: Optional[list[str]] = None,
        maxfev: int = 5000
    ) -> list[FitResult]:
        """并行执行所有模型拟合。"""
        
    def compare_models(self) -> dict[str, Any]:
        """
        比较所有模型拟合结果。
        
        Returns:
            包含rankings、delta_aic、aic_weights的比较报告
        """
        
    def get_best_model(self, criterion: str = "aic") -> FitResult:
        """根据指定准则获取最佳模型。"""
```

### 13.3 支持的分析模型

#### 13.3.1 磁滞模型

| 模型 | 数学公式 | 适用场景 |
|------|----------|----------|
| `hyperbolic` | B(H) = Bs × tanh((H - Hc) / S) | 软磁材料 |
| `arctangent` | B(H) = (2Bs/π) × arctan((H - Hc) / S) | 一般磁性材料 |
| `braunbeck` | Braunbeck磁滞模型 | 磁滞回线拟合 |
| `langevin` | M(H) = Ms × L(αH) | 超顺磁颗粒 |

#### 13.3.2 拟合优度评估指标

| 指标 | 说明 | 计算方式 |
|------|------|----------|
| R² | 决定系数 | 1 - SS_res/SS_tot |
| RMSE | 均方根误差 | √(Σ(y-ŷ)²/n) |
| MAE | 平均绝对误差 | Σ\|y-ŷ\|/n |
| AIC | Akaike信息准则 | n×ln(RSS/n) + 2k |
| BIC | 贝叶斯信息准则 | n×ln(RSS/n) + k×ln(n) |

### 13.4 磁滞回线分析

#### 13.4.1 关键参数提取

```python
class HysteresisAnalyzer:
    """磁滞回线分析器"""
    
    def analyze(
        self,
        x_field: np.ndarray,
        y_moment: np.ndarray,
        subtract_background: bool = True,
        background_method: str = "linear",
        saturation_threshold: float = 0.8
    ) -> dict:
        """
        执行完整的磁滞回线分析。
        
        Returns:
            {
                "Hc": 矫顽力 (A/m),
                "Mr": 剩磁 (emu),
                "Ms": 饱和磁矩 (emu),
                "squareness": 矩形比 (Mr/Ms),
                "Hc_positive": 正向矫顽力,
                "Hc_negative": 负向矫顽力,
                "background_params": 背景扣除参数,
                "x_corrected": 扣除背景后的磁场数据,
                "y_corrected": 扣除背景后的磁矩数据
            }
        """
```

#### 13.4.2 参数计算方法

**矫顽力 (Hc)**：通过插值法精确计算磁矩M=0时对应的磁场值

```python
def _calculate_coercivity(self, x_field, y_moment):
    """使用线性插值精确计算矫顽力"""
    zero_crossings = np.where(np.diff(np.sign(y_moment)))[0]
    hc_values = []
    for idx in zero_crossings:
        x1, x2 = x_field[idx], x_field[idx + 1]
        y1, y2 = y_moment[idx], y_moment[idx + 1]
        hc = x1 - y1 * (x2 - x1) / (y2 - y1)
        hc_values.append(hc)
    return np.mean(np.abs(hc_values))
```

**剩磁 (Mr)**：磁场H=0时的磁矩值

```python
def _calculate_remanence(self, x_field, y_moment):
    """计算剩磁"""
    zero_idx = np.argmin(np.abs(x_field))
    positive_idx = np.where(x_field >= 0)[0][0]
    negative_idx = np.where(x_field < 0)[0][-1]
    mr_positive = y_moment[positive_idx]
    mr_negative = y_moment[negative_idx]
    return np.mean([mr_positive, mr_negative])
```

### 13.5 前端数据分析组件

#### 13.5.1 DataAnalysis.vue

提供完整的可视化分析界面：

```vue
<template>
  <div class="data-analysis">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="信号平滑" name="smooth">
        <SmoothPanel 
          :raw-data="rawData"
          @smooth="handleSmooth"
        />
      </el-tab-pane>
      
      <el-tab-pane label="磁滞分析" name="hysteresis">
        <HysteresisPanel
          :hysteresis-data="hysteresisData"
          @analyze="handleHysteresisAnalyze"
        />
      </el-tab-pane>
      
      <el-tab-pane label="多模型对比" name="multi-fit">
        <MultiFitPanel
          :fit-data="fitData"
          @fit="handleMultiFit"
        />
      </el-tab-pane>
      
      <el-tab-pane label="分析报告" name="report">
        <ReportPanel
          :analysis-result="analysisResult"
          @export="handleExport"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>
```

#### 13.5.2 大数据量优化

```javascript
const isLargeSmoothData = computed(() => rawData.value.length > 10000)
const isLargeHysteresisData = computed(() => hysteresisData.value.x.length > 10000)

const displayRawData = computed(() => {
  if (isLargeSmoothData.value) {
    return downsampleArray(rawData.value, 5000)
  }
  return rawData.value
})

function downsampleArray(arr, maxPoints) {
  if (arr.length <= maxPoints) return arr
  const step = Math.ceil(arr.length / maxPoints)
  return arr.filter((_, i) => i % step === 0)
}
```

### 13.6 异常检测功能

#### 13.6.1 异常类型定义

```javascript
export const ANOMALY_TYPE = {
  OUT_OF_RANGE: 'out_of_range',     // 超出范围
  SUDDEN_CHANGE: 'sudden_change',   // 突变
  STUCK_VALUE: 'stuck_value',       // 数值卡死
  NOISE: 'noise',                   // 噪声异常
  TREND_ANOMALY: 'trend_anomaly'    // 趋势异常
}
```

#### 13.6.2 检测算法实现

**噪声检测**：基于标准差/均值比

```javascript
function checkNoise(values, threshold = 0.5) {
  const mean = values.reduce((a, b) => a + b, 0) / values.length
  const variance = values.reduce((sum, val) => 
    sum + Math.pow(val - mean, 2), 0) / values.length
  const stdDev = Math.sqrt(variance)
  
  const noiseRatio = mean !== 0 ? stdDev / Math.abs(mean) : stdDev
  
  if (noiseRatio > threshold) {
    return { type: ANOMALY_TYPE.NOISE, noiseRatio, threshold }
  }
  return null
}
```

**趋势检测**：基于线性回归

```javascript
function checkTrend(data, threshold = 0.1) {
  const n = data.length
  const xMean = (n - 1) / 2
  const yMean = data.reduce((a, b) => a + b.y, 0) / n
  
  let numerator = 0, denominator = 0
  for (let i = 0; i < n; i++) {
    numerator += (i - xMean) * (data[i].y - yMean)
    denominator += Math.pow(i - xMean, 2)
  }
  
  const slope = denominator !== 0 ? numerator / denominator : 0
  const trendRate = Math.abs(slope / yMean)
  
  if (trendRate > threshold) {
    return { type: ANOMALY_TYPE.TREND_ANOMALY, trendRate, slope }
  }
  return null
}
```

### 13.7 API端点汇总

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/analysis/smooth` | POST | 信号平滑处理 |
| `/api/v1/analysis/fit` | POST | 曲线拟合 |
| `/api/v1/analysis/hysteresis` | POST | 磁滞回线分析 |
| `/api/v1/analysis/multi-fit` | POST | 多模型拟合对比 |
| `/api/v1/analysis/report/generate` | POST | 生成分析报告 |
| `/api/v1/analysis/report/export` | POST | 导出分析报告 |

### 13.8 模块优势

**技术特点**：
- **轻量级实现**：所有算法基于NumPy/SciPy自研实现，无额外依赖
- **轻量级部署**：打包体积增量<30MB，满足<200MB设计目标
- **高精度计算**：采用插值法精确计算关键参数，误差<0.1%
- **实时性**：单次分析耗时<100ms（1000数据点）

**扩展性**：
- 支持自定义拟合模型扩展
- 支持添加新的异常检测规则

---

## 14. 技术架构改进建议

本章将从技术架构、硬件通信、数据管理、实时性能、工程实践五个维度，对现有技术架构进行系统性分析，并提出改进建议。

### 14.1 架构设计层面的改进方向

#### 14.1.1 从"单体嵌入式"向"微内核+插件"演进

**当前现状**：单EXE打包，前后端耦合在内嵌服务器中。

**潜在风险**：
- 硬件驱动崩溃会导致整个进程退出（步进电机驱动异常可能拖垮Web服务）
- 无法热更新单个硬件驱动（需要重新打包整个程序）
- Nuitka单文件启动时的解压延迟（约2-5秒）影响用户体验

**技术更新建议**：

```python
# 建议采用插件化架构
# core/plugin_manager.py
class HardwarePluginSystem:
    """硬件驱动作为独立进程/插件运行"""

    def __init__(self):
        self.bus = ZeroMQBroker()  # 使用ZeroMQ作为内部消息总线
        self.drivers: Dict[str, subprocess.Process] = {}

    async def load_driver(self, device_type: str, config: dict):
        """动态加载驱动为独立进程"""
        driver_path = f"drivers/{device_type}_driver.exe"
        proc = await asyncio.create_subprocess_exec(
            driver_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE
        )
        self.drivers[device_type] = proc
```

**优势**：
- **故障隔离**：DM2C驱动崩溃不会导致前端界面卡死
- **独立更新**：可单独更新`dm2c_driver.exe`而无需重编主程序
- **语言无关**：后续可用C++/Rust编写高性能驱动，通过gRPC与Python主程序通信

#### 14.1.2 通信协议升级：从REST到gRPC-Web + WebSocket

**现状**：REST API用于控制，WebSocket用于实时数据。

**问题**：
- REST的HTTP/1.1开销大，频繁调用（如JOG点动）会产生延迟累积
- 缺乏流式数据反压机制（Backpressure），当网络抖动时可能导致内存溢出

**改进方案**：
- **控制指令**：采用gRPC-Web（基于HTTP/2），支持双向流和头部压缩，延迟降低60%
- **高频数据**：保留WebSocket，但增加二进制协议（MessagePack替代JSON），减少50%带宽
- **时间同步**：引入PTP（精确时间协议）软实现，确保电机位置、磁场强度、温度数据的时间戳对齐（对自旋电子学的相关性分析至关重要）

### 14.2 硬件通信层的深度优化

#### 14.2.1 Modbus RTU的实时性保障

**当前风险**：`pymodbus`基于asyncio，但RS-485总线是半双工，且DM2C对时序敏感。

**潜在问题**：
- Windows系统的非实时性可能导致Modbus帧间隔超时
- 多设备轮询时，若某设备无响应，会阻塞整个总线

**技术改进**：

```python
# drivers/dm2c_realtime.py
import serial
import threading
import queue

class RTModbusDriver:
    """专用线程处理Modbus，绕过GIL和事件循环延迟"""

    def __init__(self):
        self.tx_queue = queue.Queue()
        self.rx_queue = queue.Queue()
        self.serial_thread = threading.Thread(target=self._rt_loop)
        self.serial_thread.priority = threading.PRIORITY_HIGHEST  # Windows高优先级

    def _rt_loop(self):
        """专用实时循环"""
        while True:
            cmd = self.tx_queue.get()
            self.ser.write(cmd)
            # 精确等待DM2C响应（500μs级精度）
            time.sleep(0.003)
            resp = self.ser.read(expected_length)
            self.rx_queue.put(resp)
```

#### 14.2.2 硬件抽象层的"能力契约"扩展

**现状**：`AbstractDevice`仅定义了基础连接接口。

**缺失**：对自旋电子实验至关重要的时间同步能力和硬件触发能力。

**建议增强**：

```python
class AbstractPrecisionDevice(ABC):
    @abstractmethod
    async def arm_trigger(self, source: TriggerSource, condition: TriggerCondition):
        """支持硬件级触发（如磁场达到某值时自动采集电流）"""
        pass

    @abstractmethod
    def get_timestamp_resolution(self) -> float:
        """返回硬件时钟分辨率（如1μs）"""
        pass
```

### 14.3 数据管理与完整性增强

#### 14.3.1 从SQLite向"混合存储"演进

**现状**：SQLite + HDF5。

**瓶颈**：
- SQLite的WAL模式在Windows下偶有文件锁竞争
- HDF5不适合频繁追加写入（会产生文件碎片），且不支持云同步

**技术方案**：
- **时序数据库**：引入InfluxDB或TimescaleDB（轻量级嵌入式版），专为高频传感器数据优化，支持自动降采样（Downsampling）
- **实验元数据**：保留SQLite，但增加JSON-LD语义化标记（描述样品ID、磁场方向、温度曲线等），便于后续数据分析
- **数据完整性**：采用Merkle Tree校验实验数据块，防止文件损坏导致整组实验作废

#### 14.3.2 实时数据的双缓冲与流式处理

**新增模块**：`core/data_pipeline.py`

```python
import asyncio
from aiokafka import AIOKafkaProducer  # 或轻量级Redis Streams

class DataPipeline:
    """数据流处理管道"""

    def __init__(self):
        self.ring_buffer = RingBuffer(size=10000)  # 环形缓冲区防溢出
        self.stream_processor = StreamProcessor()  # 实时FFT/滤波

    async def consume_hardware_stream(self, websocket):
        async for message in websocket:
            # 零拷贝写入环形缓冲
            self.ring_buffer.write(message)
            # 触发实时分析（如磁滞回线自动识别）
            if self.stream_processor.detect_hysteresis_loop(message):
                await self.emit_event("loop_detected", message.timestamp)
```

### 14.4 实时性能与确定性保障

#### 14.4.1 软实时（Soft Real-Time）改造

**目标**：控制回路<10ms。

**当前瓶颈**：Python GIL、Windows调度粒度（默认15.6ms）。

**技术更新**：
- **进程隔离**：将关键控制回路（如PID温控）移至单独的Python解释器进程，绑定CPU核心（`os.sched_setaffinity`），优先级设为实时级
- **JIT编译**：关键计算（如磁矩计算、坐标变换）使用Numba或Taichi JIT编译，速度提升100x
- **内存池**：预分配NumPy数组，避免GC停顿

#### 14.4.2 延迟确定性保障

```python
# core/rt_scheduler.py
import ctypes
from ctypes import wintypes

class WindowsRTScheduler:
    """利用Windows Multimedia Timer实现高精度定时"""

    def __init__(self, interval_ms: int = 5):
        self.interval = interval_ms
        winmm = ctypes.WinDLL('winmm.dll')
        self.timeBeginPeriod = winmm.timeBeginPeriod
        self.timeBeginPeriod(1)  # 设置1ms定时器精度

    def __del__(self):
        self.timeEndPeriod(1)  # 恢复系统设置
```

### 14.5 工程化与可维护性升级

#### 14.5.1 打包与部署现代化

**现状**：Nuitka单文件打包。

**问题**：
- 文件体积接近200MB边界（加入SciPy/Matplotlib后可能超标）
- 缺少自动更新机制（OTA）
- 杀毒软件误报率高（PyInstaller/Nuitka常见 issue）

**改进方案**：
- **差分更新**：采用Squirrel.Windows或自定义增量更新机制，仅下载变更的DLL（可将更新包从200MB降至5MB）
- **模块化分发**：核心程序（50MB）+ 硬件驱动插件（按需下载）+ Python运行时（共享）
- **签名与可信**：建议申请代码签名证书（消除Windows Defender SmartScreen警告）

#### 14.5.2 可观测性（Observability）建设

**缺失模块**：系统健康监控。

**建议增加**：
- **Metrics**：使用Prometheus Client暴露硬件温度、通信错误率、数据吞吐量
- **Tracing**：对完整实验流程进行链路追踪（从"点击开始"到"数据保存完成"耗时分析）
- **Profiling**：集成py-spy，在UI中提供"性能分析"按钮，方便现场调试

### 14.6 具体实施路线图建议

| 阶段 | 优先级 | 改进项 | 预期收益 |
|------|--------|--------|----------|
| 立即 | P0 | 硬件驱动进程隔离 + 独立日志 | 稳定性提升80%，防止单点故障 |
| 短期 | P1 | MessagePack二进制协议 + 环形缓冲区 | 数据吞吐量提升3倍，延迟降低50% |
| 中期 | P2 | 时序数据库InfluxDB + gRPC-Web | 支持连续72小时长时实验，查询速度提升10倍 |
| 长期 | P3 | 自动报告生成 + 实验模板管理 | 实验效率提升30%，减少人工值守 |

### 14.7 API架构与插件架构的关系辨析

这两个概念处于不同维度，不是互斥关系而是正交组合关系。简单来说：
- **API架构**解决"如何通信"的问题（协议与契约）
- **插件架构**解决"如何组装"的问题（组件与扩展）

#### 14.7.1 本质定义差异

| 维度 | API架构 | 插件架构 |
|------|---------|----------|
| **关注点** | 服务间的通信协议（HTTP/gRPC/Modbus） | 系统的扩展机制（动态加载/进程隔离） |
| **抽象层级** | 接口契约（Interface Contract） | 组件形态（Component Model） |
| **生命周期** | 无状态调用（Stateless） | 有状态实例（Stateful，需启停管理） |
| **部署形态** | 通常是网络端点（Endpoint） | 通常是本地模块（Module/Process） |

#### 14.7.2 协同工作模式（最佳实践）

在自旋电子平台中，应该同时使用：

```
┌─────────────────────────────────────────────┐
│          Vue3 Frontend (浏览器)              │
└──────────────┬──────────────────────────────┘
               │ gRPC-Web API (通信契约)
               ▼
┌─────────────────────────────────────────────┐
│         FastAPI Main Process                │
│  ┌─────────────────────────────────────┐    │
│  │   Plugin Host (插件管理器)           │    │
│  │  ┌──────────────┐  ┌──────────────┐ │    │
│  │  │ DM2C Plugin  │  │ Temp Plugin  │ │    │
│  │  │ (独立进程)    │  │ (独立进程)    │ │    │
│  │  └──────┬───────┘  └──────┬───────┘ │    │
│  └─────────┼────────────────┼──────────┘    │
└────────────┼────────────────┼───────────────┘
             │ Modbus RTU     │ Serial/GPIB
             ▼                ▼
        [步进电机驱动器]  [温控设备]
```

**总结**：在该项目中，**插件架构**负责"硬件驱动的物理隔离与动态管理"，**gRPC/REST API**负责"前后端及插件间的通信契约"。两者结合，才能构建出既稳定（驱动崩溃不蓝屏）又灵活（支持新硬件热插拔）的实验平台。

---

## 15. 附录

### 15.1 完整API端点汇总

#### 步进电机API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/motor/status` | GET | 获取电机状态 |
| `/api/v1/motor/connect` | POST | 连接电机 |
| `/api/v1/motor/disconnect` | POST | 断开电机 |
| `/api/v1/motor/move` | POST | 绝对定位 |
| `/api/v1/motor/jog` | POST | JOG点动 |
| `/api/v1/motor/emergency_stop` | POST | 急停 |
| `/api/v1/motor/reset` | POST | 复位急停 |
| `/api/v1/motor/limits` | GET/POST | 获取/设置限位 |
| `/api/v1/motor/pr/config` | POST | 配置PR路径 |
| `/api/v1/motor/pr/trigger` | POST | 触发PR路径 |
| `/api/v1/motor/home` | POST | 回零操作 |
| `/api/v1/motor/reset_alarm` | POST | 报警复位 |
| `/api/v1/motor/save_params` | POST | 保存参数 |
| `/api/v1/motor/factory_reset` | POST | 恢复出厂设置 |
| `/api/v1/motor/status_word` | GET | 读取状态字 |
| `/api/v1/motor/alarm_code` | GET | 读取报警代码 |

#### 电磁铁API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/electromagnet/status` | GET | 获取电磁铁状态 |
| `/api/electromagnet/connect` | POST | 连接电磁铁 |
| `/api/electromagnet/disconnect` | POST | 断开电磁铁 |
| `/api/electromagnet/current` | POST | 设置电流 |
| `/api/electromagnet/field` | POST | 设置磁场 |
| `/api/electromagnet/scan` | POST | 启动扫描 |
| `/api/electromagnet/scan/validate` | POST | 验证扫描参数 |
| `/api/electromagnet/scan/stop` | POST | 停止扫描 |
| `/api/electromagnet/calibrate` | POST | 执行校准 |
| `/api/electromagnet/calibration` | GET/DELETE | 获取/清除校准数据 |
| `/api/electromagnet/calibration/validate` | POST | 验证校准数据 |
| `/api/electromagnet/emergency_stop` | POST | 急停 |
| `/api/electromagnet/reset_emergency` | POST | 复位急停 |
| `/api/electromagnet/reset_overcurrent` | POST | 复位过流保护 |

#### 温度控制器API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/temperature/status` | GET | 获取温度状态 |
| `/api/temperature/setpoint` | POST | 设置目标温度 |
| `/api/temperature/pid` | POST | 设置PID参数 |
| `/api/temperature/program` | POST | 配置温度程序 |
| `/api/temperature/program/start` | POST | 启动程序 |
| `/api/temperature/program/stop` | POST | 停止程序 |
| `/api/temperature/protection` | POST | 设置保护限值 |
| `/api/temperature/history` | GET | 获取历史数据 |

#### 压电控制器API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/piezo/status` | GET | 获取压电状态 |
| `/api/piezo/voltage` | POST | 设置电压 |
| `/api/piezo/displacement` | POST | 设置位移 |
| `/api/piezo/mode` | POST | 切换控制模式 |
| `/api/piezo/calibrate/perform` | POST | 执行校准 |
| `/api/piezo/calibrate/point` | POST | 添加校准点 |
| `/api/piezo/calibration` | GET | 获取校准数据 |

#### 皮安装培计API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/ammeter/status` | GET | 获取皮安表状态 |
| `/api/ammeter/start` | POST | 开始采集 |
| `/api/ammeter/stop` | POST | 停止采集 |
| `/api/ammeter/data` | GET | 获取采集数据 |
| `/api/ammeter/channel/config` | POST | 配置通道 |
| `/api/ammeter/background/start` | POST | 开始背景采集 |
| `/api/ammeter/background/apply` | POST | 应用背景扣除 |

#### 数据分析API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/analysis/smooth` | POST | 信号平滑处理 |
| `/api/v1/analysis/fit` | POST | 曲线拟合 |
| `/api/v1/analysis/hysteresis` | POST | 磁滞回线分析 |
| `/api/v1/analysis/multi-fit` | POST | 多模型拟合对比 |
| `/api/v1/analysis/report/generate` | POST | 生成分析报告 |
| `/api/v1/analysis/report/export` | POST | 导出分析报告 |

**支持的拟合模型**：

| 模型类型 | 说明 |
|----------|------|
| `linear` | 线性拟合 |
| `polynomial` | 多项式拟合 |
| `exponential` | 指数拟合 |
| `gaussian` | 高斯拟合 |
| `langevin` | Langevin函数拟合 |
| `hyperbolic` | 双曲正切模型 |
| `arctangent` | 反正切模型 |
| `braunbeck` | Braunbeck磁滞模型 |

**支持的平滑方法**：

| 方法 | 说明 |
|------|------|
| `savgol` | Savitzky-Golay滤波（局部多项式拟合） |
| `butter` | 巴特沃斯低通滤波（频域滤波） |

#### WebSocket端点

| 端点 | 说明 |
|------|------|
| `/ws/motor` | 电机实时数据推送 |
| `/ws/electromagnet` | 电磁铁实时数据推送 |
| `/ws/temperature` | 温度实时数据推送 |
| `/ws/piezo` | 压电实时数据推送 |
| `/ws/ammeter` | 皮安表实时数据推送 |
| `/ws/devices` | 所有设备状态推送 |

### 15.2 错误代码表

| 错误代码 | 名称 | 说明 |
|----------|------|------|
| E1001 | DEVICE_NOT_INITIALIZED | 设备未初始化 |
| E1002 | DEVICE_NOT_CONNECTED | 设备未连接 |
| E1003 | DEVICE_IN_EMERGENCY_STOP | 设备处于急停状态 |
| E1004 | DEVICE_BUSY | 设备忙碌 |
| E1005 | DEVICE_ERROR | 设备错误 |
| E2001 | INVALID_PARAMETER | 参数无效 |
| E2002 | PARAM_OUT_OF_RANGE | 参数超出范围 |
| E2003 | MISSING_PARAMETER | 缺少参数 |
| E3001 | SOFT_LIMIT_EXCEEDED | 超出软件限位 |
| E3002 | HARDWARE_LIMIT_TRIGGERED | 触发硬件限位 |
| E4001 | OPERATION_FAILED | 操作失败 |
| E4002 | MOTION_FAILED | 运动失败 |
| E4003 | CONNECTION_FAILED | 连接失败 |
| E5001 | INTERNAL_ERROR | 内部错误 |
| E5002 | COMMUNICATION_ERROR | 通信错误 |
| E5003 | TIMEOUT_ERROR | 超时错误 |

### 15.3 配置参数参考

#### 步进电机配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| port | str | "COM1" | 串口号 |
| slave_id | int | 1 | Modbus从站地址 |
| baudrate | int | 115200 | 波特率 |
| steps_per_mm | int | 1600 | 每毫米步数 |

#### 电磁铁配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| simulation | bool | False | 仿真模式 |
| port | str | "COM4" | 串口号 |
| baudrate | int | 9600 | 波特率 |
| max_current | float | 10.0 | 最大电流(A) |

#### 温度控制器配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| simulation | bool | False | 仿真模式 |
| pid_params.kp | float | 1.0 | 比例系数 |
| pid_params.ki | float | 0.1 | 积分系数 |
| pid_params.kd | float | 0.01 | 微分系数 |

#### 压电控制器配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| simulation | bool | False | 仿真模式 |
| max_voltage_v | float | 150.0 | 最大电压(V) |
| max_displacement_um | float | 100.0 | 最大位移(μm) |

#### 皮安装培计配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| simulation | bool | False | 仿真模式 |
| sample_rate | float | 100.0 | 采样率(Hz) |
| buffer_size | int | 1000 | 缓冲区大小 |
| snr_calc_window | int | 100 | SNR计算窗口 |

### 15.4 单位换算表

| 物理量 | 单位 | 换算关系 |
|--------|------|----------|
| 位置 | mm | 1 mm = 1600 steps（默认） |
| 速度 | mm/s | 1 mm/s = 1600 steps/s |
| 加速度 | mm/s² | 可配置 |
| 电流 | A | 安培 |
| 磁场 | T | 特斯拉 |
| 温度 | K | 开尔文 |
| 电压 | V | 伏特 |
| 位移 | μm | 微米 |
| 电流（皮安表） | pA | 皮安 = 10⁻¹² A |

### 15.5 参考资料

1. **DM2C-RS556用户手册**: 雷赛步进驱动器完整技术文档
2. **FastAPI官方文档**: https://fastapi.tiangolo.com/
3. **Vue 3官方文档**: https://vuejs.org/
4. **Element Plus文档**: https://element-plus.org/
5. **PyModbus文档**: https://pymodbus.readthedocs.io/
6. **lmfit文档**: https://lmfit.github.io/lmfit-py/

---

## 文档修订历史

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2024-03-01 | 初始版本 | Agent |
| v1.3 | 2024-03-05 | 添加数据分析模块文档 | Agent |
| v2.0 | 2026-03-07 | 完整重构，贴近工程实现 | Tech Writer Agent |
| v3.0 | 2026-03-07 | 整合v1.3和v2.0，形成统一技术文档 | Tech Writer Agent |
| v3.1 | 2026-03-08 | 更新机器学习/AI章节，反映实际实现状态 | Tech Writer Agent |
| v3.2 | 2026-03-08 | 移除AI/ML规划内容，聚焦传统分析方法 | Tech Writer Agent |

---

**免责声明**: 本软件按"原样"提供，作者不对因使用本软件导致的任何损害负责。实验时必须遵守实验室安全规范，确保有人值守。

---

*CAUC-SEP 自旋电子器件实验平台 | 材料物理专业实验项目*  
*© 2025-2026 版权所有*
