"""
测试物理数据分析引擎

测试内容：
- 数据加载
- 信号平滑处理（Savitzky-Golay和巴特沃斯）
- 背景扣除
- 矫顽力计算
- 剩磁计算
- 饱和磁矩计算
- 磁滞回线分析
- Langevin函数拟合
- 自定义模型拟合
"""

import warnings

import lmfit
import numpy as np
import pytest

from core.analysis import PhysicsAnalyzer


class TestPhysicsAnalyzerInit:
    """测试物理分析器初始化。"""

    def test_initialization(self):
        """测试初始化。"""
        analyzer = PhysicsAnalyzer()

        assert analyzer.data_buffer is None
        assert analyzer.metadata == {}


class TestDataLoading:
    """测试数据加载。"""

    def test_load_data_basic(self):
        """测试基本数据加载。"""
        analyzer = PhysicsAnalyzer()

        x_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_data = np.array([2.0, 4.0, 6.0, 8.0, 10.0])

        analyzer.load_data(x_data, y_data)

        assert analyzer.data_buffer is not None
        assert analyzer.data_buffer.shape == (5, 2)
        np.testing.assert_array_equal(analyzer.data_buffer[:, 0], x_data)
        np.testing.assert_array_equal(analyzer.data_buffer[:, 1], y_data)

    def test_load_data_with_metadata(self):
        """测试带元数据的数据加载。"""
        analyzer = PhysicsAnalyzer()

        x_data = np.array([1.0, 2.0, 3.0])
        y_data = np.array([2.0, 4.0, 6.0])
        metadata = {"sample": "FeCo", "temperature": 300, "operator": "test_user"}

        analyzer.load_data(x_data, y_data, metadata)

        assert analyzer.metadata == metadata
        assert analyzer.metadata["sample"] == "FeCo"

    def test_load_data_overwrites_previous(self):
        """测试数据加载覆盖之前的数据。"""
        analyzer = PhysicsAnalyzer()

        x1 = np.array([1.0, 2.0, 3.0])
        y1 = np.array([2.0, 4.0, 6.0])
        analyzer.load_data(x1, y1, {"test": 1})

        x2 = np.array([10.0, 20.0, 30.0, 40.0])
        y2 = np.array([20.0, 40.0, 60.0, 80.0])
        analyzer.load_data(x2, y2, {"test": 2})

        assert analyzer.data_buffer.shape == (4, 2)
        assert analyzer.metadata == {"test": 2}


class TestSignalSmoothing:
    """测试信号平滑处理。"""

    def test_savgol_smoothing_basic(self):
        """测试Savitzky-Golay平滑基本功能。"""
        analyzer = PhysicsAnalyzer()

        x = np.linspace(0, 10, 100)
        y_clean = np.sin(x)
        noise = np.random.normal(0, 0.1, len(x))
        y_noisy = y_clean + noise

        y_smoothed = analyzer.smooth_signal(y_noisy, method="savgol", window_length=11, polyorder=2)

        assert len(y_smoothed) == len(y_noisy)
        assert isinstance(y_smoothed, np.ndarray)

        noise_reduction = np.std(y_noisy - y_clean) / np.std(y_smoothed - y_clean)
        assert noise_reduction > 1.0

    def test_savgol_smoothing_preserves_peaks(self):
        """测试Savitzky-Golay平滑保留峰值。"""
        analyzer = PhysicsAnalyzer()

        x = np.linspace(0, 4 * np.pi, 200)
        y = np.sin(x)

        y_smoothed = analyzer.smooth_signal(y, method="savgol", window_length=11, polyorder=3)

        assert np.abs(np.max(y_smoothed) - 1.0) < 0.1
        assert np.abs(np.min(y_smoothed) + 1.0) < 0.1

    def test_savgol_invalid_window_length_even(self):
        """测试Savitzky-Golay无效窗口长度（偶数）。"""
        analyzer = PhysicsAnalyzer()
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        with pytest.raises(ValueError, match="window_length 必须为奇数"):
            analyzer.smooth_signal(y, method="savgol", window_length=10)

    def test_savgol_invalid_window_length_small(self):
        """测试Savitzky-Golay无效窗口长度（过小）。"""
        analyzer = PhysicsAnalyzer()
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        
        with pytest.raises(ValueError, match="window_length"):
            analyzer.smooth_signal(y, method="savgol", window_length=2)

    def test_savgol_invalid_polyorder(self):
        """测试Savitzky-Golay无效多项式阶数。"""
        analyzer = PhysicsAnalyzer()
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])

        with pytest.raises(ValueError, match="polyorder 必须小于 window_length"):
            analyzer.smooth_signal(y, method="savgol", window_length=5, polyorder=5)

    def test_butterworth_smoothing_basic(self):
        """测试巴特沃斯平滑基本功能。"""
        analyzer = PhysicsAnalyzer()

        x = np.linspace(0, 10, 100)
        y_clean = np.sin(x)
        noise = np.random.normal(0, 0.1, len(x))
        y_noisy = y_clean + noise

        y_smoothed = analyzer.smooth_signal(
            y_noisy, method="butter", butter_lowcut=0.1, butter_order=3
        )

        assert len(y_smoothed) == len(y_noisy)
        assert isinstance(y_smoothed, np.ndarray)

    def test_butterworth_filter_method(self):
        """测试巴特沃斯滤波器方法。"""
        analyzer = PhysicsAnalyzer()

        fs = 1000
        t = np.linspace(0, 1, fs)
        freq_signal = 10
        freq_noise = 100

        y_clean = np.sin(2 * np.pi * freq_signal * t)
        y_noise = 0.5 * np.sin(2 * np.pi * freq_noise * t)
        y_noisy = y_clean + y_noise

        y_filtered = analyzer.butterworth_filter(y_noisy, cutoff=20, fs=fs, order=4)

        assert len(y_filtered) == len(y_noisy)

        noise_power_before = np.var(y_noisy - y_clean)
        noise_power_after = np.var(y_filtered - y_clean)
        assert noise_power_after < noise_power_before

    def test_unsupported_method(self):
        """测试不支持的平滑方法。"""
        analyzer = PhysicsAnalyzer()
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        with pytest.raises(ValueError, match="不支持的平滑方法"):
            analyzer.smooth_signal(y, method="invalid_method")


