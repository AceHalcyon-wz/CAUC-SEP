"""
实验全生命周期管理服务

文件名: experiment_lifecycle_service.py
路径: backend/services/
功能: 提供实验元数据管理、实验流程模板管理、多格式数据导出、实验报告自动生成等高级功能
作者: Backend Engineer Agent
创建日期: 2026-03-25
版本: 1.0.0

核心功能：
    - 实验元数据管理：实验创建、参数记录、状态跟踪、版本控制
    - 实验流程模板管理：模板定义、模板复用、参数化配置
    - 多格式数据导出：CSV、JSON、HDF5、MATLAB格式导出
    - 实验报告自动生成：模板化报告、图表生成、统计分析

依赖：
    - backend.services.device_coordinator_service: 设备协同服务
    - backend.services.data_analysis_service: 数据分析服务

安全约束：
    - 实验数据必须定期备份
    - 敏感信息必须脱敏处理
    - 报告生成必须验证数据完整性
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import numpy as np

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 实验管理参数
MAX_EXPERIMENTS = 1000  # 最大实验数量
MAX_DATA_SIZE_MB = 1000  # 最大数据大小（MB）
MAX_TEMPLATES = 100  # 最大模板数量

# 数据导出参数
EXPORT_DIR = Path("data/exports")
TEMPLATE_DIR = Path("data/templates")
REPORT_DIR = Path("data/reports")

# 报告生成参数
REPORT_TEMPLATE_DIR = Path("data/report_templates")


class ExperimentStatus(Enum):
    """实验状态枚举。

    Attributes:
        CREATED: 已创建
        RUNNING: 运行中
        PAUSED: 已暂停
        COMPLETED: 已完成
        FAILED: 失败
        ARCHIVED: 已归档
    """

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class ExportFormat(Enum):
    """导出格式枚举。

    Attributes:
        CSV: CSV格式
        JSON: JSON格式
        HDF5: HDF5格式
        MATLAB: MATLAB格式
        EXCEL: Excel格式
    """

    CSV = "csv"
    JSON = "json"
    HDF5 = "hdf5"
    MATLAB = "mat"
    EXCEL = "xlsx"


class ReportType(Enum):
    """报告类型枚举。

    Attributes:
        SUMMARY: 摘要报告
        DETAILED: 详细报告
        COMPARISON: 对比报告
        STATISTICAL: 统计报告
    """

    SUMMARY = "summary"
    DETAILED = "detailed"
    COMPARISON = "comparison"
    STATISTICAL = "statistical"


@dataclass
class ExperimentMetadata:
    """实验元数据数据类。

    Attributes:
        experiment_id: 实验ID
        name: 实验名称
        description: 实验描述
        status: 实验状态
        created_at: 创建时间
        updated_at: 更新时间
        started_at: 开始时间
        completed_at: 完成时间
        operator: 操作员
        sample_info: 样品信息
        parameters: 实验参数
        devices: 设备列表
        tags: 标签列表
        notes: 备注
        version: 版本号
    """

    experiment_id: str
    name: str
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.CREATED
    created_at: float = 0.0
    updated_at: float = 0.0
    started_at: float | None = None
    completed_at: float | None = None
    operator: str = ""
    sample_info: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    devices: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "operator": self.operator,
            "sample_info": self.sample_info,
            "parameters": self.parameters,
            "devices": self.devices,
            "tags": self.tags,
            "notes": self.notes,
            "version": self.version,
        }


@dataclass
class ExperimentData:
    """实验数据数据类。

    Attributes:
        experiment_id: 实验ID
        data_id: 数据ID
        device_id: 设备ID
        data_type: 数据类型
        timestamp: 时间戳
        values: 数据值
        metadata: 数据元数据
    """

    experiment_id: str
    data_id: str
    device_id: str
    data_type: str
    timestamp: float
    values: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentTemplate:
    """实验模板数据类。

    Attributes:
        template_id: 模板ID
        name: 模板名称
        description: 模板描述
        category: 模板分类
        parameters: 参数定义
        workflow: 流程定义
        devices: 设备配置
        created_at: 创建时间
        updated_at: 更新时间
    """

    template_id: str
    name: str
    description: str = ""
    category: str = "general"
    parameters: dict[str, Any] = field(default_factory=dict)
    workflow: dict[str, Any] = field(default_factory=dict)
    devices: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class ExportConfig:
    """导出配置数据类。

    Attributes:
        format: 导出格式
        include_metadata: 是否包含元数据
        include_raw_data: 是否包含原始数据
        include_analysis: 是否包含分析结果
        compress: 是否压缩
        file_prefix: 文件前缀
    """

    format: ExportFormat = ExportFormat.CSV
    include_metadata: bool = True
    include_raw_data: bool = True
    include_analysis: bool = True
    compress: bool = False
    file_prefix: str = ""


@dataclass
class ReportConfig:
    """报告配置数据类。

    Attributes:
        report_type: 报告类型
        template_name: 模板名称
        include_charts: 是否包含图表
        include_statistics: 是否包含统计
        include_raw_data: 是否包含原始数据
        language: 报告语言
        format: 输出格式
    """

    report_type: ReportType = ReportType.SUMMARY
    template_name: str = "default"
    include_charts: bool = True
    include_statistics: bool = True
    include_raw_data: bool = False
    language: str = "zh-CN"
    format: str = "markdown"


class ExperimentLifecycleService:
    """实验全生命周期管理服务类。

    提供实验元数据管理、实验流程模板管理、多格式数据导出、实验报告自动生成等高级功能。

    Example:
        >>> service = ExperimentLifecycleService()
        >>> # 创建实验
        >>> experiment = await service.create_experiment(
        ...     name="磁滞回线测量",
        ...     parameters={"field_range": [-1, 1], "step": 0.01}
        ... )
        >>> # 导出数据
        >>> await service.export_data(experiment.experiment_id, ExportConfig(format=ExportFormat.CSV))
        >>> # 生成报告
        >>> await service.generate_report(experiment.experiment_id, ReportConfig())
    """

    def __init__(self):
        """初始化实验生命周期管理服务。 """
        # 实验存储
        self._experiments: dict[str, ExperimentMetadata] = {}
        self._experiment_data: dict[str, list[ExperimentData]] = {}

        # 模板存储
        self._templates: dict[str, ExperimentTemplate] = {}

        # 当前实验
        self._current_experiment: ExperimentMetadata | None = None

        # 数据缓存
        self._data_cache: dict[str, Any] = {}

        # 确保目录存在
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

        # 加载模板
        self._load_templates()

        logger.info("ExperimentLifecycleService initialized")

    # ==================== 实验元数据管理 ====================

    async def create_experiment(
        self,
        name: str,
        description: str = "",
        operator: str = "",
        sample_info: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
        devices: list[str] | None = None,
        tags: list[str] | None = None,
        template_id: str | None = None,
    ) -> ExperimentMetadata:
        """创建新实验。

        Args:
            name: 实验名称
            description: 实验描述
            operator: 操作员
            sample_info: 样品信息
            parameters: 实验参数
            devices: 设备列表
            tags: 标签列表
            template_id: 模板ID

        Returns:
            ExperimentMetadata: 实验元数据

        Raises:
            ValueError: 参数无效
        """
        if len(self._experiments) >= MAX_EXPERIMENTS:
            raise ValueError(f"Maximum experiments reached: {MAX_EXPERIMENTS}")

        # 生成实验ID
        experiment_id = f"exp_{int(time.time() * 1000)}"

        # 从模板加载参数
        if template_id and template_id in self._templates:
            template = self._templates[template_id]
            if parameters is None:
                parameters = {}
            parameters.update(template.parameters)
            if devices is None:
                devices = [d.get("device_id") for d in template.devices if d.get("device_id")]

        # 创建实验元数据
        current_time = time.time()
        experiment = ExperimentMetadata(
            experiment_id=experiment_id,
            name=name,
            description=description,
            status=ExperimentStatus.CREATED,
            created_at=current_time,
            updated_at=current_time,
            operator=operator,
            sample_info=sample_info or {},
            parameters=parameters or {},
            devices=devices or [],
            tags=tags or [],
        )

        # 存储实验
        self._experiments[experiment_id] = experiment
        self._experiment_data[experiment_id] = []

        logger.info(f"Experiment created: {experiment_id}, name={name}")
        return experiment

    async def start_experiment(self, experiment_id: str) -> bool:
        """启动实验。

        Args:
            experiment_id: 实验ID

        Returns:
            bool: 启动是否成功
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            logger.error(f"Experiment not found: {experiment_id}")
            return False

        if experiment.status != ExperimentStatus.CREATED:
            logger.error(f"Experiment not in CREATED status: {experiment.status.value}")
            return False

        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = time.time()
        experiment.updated_at = time.time()

        self._current_experiment = experiment

        logger.info(f"Experiment started: {experiment_id}")
        return True

    async def pause_experiment(self, experiment_id: str) -> bool:
        """暂停实验。

        Args:
            experiment_id: 实验ID

        Returns:
            bool: 暂停是否成功
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return False

        if experiment.status != ExperimentStatus.RUNNING:
            return False

        experiment.status = ExperimentStatus.PAUSED
        experiment.updated_at = time.time()

        logger.info(f"Experiment paused: {experiment_id}")
        return True

    async def resume_experiment(self, experiment_id: str) -> bool:
        """恢复实验。

        Args:
            experiment_id: 实验ID

        Returns:
            bool: 恢复是否成功
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return False

        if experiment.status != ExperimentStatus.PAUSED:
            return False

        experiment.status = ExperimentStatus.RUNNING
        experiment.updated_at = time.time()

        logger.info(f"Experiment resumed: {experiment_id}")
        return True

    async def complete_experiment(
        self,
        experiment_id: str,
        notes: str = "",
    ) -> bool:
        """完成实验。

        Args:
            experiment_id: 实验ID
            notes: 完成备注

        Returns:
            bool: 完成是否成功
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return False

        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = time.time()
        experiment.updated_at = time.time()
        if notes:
            experiment.notes = notes

        if self._current_experiment and self._current_experiment.experiment_id == experiment_id:
            self._current_experiment = None

        logger.info(f"Experiment completed: {experiment_id}")
        return True

    async def fail_experiment(
        self,
        experiment_id: str,
        error_message: str,
    ) -> bool:
        """标记实验失败。

        Args:
            experiment_id: 实验ID
            error_message: 错误信息

        Returns:
            bool: 标记是否成功
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return False

        experiment.status = ExperimentStatus.FAILED
        experiment.updated_at = time.time()
        experiment.notes = f"Error: {error_message}"

        if self._current_experiment and self._current_experiment.experiment_id == experiment_id:
            self._current_experiment = None

        logger.error(f"Experiment failed: {experiment_id}, error: {error_message}")
        return True

    async def archive_experiment(self, experiment_id: str) -> bool:
        """归档实验。

        Args:
            experiment_id: 实验ID

        Returns:
            bool: 归档是否成功
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return False

        experiment.status = ExperimentStatus.ARCHIVED
        experiment.updated_at = time.time()

        logger.info(f"Experiment archived: {experiment_id}")
        return True

    async def record_data(
        self,
        experiment_id: str,
        device_id: str,
        data_type: str,
        values: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """记录实验数据。

        Args:
            experiment_id: 实验ID
            device_id: 设备ID
            data_type: 数据类型
            values: 数据值
            metadata: 数据元数据

        Returns:
            str: 数据ID
        """
        if experiment_id not in self._experiment_data:
            logger.error(f"Experiment not found: {experiment_id}")
            return ""

        data_id = f"data_{int(time.time() * 1000)}"

        data = ExperimentData(
            experiment_id=experiment_id,
            data_id=data_id,
            device_id=device_id,
            data_type=data_type,
            timestamp=time.time(),
            values=values,
            metadata=metadata or {},
        )

        self._experiment_data[experiment_id].append(data)

        # 更新实验元数据
        experiment = self._experiments.get(experiment_id)
        if experiment:
            experiment.updated_at = time.time()

        return data_id

    def get_experiment(self, experiment_id: str) -> ExperimentMetadata | None:
        """获取实验元数据。

        Args:
            experiment_id: 实验ID

        Returns:
            ExperimentMetadata | None: 实验元数据
        """
        return self._experiments.get(experiment_id)

    def get_experiment_data(
        self,
        experiment_id: str,
        device_id: str | None = None,
        data_type: str | None = None,
    ) -> list[ExperimentData]:
        """获取实验数据。

        Args:
            experiment_id: 实验ID
            device_id: 设备ID（可选）
            data_type: 数据类型（可选）

        Returns:
            List[ExperimentData]: 数据列表
        """
        data_list = self._experiment_data.get(experiment_id, [])

        if device_id:
            data_list = [d for d in data_list if d.device_id == device_id]
        if data_type:
            data_list = [d for d in data_list if d.data_type == data_type]

        return data_list

    def list_experiments(
        self,
        status: ExperimentStatus | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> list[ExperimentMetadata]:
        """列出实验。

        Args:
            status: 状态过滤
            tags: 标签过滤
            limit: 返回数量限制

        Returns:
            List[ExperimentMetadata]: 实验列表
        """
        experiments = list(self._experiments.values())

        if status:
            experiments = [e for e in experiments if e.status == status]

        if tags:
            experiments = [e for e in experiments if any(t in e.tags for t in tags)]

        # 按创建时间排序
        experiments.sort(key=lambda e: e.created_at, reverse=True)

        return experiments[:limit]

    # ==================== 实验流程模板管理 ====================

    def _load_templates(self) -> None:
        """加载模板文件。"""
        if not TEMPLATE_DIR.exists():
            return

        for template_file in TEMPLATE_DIR.glob("*.json"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                template = ExperimentTemplate(
                    template_id=data["template_id"],
                    name=data["name"],
                    description=data.get("description", ""),
                    category=data.get("category", "general"),
                    parameters=data.get("parameters", {}),
                    workflow=data.get("workflow", {}),
                    devices=data.get("devices", []),
                    created_at=data.get("created_at", 0.0),
                    updated_at=data.get("updated_at", 0.0),
                )

                self._templates[template.template_id] = template
                logger.debug(f"Template loaded: {template.template_id}")

            except Exception as e:
                logger.error(f"Load template error: {template_file}, {e}")

    def create_template(
        self,
        name: str,
        description: str = "",
        category: str = "general",
        parameters: dict[str, Any] | None = None,
        workflow: dict[str, Any] | None = None,
        devices: list[dict[str, Any]] | None = None,
    ) -> ExperimentTemplate:
        """创建实验模板。

        Args:
            name: 模板名称
            description: 模板描述
            category: 模板分类
            parameters: 参数定义
            workflow: 流程定义
            devices: 设备配置

        Returns:
            ExperimentTemplate: 实验模板

        Raises:
            ValueError: 模板数量超限
        """
        if len(self._templates) >= MAX_TEMPLATES:
            raise ValueError(f"Maximum templates reached: {MAX_TEMPLATES}")

        template_id = f"tpl_{int(time.time() * 1000)}"
        current_time = time.time()

        template = ExperimentTemplate(
            template_id=template_id,
            name=name,
            description=description,
            category=category,
            parameters=parameters or {},
            workflow=workflow or {},
            devices=devices or [],
            created_at=current_time,
            updated_at=current_time,
        )

        self._templates[template_id] = template

        # 保存到文件
        self._save_template(template)

        logger.info(f"Template created: {template_id}, name={name}")
        return template

    def _save_template(self, template: ExperimentTemplate) -> bool:
        """保存模板到文件。

        Args:
            template: 实验模板

        Returns:
            bool: 保存是否成功
        """
        try:
            template_file = TEMPLATE_DIR / f"{template.template_id}.json"

            data = {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "parameters": template.parameters,
                "workflow": template.workflow,
                "devices": template.devices,
                "created_at": template.created_at,
                "updated_at": template.updated_at,
            }

            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            logger.error(f"Save template error: {e}")
            return False

    def get_template(self, template_id: str) -> ExperimentTemplate | None:
        """获取模板。

        Args:
            template_id: 模板ID

        Returns:
            ExperimentTemplate | None: 实验模板
        """
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: str | None = None,
    ) -> list[ExperimentTemplate]:
        """列出模板。

        Args:
            category: 分类过滤

        Returns:
            List[ExperimentTemplate]: 模板列表
        """
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        templates.sort(key=lambda t: t.created_at, reverse=True)
        return templates

    def update_template(
        self,
        template_id: str,
        **kwargs: Any,
    ) -> bool:
        """更新模板。

        Args:
            template_id: 模板ID
            **kwargs: 更新字段

        Returns:
            bool: 更新是否成功
        """
        template = self._templates.get(template_id)
        if template is None:
            return False

        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)

        template.updated_at = time.time()
        self._save_template(template)

        logger.info(f"Template updated: {template_id}")
        return True

    def delete_template(self, template_id: str) -> bool:
        """删除模板。

        Args:
            template_id: 模板ID

        Returns:
            bool: 删除是否成功
        """
        if template_id not in self._templates:
            return False

        del self._templates[template_id]

        # 删除文件
        template_file = TEMPLATE_DIR / f"{template_id}.json"
        if template_file.exists():
            template_file.unlink()

        logger.info(f"Template deleted: {template_id}")
        return True

    # ==================== 多格式数据导出 ====================

    async def export_data(
        self,
        experiment_id: str,
        config: ExportConfig,
    ) -> str:
        """导出实验数据。

        Args:
            experiment_id: 实验ID
            config: 导出配置

        Returns:
            str: 导出文件路径

        Raises:
            ValueError: 实验不存在
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError(f"Experiment not found: {experiment_id}")

        data_list = self._experiment_data.get(experiment_id, [])

        # 生成文件名
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_prefix = config.file_prefix or experiment_id
        filename = f"{file_prefix}_{timestamp_str}"

        # 根据格式导出
        if config.format == ExportFormat.CSV:
            return await self._export_csv(experiment, data_list, filename, config)
        elif config.format == ExportFormat.JSON:
            return await self._export_json(experiment, data_list, filename, config)
        elif config.format == ExportFormat.HDF5:
            return await self._export_hdf5(experiment, data_list, filename, config)
        elif config.format == ExportFormat.MATLAB:
            return await self._export_matlab(experiment, data_list, filename, config)
        elif config.format == ExportFormat.EXCEL:
            return await self._export_excel(experiment, data_list, filename, config)
        else:
            raise ValueError(f"Unsupported export format: {config.format}")

    async def _export_csv(
        self,
        experiment: ExperimentMetadata,
        data_list: list[ExperimentData],
        filename: str,
        config: ExportConfig,
    ) -> str:
        """导出CSV格式。

        Args:
            experiment: 实验元数据
            data_list: 数据列表
            filename: 文件名
            config: 导出配置

        Returns:
            str: 文件路径
        """
        file_path = EXPORT_DIR / f"{filename}.csv"

        lines = []

        # 写入元数据
        if config.include_metadata:
            lines.append(f"# Experiment: {experiment.name}")
            lines.append(f"# ID: {experiment.experiment_id}")
            lines.append(f"# Created: {datetime.fromtimestamp(experiment.created_at).isoformat()}")
            lines.append(f"# Operator: {experiment.operator}")
            lines.append(f"# Parameters: {json.dumps(experiment.parameters)}")
            lines.append("#")

        # 写入数据头
        if data_list:
            headers = ["timestamp", "device_id", "data_type"]
            # 收集所有数据字段
            all_keys = set()
            for data in data_list:
                all_keys.update(data.values.keys())
            headers.extend(sorted(all_keys))
            lines.append(",".join(headers))

            # 写入数据
            for data in data_list:
                row = [
                    str(data.timestamp),
                    data.device_id,
                    data.data_type,
                ]
                for key in sorted(all_keys):
                    value = data.values.get(key, "")
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                    row.append(str(value))
                lines.append(",".join(row))

        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Data exported to CSV: {file_path}")
        return str(file_path)

    async def _export_json(
        self,
        experiment: ExperimentMetadata,
        data_list: list[ExperimentData],
        filename: str,
        config: ExportConfig,
    ) -> str:
        """导出JSON格式。

        Args:
            experiment: 实验元数据
            data_list: 数据列表
            filename: 文件名
            config: 导出配置

        Returns:
            str: 文件路径
        """
        file_path = EXPORT_DIR / f"{filename}.json"

        export_data = {
            "experiment": experiment.to_dict() if config.include_metadata else None,
            "data": [
                {
                    "data_id": d.data_id,
                    "device_id": d.device_id,
                    "data_type": d.data_type,
                    "timestamp": d.timestamp,
                    "values": d.values,
                    "metadata": d.metadata,
                }
                for d in data_list
            ] if config.include_raw_data else [],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Data exported to JSON: {file_path}")
        return str(file_path)

    async def _export_hdf5(
        self,
        experiment: ExperimentMetadata,
        data_list: list[ExperimentData],
        filename: str,
        config: ExportConfig,
    ) -> str:
        """导出HDF5格式。

        Args:
            experiment: 实验元数据
            data_list: 数据列表
            filename: 文件名
            config: 导出配置

        Returns:
            str: 文件路径
        """
        try:
            import h5py
        except ImportError:
            logger.error("h5py not installed, falling back to JSON")
            return await self._export_json(experiment, data_list, filename, config)

        file_path = EXPORT_DIR / f"{filename}.h5"

        with h5py.File(file_path, "w") as f:
            # 写入元数据
            if config.include_metadata:
                meta_group = f.create_group("metadata")
                meta_group.attrs["experiment_id"] = experiment.experiment_id
                meta_group.attrs["name"] = experiment.name
                meta_group.attrs["operator"] = experiment.operator
                meta_group.attrs["created_at"] = experiment.created_at

            # 写入数据
            if config.include_raw_data and data_list:
                data_group = f.create_group("data")

                # 按设备分组
                device_data: dict[str, list[ExperimentData]] = {}
                for data in data_list:
                    if data.device_id not in device_data:
                        device_data[data.device_id] = []
                    device_data[data.device_id].append(data)

                for device_id, device_data_list in device_data.items():
                    device_group = data_group.create_group(device_id)

                    timestamps = np.array([d.timestamp for d in device_data_list])
                    device_group.create_dataset("timestamps", data=timestamps)

                    # 写入数据字段
                    all_keys = set()
                    for data in device_data_list:
                        all_keys.update(data.values.keys())

                    for key in all_keys:
                        values = []
                        for data in device_data_list:
                            val = data.values.get(key, np.nan)
                            if isinstance(val, (int, float)):
                                values.append(val)
                            else:
                                values.append(np.nan)
                        device_group.create_dataset(key, data=np.array(values))

        logger.info(f"Data exported to HDF5: {file_path}")
        return str(file_path)

    async def _export_matlab(
        self,
        experiment: ExperimentMetadata,
        data_list: list[ExperimentData],
        filename: str,
        config: ExportConfig,
    ) -> str:
        """导出MATLAB格式。

        Args:
            experiment: 实验元数据
            data_list: 数据列表
            filename: 文件名
            config: 导出配置

        Returns:
            str: 文件路径
        """
        try:
            from scipy.io import savemat
        except ImportError:
            logger.error("scipy not installed, falling back to JSON")
            return await self._export_json(experiment, data_list, filename, config)

        file_path = EXPORT_DIR / f"{filename}.mat"

        mat_data = {}

        # 写入元数据
        if config.include_metadata:
            mat_data["experiment_id"] = experiment.experiment_id
            mat_data["experiment_name"] = experiment.name
            mat_data["operator"] = experiment.operator
            mat_data["created_at"] = experiment.created_at

        # 写入数据
        if config.include_raw_data and data_list:
            timestamps = np.array([d.timestamp for d in data_list])
            mat_data["timestamps"] = timestamps

            # 按设备分组
            device_data: dict[str, dict[str, list]] = {}
            for data in data_list:
                if data.device_id not in device_data:
                    device_data[data.device_id] = {}
                for key, value in data.values.items():
                    if key not in device_data[data.device_id]:
                        device_data[data.device_id][key] = []
                    device_data[data.device_id][key].append(value)

            for device_id, fields in device_data.items():
                for key, values in fields.items():
                    mat_data[f"{device_id}_{key}"] = np.array(values)

        savemat(str(file_path), mat_data)

        logger.info(f"Data exported to MATLAB: {file_path}")
        return str(file_path)

    async def _export_excel(
        self,
        experiment: ExperimentMetadata,
        data_list: list[ExperimentData],
        filename: str,
        config: ExportConfig,
    ) -> str:
        """导出Excel格式。

        Args:
            experiment: 实验元数据
            data_list: 数据列表
            filename: 文件名
            config: 导出配置

        Returns:
            str: 文件路径
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas not installed, falling back to CSV")
            return await self._export_csv(experiment, data_list, filename, config)

        file_path = EXPORT_DIR / f"{filename}.xlsx"

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            # 写入元数据
            if config.include_metadata:
                meta_df = pd.DataFrame([experiment.to_dict()])
                meta_df.to_excel(writer, sheet_name="Metadata", index=False)

            # 写入数据
            if config.include_raw_data and data_list:
                # 按设备分组写入不同sheet
                device_data: dict[str, list[ExperimentData]] = {}
                for data in data_list:
                    if data.device_id not in device_data:
                        device_data[data.device_id] = []
                    device_data[data.device_id].append(data)

                for device_id, device_data_list in device_data.items():
                    rows = []
                    for data in device_data_list:
                        row = {
                            "timestamp": data.timestamp,
                            "data_type": data.data_type,
                            **data.values,
                        }
                        rows.append(row)

                    df = pd.DataFrame(rows)
                    sheet_name = device_id[:31]  # Excel sheet名称限制31字符
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

        logger.info(f"Data exported to Excel: {file_path}")
        return str(file_path)

    # ==================== 实验报告自动生成 ====================

    async def generate_report(
        self,
        experiment_id: str,
        config: ReportConfig,
    ) -> str:
        """生成实验报告。

        Args:
            experiment_id: 实验ID
            config: 报告配置

        Returns:
            str: 报告文件路径

        Raises:
            ValueError: 实验不存在
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError(f"Experiment not found: {experiment_id}")

        data_list = self._experiment_data.get(experiment_id, [])

        # 生成报告内容
        report_content = await self._generate_report_content(experiment, data_list, config)

        # 保存报告
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{experiment_id}_{timestamp_str}.md"
        file_path = REPORT_DIR / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info(f"Report generated: {file_path}")
        return str(file_path)

    async def _generate_report_content(
        self,
        experiment: ExperimentMetadata,
        data_list: list[ExperimentData],
        config: ReportConfig,
    ) -> str:
        """生成报告内容。

        Args:
            experiment: 实验元数据
            data_list: 数据列表
            config: 报告配置

        Returns:
            str: 报告内容
        """
        lines = []

        # 标题
        lines.append(f"# 实验报告：{experiment.name}")
        lines.append("")
        lines.append(f"**实验ID**: {experiment.experiment_id}")
        lines.append(f"**实验状态**: {experiment.status.value}")
        lines.append(f"**操作员**: {experiment.operator}")
        lines.append(f"**创建时间**: {datetime.fromtimestamp(experiment.created_at).strftime('%Y-%m-%d %H:%M:%S')}")
        if experiment.started_at:
            lines.append(f"**开始时间**: {datetime.fromtimestamp(experiment.started_at).strftime('%Y-%m-%d %H:%M:%S')}")
        if experiment.completed_at:
            lines.append(f"**完成时间**: {datetime.fromtimestamp(experiment.completed_at).strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 实验描述
        if experiment.description:
            lines.append("## 实验描述")
            lines.append("")
            lines.append(experiment.description)
            lines.append("")

        # 样品信息
        if experiment.sample_info:
            lines.append("## 样品信息")
            lines.append("")
            for key, value in experiment.sample_info.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        # 实验参数
        if experiment.parameters:
            lines.append("## 实验参数")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(experiment.parameters, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

        # 设备列表
        if experiment.devices:
            lines.append("## 使用设备")
            lines.append("")
            for device_id in experiment.devices:
                lines.append(f"- {device_id}")
            lines.append("")

        # 数据统计
        if config.include_statistics and data_list:
            lines.append("## 数据统计")
            lines.append("")

            # 按设备统计
            device_counts: dict[str, int] = {}
            for data in data_list:
                device_counts[data.device_id] = device_counts.get(data.device_id, 0) + 1

            lines.append("### 数据量统计")
            lines.append("")
            lines.append("| 设备ID | 数据点数 |")
            lines.append("|--------|----------|")
            for device_id, count in device_counts.items():
                lines.append(f"| {device_id} | {count} |")
            lines.append("")

            # 时间范围
            if data_list:
                start_time = min(d.timestamp for d in data_list)
                end_time = max(d.timestamp for d in data_list)
                duration = end_time - start_time

                lines.append("### 时间范围")
                lines.append("")
                lines.append(f"- **开始时间**: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
                lines.append(f"- **结束时间**: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
                lines.append(f"- **持续时间**: {duration:.2f} 秒")
                lines.append("")

        # 原始数据（可选）
        if config.include_raw_data and data_list:
            lines.append("## 原始数据")
            lines.append("")
            lines.append("```json")
            # 只显示前10条数据
            for data in data_list[:10]:
                lines.append(json.dumps({
                    "timestamp": data.timestamp,
                    "device_id": data.device_id,
                    "data_type": data.data_type,
                    "values": data.values,
                }, ensure_ascii=False))
            if len(data_list) > 10:
                lines.append(f"... 共 {len(data_list)} 条数据")
            lines.append("```")
            lines.append("")

        # 备注
        if experiment.notes:
            lines.append("## 备注")
            lines.append("")
            lines.append(experiment.notes)
            lines.append("")

        # 标签
        if experiment.tags:
            lines.append("## 标签")
            lines.append("")
            lines.append(", ".join(f"`{tag}`" for tag in experiment.tags))
            lines.append("")

        # 页脚
        lines.append("---")
        lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    # ==================== 资源清理 ====================

    async def cleanup(self) -> None:
        """清理所有资源。"""
        # 保存所有实验数据
        for experiment_id, experiment in self._experiments.items():
            await self._save_experiment(experiment)

        logger.info("ExperimentLifecycleService cleanup completed")

    async def _save_experiment(self, experiment: ExperimentMetadata) -> bool:
        """保存实验到文件。

        Args:
            experiment: 实验元数据

        Returns:
            bool: 保存是否成功
        """
        try:
            experiment_file = EXPORT_DIR / f"{experiment.experiment_id}_metadata.json"

            with open(experiment_file, "w", encoding="utf-8") as f:
                json.dump(experiment.to_dict(), f, indent=2, ensure_ascii=False, default=str)

            return True

        except Exception as e:
            logger.error(f"Save experiment error: {e}")
            return False
