"""
链路追踪核心模块。

实现分布式追踪系统，支持请求链路追踪、性能分析和故障诊断。

功能：
    - 追踪上下文管理（Trace/Span）
    - 追踪装饰器（自动追踪函数执行）
    - 追踪数据存储和查询
    - 性能指标采集
    - 追踪数据可视化API

技术栈：
    - Python 3.11+
    - FastAPI 集成
    - SQLite 持久化存储

作者：Backend Engineer Agent
创建日期：2026-03-07
依赖：sqlalchemy, pydantic, fastapi
"""

import functools
import json
import logging
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# 追踪上下文管理
# ============================================================================

# 使用 ContextVar 实现跨异步任务的上下文传递
_current_trace: ContextVar[Optional["TraceContext"]] = ContextVar("current_trace", default=None)
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)


class SpanKind(str, Enum):
    """Span类型枚举。

    定义不同类型的Span，用于区分追踪层级。
    """

    SERVER = "server"  # 服务端处理
    CLIENT = "client"  # 客户端调用
    PRODUCER = "producer"  # 消息生产者
    CONSUMER = "consumer"  # 消息消费者
    INTERNAL = "internal"  # 内部操作


class SpanStatus(str, Enum):
    """Span状态枚举。

    定义Span的执行状态。
    """

    UNSET = "unset"  # 未设置
    OK = "ok"  # 成功
    ERROR = "error"  # 错误


@dataclass
class SpanEvent:
    """Span事件。

    记录Span执行过程中的重要事件。

    Attributes:
        name: 事件名称
        timestamp: 事件时间戳
        attributes: 事件属性
    """

    name: str
    timestamp: datetime
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """Span数据结构。

    表示一个追踪单元，记录操作的开始、结束和属性信息。

    Attributes:
        span_id: Span唯一标识
        trace_id: 所属Trace ID
        parent_span_id: 父Span ID（可选）
        name: Span名称
        kind: Span类型
        start_time: 开始时间
        end_time: 结束时间（可选）
        status: Span状态
        attributes: Span属性字典
        events: Span事件列表
    """

    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    name: str = ""
    kind: SpanKind = SpanKind.INTERNAL
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)

    def set_attribute(self, key: str, value: Any) -> None:
        """设置Span属性。

        Args:
            key: 属性键
            value: 属性值
        """
        self.attributes[key] = value

    def add_event(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """添加Span事件。

        Args:
            name: 事件名称
            attributes: 事件属性（可选）
        """
        event = SpanEvent(
            name=name,
            timestamp=datetime.now(),
            attributes=attributes or {},
        )
        self.events.append(event)

    def set_status(self, status: SpanStatus, description: str | None = None) -> None:
        """设置Span状态。

        Args:
            status: Span状态
            description: 状态描述（可选）
        """
        self.status = status
        if description:
            self.attributes["status_description"] = description

    def end(self) -> None:
        """结束Span。"""
        self.end_time = datetime.now()

    @property
    def duration_ms(self) -> int | None:
        """计算Span持续时间（毫秒）。

        Returns:
            Optional[int]: 持续时间（毫秒），未结束时返回None
        """
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() * 1000)
        return None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            dict: Span数据字典
        """
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp.isoformat(),
                    "attributes": e.attributes,
                }
                for e in self.events
            ],
        }


@dataclass
class TraceContext:
    """追踪上下文。

    管理一个完整的追踪链路，包含多个Span。

    Attributes:
        trace_id: Trace唯一标识
        root_span: 根Span
        spans: Span列表
        baggage: 跨Span传递的上下文数据
    """

    trace_id: str
    root_span: Span | None = None
    spans: list[Span] = field(default_factory=list)
    baggage: dict[str, str] = field(default_factory=dict)

    def create_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: str | None = None,
    ) -> Span:
        """创建新的Span。

        Args:
            name: Span名称
            kind: Span类型
            parent_span_id: 父Span ID（可选）

        Returns:
            Span: 新创建的Span
        """
        span = Span(
            span_id=generate_span_id(),
            trace_id=self.trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
        )
        self.spans.append(span)
        return span

    def set_baggage(self, key: str, value: str) -> None:
        """设置Baggage项。

        Baggage用于在Span之间传递上下文数据。

        Args:
            key: Baggage键
            value: Baggage值
        """
        self.baggage[key] = value

    def get_baggage(self, key: str) -> str | None:
        """获取Baggage项。

        Args:
            key: Baggage键

        Returns:
            Optional[str]: Baggage值，不存在时返回None
        """
        return self.baggage.get(key)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            dict: Trace数据字典
        """
        return {
            "trace_id": self.trace_id,
            "root_span": self.root_span.to_dict() if self.root_span else None,
            "spans": [s.to_dict() for s in self.spans],
            "baggage": self.baggage,
        }