class TestBackgroundSubtraction:
    """测试背景扣除。"""

    def test_background_subtraction_linear(self):
        """测试线性背景扣除。"""
        analyzer = PhysicsAnalyzer()
        
        x = np.linspace(-100, 100, 200)
        slope = 0.01
        intercept = 0.5
        background = slope * x + intercept
        signal = np.tanh(x / 30)
        y = signal + background
        
        x_corr, y_corr, params = analyzer.subtract_background(x, y)
        
        assert "coefficients" in params
        assert "r_squared" in params
        assert abs(params["coefficients"][0] - slope) < 0.02

    def test_background_subtraction_custom_threshold(self):
        """测试自定义阈值背景扣除。"""
        analyzer = PhysicsAnalyzer()

        x = np.linspace(-100, 100, 200)
        y = x * 0.01 + np.tanh(x / 30)

        x_corr, y_corr, params = analyzer.subtract_background(x, y, high_field_threshold=80)

        assert isinstance(params, dict)
        assert "coefficients" in params

    def test_background_subtraction_insufficient_data(self):
        """测试高场数据不足时的背景扣除。"""
        analyzer = PhysicsAnalyzer()

        x = np.array([0.0, 1.0, 2.0])
        y = np.array([1.0, 2.0, 3.0])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            x_corr, y_corr, params = analyzer.subtract_background(x, y, high_field_threshold=1000)

            assert len(w) == 1
            assert "高场数据点不足" in str(w[0].message)

        assert params["coefficients"][0] == 0.0
        assert len(params["coefficients"]) >= 1


class TestCoercivityCalculation:
    """测试矫顽力计算。"""

    def test_coercivity_calculation_ideal(self):
        """测试理想磁滞回线矫顽力计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.linspace(-100, 100, 200)
        moment = np.tanh(h_field / 20)

        hc = analyzer._calculate_coercivity(h_field, moment)

        assert isinstance(hc, float)
        assert hc >= 0
        assert hc < 25

    def test_coercivity_no_zero_crossing(self):
        """测试无过零点时的矫顽力计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.linspace(-100, 100, 100)
        moment = np.ones_like(h_field)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            hc = analyzer._calculate_coercivity(h_field, moment)

            assert len(w) == 1
            assert "未找到磁矩过零点" in str(w[0].message)

        assert hc == 0.0

    def test_coercivity_multiple_crossings(self):
        """测试多个过零点时的矫顽力计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.concatenate([np.linspace(-100, 100, 100), np.linspace(100, -100, 100)])
        moment = np.concatenate([np.tanh(h_field[:100] / 20), np.tanh(h_field[100:] / 20)])

        hc = analyzer._calculate_coercivity(h_field, moment)

        assert isinstance(hc, float)
        assert hc >= 0


class TestRemanenceCalculation:
    """测试剩磁计算。"""

    def test_remanence_calculation_ideal(self):
        """测试理想磁滞回线剩磁计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.linspace(-100, 100, 200)
        moment = np.tanh(h_field / 20)

        mr = analyzer._calculate_remanence(h_field, moment)

        assert isinstance(mr, float)
        assert mr >= 0
        assert mr < 1.0

    def test_remanence_with_zero_field(self):
        """测试包含零场的剩磁计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.array([-100, -50, 0, 50, 100])
        moment = np.array([-0.9, -0.7, 0.8, 0.9, 0.95])

        mr = analyzer._calculate_remanence(h_field, moment)

        assert isinstance(mr, float)
        assert mr >= 0

    def test_remanence_no_zero_crossing(self):
        """测试无过零点时的剩磁计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.linspace(1, 100, 50)
        moment = np.tanh(h_field / 20)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mr = analyzer._calculate_remanence(h_field, moment)

            assert len(w) == 1
            assert "未找到磁场过零点" in str(w[0].message)

        assert mr == 0.0


