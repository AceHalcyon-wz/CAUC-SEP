/**
 * @file useProgress.test.js
 * @path frontend/src/composables/__tests__/
 * @description useProgress组合式函数单元测试
 * @author Agent
 * @date 2024-03-07
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useProgress, OPERATION_STATUS, createProgressTracker } from '@/composables/useProgress';

describe('useProgress', () => {
  let progress;

  beforeEach(() => {
    vi.useFakeTimers();
    progress = useProgress({
      autoResetDelay: 1000,
      enableAutoReset: false,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe('初始化状态', () => {
    it('应该初始化为空闲状态', () => {
      expect(progress.isRunning.value).toBe(false);
      expect(progress.status.value).toBe(OPERATION_STATUS.IDLE);
      expect(progress.progress.value).toBe(0);
      expect(progress.operationName.value).toBe('');
      expect(progress.message.value).toBe('');
    });

    it('应该初始化所有计算属性', () => {
      expect(progress.isCompleted.value).toBe(false);
      expect(progress.isCancellable.value).toBe(false);
      expect(progress.isPausable.value).toBe(false);
      expect(progress.isResumable.value).toBe(false);
      expect(progress.duration.value).toBe(0);
    });
  });

  describe('开始操作', () => {
    it('应该正确开始操作', () => {
      const controller = progress.startOperation('测试操作', {
        total: 100,
        description: '测试描述',
      });

      expect(progress.isRunning.value).toBe(true);
      expect(progress.status.value).toBe(OPERATION_STATUS.RUNNING);
      expect(progress.operationName.value).toBe('测试操作');
      expect(progress.message.value).toBe('测试描述');
      expect(progress.metadata.value.total).toBe(100);
      expect(controller).toBeInstanceOf(AbortController);
    });

    it('应该设置开始时间', () => {
      const now = Date.now();
      vi.setSystemTime(now);

      progress.startOperation('测试操作');

      expect(progress.startTime.value).toBe(now);
    });

    it('应该重置之前的状态', () => {
      progress.startOperation('第一个操作');
      progress.completeOperation();
      
      progress.startOperation('第二个操作');
      
      expect(progress.operationName.value).toBe('第二个操作');
      expect(progress.progress.value).toBe(0);
      expect(progress.status.value).toBe(OPERATION_STATUS.RUNNING);
    });

    it('应该初始化子任务', () => {
      const subtasks = [
        { name: '任务1', status: 'pending' },
        { name: '任务2', status: 'pending' },
      ];

      progress.startOperation('测试操作', { subtasks });

      expect(progress.subtasks.value).toHaveLength(2);
      expect(progress.activeSubtaskIndex.value).toBe(0);
    });
  });

  describe('更新进度', () => {
    it('应该正确更新进度', () => {
      progress.startOperation('测试操作');
      progress.updateProgress(50, '处理中...');

      expect(progress.progress.value).toBe(50);
      expect(progress.message.value).toBe('处理中...');
    });

    it('应该限制进度值在0-100之间', () => {
      progress.startOperation('测试操作');
      
      progress.updateProgress(150);
      expect(progress.progress.value).toBe(100);
      
      progress.updateProgress(-10);
      expect(progress.progress.value).toBe(0);
    });

    it('应该正确增加进度', () => {
      progress.startOperation('测试操作');
      progress.updateProgress(30);
      progress.incrementProgress(20, '继续处理');

      expect(progress.progress.value).toBe(50);
      expect(progress.message.value).toBe('继续处理');
    });

    it('应该更新子任务状态', () => {
      progress.startOperation('测试操作', {
        subtasks: [
          { name: '任务1', status: 'pending' },
          { name: '任务2', status: 'pending' },
        ],
      });

      progress.updateSubtask(0, 'running', '正在执行任务1');

      expect(progress.subtasks.value[0].status).toBe('running');
      expect(progress.subtasks.value[0].message).toBe('正在执行任务1');
      expect(progress.activeSubtaskIndex.value).toBe(0);
    });
  });

  describe('完成操作', () => {
    it('应该正确完成操作', () => {
      const onComplete = vi.fn();
      progress = useProgress({ onComplete, enableAutoReset: false });
      
      progress.startOperation('测试操作');
      progress.completeOperation('操作完成');

      expect(progress.isRunning.value).toBe(false);
      expect(progress.status.value).toBe(OPERATION_STATUS.COMPLETED);
      expect(progress.progress.value).toBe(100);
      expect(progress.message.value).toBe('操作完成');
      expect(onComplete).toHaveBeenCalled();
    });

    it('应该设置结束时间', () => {
      const now = Date.now();
      vi.setSystemTime(now);

      progress.startOperation('测试操作');
      vi.advanceTimersByTime(1000);
      progress.completeOperation();

      expect(progress.endTime.value).toBe(now + 1000);
    });

    it('应该清除AbortController', () => {
      progress.startOperation('测试操作');
      expect(progress.abortController.value).not.toBeNull();

      progress.completeOperation();
      expect(progress.abortController.value).toBeNull();
    });
  });

  describe('失败操作', () => {
    it('应该正确标记操作失败', () => {
      const onFail = vi.fn();
      progress = useProgress({ onFail, enableAutoReset: false });
      
      progress.startOperation('测试操作');
      progress.failOperation(new Error('测试错误'), '操作失败');

      expect(progress.isRunning.value).toBe(false);
      expect(progress.status.value).toBe(OPERATION_STATUS.FAILED);
      expect(progress.error.value).toBeInstanceOf(Error);
      expect(progress.message.value).toBe('操作失败');
      expect(onFail).toHaveBeenCalled();
    });

    it('应该保存错误信息', () => {
      progress.startOperation('测试操作');
      progress.failOperation('错误字符串');

      expect(progress.error.value).toBe('错误字符串');
    });
  });

  describe('取消操作', () => {
    it('应该正确取消操作', () => {
      const onCancel = vi.fn();
      progress = useProgress({ onCancel, enableAutoReset: false });
      
      progress.startOperation('测试操作');
      progress.cancelOperation('用户取消');

      expect(progress.isRunning.value).toBe(false);
      expect(progress.status.value).toBe(OPERATION_STATUS.CANCELLED);
      expect(progress.message.value).toBe('用户取消');
      expect(onCancel).toHaveBeenCalled();
    });

    it('应该触发AbortController', () => {
      const controller = progress.startOperation('测试操作');
      const abortSpy = vi.spyOn(controller, 'abort');

      progress.cancelOperation();

      expect(abortSpy).toHaveBeenCalled();
    });

    it('不应该取消非运行状态的操作', () => {
      progress.cancelOperation();

      expect(progress.status.value).toBe(OPERATION_STATUS.IDLE);
    });
  });

  describe('暂停和恢复', () => {
    it('应该正确暂停操作', () => {
      progress.startOperation('测试操作');
      progress.pauseOperation();

      expect(progress.status.value).toBe(OPERATION_STATUS.PAUSED);
      expect(progress.isPausable.value).toBe(false);
      expect(progress.isResumable.value).toBe(true);
    });

    it('应该正确恢复操作', () => {
      progress.startOperation('测试操作');
      progress.pauseOperation();
      progress.resumeOperation();

      expect(progress.status.value).toBe(OPERATION_STATUS.RUNNING);
      expect(progress.isPausable.value).toBe(true);
      expect(progress.isResumable.value).toBe(false);
    });

    it('不应该暂停非运行状态的操作', () => {
      progress.pauseOperation();
      expect(progress.status.value).toBe(OPERATION_STATUS.IDLE);
    });
  });

  describe('计算属性', () => {
    it('应该计算操作持续时间', () => {
      vi.setSystemTime(0);
      progress.startOperation('测试操作');
      
      vi.advanceTimersByTime(5000);
      
      expect(progress.duration.value).toBe(5000);
    });

    it('应该格式化持续时间', () => {
      vi.setSystemTime(0);
      progress.startOperation('测试操作');
      
      vi.advanceTimersByTime(1500);
      expect(progress.formattedDuration.value).toBe('1.5s');
      
      vi.advanceTimersByTime(60000);
      expect(progress.formattedDuration.value).toContain('m');
    });

    it('应该计算预计剩余时间', () => {
      vi.setSystemTime(0);
      progress.startOperation('测试操作');
      
      vi.advanceTimersByTime(1000);
      progress.updateProgress(50);
      
      // 已用1秒完成50%，预计总时间2秒，剩余1秒
      expect(progress.estimatedTimeRemaining.value).toBe(1000);
    });

    it('应该在进度为0或100时不计算预计时间', () => {
      progress.startOperation('测试操作');
      expect(progress.estimatedTimeRemaining.value).toBe(0);
      
      progress.updateProgress(100);
      expect(progress.estimatedTimeRemaining.value).toBe(0);
    });
  });

  describe('快照功能', () => {
    it('应该获取进度快照', () => {
      progress.startOperation('测试操作', { total: 100 });
      progress.updateProgress(50, '处理中');

      const snapshot = progress.getSnapshot();

      expect(snapshot.isRunning).toBe(true);
      expect(snapshot.progress).toBe(50);
      expect(snapshot.operationName).toBe('测试操作');
      expect(snapshot.message).toBe('处理中');
      expect(snapshot.metadata.total).toBe(100);
    });

    it('应该从快照恢复进度', () => {
      const snapshot = {
        isRunning: true,
        progress: 75,
        status: OPERATION_STATUS.RUNNING,
        operationName: '恢复的操作',
        message: '恢复的消息',
        error: null,
        startTime: Date.now(),
        endTime: null,
        metadata: { total: 200 },
        subtasks: [],
        activeSubtaskIndex: -1,
      };

      progress.restoreFromSnapshot(snapshot);

      expect(progress.isRunning.value).toBe(true);
      expect(progress.progress.value).toBe(75);
      expect(progress.operationName.value).toBe('恢复的操作');
    });
  });

  describe('自动重置', () => {
    it('应该在操作完成后自动重置', () => {
      vi.useRealTimers();
      
      progress = useProgress({
        autoResetDelay: 100,
        enableAutoReset: true,
      });

      progress.startOperation('测试操作');
      progress.completeOperation();

      expect(progress.status.value).toBe(OPERATION_STATUS.COMPLETED);

      return new Promise(resolve => {
        setTimeout(() => {
          expect(progress.status.value).toBe(OPERATION_STATUS.IDLE);
          resolve();
        }, 150);
      });
    });
  });

  describe('重置功能', () => {
    it('应该重置所有状态', () => {
      progress.startOperation('测试操作');
      progress.updateProgress(50);
      progress.failOperation('错误');

      progress.resetProgress();

      expect(progress.isRunning.value).toBe(false);
      expect(progress.progress.value).toBe(0);
      expect(progress.status.value).toBe(OPERATION_STATUS.IDLE);
      expect(progress.operationName.value).toBe('');
      expect(progress.error.value).toBeNull();
    });
  });
});

describe('createProgressTracker', () => {
  it('应该创建进度跟踪器', () => {
    const updater = vi.fn();
    const tracker = createProgressTracker(updater);

    expect(tracker).toHaveProperty('report');
    expect(tracker).toHaveProperty('increment');
    expect(tracker).toHaveProperty('complete');
    expect(tracker).toHaveProperty('getProgress');
  });

  it('应该报告进度', () => {
    const updater = vi.fn();
    const tracker = createProgressTracker(updater);

    tracker.report(50, '处理中');

    expect(updater).toHaveBeenCalledWith(50, '处理中');
    expect(tracker.getProgress()).toBe(50);
  });

  it('应该增加进度', () => {
    const updater = vi.fn();
    const tracker = createProgressTracker(updater);

    tracker.report(30);
    tracker.increment(20, '继续');

    expect(updater).toHaveBeenCalledWith(50, '继续');
  });

  it('应该完成进度', () => {
    const updater = vi.fn();
    const tracker = createProgressTracker(updater);

    tracker.complete('完成');

    expect(updater).toHaveBeenCalledWith(100, '完成');
  });

  it('应该在完成后不再接受更新', () => {
    const updater = vi.fn();
    const tracker = createProgressTracker(updater);

    tracker.complete('完成');
    tracker.report(50, '尝试更新');

    expect(updater).toHaveBeenCalledTimes(1);
    expect(updater).toHaveBeenCalledWith(100, '完成');
  });
});