# ============================================================================
# 追踪ID生成器
# ============================================================================


def generate_trace_id() -> str:
    """生成Trace ID。

    使用UUID4生成唯一标识符。

    Returns:
        str: 32位十六进制字符串
    """
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """生成Span ID。

    使用UUID4生成唯一标识符。

    Returns:
        str: 16位十六进制字符串
    """
    return uuid.uuid4().hex[:16]


# ============================================================================
# 追踪上下文管理器
# ============================================================================


def get_current_trace() -> TraceContext | None:
    """获取当前追踪上下文。

    Returns:
        Optional[TraceContext]: 当前追踪上下文，不存在时返回None
    """
    return _current_trace.get()


def get_current_span() -> Span | None:
    """获取当前Span。

    Returns:
        Optional[Span]: 当前Span，不存在时返回None
    """
    return _current_span.get()


def set_current_trace(trace: TraceContext | None) -> None:
    """设置当前追踪上下文。

    Args:
        trace: 追踪上下文对象
    """
    _current_trace.set(trace)


def set_current_span(span: Span | None) -> None:
    """设置当前Span。

    Args:
        span: Span对象
    """
    _current_span.set(span)


class Tracer:
    """追踪器。

    提供追踪上下文创建和管理功能。

    Example:
        >>> tracer = Tracer("my_service")
        >>> with tracer.start_as_current_span("operation") as span:
        ...     span.set_attribute("key", "value")
        ...     # 执行操作
    """

    def __init__(self, service_name: str = "cauc-sep"):
        """初始化追踪器。

        Args:
            service_name: 服务名称
        """
        self.service_name = service_name
        self._trace_storage: TraceStorage | None = None

    def set_storage(self, storage: "TraceStorage") -> None:
        """设置追踪数据存储。

        Args:
            storage: 追踪数据存储实例
        """
        self._trace_storage = storage

    def start_trace(
        self,
        name: str = "root",
        kind: SpanKind = SpanKind.SERVER,
        attributes: dict[str, Any] | None = None,
    ) -> TraceContext:
        """开始新的追踪。

        Args:
            name: 根Span名称
            kind: Span类型
            attributes: Span属性（可选）

        Returns:
            TraceContext: 新创建的追踪上下文
        """
        trace_id = generate_trace_id()
        trace = TraceContext(trace_id=trace_id)

        # 创建根Span
        root_span = trace.create_span(name=name, kind=kind)
        root_span.set_attribute("service.name", self.service_name)

        if attributes:
            for key, value in attributes.items():
                root_span.set_attribute(key, value)

        trace.root_span = root_span

        # 设置为当前追踪上下文
        set_current_trace(trace)
        set_current_span(root_span)

        logger.debug(f"[Trace] Started trace: {trace_id}")
        return trace

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """开始新的Span。

        Args:
            name: Span名称
            kind: Span类型
            attributes: Span属性（可选）

        Returns:
            Span: 新创建的Span

        Raises:
            RuntimeError: 当前没有活跃的追踪上下文
        """
        trace = get_current_trace()
        if not trace:
            raise RuntimeError("No active trace context")

        parent_span = get_current_span()
        parent_span_id = parent_span.span_id if parent_span else None

        span = trace.create_span(
            name=name,
            kind=kind,
            parent_span_id=parent_span_id,
        )

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        set_current_span(span)
        return span

    def end_trace(self, trace: TraceContext | None = None) -> None:
        """结束追踪。

        Args:
            trace: 追踪上下文（可选，默认使用当前上下文）
        """
        if trace is None:
            trace = get_current_trace()

        if not trace:
            return

        # 结束所有未结束的Span
        for span in trace.spans:
            if span.end_time is None:
                span.end()

        # 持久化追踪数据
        if self._trace_storage:
            self._trace_storage.save_trace(trace)

        # 清除上下文
        set_current_trace(None)
        set_current_span(None)

        logger.debug(f"[Trace] Ended trace: {trace.trace_id}")

    def end_span(self, span: Span | None = None) -> None:
        """结束Span。

        Args:
            span: Span对象（可选，默认使用当前Span）
        """
        if span is None:
            span = get_current_span()

        if not span:
            return

        span.end()

        # 恢复父Span为当前Span
        trace = get_current_trace()
        if trace and span.parent_span_id:
            parent_span = next(
                (s for s in trace.spans if s.span_id == span.parent_span_id),
                None,
            )
            set_current_span(parent_span)
        else:
            set_current_span(trace.root_span if trace else None)