class TestSaturationMomentCalculation:
    """测试饱和磁矩计算。"""

    def test_saturation_moment_calculation(self):
        """测试饱和磁矩计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.linspace(-100, 100, 200)
        moment = np.tanh(h_field / 20)

        ms = analyzer._calculate_saturation_moment(h_field, moment)

        assert isinstance(ms, float)
        assert ms > 0
        assert ms <= 1.1

    def test_saturation_moment_custom_threshold(self):
        """测试自定义阈值饱和磁矩计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.linspace(-100, 100, 200)
        moment = 2.0 * np.tanh(h_field / 20)

        ms = analyzer._calculate_saturation_moment(h_field, moment, saturation_threshold=80)

        assert isinstance(ms, float)
        assert ms > 0

    def test_saturation_moment_no_saturation_data(self):
        """测试无饱和场数据时的计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.linspace(-10, 10, 50)
        moment = np.tanh(h_field / 20)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ms = analyzer._calculate_saturation_moment(h_field, moment, saturation_threshold=100)

            assert len(w) == 1
            assert "未找到饱和场区数据点" in str(w[0].message)

        assert ms > 0


class TestHysteresisLoopAnalysis:
    """测试磁滞回线分析。"""

    def test_hysteresis_analysis_complete(self):
        """测试完整磁滞回线分析。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.linspace(-1000, 1000, 200)
        h_field = np.concatenate([h_field, h_field[::-1]])
        moment = np.concatenate([np.tanh(h_field[:200] / 200), np.tanh(h_field[200:] / 200)])

        result = analyzer.analyze_hysteresis_loop(h_field, moment, subtract_background=True)

        assert "Hc" in result
        assert "Mr" in result
        assert "Ms" in result
        assert "background_params" in result
        assert "x_corrected" in result
        assert "y_corrected" in result

        assert isinstance(result["Hc"], float)
        assert isinstance(result["Mr"], float)
        assert isinstance(result["Ms"], float)
        assert result["Hc"] >= 0
        assert result["Mr"] >= 0
        assert result["Ms"] > 0

    def test_hysteresis_analysis_no_background_subtraction(self):
        """测试不扣除背景的磁滞回线分析。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.linspace(-100, 100, 100)
        moment = np.tanh(h_field / 20)

        result = analyzer.analyze_hysteresis_loop(h_field, moment, subtract_background=False)

        assert result["background_params"] == {}
        np.testing.assert_array_equal(result["x_corrected"], h_field)
        np.testing.assert_array_equal(result["y_corrected"], moment)

    def test_hysteresis_analysis_with_sample_data(self, sample_hysteresis_data):
        """测试使用示例数据的磁滞回线分析。"""
        analyzer = PhysicsAnalyzer()
        h_field, moment = sample_hysteresis_data

        result = analyzer.analyze_hysteresis_loop(h_field, moment)

        assert result["Hc"] > 0
        assert result["Mr"] > 0
        assert result["Ms"] > 0
        assert result["Ms"] > result["Mr"]


class TestLangevinFit:
    """测试Langevin函数拟合。"""
    
    def test_langevin_fit_basic(self):
        """测试基本Langevin拟合。"""
        analyzer = PhysicsAnalyzer()
        
        h_field = np.linspace(0, 1000, 100)
        ms_true = 1.0
        
        moment = np.tanh(h_field / 200)
        
        result, params = analyzer.fit_langevin(h_field, moment)
        
        assert isinstance(result, lmfit.model.ModelResult)
        assert "Ms" in params
        assert "alpha" in params
        assert "chi2" in params
        assert "redchi" in params
    
    def test_langevin_fit_returns_best_fit(self):
        """测试Langevin拟合返回最佳拟合曲线。"""
        analyzer = PhysicsAnalyzer()
        
        h_field = np.linspace(0, 500, 50)
        moment = np.tanh(h_field / 100)
        
        result, params = analyzer.fit_langevin(h_field, moment)
        
        assert hasattr(result, 'best_fit')
        assert len(result.best_fit) == len(h_field)


class TestCustomModelFit:
    """测试自定义模型拟合。"""

    def test_custom_linear_fit(self):
        """测试自定义线性拟合。"""
        analyzer = PhysicsAnalyzer()

        x_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_data = np.array([2.1, 4.0, 5.9, 8.1, 10.0])

        def linear_model(x, slope, intercept):
            return slope * x + intercept

        result, params = analyzer.fit_custom_model(
            x_data, y_data, linear_model, {"slope": 2.0, "intercept": 0.0}
        )

        assert "slope" in params
        assert "intercept" in params
        assert "chi2" in params

        assert abs(params["slope"] - 2.0) < 0.1
        assert abs(params["intercept"]) < 0.2

    def test_custom_quadratic_fit(self):
        """测试自定义二次拟合。"""
        analyzer = PhysicsAnalyzer()

        x_data = np.linspace(-5, 5, 50)
        y_data = 2 * x_data**2 + 3 * x_data + 1
        noise = np.random.normal(0, 0.5, len(x_data))
        y_noisy = y_data + noise

        def quadratic_model(x, a, b, c):
            return a * x**2 + b * x + c

        result, params = analyzer.fit_custom_model(
            x_data, y_noisy, quadratic_model, {"a": 2.0, "b": 3.0, "c": 1.0}
        )

        assert "a" in params
        assert "b" in params
        assert "c" in params

        assert abs(params["a"] - 2.0) < 0.2
        assert abs(params["b"] - 3.0) < 0.5
        assert abs(params["c"] - 1.0) < 0.5

    def test_custom_exponential_fit(self):
        """测试自定义指数拟合。"""
        analyzer = PhysicsAnalyzer()

        x_data = np.linspace(0, 5, 50)
        y_data = 2.0 * np.exp(-0.5 * x_data)
        noise = np.random.normal(0, 0.05, len(x_data))
        y_noisy = y_data + noise

        def exp_model(x, amplitude, decay):
            return amplitude * np.exp(-decay * x)

        result, params = analyzer.fit_custom_model(
            x_data, y_noisy, exp_model, {"amplitude": 2.0, "decay": 0.5}
        )

        assert "amplitude" in params
        assert "decay" in params

        assert abs(params["amplitude"] - 2.0) < 0.2
        assert abs(params["decay"] - 0.5) < 0.1


class TestEdgeCases:
    """测试边界情况。"""

    def test_empty_data(self):
        """测试空数据。"""
        analyzer = PhysicsAnalyzer()

        x_empty = np.array([])
        y_empty = np.array([])

        analyzer.load_data(x_empty, y_empty)

        assert analyzer.data_buffer is not None
        assert analyzer.data_buffer.shape == (0, 2)

    def test_single_point_data(self):
        """测试单点数据。"""
        analyzer = PhysicsAnalyzer()

        x = np.array([1.0])
        y = np.array([2.0])

        analyzer.load_data(x, y)

        assert analyzer.data_buffer.shape == (1, 2)

    def test_very_large_data(self):
        """测试大数据集。"""
        analyzer = PhysicsAnalyzer()

        n_points = 100000
        x = np.linspace(0, 100, n_points)
        y = np.sin(x)

        analyzer.load_data(x, y)

        assert analyzer.data_buffer.shape == (n_points, 2)

    def test_nan_handling(self):
        """测试NaN值处理。"""
        analyzer = PhysicsAnalyzer()

        x = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        y = np.array([2.0, np.nan, 6.0, 8.0, 10.0])

        analyzer.load_data(x, y)

        assert analyzer.data_buffer is not None


class TestMultiModelFitter:
    """多模型拟合器测试。"""

    def test_register_model(self):
        """测试模型注册。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        def linear_func(x, a, b):
            return a * x + b

        fitter.register_model(
            name="linear",
            func=linear_func,
            initial_params=[1.0, 0.0],
            param_names=["slope", "intercept"],
        )

        assert "linear" in fitter.models

    def test_register_model_duplicate_name(self):
        """测试注册重复名称的模型。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        def func(x, a):
            return a * x

        fitter.register_model("test", func, [1.0])

        with pytest.raises(ValueError, match="已存在"):
            fitter.register_model("test", func, [1.0])

    def test_register_model_invalid_func(self):
        """测试注册无效函数。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        with pytest.raises(ValueError, match="可调用对象"):
            fitter.register_model("test", "not_a_function", [1.0])

    def test_register_model_empty_params(self):
        """测试注册空参数。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        def func(x, a):
            return a * x

        with pytest.raises(ValueError, match="不能为空"):
            fitter.register_model("test", func, [])

    def test_register_model_mismatched_param_names(self):
        """测试参数名称数量不匹配。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        def func(x, a, b):
            return a * x + b

        with pytest.raises(ValueError, match="长度一致"):
            fitter.register_model("test", func, [1.0, 0.0], param_names=["a"])

    def test_fit_all(self):
        """测试多模型拟合。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        x_data = np.linspace(0, 10, 50)
        y_data = 2.0 * x_data + 1.0 + np.random.normal(0, 0.1, 50)

        def linear_func(x, a, b):
            return a * x + b

        def quadratic_func(x, a, b, c):
            return a * x**2 + b * x + c

        fitter.register_model("linear", linear_func, [1.0, 0.0])
        fitter.register_model("quadratic", quadratic_func, [0.1, 1.0, 0.0])

        results = fitter.fit_all(x_data, y_data)

        assert len(results) == 2
        assert all(r.r_squared > 0 for r in results)

    def test_fit_all_no_models(self):
        """测试无模型时拟合。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        x_data = np.linspace(0, 10, 50)
        y_data = x_data

        with pytest.raises(ValueError, match="未注册任何模型"):
            fitter.fit_all(x_data, y_data)

    def test_fit_all_insufficient_data(self):
        """测试数据不足时拟合。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        def func(x, a):
            return a * x

        fitter.register_model("test", func, [1.0])

        with pytest.raises(ValueError, match="至少需要3个点"):
            fitter.fit_all(np.array([1.0, 2.0]), np.array([1.0, 2.0]))

    def test_compare_models(self):
        """测试模型比较。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        x_data = np.linspace(0, 10, 50)
        y_data = 2.0 * x_data + 1.0

        def linear_func(x, a, b):
            return a * x + b

        fitter.register_model("linear", linear_func, [1.0, 0.0])
        fitter.fit_all(x_data, y_data)

        comparison = fitter.compare_models()

        assert "rankings" in comparison
        assert "best_model" in comparison
        assert "delta_aic" in comparison
        assert "aic_weights" in comparison
        assert "summary" in comparison

    def test_compare_models_no_results(self):
        """测试无结果时比较。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        with pytest.raises(ValueError, match="没有拟合结果"):
            fitter.compare_models()

    def test_get_best_model_aic(self):
        """测试根据AIC获取最佳模型。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        x_data = np.linspace(0, 10, 50)
        y_data = 2.0 * x_data + 1.0

        def linear_func(x, a, b):
            return a * x + b

        fitter.register_model("linear", linear_func, [1.0, 0.0])
        fitter.fit_all(x_data, y_data)

        best = fitter.get_best_model(criterion="aic")

        assert best.model_name == "linear"

    def test_get_best_model_r_squared(self):
        """测试根据R²获取最佳模型。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        x_data = np.linspace(0, 10, 50)
        y_data = 2.0 * x_data + 1.0

        def linear_func(x, a, b):
            return a * x + b

        fitter.register_model("linear", linear_func, [1.0, 0.0])
        fitter.fit_all(x_data, y_data)

        best = fitter.get_best_model(criterion="r_squared")

        assert best.r_squared > 0.99

    def test_get_best_model_invalid_criterion(self):
        """测试无效准则。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        x_data = np.linspace(0, 10, 50)
        y_data = x_data

        def func(x, a):
            return a * x

        fitter.register_model("test", func, [1.0])
        fitter.fit_all(x_data, y_data)

        with pytest.raises(ValueError, match="无效的选择准则"):
            fitter.get_best_model(criterion="invalid")

    def test_get_best_model_no_results(self):
        """测试无结果时获取最佳模型。"""
        from core.analysis import MultiModelFitter

        fitter = MultiModelFitter()

        with pytest.raises(ValueError, match="没有拟合结果"):
            fitter.get_best_model()


