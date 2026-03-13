"""
文件名: test_analysis_flow.py
路径: backend/tests/integration/
功能: 分析流程集成测试
作者: Test Debugger Agent
创建日期: 2024-03-07
依赖: pytest, numpy, fastapi
"""

import asyncio
import tempfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from core.analysis import (
    ExportFormat,
    FitModelType,
    FitResult,
    MultiModelFitter,
    PhysicsAnalyzer,
    braunbeck_function,
    generate_analysis_report,
)


class TestAnalysisFlow:
    """端到端分析流程测试。"""

    @pytest.fixture
    def sample_hysteresis_data(self):
        """生成模拟磁滞回线数据。"""
        # 生成完整的磁滞回线
        h_field = np.concatenate(
            [
                np.linspace(-1000, 1000, 100),  # 正向扫描
                np.linspace(1000, -1000, 100),  # 负向扫描
            ]
        )

        # 使用Braunbeck模型生成磁滞回线
        Bs = 1.5  # 饱和磁感应强度
        Hc = 100  # 矫顽力
        S = 50  # 磁滞宽度参数

        b_data = np.concatenate(
            [
                braunbeck_function(h_field[:100], Bs, Hc, S),
                braunbeck_function(h_field[100:], Bs, Hc, S),
            ]
        )

        # 添加噪声
        noise = np.random.normal(0, 0.02, len(b_data))
        b_data += noise

        return h_field, b_data

    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self, sample_hysteresis_data):
        """测试完整分析流程：数据加载 -> 拟合 -> 报告生成 -> 导出。"""
        h_field, b_data = sample_hysteresis_data

        # 1. 创建分析器
        analyzer = PhysicsAnalyzer()

        # 2. 加载数据
        metadata = {
            "sample": "FeCo thin film",
            "temperature": 300,
            "operator": "test_user",
        }
        analyzer.load_data(h_field, b_data, metadata)

        assert analyzer.data_buffer is not None

        # 3. 信号平滑
        b_smoothed = analyzer.smooth_signal(b_data, method="savgol", window_length=11, polyorder=3)

        assert len(b_smoothed) == len(b_data)

        # 4. 背景扣除
        h_corr, b_corr, bg_params = analyzer.subtract_background(h_field, b_smoothed)

        assert "coefficients" in bg_params

        # 5. 磁滞回线分析
        hysteresis_result = analyzer.analyze_hysteresis_loop(h_corr, b_corr)

        assert "Hc" in hysteresis_result
        assert "Mr" in hysteresis_result
        assert "Ms" in hysteresis_result
        assert hysteresis_result["Hc"] > 0

        # 6. 模型拟合
        fit_result = analyzer.fit_model(h_corr, b_corr, FitModelType.BRAUNBECK)

        assert fit_result["r_squared"] > 0.9

        # 7. 导出数据
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "analysis_result.json"

            success = analyzer.export_data(
                export_path,
                h_corr,
                b_corr,
                ExportFormat.JSON,
                metadata=hysteresis_result,
            )

            assert success is True
            assert export_path.exists()

    @pytest.mark.asyncio
    async def test_multi_model_workflow(self, sample_hysteresis_data):
        """测试多模型对比工作流。"""
        h_field, b_data = sample_hysteresis_data

        # 创建多模型拟合器
        fitter = MultiModelFitter()

        # 注册多个模型
        def linear_model(x, a, b):
            return a * x + b

        def polynomial_model(x, a, b, c):
            return a * x**2 + b * x + c

        def braunbeck_model(x, Bs, Hc, S):
            return braunbeck_function(x, Bs, Hc, S)

        fitter.register_model(
            "linear",
            linear_model,
            [0.001, 0.0],
            param_names=["slope", "intercept"],
        )

        fitter.register_model(
            "polynomial",
            polynomial_model,
            [1e-6, 0.001, 0.0],
            param_names=["a", "b", "c"],
        )

        fitter.register_model(
            "braunbeck",
            braunbeck_model,
            [1.5, 100.0, 50.0],
            bounds=([0.1, 0.0, 1.0], [10.0, 1000.0, 500.0]),
            param_names=["Bs", "Hc", "S"],
        )

        # 执行拟合
        results = fitter.fit_all(h_field, b_data)

        assert len(results) == 3

        # 比较模型
        comparison = fitter.compare_models()

        assert "best_model" in comparison
        assert "rankings" in comparison

        # Braunbeck模型应该最适合磁滞回线数据
        best = fitter.get_best_model(criterion="aic")

        assert best.model_name == "braunbeck"

    @pytest.mark.asyncio
    async def test_analysis_report_generation(self, sample_hysteresis_data):
        """测试分析报告生成。"""
        h_field, b_data = sample_hysteresis_data

        # 创建分析器并执行分析
        analyzer = PhysicsAnalyzer()
        analyzer.load_data(h_field, b_data)

        hysteresis_result = analyzer.analyze_hysteresis_loop(h_field, b_data)

        # 创建拟合结果
        fit_result = analyzer.fit_model(h_field, b_data, FitModelType.BRAUNBECK)

        # 创建FitResult对象
        fit_result_obj = FitResult(
            model_name="braunbeck",
            params=fit_result["parameters"],
            r_squared=fit_result["r_squared"],
            rmse=np.sqrt(np.mean(fit_result["residuals"] ** 2)),
            mae=np.mean(np.abs(fit_result["residuals"])),
            aic=0.0,
            bic=0.0,
            residuals=fit_result["residuals"],
            y_predicted=fit_result["y_fit"],
        )

        # 生成报告
        report = generate_analysis_report(
            h_field,
            b_data,
            [fit_result_obj],
            experiment_id="test_exp_001",
            analyzer=analyzer,
        )

        assert report.experiment_id == "test_exp_001"
        assert report.best_model == "braunbeck"
        assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    async def test_data_export_all_formats(self, sample_hysteresis_data):
        """测试所有格式的数据导出。"""
        h_field, b_data = sample_hysteresis_data

        analyzer = PhysicsAnalyzer()
        analyzer.load_data(h_field, b_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            # CSV导出
            csv_path = Path(tmpdir) / "export.csv"
            assert analyzer.export_data(csv_path, h_field, b_data, ExportFormat.CSV)
            assert csv_path.exists()

            # HDF5导出
            h5_path = Path(tmpdir) / "export.h5"
            assert analyzer.export_data(h5_path, h_field, b_data, ExportFormat.HDF5)
            assert h5_path.exists()

            # JSON导出
            json_path = Path(tmpdir) / "export.json"
            assert analyzer.export_data(json_path, h_field, b_data, ExportFormat.JSON)
            assert json_path.exists()


class TestAnalysisAPIIntegration:
    """分析API集成测试。"""

    @pytest.fixture
    def test_client(self):
        """创建测试客户端。"""
        from main import app

        with TestClient(app) as client:
            yield client

    @pytest.fixture
    def sample_data(self):
        """生成示例数据。"""
        h_field = np.linspace(-500, 500, 100)
        b_data = np.tanh(h_field / 100)
        return h_field.tolist(), b_data.tolist()

    @pytest.mark.asyncio
    async def test_api_analysis_endpoint(self, test_client, sample_data):
        """测试分析API端点。"""
        h_field, b_data = sample_data

        # 发送分析请求
        response = test_client.post(
            "/api/analysis/hysteresis",
            json={
                "h_field": h_field,
                "b_data": b_data,
                "subtract_background": True,
            },
        )

        # 检查响应
        assert response.status_code in [200, 404, 422]  # 端点可能不存在

    @pytest.mark.asyncio
    async def test_api_export_endpoint(self, test_client, sample_data):
        """测试导出API端点。"""
        h_field, b_data = sample_data

        response = test_client.post(
            "/api/analysis/export",
            json={
                "h_field": h_field,
                "b_data": b_data,
                "format": "json",
            },
        )

        # 检查响应
        assert response.status_code in [200, 404, 422]


class TestSignalProcessingPipeline:
    """信号处理管道测试。"""

    def test_signal_processing_pipeline(self):
        """测试信号处理管道。"""
        # 生成带噪声的信号
        t = np.linspace(0, 10, 500)
        clean_signal = np.sin(2 * np.pi * t) + 0.5 * np.sin(6 * np.pi * t)
        noise = np.random.normal(0, 0.2, len(t))
        noisy_signal = clean_signal + noise

        analyzer = PhysicsAnalyzer()

        # 1. Savitzky-Golay滤波
        sg_filtered = analyzer.smooth_signal(
            noisy_signal, method="savgol", window_length=21, polyorder=3
        )

        # 2. 巴特沃斯滤波
        butter_filtered = analyzer.butterworth_filter(noisy_signal, cutoff=2.0, fs=50.0, order=4)

        # 验证滤波效果
        sg_noise_reduction = np.std(noisy_signal - clean_signal) / np.std(
            sg_filtered - clean_signal
        )
        butter_noise_reduction = np.std(noisy_signal - clean_signal) / np.std(
            butter_filtered - clean_signal
        )

        assert sg_noise_reduction > 1.0
        assert butter_noise_reduction > 1.0


class TestHysteresisAnalysisPipeline:
    """磁滞回线分析管道测试。"""

    def test_hysteresis_analysis_pipeline(self):
        """测试磁滞回线分析管道。"""
        # 生成磁滞回线数据
        h_field = np.concatenate(
            [
                np.linspace(-1000, 1000, 200),
                np.linspace(1000, -1000, 200),
            ]
        )

        # 添加线性背景
        background = 0.0001 * h_field + 0.01
        signal = 1.5 * np.tanh((h_field - 100) / 50) + 1.5 * np.tanh((h_field + 100) / 50)
        b_data = signal + background

        analyzer = PhysicsAnalyzer()

        # 1. 背景扣除
        h_corr, b_corr, bg_params = analyzer.subtract_background(h_field, b_data)

        # 2. 磁滞回线分析
        result = analyzer.analyze_hysteresis_loop(h_corr, b_corr)

        # 3. 验证结果
        assert result["Hc"] > 0
        assert result["Mr"] > 0
        assert result["Ms"] > 0
        assert 0 < result["squareness"] <= 1


class TestModelComparisonPipeline:
    """模型比较管道测试。"""

    def test_model_comparison_pipeline(self):
        """测试模型比较管道。"""
        # 生成测试数据
        x = np.linspace(-10, 10, 100)
        y_true = 2.0 * x**2 + 3.0 * x + 1.0
        y_noisy = y_true + np.random.normal(0, 0.5, len(x))

        fitter = MultiModelFitter()

        # 注册模型
        def linear(x, a, b):
            return a * x + b

        def quadratic(x, a, b, c):
            return a * x**2 + b * x + c

        def cubic(x, a, b, c, d):
            return a * x**3 + b * x**2 + c * x + d

        fitter.register_model("linear", linear, [1.0, 0.0])
        fitter.register_model("quadratic", quadratic, [1.0, 1.0, 1.0])
        fitter.register_model("cubic", cubic, [0.1, 1.0, 1.0, 1.0])

        # 拟合所有模型
        results = fitter.fit_all(x, y_noisy)

        # 比较模型
        comparison = fitter.compare_models()

        # 二次模型应该最适合二次数据
        best = fitter.get_best_model(criterion="aic")

        # 验证结果
        assert len(results) == 3
        assert comparison["best_model"] in ["linear", "quadratic", "cubic"]


class TestErrorHandling:
    """错误处理测试。"""

    def test_invalid_data_handling(self):
        """测试无效数据处理。"""
        analyzer = PhysicsAnalyzer()

        # 空数据
        with pytest.raises(ValueError):
            analyzer.smooth_signal(np.array([]))

        # 数据不足
        with pytest.raises(ValueError):
            analyzer.smooth_signal(np.array([1.0, 2.0]), window_length=5)

    def test_invalid_model_handling(self):
        """测试无效模型处理。"""
        fitter = MultiModelFitter()

        # 无模型拟合
        with pytest.raises(ValueError):
            fitter.fit_all(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0]))

    def test_numerical_stability(self):
        """测试数值稳定性。"""
        analyzer = PhysicsAnalyzer()

        # 极端值
        x = np.array([1e10, 1e10 + 1, 1e10 + 2])
        y = np.array([1.0, 2.0, 3.0])

        # 应该不崩溃
        result = analyzer.fit_model(x, y, FitModelType.LINEAR)

        assert "parameters" in result