# ============================================================================
# 追踪装饰器
# ============================================================================


def traced(
    name: str | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> Callable:
    """追踪装饰器。

    自动追踪函数执行，记录执行时间和异常信息。

    Args:
        name: Span名称（可选，默认使用函数名）
        kind: Span类型
        attributes: Span属性（可选）

    Returns:
        Callable: 装饰器函数

    Example:
        >>> @traced(name="process_data", kind=SpanKind.INTERNAL)
        ... def process_data(data):
        ...     return data * 2
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            span_name = name or func.__name__

            # 获取或创建追踪上下文
            trace = get_current_trace()
            if not trace:
                # 如果没有追踪上下文，创建新的
                tracer = Tracer()
                trace = tracer.start_trace(name=span_name, kind=kind)
                should_end_trace = True
            else:
                should_end_trace = False

            # 创建Span
            span = trace.create_span(
                name=span_name,
                kind=kind,
                parent_span_id=get_current_span().span_id if get_current_span() else None,
            )

            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)

            # 记录函数参数
            span.set_attribute("function.args", str(args[:3]))  # 限制长度
            span.set_attribute("function.kwargs", str(list(kwargs.keys())[:5]))

            try:
                # 执行函数
                result = func(*args, **kwargs)
                span.set_status(SpanStatus.OK)
                return result
            except Exception as e:
                # 记录异常
                span.set_status(SpanStatus.ERROR, str(e))
                span.add_event(
                    "exception",
                    {
                        "type": type(e).__name__,
                        "message": str(e),
                    },
                )
                raise
            finally:
                span.end()

                if should_end_trace:
                    tracer.end_trace(trace)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_name = name or func.__name__

            # 获取或创建追踪上下文
            trace = get_current_trace()
            if not trace:
                tracer = Tracer()
                trace = tracer.start_trace(name=span_name, kind=kind)
                should_end_trace = True
            else:
                should_end_trace = False

            # 创建Span
            span = trace.create_span(
                name=span_name,
                kind=kind,
                parent_span_id=get_current_span().span_id if get_current_span() else None,
            )

            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)

            # 记录函数参数
            span.set_attribute("function.args", str(args[:3]))
            span.set_attribute("function.kwargs", str(list(kwargs.keys())[:5]))

            try:
                # 执行异步函数
                result = await func(*args, **kwargs)
                span.set_status(SpanStatus.OK)
                return result
            except Exception as e:
                # 记录异常
                span.set_status(SpanStatus.ERROR, str(e))
                span.add_event(
                    "exception",
                    {
                        "type": type(e).__name__,
                        "message": str(e),
                    },
                )
                raise
            finally:
                span.end()

                if should_end_trace:
                    tracer.end_trace(trace)

        # 根据函数类型返回不同的包装器
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# FastAPI 中间件
# ============================================================================


class TracingMiddleware:
    """追踪中间件。

    自动为FastAPI请求创建追踪上下文。

    Example:
        >>> app.add_middleware(TracingMiddleware, tracer=tracer)
    """

    def __init__(
        self,
        app,
        tracer: Tracer | None = None,
        exclude_paths: set[str] | None = None,
    ):
        """初始化追踪中间件。

        Args:
            app: FastAPI应用实例
            tracer: 追踪器实例（可选）
            exclude_paths: 排除的路径集合（可选）
        """
        self.app = app
        self.tracer = tracer or Tracer()
        self.exclude_paths = exclude_paths or {
            "/",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
        }

    async def __call__(self, scope, receive, send):
        """处理请求。

        Args:
            scope: ASGI scope
            receive: ASGI receive
            send: ASGI send
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # 排除特定路径
        if path in self.exclude_paths or path.startswith("/ws/"):
            await self.app(scope, receive, send)
            return

        # 开始追踪
        trace = self.tracer.start_trace(
            name=f"{scope['method']} {path}",
            kind=SpanKind.SERVER,
            attributes={
                "http.method": scope["method"],
                "http.url": str(scope.get("root_path", "")) + path,
                "http.scheme": scope.get("scheme", "http"),
                "http.host": scope.get("server", ("unknown", 0))[0],
            },
        )

        # 提取请求头中的追踪信息（支持分布式追踪）
        headers = dict(scope.get("headers", []))
        if b"traceparent" in headers:
            # 解析 W3C Trace Context 格式
            traceparent = headers[b"traceparent"].decode("utf-8")
            # 格式: version-traceid-parentid-flags
            parts = traceparent.split("-")
            if len(parts) >= 2:
                trace.trace_id = parts[1]
                if trace.root_span:
                    trace.root_span.trace_id = trace.trace_id

        # 添加客户端信息
        client = scope.get("client")
        if client:
            trace.root_span.set_attribute("http.client_ip", client[0])

        try:
            await self.app(scope, receive, send)
            trace.root_span.set_status(SpanStatus.OK)
        except Exception as e:
            trace.root_span.set_status(SpanStatus.ERROR, str(e))
            trace.root_span.add_event(
                "exception",
                {
                    "type": type(e).__name__,
                    "message": str(e),
                },
            )
            raise
        finally:
            self.tracer.end_trace(trace)


# ============================================================================
# 追踪数据存储
# ============================================================================


class TraceStorage:
    """追踪数据存储。

    持久化追踪数据到数据库，支持查询和分析。

    Example:
        >>> storage = TraceStorage(db_path="traces.db")
        >>> storage.save_trace(trace)
        >>> traces = storage.query_traces(service_name="cauc-sep")
    """

    def __init__(self, db_path: str = "traces.db"):
        """初始化追踪数据存储。

        Args:
            db_path: 数据库文件路径
        """
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

        # 创建表
        self._create_tables()

        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"TraceStorage initialized: {db_path}")

    def _create_tables(self) -> None:
        """创建数据库表。"""
        from sqlalchemy import Column, DateTime, Integer, String, Text
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()

        class TraceRecord(Base):
            """追踪记录表。"""

            __tablename__ = "trace_records"

            id = Column(Integer, primary_key=True, autoincrement=True)
            trace_id = Column(String(32), unique=True, nullable=False, index=True)
            service_name = Column(String(100), nullable=False)
            root_span_name = Column(String(200))
            start_time = Column(DateTime, nullable=False, index=True)
            end_time = Column(DateTime)
            duration_ms = Column(Integer)
            status = Column(String(20))
            span_count = Column(Integer, default=0)
            attributes = Column(Text)  # JSON
            created_at = Column(DateTime, default=datetime.now)

        class SpanRecord(Base):
            """Span记录表。"""

            __tablename__ = "span_records"

            id = Column(Integer, primary_key=True, autoincrement=True)
            span_id = Column(String(16), unique=True, nullable=False, index=True)
            trace_id = Column(String(32), nullable=False, index=True)
            parent_span_id = Column(String(16))
            name = Column(String(200), nullable=False)
            kind = Column(String(20))
            start_time = Column(DateTime, nullable=False)
            end_time = Column(DateTime)
            duration_ms = Column(Integer)
            status = Column(String(20))
            attributes = Column(Text)  # JSON
            events = Column(Text)  # JSON
            created_at = Column(DateTime, default=datetime.now)

        Base.metadata.create_all(self.engine)

        self.TraceRecord = TraceRecord
        self.SpanRecord = SpanRecord

    def save_trace(self, trace: TraceContext) -> None:
        """保存追踪数据。

        Args:
            trace: 追踪上下文对象
        """
        session = self.Session()
        try:
            # 保存Trace记录
            root_span = trace.root_span
            trace_record = self.TraceRecord(
                trace_id=trace.trace_id,
                service_name=(
                    root_span.attributes.get("service.name", "unknown") if root_span else "unknown"
                ),
                root_span_name=root_span.name if root_span else None,
                start_time=root_span.start_time if root_span else datetime.now(),
                end_time=root_span.end_time if root_span else None,
                duration_ms=root_span.duration_ms if root_span else None,
                status=root_span.status.value if root_span else SpanStatus.UNSET.value,
                span_count=len(trace.spans),
                attributes=json.dumps(trace.baggage),
            )
            session.add(trace_record)

            # 保存所有Span记录
            for span in trace.spans:
                span_record = self.SpanRecord(
                    span_id=span.span_id,
                    trace_id=span.trace_id,
                    parent_span_id=span.parent_span_id,
                    name=span.name,
                    kind=span.kind.value,
                    start_time=span.start_time,
                    end_time=span.end_time,
                    duration_ms=span.duration_ms,
                    status=span.status.value,
                    attributes=json.dumps(span.attributes),
                    events=json.dumps(
                        [
                            {
                                "name": e.name,
                                "timestamp": e.timestamp.isoformat(),
                                "attributes": e.attributes,
                            }
                            for e in span.events
                        ]
                    ),
                )
                session.add(span_record)

            session.commit()
            logger.debug(f"[TraceStorage] Saved trace: {trace.trace_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"[TraceStorage] Failed to save trace: {e}")
            raise
        finally:
            session.close()

    def query_traces(
        self,
        service_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """查询追踪记录。

        Args:
            service_name: 服务名称过滤（可选）
            start_time: 开始时间过滤（可选）
            end_time: 结束时间过滤（可选）
            status: 状态过滤（可选）
            limit: 返回数量限制

        Returns:
            list: 追踪记录列表
        """
        session = self.Session()
        try:
            query = session.query(self.TraceRecord)

            if service_name:
                query = query.filter(self.TraceRecord.service_name == service_name)
            if start_time:
                query = query.filter(self.TraceRecord.start_time >= start_time)
            if end_time:
                query = query.filter(self.TraceRecord.start_time <= end_time)
            if status:
                query = query.filter(self.TraceRecord.status == status)

            records = query.order_by(self.TraceRecord.start_time.desc()).limit(limit).all()

            return [
                {
                    "trace_id": r.trace_id,
                    "service_name": r.service_name,
                    "root_span_name": r.root_span_name,
                    "start_time": r.start_time.isoformat(),
                    "end_time": r.end_time.isoformat() if r.end_time else None,
                    "duration_ms": r.duration_ms,
                    "status": r.status,
                    "span_count": r.span_count,
                }
                for r in records
            ]
        finally:
            session.close()

    def get_trace_detail(self, trace_id: str) -> dict[str, Any] | None:
        """获取追踪详情。

        Args:
            trace_id: Trace ID

        Returns:
            Optional[dict]: 追踪详情，不存在时返回None
        """
        session = self.Session()
        try:
            # 获取Trace记录
            trace_record = (
                session.query(self.TraceRecord)
                .filter(self.TraceRecord.trace_id == trace_id)
                .first()
            )

            if not trace_record:
                return None

            # 获取所有Span记录
            span_records = (
                session.query(self.SpanRecord)
                .filter(self.SpanRecord.trace_id == trace_id)
                .order_by(self.SpanRecord.start_time)
                .all()
            )

            return {
                "trace_id": trace_record.trace_id,
                "service_name": trace_record.service_name,
                "root_span_name": trace_record.root_span_name,
                "start_time": trace_record.start_time.isoformat(),
                "end_time": trace_record.end_time.isoformat() if trace_record.end_time else None,
                "duration_ms": trace_record.duration_ms,
                "status": trace_record.status,
                "span_count": trace_record.span_count,
                "attributes": (
                    json.loads(trace_record.attributes) if trace_record.attributes else {}
                ),
                "spans": [
                    {
                        "span_id": s.span_id,
                        "parent_span_id": s.parent_span_id,
                        "name": s.name,
                        "kind": s.kind,
                        "start_time": s.start_time.isoformat(),
                        "end_time": s.end_time.isoformat() if s.end_time else None,
                        "duration_ms": s.duration_ms,
                        "status": s.status,
                        "attributes": json.loads(s.attributes) if s.attributes else {},
                        "events": json.loads(s.events) if s.events else [],
                    }
                    for s in span_records
                ],
            }
        finally:
            session.close()

    def get_statistics(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """获取追踪统计信息。

        Args:
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            dict: 统计信息
        """
        session = self.Session()
        try:
            query = session.query(self.TraceRecord)

            if start_time:
                query = query.filter(self.TraceRecord.start_time >= start_time)
            if end_time:
                query = query.filter(self.TraceRecord.start_time <= end_time)

            records = query.all()

            if not records:
                return {
                    "total_traces": 0,
                    "avg_duration_ms": 0,
                    "max_duration_ms": 0,
                    "min_duration_ms": 0,
                    "error_count": 0,
                    "error_rate": 0.0,
                }

            durations = [r.duration_ms for r in records if r.duration_ms]
            error_count = sum(1 for r in records if r.status == SpanStatus.ERROR.value)

            return {
                "total_traces": len(records),
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "error_count": error_count,
                "error_rate": error_count / len(records) if records else 0.0,
            }
        finally:
            session.close()

    def cleanup_old_traces(self, max_age_days: int = 30) -> int:
        """清理过期追踪数据。

        Args:
            max_age_days: 保留天数

        Returns:
            int: 删除的记录数
        """
        from datetime import timedelta

        session = self.Session()
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            # 删除Span记录
            span_count = (
                session.query(self.SpanRecord)
                .filter(self.SpanRecord.created_at < cutoff_date)
                .delete()
            )

            # 删除Trace记录
            trace_count = (
                session.query(self.TraceRecord)
                .filter(self.TraceRecord.created_at < cutoff_date)
                .delete()
            )

            session.commit()
            logger.info(f"[TraceStorage] Cleaned up {trace_count} traces and {span_count} spans")
            return trace_count
        except Exception as e:
            session.rollback()
            logger.error(f"[TraceStorage] Cleanup failed: {e}")
            return 0
        finally:
            session.close()


# ============================================================================
# API响应模型
# ============================================================================


class TraceListResponse(BaseModel):
    """追踪列表响应模型。"""

    total: int = Field(..., description="总数量")
    traces: list[dict[str, Any]] = Field(..., description="追踪列表")


class TraceDetailResponse(BaseModel):
    """追踪详情响应模型。"""

    trace_id: str = Field(..., description="Trace ID")
    service_name: str = Field(..., description="服务名称")
    root_span_name: str | None = Field(None, description="根Span名称")
    start_time: str = Field(..., description="开始时间")
    end_time: str | None = Field(None, description="结束时间")
    duration_ms: int | None = Field(None, description="持续时间（毫秒）")
    status: str = Field(..., description="状态")
    span_count: int = Field(0, description="Span数量")
    spans: list[dict[str, Any]] = Field(default_factory=list, description="Span列表")


class TraceStatisticsResponse(BaseModel):
    """追踪统计响应模型。"""

    total_traces: int = Field(0, description="总追踪数")
    avg_duration_ms: float = Field(0.0, description="平均持续时间（毫秒）")
    max_duration_ms: int = Field(0, description="最大持续时间（毫秒）")
    min_duration_ms: int = Field(0, description="最小持续时间（毫秒）")
    error_count: int = Field(0, description="错误数量")
    error_rate: float = Field(0.0, description="错误率")


# ============================================================================
# 全局追踪器实例
# ============================================================================

# 全局追踪器实例
tracer = Tracer(service_name="cauc-sep")

# 全局追踪存储实例
trace_storage: TraceStorage | None = None


def init_tracing(db_path: str = "traces.db") -> Tracer:
    """初始化追踪系统。

    Args:
        db_path: 数据库文件路径

    Returns:
        Tracer: 追踪器实例

    Example:
        >>> tracer = init_tracing("traces.db")
        >>> app.add_middleware(TracingMiddleware, tracer=tracer)
    """
    global trace_storage

    trace_storage = TraceStorage(db_path=db_path)
    tracer.set_storage(trace_storage)

    logger.info(f"[Tracing] Initialized with database: {db_path}")
    return tracer


def get_trace_storage() -> TraceStorage | None:
    """获取追踪存储实例。

    Returns:
        Optional[TraceStorage]: 追踪存储实例
    """
    return trace_storage