class TestBraunbeckFunction:
    """Braunbeck函数测试。"""

    def test_braunbeck_fit(self):
        """测试Braunbeck拟合。"""
        from core.analysis import FitModelType, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        # 生成模拟磁滞回线数据
        h_field = np.linspace(-1000, 1000, 200)
        b_data = 1.5 * np.tanh((h_field - 100) / 50) + 1.5 * np.tanh((h_field + 100) / 50)

        result = analyzer.fit_model(h_field, b_data, FitModelType.BRAUNBECK)

        assert result["model_type"] == "braunbeck"
        assert "parameters" in result
        assert "Bs" in result["parameters"]
        assert "Hc" in result["parameters"]
        assert "S" in result["parameters"]
        assert result["r_squared"] > 0.9

    def test_braunbeck_function_basic(self):
        """测试Braunbeck函数基本功能。"""
        from core.analysis import braunbeck_function

        h = np.linspace(-1000, 1000, 100)
        b = braunbeck_function(h, Bs=1.5, Hc=100, S=50)

        assert len(b) == len(h)
        assert np.max(b) > 0
        assert np.min(b) < 0

    def test_braunbeck_function_invalid_s(self):
        """测试Braunbeck函数无效S参数。"""
        from core.analysis import braunbeck_function

        h = np.linspace(-100, 100, 50)

        with pytest.raises(ValueError, match="必须大于零"):
            braunbeck_function(h, Bs=1.0, Hc=10, S=0)

    def test_numerical_stability_large_values(self):
        """测试大值数值稳定性。"""
        from core.analysis import braunbeck_function

        # 非常大的磁场值
        h = np.linspace(-1e6, 1e6, 100)
        b = braunbeck_function(h, Bs=1.0, Hc=100, S=50)

        assert not np.any(np.isnan(b))
        assert not np.any(np.isinf(b))

    def test_numerical_stability_small_s(self):
        """测试小S值数值稳定性。"""
        from core.analysis import braunbeck_function

        h = np.linspace(-100, 100, 100)
        b = braunbeck_function(h, Bs=1.0, Hc=10, S=1e-8)

        assert not np.any(np.isnan(b))


