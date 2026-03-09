"""
性能测试脚本：验证数据管道和调度器优化效果

测试内容：
1. RingBuffer 读写性能对比
2. StreamProcessor 触发器检查性能
3. WindowsRTScheduler 稳定性测试
"""

import sys
import time
import numpy as np

# 添加项目路径
sys.path.insert(0, r"c:\Users\15272\Downloads\kimiOKC\cauc-sep\backend")


def test_ring_buffer_performance():
    """测试 RingBuffer 性能。"""
    from core.data_pipeline import RingBuffer
    
    print("\n" + "=" * 60)
    print("RingBuffer 性能测试")
    print("=" * 60)
    
    buffer = RingBuffer(size=100000)
    data = np.random.randn(1000).astype(np.float64)
    
    # 测试写入性能
    iterations = 10000
    start = time.perf_counter()
    for _ in range(iterations):
        buffer.write(data)
    write_time = (time.perf_counter() - start) * 1000
    
    print(f"写入性能:")
    print(f"  - {iterations} 次写入，每次 {len(data)} 个数据点")
    print(f"  - 总耗时: {write_time:.2f} ms")
    print(f"  - 平均每次: {write_time / iterations:.4f} ms")
    print(f"  - 吞吐量: {iterations * len(data) / (write_time / 1000):.0f} 点/秒")
    
    # 测试读取性能
    buffer.clear()
    buffer.write(np.random.randn(50000).astype(np.float64))
    
    start = time.perf_counter()
    for _ in range(iterations):
        result = buffer.read(100)
    read_time = (time.perf_counter() - start) * 1000
    
    print(f"\n读取性能:")
    print(f"  - {iterations} 次读取，每次 100 个数据点")
    print(f"  - 总耗时: {read_time:.2f} ms")
    print(f"  - 平均每次: {read_time / iterations:.4f} ms")
    
    # 测试零拷贝读取
    buffer.clear()
    buffer.write(np.random.randn(50000).astype(np.float64))
    
    start = time.perf_counter()
    for _ in range(iterations):
        view, n = buffer.read_zero_copy(100)
    zero_copy_time = (time.perf_counter() - start) * 1000
    
    print(f"\n零拷贝读取性能:")
    print(f"  - {iterations} 次读取，每次 100 个数据点")
    print(f"  - 总耗时: {zero_copy_time:.2f} ms")
    print(f"  - 平均每次: {zero_copy_time / iterations:.4f} ms")
    print(f"  - 相比普通读取提升: {(read_time - zero_copy_time) / read_time * 100:.1f}%")
    
    # 测试快速写入
    buffer.clear()
    start = time.perf_counter()
    for _ in range(iterations):
        buffer.write_fast(data)
    fast_write_time = (time.perf_counter() - start) * 1000
    
    print(f"\n快速写入性能:")
    print(f"  - {iterations} 次写入，每次 {len(data)} 个数据点")
    print(f"  - 总耗时: {fast_write_time:.2f} ms")
    print(f"  - 相比普通写入提升: {(write_time - fast_write_time) / write_time * 100:.1f}%")