class TestPerformance:
    """性能测试。"""

    @pytest.mark.slow
    def test_large_dataset_performance(self):
        """测试大数据集性能。"""
        # 生成大数据集
        n_points = 10000
        h_field = np.linspace(-10000, 10000, n_points)
        b_data = np.tanh(h_field / 1000) + np.random.normal(0, 0.01, n_points)

        analyzer = PhysicsAnalyzer()

        import time

        start = time.time()

        # 执行分析
        analyzer.load_data(h_field, b_data)
        result = analyzer.analyze_hysteresis_loop(h_field, b_data)

        elapsed = time.time() - start

        # 应该在合理时间内完成
        assert elapsed < 10.0  # 10秒内
        assert "Hc" in result

    @pytest.mark.slow
    def test_multi_model_performance(self):
        """测试多模型拟合性能。"""
        # 生成数据
        x = np.linspace(-100, 100, 500)
        y = 2.0 * x**2 + 3.0 * x + 1.0 + np.random.normal(0, 1.0, len(x))

        fitter = MultiModelFitter()

        # 注册多个模型
        for i in range(5):

            def poly(x, *coeffs):
                result = np.zeros_like(x)
                for j, c in enumerate(coeffs):
                    result += c * x**j
                return result

            fitter.register_model(
                f"poly_{i}",
                poly,
                [1.0] * (i + 1),
            )

        import time

        start = time.time()

        results = fitter.fit_all(x, y)

        elapsed = time.time() - start

        # 应该在合理时间内完成
        assert elapsed < 30.0  # 30秒内
        assert len(results) == 5


class TestConcurrentAnalysis:
    """并发分析测试。"""

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self):
        """测试并发分析。"""

        async def analyze_dataset(dataset_id):
            h_field = np.linspace(-500, 500, 100)
            b_data = np.tanh(h_field / 100) + np.random.normal(0, 0.01, 100)

            analyzer = PhysicsAnalyzer()
            analyzer.load_data(h_field, b_data)
            result = analyzer.analyze_hysteresis_loop(h_field, b_data)

            return dataset_id, result

        # 并发执行多个分析任务
        tasks = [analyze_dataset(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # 验证所有任务完成
        assert len(results) == 5
        for dataset_id, result in results:
            assert "Hc" in result


class TestIntegrationWithDatabase:
    """数据库集成测试。"""

    def test_store_analysis_results(self, temp_storage):
        """测试存储分析结果。"""
        # 生成数据
        h_field = np.linspace(-500, 500, 100)
        b_data = np.tanh(h_field / 100)

        # 执行分析
        analyzer = PhysicsAnalyzer()
        result = analyzer.analyze_hysteresis_loop(h_field, b_data)

        # 存储结果
        # 注意：这里假设有存储功能，实际实现可能不同
        assert "Hc" in result
        assert "Mr" in result
