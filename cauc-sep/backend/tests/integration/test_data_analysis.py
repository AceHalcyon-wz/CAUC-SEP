"""
文件名: test_data_analysis.py
路径: backend/tests/integration/
功能: 数据分析流程集成测试
作者: Test Debugger Agent
创建日期: 2026-03-08
依赖: pytest, numpy, pandas
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from core.analysis import (
    AnalysisReport,
    ExportFormat,
    FitModelType,
    FitResult,
    MultiModelFitter,
    PhysicsAnalyzer,
    braunbeck_function,
    calculate_goodness_of_fit,
    generate_analysis_report,
)
from core.data_pipeline import (
    DataPipeline,
    StreamProcessor,
    TriggerConfig,
)
from core.data_storage import DataStorage


class TestDataLoading:
    """数据加载测试。"""

    @pytest.fixture
    def sample_experiment_data(self):
        """生成示例实验数据。"""
        # 生成磁滞回线数据
        h_field = np.concatenate([
            np.linspace(-1000, 1000, 200),
            np.linspace(1000, -1000, 200),
        ])

        # 使用物理模型生成数据
        Bs = 1.5  # 饱和磁感应强度
        Hc = 100  # 矫顽力
        S = 50    # 磁滞宽度参数

        b_data = np.concatenate([
            braunbeck_function(h_field[:200], Bs, Hc, S),
            braunbeck_function(h_field[200:], Bs, Hc, S),
        ])

        # 添加噪声
        noise = np.random.normal(0, 0.02, len(b_data))
        b_data += noise

        return h_field, b_data

    @pytest.mark.asyncio
    async def test_load_data_from_array(self, sample_experiment_data):
        """测试从数组加载数据。"""
        h_field, b_data = sample_experiment_data

        analyzer = PhysicsAnalyzer()
        analyzer.load_data(h_field, b_data)

        assert analyzer.data_buffer is not None
        assert len(analyzer.data_buffer) == len(h_field)

    @pytest.mark.asyncio
    async def test_load_data_from_csv(self, sample_experiment_data):
        """测试从CSV文件加载数据。"""
        h_field, b_data = sample_experiment_data

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_data.csv"

            # 创建CSV文件
            df = pd.DataFrame({
                "h_field": h_field,
                "b_data": b_data,
            })
            df.to_csv(csv_path, index=False)

            # 加载数据
            analyzer = PhysicsAnalyzer()
            loaded_data = analyzer.load_from_csv(csv_path, "h_field", "b_data")

            assert loaded_data is not None
            assert len(loaded_data[0]) == len(h_field)

    @pytest.mark.asyncio
    async def test_load_data_from_database(self, temp_storage, sample_experiment_data):
        """测试从数据库加载数据。"""
        h_field, b_data = sample_experiment_data

        # 创建实验
        exp_id = temp_storage.start_experiment(name="test_analysis")

        # 添加数据记录
        for i, (h, b) in enumerate(zip(h_field, b_data)):
            temp_storage.add_data_record(
                experiment_id=exp_id,
                position_mm=h / 100,  # 转换为位置
                field_value=h,
                current_value=b,
            )

        # 获取数据
        records = temp_storage.get_experiment_data(exp_id)

        assert len(records) == len(h_field)


class TestDataProcessing:
    """数据处理测试。"""

    @pytest.fixture
    def noisy_signal(self):
        """生成带噪声的信号。"""
        t = np.linspace(0, 10, 500)
        clean_signal = np.sin(2 * np.pi * t) + 0.5 * np.sin(6 * np.pi * t)
        noise = np.random.normal(0, 0.3, len(t))
        return t, clean_signal, clean_signal + noise

    @pytest.mark.asyncio
    async def test_signal_smoothing_savgol(self, noisy_signal):
        """测试Savitzky-Golay滤波。"""
        t, clean, noisy = noisy_signal

        analyzer = PhysicsAnalyzer()
        smoothed = analyzer.smooth_signal(
            noisy,
            method="savgol",
            window_length=21,
            polyorder=3,
        )

        # 验证滤波效果
        noise_reduction = np.std(noisy - clean) / np.std(smoothed - clean)
        assert noise_reduction > 1.0

    @pytest.mark.asyncio
    async def test_signal_smoothing_butterworth(self, noisy_signal):
        """测试巴特沃斯滤波。"""
        t, clean, noisy = noisy_signal

        analyzer = PhysicsAnalyzer()
        filtered = analyzer.butterworth_filter(
            noisy,
            cutoff=2.0,
            fs=50.0,
            order=4,
        )

        # 验证滤波效果
        noise_reduction = np.std(noisy - clean) / np.std(filtered - clean)
        assert noise_reduction > 1.0

    @pytest.mark.asyncio
    async def test_background_subtraction(self):
        """测试背景扣除。"""
        # 生成带线性背景的信号
        x = np.linspace(-100, 100, 200)
        signal = np.tanh(x / 20)
        background = 0.01 * x + 0.5
        data = signal + background

        analyzer = PhysicsAnalyzer()
        x_corr, data_corr, bg_params = analyzer.subtract_background(x, data)

        # 验证背景参数
        assert "coefficients" in bg_params

        # 验证背景被扣除
        assert np.abs(np.mean(data_corr)) < 0.1

    @pytest.mark.asyncio
    async def test_data_normalization(self):
        """测试数据归一化。"""
        data = np.random.randn(100) * 10 + 5

        analyzer = PhysicsAnalyzer()
        normalized = analyzer.normalize_data(data, method="minmax")

        # 验证归一化范围
        assert normalized.min() >= 0
        assert normalized.max() <= 1

    @pytest.mark.asyncio
    async def test_data_outlier_removal(self):
        """测试异常值移除。"""
        data = np.random.randn(100)
        # 添加异常值
        data[10] = 100
        data[50] = -100

        analyzer = PhysicsAnalyzer()
        cleaned = analyzer.remove_outliers(data, method="iqr", threshold=1.5)

        # 验证异常值被移除
        assert np.max(np.abs(cleaned)) < 10


class TestDataAnalysis:
    """数据分析测试。"""

    @pytest.fixture
    def hysteresis_data(self):
        """生成磁滞回线数据。"""
        h_field = np.concatenate([
            np.linspace(-1000, 1000, 200),
            np.linspace(1000, -1000, 200),
        ])

        Bs = 1.5
        Hc = 100
        S = 50

        b_data = np.concatenate([
            braunbeck_function(h_field[:200], Bs, Hc, S),
            braunbeck_function(h_field[200:], Bs, Hc, S),
        ])

        return h_field, b_data, Bs, Hc, S

    @pytest.mark.asyncio
    async def test_hysteresis_analysis(self, hysteresis_data):
        """测试磁滞回线分析。"""
        h_field, b_data, Bs, Hc, S = hysteresis_data

        analyzer = PhysicsAnalyzer()
        result = analyzer.analyze_hysteresis_loop(h_field, b_data)

        # 验证关键参数
        assert "Hc" in result
        assert "Mr" in result
        assert "Ms" in result
        assert "squareness" in result

        # 验证参数值在合理范围内
        assert 50 < result["Hc"] < 200
        assert result["Ms"] > 0
        assert 0 < result["squareness"] <= 1

    @pytest.mark.asyncio
    async def test_model_fitting_braunbeck(self, hysteresis_data):
        """测试Braunbeck模型拟合。"""
        h_field, b_data, Bs, Hc, S = hysteresis_data

        analyzer = PhysicsAnalyzer()
        result = analyzer.fit_model(h_field, b_data, FitModelType.BRAUNBECK)

        # 验证拟合结果
        assert "parameters" in result
        assert "r_squared" in result
        assert result["r_squared"] > 0.95

        # 验证参数估计
        params = result["parameters"]
        assert np.abs(params[0] - Bs) / Bs < 0.1  # Bs误差小于10%
        assert np.abs(params[1] - Hc) / Hc < 0.1  # Hc误差小于10%

    @pytest.mark.asyncio
    async def test_model_fitting_linear(self):
        """测试线性模型拟合。"""
        x = np.linspace(0, 10, 100)
        y = 2.5 * x + 1.0 + np.random.normal(0, 0.1, 100)

        analyzer = PhysicsAnalyzer()
        result = analyzer.fit_model(x, y, FitModelType.LINEAR)

        assert "parameters" in result
        assert np.abs(result["parameters"][0] - 2.5) < 0.1
        assert np.abs(result["parameters"][1] - 1.0) < 0.1

    @pytest.mark.asyncio
    async def test_model_fitting_polynomial(self):
        """测试多项式模型拟合。"""
        x = np.linspace(-5, 5, 100)
        y = 0.5 * x**2 + 2 * x + 1 + np.random.normal(0, 0.2, 100)

        analyzer = PhysicsAnalyzer()
        result = analyzer.fit_model(x, y, FitModelType.POLYNOMIAL, degree=2)

        assert "parameters" in result
        assert result["r_squared"] > 0.95

    @pytest.mark.asyncio
    async def test_multi_model_comparison(self, hysteresis_data):
        """测试多模型比较。"""
        h_field, b_data, _, _, _ = hysteresis_data

        fitter = MultiModelFitter()

        # 注册多个模型
        fitter.register_model(
            "linear",
            lambda x, a, b: a * x + b,
            [0.001, 0.0],
        )

        fitter.register_model(
            "braunbeck",
            braunbeck_function,
            [1.5, 100.0, 50.0],
            bounds=([0.1, 0.0, 1.0], [10.0, 1000.0, 500.0]),
        )

        # 拟合所有模型
        results = fitter.fit_all(h_field, b_data)

        # 比较模型
        comparison = fitter.compare_models()

        assert len(results) == 2
        assert "best_model" in comparison
        assert comparison["best_model"] == "braunbeck"


class TestDataExport:
    """数据导出测试。"""

    @pytest.fixture
    def sample_data(self):
        """生成示例数据。"""
        h_field = np.linspace(-500, 500, 100)
        b_data = np.tanh(h_field / 100)
        return h_field, b_data

    @pytest.mark.asyncio
    async def test_export_to_csv(self, sample_data):
        """测试导出为CSV格式。"""
        h_field, b_data = sample_data

        analyzer = PhysicsAnalyzer()

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "export.csv"

            success = analyzer.export_data(
                export_path,
                h_field,
                b_data,
                ExportFormat.CSV,
            )

            assert success is True
            assert export_path.exists()

            # 验证文件内容
            df = pd.read_csv(export_path)
            assert len(df) == len(h_field)

    @pytest.mark.asyncio
    async def test_export_to_json(self, sample_data):
        """测试导出为JSON格式。"""
        h_field, b_data = sample_data

        analyzer = PhysicsAnalyzer()

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "export.json"

            success = analyzer.export_data(
                export_path,
                h_field,
                b_data,
                ExportFormat.JSON,
                metadata={"experiment": "test"},
            )

            assert success is True
            assert export_path.exists()

            # 验证文件内容
            with open(export_path) as f:
                data = json.load(f)

            assert "h_field" in data
            assert "b_data" in data

    @pytest.mark.asyncio
    async def test_export_to_hdf5(self, sample_data):
        """测试导出为HDF5格式。"""
        h_field, b_data = sample_data

        analyzer = PhysicsAnalyzer()

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "export.h5"

            success = analyzer.export_data(
                export_path,
                h_field,
                b_data,
                ExportFormat.HDF5,
            )

            assert success is True
            assert export_path.exists()


class TestAnalysisReport:
    """分析报告测试。"""

    @pytest.fixture
    def analysis_result(self):
        """生成分析结果。"""
        h_field = np.linspace(-500, 500, 100)
        b_data = np.tanh(h_field / 100)

        analyzer = PhysicsAnalyzer()
        analyzer.load_data(h_field, b_data)

        hysteresis_result = analyzer.analyze_hysteresis_loop(h_field, b_data)
        fit_result = analyzer.fit_model(h_field, b_data, FitModelType.BRAUNBECK)

        fit_result_obj = FitResult(
            model_name="braunbeck",
            params=fit_result["parameters"],
            r_squared=fit_result["r_squared"],
            rmse=np.sqrt(np.mean(fit_result["residuals"]**2)),
            mae=np.mean(np.abs(fit_result["residuals"])),
            aic=0.0,
            bic=0.0,
            residuals=fit_result["residuals"],
            y_predicted=fit_result["y_fit"],
        )

        return h_field, b_data, [fit_result_obj], hysteresis_result

    @pytest.mark.asyncio
    async def test_generate_report(self, analysis_result):
        """测试生成分析报告。"""
        h_field, b_data, fit_results, hysteresis_result = analysis_result

        report = generate_analysis_report(
            h_field,
            b_data,
            fit_results,
            experiment_id="test_001",
        )

        assert report.experiment_id == "test_001"
        assert report.best_model == "braunbeck"
        assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    async def test_report_to_dict(self, analysis_result):
        """测试报告转换为字典。"""
        h_field, b_data, fit_results, _ = analysis_result

        report = generate_analysis_report(
            h_field,
            b_data,
            fit_results,
        )

        report_dict = report.to_dict()

        assert "experiment_id" in report_dict
        assert "best_model" in report_dict
        assert "fit_results" in report_dict

    @pytest.mark.asyncio
    async def test_report_to_json(self, analysis_result):
        """测试报告转换为JSON。"""
        h_field, b_data, fit_results, _ = analysis_result

        report = generate_analysis_report(
            h_field,
            b_data,
            fit_results,
        )

        report_json = report.to_json()

        # 验证JSON格式
        parsed = json.loads(report_json)
        assert "experiment_id" in parsed


class TestDataPipelineIntegration:
    """数据管道集成测试。"""

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self):
        """测试完整管道流程。"""
        # 创建数据点
        data_points = []
        for i in range(100):
            data_points.append({
                "timestamp": i * 0.1,
                "position_mm": i * 0.5,
                "field_value": np.sin(i * 0.1) * 100,
                "current_value": np.cos(i * 0.1) * 10,
            })

        # 创建处理器
        processor = StreamProcessor(buffer_size=1000)

        # 处理数据
        for point in data_points:
            processor.process(np.array([point["field_value"], point["current_value"]]))

        assert processor._buffer.count >= 0

    @pytest.mark.asyncio
    async def test_stream_processor(self):
        """测试流处理器。"""
        processor = StreamProcessor(
            buffer_size=50,
            backpressure_enabled=True,
        )

        # 添加数据点
        for i in range(100):
            processor.process(np.array([np.sin(i * 0.1), i * 0.01]))

        # 验证缓冲区
        assert processor._buffer.count <= 50  # 缓冲区大小限制


class TestAnalysisWithDatabase:
    """与数据库集成的分析测试。"""

    @pytest.fixture
    def temp_storage(self):
        """创建临时存储。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        storage = DataStorage(db_path, enable_monitoring=False)
        yield storage

        # 清理
        Path(db_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_analyze_experiment_data(self, temp_storage):
        """测试分析实验数据。"""
        # 创建实验
        exp_id = temp_storage.start_experiment(name="analysis_test")

        # 添加数据
        h_field = np.linspace(-500, 500, 100)
        b_data = np.tanh(h_field / 100)

        for i, (h, b) in enumerate(zip(h_field, b_data)):
            temp_storage.add_data_record(
                experiment_id=exp_id,
                position_mm=h / 100,
                field_value=h,
                current_value=b,
            )

        # 获取数据并分析
        records = temp_storage.get_experiment_data(exp_id)

        h_field_loaded = np.array([r["field_value"] for r in records])
        b_data_loaded = np.array([r["current_value"] for r in records])

        analyzer = PhysicsAnalyzer()
        result = analyzer.analyze_hysteresis_loop(h_field_loaded, b_data_loaded)

        assert "Hc" in result

    @pytest.mark.asyncio
    async def test_store_analysis_results(self, temp_storage):
        """测试存储分析结果。"""
        # 创建实验
        exp_id = temp_storage.start_experiment(name="store_analysis")

        # 执行分析
        h_field = np.linspace(-500, 500, 100)
        b_data = np.tanh(h_field / 100)

        analyzer = PhysicsAnalyzer()
        result = analyzer.analyze_hysteresis_loop(h_field, b_data)

        # 存储结果（通过元数据）
        temp_storage.update_experiment_progress(
            exp_id,
            current_step=100,
            status="completed",
            data={"analysis_result": result},
        )

        # 验证存储
        exp_data = temp_storage.get_experiment(exp_id)
        assert exp_data is not None


class TestConcurrentAnalysis:
    """并发分析测试。"""

    @pytest.mark.asyncio
    async def test_concurrent_analysis_tasks(self):
        """测试并发分析任务。"""
        async def analyze_dataset(dataset_id):
            h_field = np.linspace(-500, 500, 100)
            b_data = np.tanh(h_field / 100) + np.random.normal(0, 0.01, 100)

            analyzer = PhysicsAnalyzer()
            result = analyzer.analyze_hysteresis_loop(h_field, b_data)

            return dataset_id, result

        # 并发执行多个分析
        tasks = [analyze_dataset(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # 验证所有任务完成
        assert len(results) == 5
        for dataset_id, result in results:
            assert "Hc" in result

    @pytest.mark.asyncio
    async def test_parallel_model_fitting(self):
        """测试并行模型拟合。"""
        h_field = np.linspace(-500, 500, 100)
        b_data = np.tanh(h_field / 100)

        fitter = MultiModelFitter()

        # 注册多个模型
        models = {
            "linear": (lambda x, a, b: a * x + b, [0.001, 0.0]),
            "quadratic": (lambda x, a, b, c: a * x**2 + b * x + c, [1e-6, 0.001, 0.0]),
            "cubic": (lambda x, a, b, c, d: a * x**3 + b * x**2 + c * x + d, [1e-9, 1e-6, 0.001, 0.0]),
        }

        for name, (func, p0) in models.items():
            fitter.register_model(name, func, p0)

        # 并行拟合
        results = fitter.fit_all(h_field, b_data)

        assert len(results) == 3


class TestErrorHandling:
    """错误处理测试。"""

    @pytest.mark.asyncio
    async def test_invalid_data_handling(self):
        """测试无效数据处理。"""
        analyzer = PhysicsAnalyzer()

        # 空数据
        with pytest.raises(ValueError):
            analyzer.smooth_signal(np.array([]))

        # 数据不足
        with pytest.raises(ValueError):
            analyzer.smooth_signal(np.array([1.0, 2.0]), window_length=5)

    @pytest.mark.asyncio
    async def test_invalid_model_handling(self):
        """测试无效模型处理。"""
        fitter = MultiModelFitter()

        # 无模型拟合
        with pytest.raises(ValueError):
            fitter.fit_all(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0]))

    @pytest.mark.asyncio
    async def test_numerical_stability(self):
        """测试数值稳定性。"""
        analyzer = PhysicsAnalyzer()

        # 极端值
        x = np.array([1e10, 1e10 + 1, 1e10 + 2])
        y = np.array([1.0, 2.0, 3.0])

        # 应该不崩溃
        result = analyzer.fit_model(x, y, FitModelType.LINEAR)

        assert "parameters" in result

    @pytest.mark.asyncio
    async def test_nan_handling(self):
        """测试NaN值处理。"""
        analyzer = PhysicsAnalyzer()

        # 包含NaN的数据
        x = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        y = np.array([1.0, np.nan, 3.0, 4.0, 5.0])

        # 清理NaN
        x_clean, y_clean = analyzer.clean_nan_values(x, y)

        assert len(x_clean) == 3
        assert len(y_clean) == 3


class TestPerformance:
    """性能测试。"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self):
        """测试大数据集性能。"""
        import time

        n_points = 10000
        h_field = np.linspace(-10000, 10000, n_points)
        b_data = np.tanh(h_field / 1000) + np.random.normal(0, 0.01, n_points)

        analyzer = PhysicsAnalyzer()

        start = time.time()
        analyzer.load_data(h_field, b_data)
        result = analyzer.analyze_hysteresis_loop(h_field, b_data)
        elapsed = time.time() - start

        assert elapsed < 10.0
        assert "Hc" in result

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multi_model_performance(self):
        """测试多模型拟合性能。"""
        import time

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

            fitter.register_model(f"poly_{i}", poly, [1.0] * (i + 1))

        start = time.time()
        results = fitter.fit_all(x, y)
        elapsed = time.time() - start

        assert elapsed < 30.0
        assert len(results) == 5
