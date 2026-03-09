"""
性能测试脚本：验证数据管道和调度器优化效果（简化版）
"""

import sys
import time

import numpy as np

sys.path.insert(0, r"c:\Users\15272\Downloads\kimiOKC\cauc-sep\backend")


def test_ring_buffer():
    """测试 RingBuffer 性能。"""
    from core.data_pipeline import RingBuffer

    print("\n" + "=" * 60)
    print("RingBuffer 性能测试")
    print("=" * 60)

    buffer = RingBuffer(size=100000)
    data = np.random.randn(1000).astype(np.float64)

    # 写入性能
    iterations = 10000
    start = time.perf_counter()
    for _ in range(iterations):
        buffer.write(data)
    write_time = (time.perf_counter() - start) * 1000

    print(f"写入性能: {iterations} 次 x {len(data)} 点")
    print(
        f"  总耗时: {write_time:.2f} ms, 吞吐量: {iterations * len(data) / (write_time / 1000):.0f} 点/秒"
    )

    # 快速写入
    buffer.clear()
    start = time.perf_counter()
    for _ in range(iterations):
        buffer.write_fast(data)
    fast_write_time = (time.perf_counter() - start) * 1000

    print(f"快速写入: {iterations} 次 x {len(data)} 点")
    print(
        f"  总耗时: {fast_write_time:.2f} ms, 提升: {(write_time - fast_write_time) / write_time * 100:.1f}%"
    )

    # 读取性能
    buffer.clear()
    buffer.write(np.random.randn(50000).astype(np.float64))

    start = time.perf_counter()
    for _ in range(iterations):
        buffer.read(100)
    read_time = (time.perf_counter() - start) * 1000

    print(f"读取性能: {iterations} 次 x 100 点")
    print(f"  总耗时: {read_time:.2f} ms")


def test_rt_scheduler():
    """测试 WindowsRTScheduler。"""
    if sys.platform != "win32":
        print("\n跳过 WindowsRTScheduler 测试（非 Windows 平台）")
        return

    from core.rt_scheduler import THREAD_PRIORITY_ABOVE_NORMAL, WindowsRTScheduler

    print("\n" + "=" * 60)
    print("WindowsRTScheduler 稳定性测试")
    print("=" * 60)

    try:
        with WindowsRTScheduler(interval_ms=5) as scheduler:
            scheduler.set_thread_priority(THREAD_PRIORITY_ABOVE_NORMAL)

            # 测量执行时间
            for i in range(50):
                with scheduler.measure_execution(expected_ms=10.0):
                    time.sleep(0.01)

            report = scheduler.get_performance_report()

            print(f"性能报告:")
            print(f"  运行时间: {report['uptime_seconds']:.2f} 秒")
            print(f"  执行次数: {report['total_executions']}")
            print(f"  平均延迟: {report['execution_time']['avg_ms']:.3f} ms")
            print(f"  P95延迟: {report['execution_time']['p95_ms']:.3f} ms")
            print(f"  平均精度偏差: {report['precision']['avg_error_ms']:.3f} ms")
            print(f"  错过截止时间: {report['reliability']['missed_deadlines']}")

            scheduler.request_shutdown()
            print(f"\n优雅退出: 关闭请求状态 = {scheduler.is_shutdown_requested()}")

        print("调度器资源已正确释放")

    except Exception as e:
        print(f"调度器测试失败: {e}")


def main():
    print("\n" + "=" * 60)
    print("CAUC-SEP 后端性能优化测试（简化版）")
    print("=" * 60)

    test_ring_buffer()
    test_rt_scheduler()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
