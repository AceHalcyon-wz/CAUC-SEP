"""
文件名: test_performance.py
路径: backend/tests/
功能: 数据管道性能测试
作者: Performance Optimization Agent
创建日期: 2024-03-08
依赖: pytest, numpy
"""

import time

import numpy as np

from core.data_pipeline import OverflowStrategy, RingBuffer, StreamProcessor, TriggerType


def test_ring_buffer_performance():
    """测试环形缓冲区性能。"""
    print("\n=== 环形缓冲区性能测试 ===")

    # 测试1: 大量小数据写入
    buffer = RingBuffer(size=100000)
    start_time = time.time()

    for i in range(1000):
        data = np.random.randn(100)
        buffer.write(data)

    elapsed = time.time() - start_time
    print(f"小数据写入: 1000次 x 100点 = {elapsed:.4f}秒")
    print(f"吞吐量: {100000 / elapsed:.2f} 点/秒")

    # 测试2: 批量写入
    buffer2 = RingBuffer(size=100000)
    start_time = time.time()

    data_list = [np.random.randn(100) for _ in range(1000)]
    buffer2.write_batch(data_list)

    elapsed = time.time() - start_time
    print(f"批量写入: 1000次 x 100点 = {elapsed:.4f}秒")
    print(f"吞吐量: {100000 / elapsed:.2f} 点/秒")

    # 测试3: peek操作性能
    buffer3 = RingBuffer(size=10000)
    buffer3.write(np.random.randn(10000))

    start_time = time.time()
    for _ in range(1000):
        buffer3.peek(100)
    elapsed = time.time() - start_time
    print(f"Peek操作: 1000次 = {elapsed:.4f}秒")


def test_overflow_strategies():
    """测试不同溢出策略。"""
    print("\n=== 溢出策略测试 ===")

    # 测试OVERWRITE_OLDEST策略
    buffer1 = RingBuffer(size=100, overflow_strategy=OverflowStrategy.OVERWRITE_OLDEST)
    buffer1.write(np.arange(100))
    written = buffer1.write(np.arange(50))
    print(
        f"OVERWRITE_OLDEST: 写入{written}点，缓冲区使用率: {buffer1.available / buffer1.capacity * 100:.1f}%"
    )

    # 测试DROP_NEW策略
    buffer2 = RingBuffer(size=100, overflow_strategy=OverflowStrategy.DROP_NEW)
    buffer2.write(np.arange(100))
    written = buffer2.write(np.arange(50))
    print(
        f"DROP_NEW: 写入{written}点，缓冲区使用率: {buffer2.available / buffer2.capacity * 100:.1f}%"
    )

    # 测试EXPAND策略
    buffer3 = RingBuffer(size=100, overflow_strategy=OverflowStrategy.EXPAND)
    initial_size = buffer3.capacity
    buffer3.write(np.arange(100))
    written = buffer3.write(np.arange(50))
    print(f"EXPAND: 写入{written}点，缓冲区大小: {initial_size} -> {buffer3.capacity}")


def test_stream_processor_performance():
    """测试流式数据处理器性能。"""
    print("\n=== 流式数据处理器性能测试 ===")

    processor = StreamProcessor(buffer_size=10000)

    # 添加触发器
    trigger_count = [0]

    def callback(data):
        trigger_count[0] += 1

    processor.add_trigger(
        name="test_trigger",
        trigger_type=TriggerType.THRESHOLD,
        condition=lambda data: len(data) > 0 and np.max(data) > 5.0,
        callback=callback,
        # 移除check_interval以避免延迟
    )

    # 测试单次处理
    start_time = time.time()
    for i in range(50):  # 减少次数
        data = np.random.randn(100)
        processor.process(data)
    elapsed = time.time() - start_time
    print(f"单次处理: 50次 x 100点 = {elapsed:.4f}秒")
    print(f"吞吐量: {5000 / elapsed:.2f} 点/秒")
    print(f"触发次数: {trigger_count[0]}")

    # 测试批量处理
    processor2 = StreamProcessor(buffer_size=10000)
    trigger_count2 = [0]
    processor2.add_trigger(
        name="test_trigger",
        trigger_type=TriggerType.THRESHOLD,
        condition=lambda data: len(data) > 0 and np.max(data) > 5.0,
        callback=lambda data: trigger_count2.__setitem__(0, trigger_count2[0] + 1),
    )

    start_time = time.time()
    data_list = [np.random.randn(100) for _ in range(50)]  # 减少次数
    processor2.process_batch(data_list)
    elapsed = time.time() - start_time
    print(f"批量处理: 50次 x 100点 = {elapsed:.4f}秒")
    print(f"吞吐量: {5000 / elapsed:.2f} 点/秒")
    print(f"触发次数: {trigger_count2[0]}")


def test_pipeline_statistics():
    """测试管道统计信息。"""
    print("\n=== 管道统计信息测试 ===")

    processor = StreamProcessor(buffer_size=10000)

    # 处理一些数据
    for i in range(10):
        data = np.random.randn(100)
        processor.process(data)

    stats = processor.get_statistics()
    print(f"总数据点数: {stats['total_data_points']}")
    print(f"平均处理时间: {stats['avg_processing_time_ms']:.2f}ms")
    print(f"吞吐量: {stats['throughput_points_per_sec']:.2f} 点/秒")
    print(f"峰值内存: {stats['peak_memory_usage_mb']:.4f} MB")
    print(f"延迟分布: {stats['latency_distribution']}")


def test_memory_optimization():
    """测试内存优化效果。"""
    print("\n=== 内存优化测试 ===")

    # 测试缓冲区内存使用
    buffer = RingBuffer(size=100000)
    initial_stats = buffer.get_statistics()
    print(f"初始内存使用: {initial_stats['memory_bytes'] / 1024:.2f} KB")

    # 写入数据
    buffer.write(np.random.randn(100000))
    stats = buffer.get_statistics()
    print(f"写入后内存使用: {stats['memory_bytes'] / 1024:.2f} KB")
    print(f"溢出次数: {stats['overflow_count']}")


if __name__ == "__main__":
    test_ring_buffer_performance()
    test_overflow_strategies()
    test_stream_processor_performance()
    test_pipeline_statistics()
    test_memory_optimization()
    print("\n=== 所有性能测试完成 ===")