class TestAnalysisReport:
    """分析报告测试。"""

    def test_generate_report(self):
        """测试报告生成。"""
        from core.analysis import (
            AnalysisReport,
            FitResult,
            generate_analysis_report,
        )

        h_data = np.linspace(-1000, 1000, 100)
        b_data = np.tanh(h_data / 200)

        fit_result = FitResult(
            model_name="test_model",
            params={"a": 1.0},
            r_squared=0.99,
            rmse=0.01,
            mae=0.005,
            aic=-100,
            bic=-90,
            residuals=np.zeros(100),
            y_predicted=b_data,
        )

        report = generate_analysis_report(
            h_data, b_data, [fit_result], experiment_id="test_exp"
        )

        assert report.experiment_id == "test_exp"
        assert report.best_model == "test_model"
        assert len(report.fit_results) == 1

    def test_generate_report_auto_id(self):
        """测试自动生成实验ID。"""
        from core.analysis import FitResult, generate_analysis_report

        h_data = np.linspace(-100, 100, 50)
        b_data = np.tanh(h_data / 20)

        fit_result = FitResult(
            model_name="test",
            params={},
            r_squared=0.9,
            rmse=0.1,
            mae=0.05,
            aic=-50,
            bic=-40,
            residuals=np.zeros(50),
            y_predicted=b_data,
        )

        report = generate_analysis_report(h_data, b_data, [fit_result])

        assert report.experiment_id.startswith("exp_")

    def test_generate_report_insufficient_data(self):
        """测试数据不足时生成报告。"""
        from core.analysis import generate_analysis_report

        h_data = np.array([1.0, 2.0])
        b_data = np.array([0.5, 1.0])

        with pytest.raises(ValueError, match="至少需要5个点"):
            generate_analysis_report(h_data, b_data, [])

    def test_generate_report_mismatched_data(self):
        """测试数据长度不匹配。"""
        from core.analysis import generate_analysis_report

        h_data = np.linspace(0, 10, 10)
        b_data = np.linspace(0, 10, 5)

        with pytest.raises(ValueError, match="长度不匹配"):
            generate_analysis_report(h_data, b_data, [])

    def test_recommendations(self):
        """测试建议生成。"""
        from core.analysis import (
            FitResult,
            _generate_recommendations,
        )

        hysteresis_params = {
            "Hc": 100.0,
            "Mr": 0.8,
            "Ms": 1.0,
            "squareness": 0.8,
        }

        fit_result = FitResult(
            model_name="test",
            params={},
            r_squared=0.95,
            rmse=0.05,
            mae=0.03,
            aic=-100,
            bic=-90,
            residuals=np.zeros(100),
            y_predicted=np.zeros(100),
        )

        quality_metrics = {
            "data_density": 50,
            "signal_to_noise": 10,
            "b_range": 2.0,
        }

        recommendations = _generate_recommendations(
            hysteresis_params, [fit_result], quality_metrics
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    def test_recommendations_low_r_squared(self):
        """测试低R²时的建议。"""
        from core.analysis import (
            FitResult,
            _generate_recommendations,
        )

        fit_result = FitResult(
            model_name="test",
            params={},
            r_squared=0.8,
            rmse=0.2,
            mae=0.15,
            aic=-50,
            bic=-40,
            residuals=np.zeros(100),
            y_predicted=np.zeros(100),
        )

        quality_metrics = {"b_range": 1.0}

        recommendations = _generate_recommendations({}, [fit_result], quality_metrics)

        assert any("R²" in r for r in recommendations)

    def test_recommendations_low_density(self):
        """测试低数据密度时的建议。"""
        from core.analysis import _generate_recommendations

        quality_metrics = {"data_density": 5}

        recommendations = _generate_recommendations({}, [], quality_metrics)

        assert any("密度" in r for r in recommendations)


class TestGoodnessOfFit:
    """拟合优度评估测试。"""

    def test_calculate_goodness_of_fit_perfect(self):
        """测试完美拟合。"""
        from core.analysis import calculate_goodness_of_fit

        y_obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = y_obs.copy()

        metrics = calculate_goodness_of_fit(y_obs, y_pred, n_params=2)

        assert metrics["r_squared"] == 1.0
        assert metrics["rmse"] == 0.0
        assert metrics["mae"] == 0.0

    def test_calculate_goodness_of_fit_poor(self):
        """测试较差拟合。"""
        from core.analysis import calculate_goodness_of_fit

        y_obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([5.0, 4.0, 3.0, 2.0, 1.0])

        metrics = calculate_goodness_of_fit(y_obs, y_pred, n_params=2)

        assert metrics["r_squared"] < 0

    def test_calculate_goodness_of_fit_empty(self):
        """测试空数据。"""
        from core.analysis import calculate_goodness_of_fit

        with pytest.raises(ValueError, match="不能为空"):
            calculate_goodness_of_fit(np.array([]), np.array([]), n_params=1)

    def test_calculate_goodness_of_fit_mismatched_length(self):
        """测试长度不匹配。"""
        from core.analysis import calculate_goodness_of_fit

        with pytest.raises(ValueError, match="长度不匹配"):
            calculate_goodness_of_fit(
                np.array([1.0, 2.0, 3.0]),
                np.array([1.0, 2.0]),
                n_params=1,
            )

    def test_calculate_goodness_of_fit_invalid_params(self):
        """测试无效参数数量。"""
        from core.analysis import calculate_goodness_of_fit

        y = np.array([1.0, 2.0, 3.0])

        with pytest.raises(ValueError, match="参数数量"):
            calculate_goodness_of_fit(y, y, n_params=0)


class TestFitModel:
    """统一模型拟合接口测试。"""

    def test_fit_model_linear(self):
        """测试线性拟合。"""
        from core.analysis import FitModelType, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = 2.0 * x + 1.0

        result = analyzer.fit_model(x, y, FitModelType.LINEAR)

        assert result["model_type"] == "linear"
        assert abs(result["parameters"]["slope"] - 2.0) < 0.01
        assert abs(result["parameters"]["intercept"] - 1.0) < 0.01

    def test_fit_model_polynomial(self):
        """测试多项式拟合。"""
        from core.analysis import FitModelType, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.linspace(-5, 5, 50)
        y = 2.0 * x**2 + 3.0 * x + 1.0

        result = analyzer.fit_model(x, y, FitModelType.POLYNOMIAL, polynomial_order=2)

        assert result["model_type"] == "polynomial"
        assert result["r_squared"] > 0.99

    def test_fit_model_exponential(self):
        """测试指数拟合。"""
        from core.analysis import FitModelType, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.linspace(0, 5, 50)
        y = 2.0 * np.exp(-0.5 * x)

        result = analyzer.fit_model(x, y, FitModelType.EXPONENTIAL)

        assert result["model_type"] == "exponential"
        assert "A" in result["parameters"]
        assert "B" in result["parameters"]

    def test_fit_model_gaussian(self):
        """测试高斯拟合。"""
        from core.analysis import FitModelType, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.linspace(-5, 5, 100)
        y = 2.0 * np.exp(-((x - 0) ** 2) / (2 * 1.0**2))

        result = analyzer.fit_model(x, y, FitModelType.GAUSSIAN)

        assert result["model_type"] == "gaussian"
        assert abs(result["parameters"]["mu"]) < 0.5

    def test_fit_model_langevin(self):
        """测试Langevin拟合。"""
        from core.analysis import FitModelType, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.linspace(0, 1000, 100)
        y = np.tanh(x / 200)

        result = analyzer.fit_model(x, y, FitModelType.LANGEVIN)

        assert result["model_type"] == "langevin"

    def test_fit_model_unsupported(self):
        """测试不支持的模型类型。"""
        from core.analysis import FitModelType, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        # 使用无效的枚举值
        with pytest.raises(ValueError, match="不支持的模型类型"):
            analyzer.fit_model(np.array([1.0]), np.array([1.0]), "invalid")


class TestExportFormats:
    """数据导出格式测试。"""

    def test_export_csv(self, tmp_path):
        """测试CSV导出。"""
        from core.analysis import ExportFormat, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.array([1.0, 2.0, 3.0])
        y = np.array([2.0, 4.0, 6.0])

        filepath = tmp_path / "test_export.csv"

        result = analyzer.export_data(filepath, x, y, ExportFormat.CSV)

        assert result is True
        assert filepath.exists()

    def test_export_hdf5(self, tmp_path):
        """测试HDF5导出。"""
        from core.analysis import ExportFormat, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.array([1.0, 2.0, 3.0])
        y = np.array([2.0, 4.0, 6.0])

        filepath = tmp_path / "test_export.h5"

        result = analyzer.export_data(filepath, x, y, ExportFormat.HDF5)

        assert result is True
        assert filepath.exists()

    def test_export_json(self, tmp_path):
        """测试JSON导出。"""
        from core.analysis import ExportFormat, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.array([1.0, 2.0, 3.0])
        y = np.array([2.0, 4.0, 6.0])

        filepath = tmp_path / "test_export.json"

        result = analyzer.export_data(filepath, x, y, ExportFormat.JSON)

        assert result is True
        assert filepath.exists()

    def test_export_with_metadata(self, tmp_path):
        """测试带元数据导出。"""
        from core.analysis import ExportFormat, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.array([1.0, 2.0, 3.0])
        y = np.array([2.0, 4.0, 6.0])
        metadata = {"sample": "FeCo", "temperature": 300}

        filepath = tmp_path / "test_export.json"

        result = analyzer.export_data(
            filepath, x, y, ExportFormat.JSON, metadata=metadata
        )

        assert result is True

    def test_export_unsupported_format(self, tmp_path):
        """测试不支持的导出格式。"""
        from core.analysis import PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.array([1.0, 2.0, 3.0])
        y = np.array([2.0, 4.0, 6.0])

        filepath = tmp_path / "test_export.xyz"

        with pytest.raises(ValueError, match="不支持的导出格式"):
            analyzer.export_data(filepath, x, y, "xyz")


class TestCoercivityDetailed:
    """详细矫顽力计算测试。"""

    def test_coercivity_detailed_positive_negative(self):
        """测试正向和负向矫顽力计算。"""
        analyzer = PhysicsAnalyzer()

        # 创建对称磁滞回线
        h_field = np.concatenate([
            np.linspace(-100, 100, 50),
            np.linspace(100, -100, 50)
        ])
        moment = np.concatenate([
            np.tanh((h_field[:50] - 20) / 10),
            np.tanh((h_field[50:] + 20) / 10)
        ])

        result = analyzer._calculate_coercivity_detailed(h_field, moment)

        assert "Hc" in result
        assert "Hc_positive" in result
        assert "Hc_negative" in result
        assert result["Hc"] >= 0


class TestRemanenceDetailed:
    """详细剩磁计算测试。"""

    def test_remanence_detailed_positive_negative(self):
        """测试正向和负向剩磁计算。"""
        analyzer = PhysicsAnalyzer()

        h_field = np.concatenate([
            np.linspace(-100, 100, 50),
            np.linspace(100, -100, 50)
        ])
        moment = np.concatenate([
            np.tanh(h_field[:50] / 20),
            np.tanh(h_field[50:] / 20)
        ])

        result = analyzer._calculate_remanence_detailed(h_field, moment)

        assert "Mr" in result
        assert "Mr_positive" in result
        assert "Mr_negative" in result
        assert result["Mr"] >= 0


class TestBackgroundMethod:
    """背景扣除方法测试。"""

    def test_background_method_polynomial(self):
        """测试多项式背景扣除。"""
        from core.analysis import BackgroundMethod, PhysicsAnalyzer

        analyzer = PhysicsAnalyzer()

        x = np.linspace(-100, 100, 200)
        background = 0.001 * x**2 + 0.01 * x + 0.5
        signal = np.tanh(x / 30)
        y = signal + background

        x_corr, y_corr, params = analyzer.subtract_background(
            x, y, method=BackgroundMethod.POLYNOMIAL, polynomial_order=2
        )

        assert params["method"] == "polynomial"
        assert params["polynomial_order"] == 2
        # 验证返回的 x_corr 与输入一致
        assert np.array_equal(x_corr, x)
        # 验证拟合参数包含必要的键
        assert "coefficients" in params
        assert "r_squared" in params
        # 验证 R² 值合理（接近1表示拟合良好）
        assert 0 <= params["r_squared"] <= 1

    def test_inf_handling(self):
        """测试无穷大值处理。"""
        analyzer = PhysicsAnalyzer()

        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([2.0, np.inf, 6.0, -np.inf, 10.0])

        analyzer.load_data(x, y)

        assert analyzer.data_buffer is not None