def test_stream_processor_performance():
    """测试 StreamProcessor 性能。"""
    from core.data_pipeline import StreamProcessor, TriggerType
    
    print("\n" + "=" * 60)
    print("StreamProcessor 性能测试")
    print("=" * 60)
    
    # 创建处理器（不启用并行触发器检查，避免线程池开销）
    processor = StreamProcessor(
        buffer_size=100000,
        enable_parallel_triggers=False,  # 串行模式更稳定
        backpressure_enabled=True
    )
    
    # 添加多个触发器
    trigger_count = 10
    for i in range(trigger_count):
        processor.add_trigger(
            f"trigger_{i}",
            TriggerType.THRESHOLD,
            lambda d, i=i: len(d) > 0 and np.max(d) > i * 10,
            lambda d, i=i: None  # 空回调
        )
    
    data = np.random.randn(1000).astype(np.float64) * 100
    
    iterations = 1000
    
    start = time.perf_counter()
    for _ in range(iterations):
        processor.process(data)
    process_time = (time.perf_counter() - start) * 1000
    
    print(f"触发器检查性能:")
    print(f"  - {trigger_count} 个触发器")
    print(f"  - {iterations} 次处理")
    print(f"  - 总耗时: {process_time:.2f} ms")
    print(f"  - 平均每次: {process_time / iterations:.4f} ms")
    print(f"  - 吞吐量: {iterations / (process_time / 1000):.0f} 次/秒")
    
    # 获取性能指标
    metrics = processor.get_performance_metrics()
    print(f"\n性能指标:")
    print(f"  - 平均处理时间: {metrics['avg_process_time_ms']:.4f} ms")
    print(f"  - P95 处理时间: {metrics['process_p95_ms']:.4f} ms")
    print(f"  - 平均触发器检查时间: {metrics['avg_trigger_check_time_ms']:.4f} ms")
    
    # 获取背压状态
    backpressure = processor.get_backpressure_status()
    print(f"\n背压状态:")
    print(f"  - 启用: {backpressure['enabled']}")
    print(f"  - 激活: {backpressure['active']}")
    print(f"  - 高水位: {backpressure['high_watermark']}")
    print(f"  - 低水位: {backpressure['low_watermark']}")
    
    # 获取统计信息
    stats = processor.get_statistics()
    print(f"\n统计信息:")
    print(f"  - 总数据点: {stats['total_data_points']}")
    print(f"  - 触发器激活次数: {stats['trigger_activations']}")
    print(f"  - 吞吐量: {stats['throughput_points_per_sec']:.0f} 点/秒")


def test_rt_scheduler_stability():
    """测试 WindowsRTScheduler 稳定性。"""
    if sys.platform != "win32":
        print("\n跳过 WindowsRTScheduler 测试（非 Windows 平台）")
        return
    
    from core.rt_scheduler import WindowsRTScheduler, THREAD_PRIORITY_ABOVE_NORMAL
    
    print("\n" + "=" * 60)
    print("WindowsRTScheduler 稳定性测试")
    print("=" * 60)
    
    try:
        with WindowsRTScheduler(interval_ms=5) as scheduler:
            # 设置线程优先级
            scheduler.set_thread_priority(THREAD_PRIORITY_ABOVE_NORMAL)
            
            # 测量执行时间
            for i in range(100):
                with scheduler.measure_execution(expected_ms=10.0):
                    time.sleep(0.01)  # 模拟 10ms 任务
            
            # 获取性能报告
            report = scheduler.get_performance_report()
            
            print(f"性能报告:")
            print(f"  - 运行时间: {report['uptime_seconds']:.2f} 秒")
            print(f"  - 总执行次数: {report['total_executions']}")
            print(f"  - 每秒执行次数: {report['executions_per_second']:.1f}")
            print(f"\n执行时间统计:")
            print(f"  - 平均: {report['execution_time']['avg_ms']:.3f} ms")
            print(f"  - 最大: {report['execution_time']['max_ms']:.3f} ms")
            print(f"  - 最小: {report['execution_time']['min_ms']:.3f} ms")
            print(f"  - P50: {report['execution_time']['p50_ms']:.3f} ms")
            print(f"  - P95: {report['execution_time']['p95_ms']:.3f} ms")
            print(f"  - P99: {report['execution_time']['p99_ms']:.3f} ms")
            print(f"\n精度偏差:")
            print(f"  - 平均: {report['precision']['avg_error_ms']:.3f} ms")
            print(f"  - 最大: {report['precision']['max_error_ms']:.3f} ms")
            print(f"\n可靠性:")
            print(f"  - 错过截止时间: {report['reliability']['missed_deadlines']}")
            print(f"  - 错过率: {report['reliability']['miss_rate'] * 100:.2f}%")
            
            # 测试优雅退出
            scheduler.request_shutdown()
            print(f"\n优雅退出测试:")
            print(f"  - 关闭请求状态: {scheduler.is_shutdown_requested()}")
            
        print("\n调度器资源已正确释放")
        
    except Exception as e:
        print(f"调度器测试失败: {e}")


def main():
    """主测试函数。"""
    print("\n" + "=" * 60)
    print("CAUC-SEP 后端性能优化测试")
    print("=" * 60)
    
    test_ring_buffer_performance()
    test_stream_processor_performance()
    test_rt_scheduler_stability()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
