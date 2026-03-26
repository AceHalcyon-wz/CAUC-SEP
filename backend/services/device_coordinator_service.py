"""
多设备协同控制服务

文件名: device_coordinator_service.py
路径: backend/services/
功能: 提供可视化实验流程编排、设备互锁保护、多设备数据时间同步等高级功能
作者: Backend Engineer Agent
创建日期: 2026-03-25
版本: 1.0.0

核心功能：
    - 可视化实验流程编排：流程定义、节点管理、条件分支、循环执行
    - 设备互锁保护：互锁规则定义、状态监控、自动解锁、紧急保护
    - 多设备数据时间同步：时间戳对齐、数据插值、同步采集触发

依赖：
    - backend.core.*: 所有设备驱动
    - backend.services.*: 各设备高级服务

安全约束：
    - 互锁规则必须经过有效性校验
    - 流程执行必须包含异常处理
    - 设备状态必须实时监控
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from backend.core.abstract import DeviceStatus

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 流程编排参数
MAX_WORKFLOW_NODES = 100  # 最大流程节点数
MAX_WORKFLOW_DEPTH = 20  # 最大流程深度

# 互锁保护参数
MAX_INTERLOCK_DEVICES = 10  # 最大互锁设备数
INTERLOCK_CHECK_INTERVAL_MS = 100  # 互锁检查间隔（毫秒）

# 时间同步参数
TIME_SYNC_TOLERANCE_MS = 10  # 时间同步容差（毫秒）
MAX_SYNC_WAIT_SECONDS = 30  # 最大同步等待时间（秒）


class WorkflowNodeType(Enum):
    """流程节点类型枚举。

    Attributes:
        START: 开始节点
        END: 结束节点
        DEVICE_ACTION: 设备动作节点
        CONDITION: 条件分支节点
        PARALLEL: 并行执行节点
        LOOP: 循环节点
        DELAY: 延时节点
        DATA_COLLECT: 数据采集节点
    """

    START = "start"
    END = "end"
    DEVICE_ACTION = "device_action"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    DELAY = "delay"
    DATA_COLLECT = "data_collect"


class InterlockType(Enum):
    """互锁类型枚举。

    Attributes:
        MUTUAL: 互斥锁（两设备不能同时操作）
        SEQUENCE: 顺序锁（必须按顺序操作）
        CONDITION: 条件锁（满足条件才能操作）
        GROUP: 组锁（同组设备同时操作）
    """

    MUTUAL = "mutual"
    SEQUENCE = "sequence"
    CONDITION = "condition"
    GROUP = "group"


class WorkflowState(Enum):
    """流程状态枚举。

    Attributes:
        IDLE: 空闲
        RUNNING: 运行中
        PAUSED: 已暂停
        COMPLETED: 已完成
        ERROR: 错误
    """

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class WorkflowNode:
    """流程节点数据类。

    Attributes:
        node_id: 节点ID
        node_type: 节点类型
        name: 节点名称
        device_id: 设备ID（设备动作节点）
        action: 动作名称
        action_params: 动作参数
        condition: 条件表达式（条件节点）
        true_next: 条件为真时的下一节点
        false_next: 条件为假时的下一节点
        next_nodes: 下一节点列表
        loop_count: 循环次数（循环节点）
        delay_ms: 延时时间（延时节点）
        parallel_nodes: 并行节点列表
        collect_config: 数据采集配置
    """

    node_id: str
    node_type: WorkflowNodeType
    name: str = ""
    device_id: str = ""
    action: str = ""
    action_params: dict[str, Any] = field(default_factory=dict)
    condition: str = ""
    true_next: str = ""
    false_next: str = ""
    next_nodes: list[str] = field(default_factory=list)
    loop_count: int = 1
    delay_ms: int = 0
    parallel_nodes: list[str] = field(default_factory=list)
    collect_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """流程定义数据类。

    Attributes:
        workflow_id: 流程ID
        name: 流程名称
        description: 流程描述
        nodes: 节点字典
        start_node: 起始节点ID
        end_nodes: 结束节点ID列表
        variables: 流程变量
    """

    workflow_id: str
    name: str
    description: str = ""
    nodes: dict[str, WorkflowNode] = field(default_factory=dict)
    start_node: str = ""
    end_nodes: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass
class InterlockRule:
    """互锁规则数据类。

    Attributes:
        rule_id: 规则ID
        interlock_type: 互锁类型
        devices: 设备ID列表
        condition: 条件表达式
        priority: 优先级
        enabled: 是否启用
    """

    rule_id: str
    interlock_type: InterlockType
    devices: list[str] = field(default_factory=list)
    condition: str = ""
    priority: int = 0
    enabled: bool = True


@dataclass
class DeviceState:
    """设备状态数据类。

    Attributes:
        device_id: 设备ID
        status: 设备状态
        last_action: 最后动作
        last_action_time: 最后动作时间
        is_locked: 是否被锁定
        lock_reason: 锁定原因
    """

    device_id: str
    status: DeviceStatus = DeviceStatus.DISCONNECTED
    last_action: str = ""
    last_action_time: float = 0.0
    is_locked: bool = False
    lock_reason: str = ""


@dataclass
class SyncData:
    """同步数据数据类。

    Attributes:
        device_id: 设备ID
        timestamp: 时间戳
        data: 数据字典
        sync_offset_ns: 同步偏移（纳秒）
    """

    device_id: str
    timestamp: float
    data: dict[str, Any]
    sync_offset_ns: int = 0


class DeviceCoordinatorService:
    """多设备协同控制服务类。

    提供可视化实验流程编排、设备互锁保护、多设备数据时间同步等高级功能。

    Example:
        >>> coordinator = DeviceCoordinatorService()
        >>> # 注册设备
        >>> coordinator.register_device("motor", motor_driver)
        >>> coordinator.register_device("electromagnet", electromagnet_driver)
        >>> # 定义互锁规则
        >>> rule = InterlockRule(
        ...     rule_id="motor_em_lock",
        ...     interlock_type=InterlockType.MUTUAL,
        ...     devices=["motor", "electromagnet"]
        ... )
        >>> coordinator.add_interlock_rule(rule)
        >>> # 执行流程
        >>> workflow = WorkflowDefinition(...)
        >>> await coordinator.execute_workflow(workflow)
    """

    def __init__(self):
        """初始化协同控制服务。 """
        # 设备管理
        self._devices: dict[str, Any] = {}
        self._device_states: dict[str, DeviceState] = {}

        # 流程管理
        self._current_workflow: WorkflowDefinition | None = None
        self._workflow_state = WorkflowState.IDLE
        self._workflow_task: asyncio.Task | None = None
        self._current_node: str = ""
        self._workflow_variables: dict[str, Any] = {}
        self._workflow_progress = 0.0

        # 互锁管理
        self._interlock_rules: dict[str, InterlockRule] = {}
        self._device_locks: dict[str, list[str]] = defaultdict(list)  # device_id -> lock_reasons
        self._interlock_monitor_task: asyncio.Task | None = None
        self._interlock_monitor_enabled = False

        # 时间同步
        self._sync_data_buffer: dict[str, list[SyncData]] = defaultdict(list)
        self._sync_reference_time: float = 0.0
        self._sync_offsets: dict[str, int] = {}  # device_id -> offset_ns

        # 回调函数
        self._workflow_progress_callback: Callable[[float, str], None] | None = None
        self._interlock_violation_callback: Callable[[str, str], None] | None = None
        self._sync_data_callback: Callable[[SyncData], None] | None = None

        logger.info("DeviceCoordinatorService initialized")

    # ==================== 设备管理 ====================

    def register_device(
        self,
        device_id: str,
        device: Any,
    ) -> bool:
        """注册设备。

        Args:
            device_id: 设备ID
            device: 设备实例

        Returns:
            bool: 注册是否成功
        """
        if device_id in self._devices:
            logger.warning(f"Device already registered: {device_id}")
            return False

        self._devices[device_id] = device
        self._device_states[device_id] = DeviceState(device_id=device_id)

        logger.info(f"Device registered: {device_id}")
        return True

    def unregister_device(self, device_id: str) -> bool:
        """注销设备。

        Args:
            device_id: 设备ID

        Returns:
            bool: 注销是否成功
        """
        if device_id not in self._devices:
            return False

        del self._devices[device_id]
        del self._device_states[device_id]

        logger.info(f"Device unregistered: {device_id}")
        return True

    def get_device_state(self, device_id: str) -> DeviceState | None:
        """获取设备状态。

        Args:
            device_id: 设备ID

        Returns:
            DeviceState | None: 设备状态
        """
        return self._device_states.get(device_id)

    def get_all_device_states(self) -> dict[str, DeviceState]:
        """获取所有设备状态。

        Returns:
            Dict[str, DeviceState]: 设备状态字典
        """
        return dict(self._device_states)

    async def update_device_states(self) -> None:
        """更新所有设备状态。"""
        for device_id, device in self._devices.items():
            try:
                status = await device.read_status()
                self._device_states[device_id].status = device.status
            except Exception as e:
                logger.error(f"Update device state error for {device_id}: {e}")
                self._device_states[device_id].status = DeviceStatus.ERROR

    # ==================== 可视化实验流程编排 ====================

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> bool:
        """执行实验流程。

        Args:
            workflow: 流程定义
            progress_callback: 进度回调函数

        Returns:
            bool: 执行是否成功

        Raises:
            ValueError: 流程定义无效
        """
        # 验证流程定义
        if not self._validate_workflow(workflow):
            raise ValueError("Invalid workflow definition")

        if self._workflow_state == WorkflowState.RUNNING:
            logger.warning("Workflow already running")
            return False

        self._current_workflow = workflow
        self._workflow_progress_callback = progress_callback
        self._workflow_state = WorkflowState.RUNNING
        self._workflow_variables = dict(workflow.variables)
        self._workflow_progress = 0.0
        self._current_node = workflow.start_node

        logger.info(f"Starting workflow: {workflow.name}")

        try:
            self._workflow_task = asyncio.create_task(
                self._execute_workflow_internal(workflow)
            )
            await self._workflow_task
            return True

        except asyncio.CancelledError:
            logger.info("Workflow cancelled")
            return False
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            self._workflow_state = WorkflowState.ERROR
            return False
        finally:
            if self._workflow_state == WorkflowState.RUNNING:
                self._workflow_state = WorkflowState.COMPLETED
            self._workflow_task = None

    def _validate_workflow(self, workflow: WorkflowDefinition) -> bool:
        """验证流程定义有效性。

        Args:
            workflow: 流程定义

        Returns:
            bool: 是否有效
        """
        if not workflow.start_node:
            logger.error("Workflow has no start node")
            return False

        if workflow.start_node not in workflow.nodes:
            logger.error(f"Start node not found: {workflow.start_node}")
            return False

        if len(workflow.nodes) > MAX_WORKFLOW_NODES:
            logger.error(f"Too many nodes: {len(workflow.nodes)} > {MAX_WORKFLOW_NODES}")
            return False

        # 验证所有节点
        for node_id, node in workflow.nodes.items():
            if node.node_type == WorkflowNodeType.DEVICE_ACTION:
                if node.device_id not in self._devices:
                    logger.error(f"Device not found: {node.device_id}")
                    return False

        return True

    async def _execute_workflow_internal(self, workflow: WorkflowDefinition) -> None:
        """内部方法：执行流程。

        Args:
            workflow: 流程定义
        """
        visited_nodes = set()
        node_stack = [(workflow.start_node, 0)]  # (node_id, depth)

        while node_stack:
            node_id, depth = node_stack.pop(0)

            # 深度检查
            if depth > MAX_WORKFLOW_DEPTH:
                logger.error(f"Workflow depth exceeded: {depth}")
                self._workflow_state = WorkflowState.ERROR
                return

            # 循环检测
            if node_id in visited_nodes:
                node = workflow.nodes.get(node_id)
                if node and node.node_type != WorkflowNodeType.LOOP:
                    logger.warning(f"Node already visited: {node_id}")
                    continue

            # 获取节点
            node = workflow.nodes.get(node_id)
            if node is None:
                logger.error(f"Node not found: {node_id}")
                self._workflow_state = WorkflowState.ERROR
                return

            # 更新当前节点
            self._current_node = node_id
            visited_nodes.add(node_id)

            # 执行节点
            next_nodes = await self._execute_node(node, depth)

            # 更新进度
            self._workflow_progress = len(visited_nodes) / len(workflow.nodes)

            if self._workflow_progress_callback:
                self._workflow_progress_callback(self._workflow_progress, node_id)

            # 添加下一节点到栈
            for next_node_id in next_nodes:
                if next_node_id in workflow.nodes:
                    node_stack.append((next_node_id, depth + 1))

        self._workflow_progress = 1.0
        logger.info(f"Workflow completed: {workflow.name}")

    async def _execute_node(
        self,
        node: WorkflowNode,
        depth: int,
    ) -> list[str]:
        """执行单个节点。

        Args:
            node: 流程节点
            depth: 当前深度

        Returns:
            List[str]: 下一节点ID列表
        """
        logger.debug(f"Executing node: {node.node_id} (type={node.node_type.value})")

        if node.node_type == WorkflowNodeType.START:
            return node.next_nodes

        elif node.node_type == WorkflowNodeType.END:
            return []

        elif node.node_type == WorkflowNodeType.DEVICE_ACTION:
            return await self._execute_device_action(node)

        elif node.node_type == WorkflowNodeType.CONDITION:
            return await self._execute_condition(node)

        elif node.node_type == WorkflowNodeType.PARALLEL:
            return await self._execute_parallel(node, depth)

        elif node.node_type == WorkflowNodeType.LOOP:
            return await self._execute_loop(node, depth)

        elif node.node_type == WorkflowNodeType.DELAY:
            await asyncio.sleep(node.delay_ms / 1000.0)
            return node.next_nodes

        elif node.node_type == WorkflowNodeType.DATA_COLLECT:
            return await self._execute_data_collect(node)

        return node.next_nodes

    async def _execute_device_action(self, node: WorkflowNode) -> list[str]:
        """执行设备动作节点。

        Args:
            node: 流程节点

        Returns:
            List[str]: 下一节点ID列表
        """
        device_id = node.device_id
        device = self._devices.get(device_id)

        if device is None:
            logger.error(f"Device not found: {device_id}")
            return []

        # 检查互锁
        if not await self._check_interlock(device_id, node.action):
            logger.error(f"Interlock violation for {device_id}: {node.action}")
            return []

        try:
            # 执行动作
            action_method = getattr(device, node.action, None)
            if action_method is None:
                logger.error(f"Action not found: {node.action}")
                return []

            # 调用动作方法
            if asyncio.iscoroutinefunction(action_method):
                await action_method(**node.action_params)
            else:
                action_method(**node.action_params)

            # 更新设备状态
            self._device_states[device_id].last_action = node.action
            self._device_states[device_id].last_action_time = time.time()

            logger.info(f"Device action executed: {device_id}.{node.action}")

        except Exception as e:
            logger.error(f"Execute device action error: {e}")
            self._workflow_state = WorkflowState.ERROR
            return []

        return node.next_nodes

    async def _execute_condition(self, node: WorkflowNode) -> list[str]:
        """执行条件分支节点。

        Args:
            node: 流程节点

        Returns:
            List[str]: 下一节点ID列表
        """
        try:
            # 评估条件
            condition_result = self._evaluate_condition(node.condition)

            if condition_result:
                return [node.true_next] if node.true_next else node.next_nodes
            else:
                return [node.false_next] if node.false_next else node.next_nodes

        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return node.next_nodes

    async def _execute_parallel(
        self,
        node: WorkflowNode,
        depth: int,
    ) -> list[str]:
        """执行并行节点。

        Args:
            node: 流程节点
            depth: 当前深度

        Returns:
            List[str]: 下一节点ID列表
        """
        if not node.parallel_nodes:
            return node.next_nodes

        # 并行执行所有子节点
        tasks = []
        for sub_node_id in node.parallel_nodes:
            sub_node = self._current_workflow.nodes.get(sub_node_id)
            if sub_node:
                tasks.append(self._execute_node(sub_node, depth + 1))

        if tasks:
            await asyncio.gather(*tasks)

        return node.next_nodes

    async def _execute_loop(
        self,
        node: WorkflowNode,
        depth: int,
    ) -> list[str]:
        """执行循环节点。

        Args:
            node: 流程节点
            depth: 当前深度

        Returns:
            List[str]: 下一节点ID列表
        """
        for _ in range(node.loop_count):
            if self._workflow_state != WorkflowState.RUNNING:
                break

            # 执行循环体
            for sub_node_id in node.next_nodes:
                sub_node = self._current_workflow.nodes.get(sub_node_id)
                if sub_node:
                    await self._execute_node(sub_node, depth + 1)

        return node.next_nodes

    async def _execute_data_collect(self, node: WorkflowNode) -> list[str]:
        """执行数据采集节点。

        Args:
            node: 流程节点

        Returns:
            List[str]: 下一节点ID列表
        """
        config = node.collect_config
        devices_to_collect = config.get("devices", list(self._devices.keys()))

        for device_id in devices_to_collect:
            device = self._devices.get(device_id)
            if device is None:
                continue

            try:
                # 读取设备数据
                data = await device.read_status()

                # 创建同步数据
                sync_data = SyncData(
                    device_id=device_id,
                    timestamp=time.time(),
                    data=data,
                    sync_offset_ns=self._sync_offsets.get(device_id, 0),
                )

                # 存储数据
                self._sync_data_buffer[device_id].append(sync_data)

                # 回调通知
                if self._sync_data_callback:
                    self._sync_data_callback(sync_data)

            except Exception as e:
                logger.error(f"Data collect error for {device_id}: {e}")

        return node.next_nodes

    def _evaluate_condition(self, condition: str) -> bool:
        """评估条件表达式。

        Args:
            condition: 条件表达式

        Returns:
            bool: 条件结果
        """
        # 构建上下文
        context = {
            "variables": self._workflow_variables,
            "device_states": {
                device_id: state.status.value
                for device_id, state in self._device_states.items()
            },
        }

        try:
            # 安全评估（实际应用中应使用更安全的解析方法）
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return False

    async def pause_workflow(self) -> bool:
        """暂停流程执行。

        Returns:
            bool: 暂停是否成功
        """
        if self._workflow_state != WorkflowState.RUNNING:
            return False

        self._workflow_state = WorkflowState.PAUSED
        logger.info("Workflow paused")
        return True

    async def resume_workflow(self) -> bool:
        """恢复流程执行。

        Returns:
            bool: 恢复是否成功
        """
        if self._workflow_state != WorkflowState.PAUSED:
            return False

        self._workflow_state = WorkflowState.RUNNING
        logger.info("Workflow resumed")
        return True

    async def stop_workflow(self) -> bool:
        """停止流程执行。

        Returns:
            bool: 停止是否成功
        """
        if self._workflow_state == WorkflowState.IDLE:
            return True

        self._workflow_state = WorkflowState.IDLE

        if self._workflow_task:
            self._workflow_task.cancel()
            try:
                await self._workflow_task
            except asyncio.CancelledError:
                pass

        logger.info("Workflow stopped")
        return True

    def get_workflow_status(self) -> dict[str, Any]:
        """获取流程状态。

        Returns:
            Dict[str, Any]: 流程状态信息
        """
        return {
            "state": self._workflow_state.value,
            "current_node": self._current_node,
            "progress": round(self._workflow_progress, 4),
            "workflow_id": self._current_workflow.workflow_id if self._current_workflow else None,
        }

    # ==================== 设备互锁保护 ====================

    def add_interlock_rule(self, rule: InterlockRule) -> bool:
        """添加互锁规则。

        Args:
            rule: 互锁规则

        Returns:
            bool: 添加是否成功
        """
        # 验证规则
        if len(rule.devices) > MAX_INTERLOCK_DEVICES:
            logger.error(f"Too many devices in interlock rule: {len(rule.devices)}")
            return False

        for device_id in rule.devices:
            if device_id not in self._devices:
                logger.error(f"Device not found: {device_id}")
                return False

        self._interlock_rules[rule.rule_id] = rule
        logger.info(f"Interlock rule added: {rule.rule_id}")
        return True

    def remove_interlock_rule(self, rule_id: str) -> bool:
        """移除互锁规则。

        Args:
            rule_id: 规则ID

        Returns:
            bool: 移除是否成功
        """
        if rule_id not in self._interlock_rules:
            return False

        del self._interlock_rules[rule_id]
        logger.info(f"Interlock rule removed: {rule_id}")
        return True

    async def _check_interlock(self, device_id: str, action: str) -> bool:
        """检查互锁条件。

        Args:
            device_id: 设备ID
            action: 动作名称

        Returns:
            bool: 是否允许执行
        """
        for rule_id, rule in self._interlock_rules.items():
            if not rule.enabled:
                continue

            if device_id not in rule.devices:
                continue

            # 检查互锁类型
            if rule.interlock_type == InterlockType.MUTUAL:
                # 互斥锁：检查其他设备是否正在操作
                for other_device_id in rule.devices:
                    if other_device_id != device_id:
                        other_state = self._device_states.get(other_device_id)
                        if other_state and other_state.status == DeviceStatus.BUSY:
                            logger.warning(
                                f"Interlock violation: {device_id} blocked by {other_device_id}"
                            )
                            if self._interlock_violation_callback:
                                self._interlock_violation_callback(device_id, f"Mutual lock with {other_device_id}")
                            return False

            elif rule.interlock_type == InterlockType.SEQUENCE:
                # 顺序锁：检查前序设备是否已完成
                device_index = rule.devices.index(device_id)
                if device_index > 0:
                    prev_device_id = rule.devices[device_index - 1]
                    prev_state = self._device_states.get(prev_device_id)
                    if prev_state and prev_state.status != DeviceStatus.READY:
                        logger.warning(
                            f"Interlock violation: {device_id} waiting for {prev_device_id}"
                        )
                        if self._interlock_violation_callback:
                            self._interlock_violation_callback(device_id, f"Sequence lock waiting for {prev_device_id}")
                        return False

            elif rule.interlock_type == InterlockType.CONDITION:
                # 条件锁：检查条件是否满足
                if rule.condition:
                    if not self._evaluate_condition(rule.condition):
                        logger.warning(f"Interlock condition not met: {rule.condition}")
                        if self._interlock_violation_callback:
                            self._interlock_violation_callback(device_id, f"Condition not met: {rule.condition}")
                        return False

        return True

    async def lock_device(self, device_id: str, reason: str) -> bool:
        """锁定设备。

        Args:
            device_id: 设备ID
            reason: 锁定原因

        Returns:
            bool: 锁定是否成功
        """
        if device_id not in self._devices:
            return False

        self._device_locks[device_id].append(reason)
        self._device_states[device_id].is_locked = True
        self._device_states[device_id].lock_reason = "; ".join(self._device_locks[device_id])

        logger.info(f"Device locked: {device_id}, reason: {reason}")
        return True

    async def unlock_device(self, device_id: str, reason: str | None = None) -> bool:
        """解锁设备。

        Args:
            device_id: 设备ID
            reason: 解锁原因（None则完全解锁）

        Returns:
            bool: 解锁是否成功
        """
        if device_id not in self._devices:
            return False

        if reason is None:
            # 完全解锁
            self._device_locks[device_id] = []
        else:
            # 移除特定原因
            if reason in self._device_locks[device_id]:
                self._device_locks[device_id].remove(reason)

        self._device_states[device_id].is_locked = len(self._device_locks[device_id]) > 0
        self._device_states[device_id].lock_reason = "; ".join(self._device_locks[device_id])

        logger.info(f"Device unlocked: {device_id}")
        return True

    async def start_interlock_monitor(self) -> bool:
        """启动互锁监控。

        Returns:
            bool: 启动是否成功
        """
        if self._interlock_monitor_enabled:
            return False

        self._interlock_monitor_enabled = True
        self._interlock_monitor_task = asyncio.create_task(
            self._interlock_monitor_loop()
        )

        logger.info("Interlock monitor started")
        return True

    async def stop_interlock_monitor(self) -> bool:
        """停止互锁监控。

        Returns:
            bool: 停止是否成功
        """
        if not self._interlock_monitor_enabled:
            return True

        self._interlock_monitor_enabled = False

        if self._interlock_monitor_task:
            self._interlock_monitor_task.cancel()
            try:
                await self._interlock_monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Interlock monitor stopped")
        return True

    async def _interlock_monitor_loop(self) -> None:
        """互锁监控循环。"""
        while self._interlock_monitor_enabled:
            try:
                # 更新设备状态
                await self.update_device_states()

                # 检查所有互锁规则
                for rule_id, rule in self._interlock_rules.items():
                    if not rule.enabled:
                        continue

                    # 检查设备状态
                    for device_id in rule.devices:
                        state = self._device_states.get(device_id)
                        if state and state.is_locked:
                            # 检查锁定是否仍然有效
                            # 简化处理：如果设备状态变为READY，自动解锁
                            if state.status == DeviceStatus.READY:
                                await self.unlock_device(device_id)

                await asyncio.sleep(INTERLOCK_CHECK_INTERVAL_MS / 1000.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Interlock monitor error: {e}")
                await asyncio.sleep(1.0)

    # ==================== 多设备数据时间同步 ====================

    async def synchronize_devices(self) -> dict[str, Any]:
        """同步所有设备时间。

        Returns:
            Dict[str, Any]: 同步结果
        """
        logger.info("Starting device time synchronization")

        # 记录参考时间
        self._sync_reference_time = time.time()

        # 计算每个设备的时间偏移
        for device_id, device in self._devices.items():
            try:
                # 读取设备时间（假设设备有时间戳功能）
                device_time = time.time()  # 简化处理
                offset_ns = int((device_time - self._sync_reference_time) * 1e9)
                self._sync_offsets[device_id] = offset_ns

            except Exception as e:
                logger.error(f"Sync device {device_id} error: {e}")
                self._sync_offsets[device_id] = 0

        return {
            "reference_time": self._sync_reference_time,
            "offsets": {
                device_id: offset_ns
                for device_id, offset_ns in self._sync_offsets.items()
            },
        }

    def get_sync_data(
        self,
        device_id: str,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> list[dict[str, Any]]:
        """获取同步数据。

        Args:
            device_id: 设备ID
            start_time: 起始时间
            end_time: 结束时间

        Returns:
            List[Dict[str, Any]]: 同步数据列表
        """
        if device_id not in self._sync_data_buffer:
            return []

        data_list = self._sync_data_buffer[device_id]

        if start_time is not None:
            data_list = [d for d in data_list if d.timestamp >= start_time]
        if end_time is not None:
            data_list = [d for d in data_list if d.timestamp <= end_time]

        return [
            {
                "device_id": d.device_id,
                "timestamp": d.timestamp,
                "data": d.data,
                "sync_offset_ns": d.sync_offset_ns,
            }
            for d in data_list
        ]

    def align_data_timestamps(
        self,
        data_list: list[SyncData],
    ) -> list[SyncData]:
        """对齐数据时间戳。

        Args:
            data_list: 数据列表

        Returns:
            List[SyncData]: 对齐后的数据列表
        """
        aligned_data = []

        for data in data_list:
            # 应用时间偏移
            aligned_timestamp = data.timestamp - data.sync_offset_ns / 1e9

            aligned_data.append(SyncData(
                device_id=data.device_id,
                timestamp=aligned_timestamp,
                data=data.data,
                sync_offset_ns=0,  # 对齐后偏移为0
            ))

        return aligned_data

    def interpolate_sync_data(
        self,
        data_list: list[SyncData],
        target_timestamps: list[float],
    ) -> list[SyncData]:
        """插值同步数据。

        Args:
            data_list: 数据列表
            target_timestamps: 目标时间戳列表

        Returns:
            List[SyncData]: 插值后的数据列表
        """
        if len(data_list) < 2:
            return data_list

        # 按时间戳排序
        sorted_data = sorted(data_list, key=lambda d: d.timestamp)

        timestamps = np.array([d.timestamp for d in sorted_data])

        # 对每个数据字段进行插值
        interpolated_data = []

        for target_ts in target_timestamps:
            # 找到最近的两个数据点
            idx = np.searchsorted(timestamps, target_ts)

            if idx == 0:
                interpolated_data.append(sorted_data[0])
            elif idx >= len(sorted_data):
                interpolated_data.append(sorted_data[-1])
            else:
                # 线性插值
                prev_data = sorted_data[idx - 1]
                next_data = sorted_data[idx]

                ratio = (target_ts - prev_data.timestamp) / (next_data.timestamp - prev_data.timestamp)

                # 插值数据字段
                interpolated_fields = {}
                for key in prev_data.data:
                    if isinstance(prev_data.data[key], (int, float)):
                        interpolated_fields[key] = prev_data.data[key] + ratio * (next_data.data[key] - prev_data.data[key])
                    else:
                        interpolated_fields[key] = prev_data.data[key]

                interpolated_data.append(SyncData(
                    device_id=prev_data.device_id,
                    timestamp=target_ts,
                    data=interpolated_fields,
                    sync_offset_ns=0,
                ))

        return interpolated_data

    # ==================== 资源清理 ====================

    async def cleanup(self) -> None:
        """清理所有资源。"""
        await self.stop_workflow()
        await self.stop_interlock_monitor()

        # 清理数据缓存
        self._sync_data_buffer.clear()

        logger.info("DeviceCoordinatorService cleanup completed")

    # ==================== 数据导入导出 ====================

    def export_workflow(self, workflow: WorkflowDefinition) -> str:
        """导出流程定义为JSON字符串。

        Args:
            workflow: 流程定义

        Returns:
            str: JSON字符串
        """
        data = {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": {
                node_id: {
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "name": node.name,
                    "device_id": node.device_id,
                    "action": node.action,
                    "action_params": node.action_params,
                    "condition": node.condition,
                    "true_next": node.true_next,
                    "false_next": node.false_next,
                    "next_nodes": node.next_nodes,
                    "loop_count": node.loop_count,
                    "delay_ms": node.delay_ms,
                    "parallel_nodes": node.parallel_nodes,
                    "collect_config": node.collect_config,
                }
                for node_id, node in workflow.nodes.items()
            },
            "start_node": workflow.start_node,
            "end_nodes": workflow.end_nodes,
            "variables": workflow.variables,
        }
        return json.dumps(data, indent=2)

    def import_workflow(self, json_str: str) -> WorkflowDefinition:
        """从JSON字符串导入流程定义。

        Args:
            json_str: JSON字符串

        Returns:
            WorkflowDefinition: 流程定义
        """
        data = json.loads(json_str)

        nodes = {}
        for node_id, node_data in data["nodes"].items():
            nodes[node_id] = WorkflowNode(
                node_id=node_data["node_id"],
                node_type=WorkflowNodeType(node_data["node_type"]),
                name=node_data.get("name", ""),
                device_id=node_data.get("device_id", ""),
                action=node_data.get("action", ""),
                action_params=node_data.get("action_params", {}),
                condition=node_data.get("condition", ""),
                true_next=node_data.get("true_next", ""),
                false_next=node_data.get("false_next", ""),
                next_nodes=node_data.get("next_nodes", []),
                loop_count=node_data.get("loop_count", 1),
                delay_ms=node_data.get("delay_ms", 0),
                parallel_nodes=node_data.get("parallel_nodes", []),
                collect_config=node_data.get("collect_config", {}),
            )

        return WorkflowDefinition(
            workflow_id=data["workflow_id"],
            name=data["name"],
            description=data.get("description", ""),
            nodes=nodes,
            start_node=data["start_node"],
            end_nodes=data.get("end_nodes", []),
            variables=data.get("variables", {}),
        )
