"""
测试数据分析 API 端点

测试内容：
- 信号平滑处理
- 曲线拟合
- 磁滞回线分析
"""

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import analysis


@pytest.fixture
def app_with_analysis():
    """创建带分析路由的FastAPI应用。"""
    app = FastAPI()
    app.include_router(analysis.router)
    return app


@pytest.fixture
def client_with_analysis(app_with_analysis):
    """创建测试客户端。"""
    with TestClient(app_with_analysis) as client:
        yield client


@pytest.fixture
def sample_smooth_data():
    """生成平滑测试数据。"""
    x = np.linspace(0, 10, 100)
    y_clean = np.sin(x)
    noise = np.random.normal(0, 0.1, len(x))
    y_noisy = y_clean + noise
    return y_noisy.tolist()


@pytest.fixture
def sample_fit_data():
    """生成拟合测试数据。"""
    x = np.linspace(0, 10, 50)
    y = 2.5 * x + 1.0
    noise = np.random.normal(0, 0.5, len(x))
    y_noisy = y + noise
    return x.tolist(), y_noisy.tolist()


@pytest.fixture
def sample_hysteresis_data():
    """生成磁滞回线测试数据。"""
    h_field = np.linspace(-1000, 1000, 100)
    moment = np.tanh(h_field / 200)
    return h_field.tolist(), moment.tolist()


class TestSmoothEndpoint:
    """测试信号平滑端点。"""

    def test_smooth_savgol_success(self, client_with_analysis, sample_smooth_data):
        """测试Savitzky-Golay平滑成功。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/smooth",
            json={
                "y_data": sample_smooth_data,
                "method": "savgol",
                "window_length": 11,
                "polyorder": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "smoothed_data" in data
        assert len(data["smoothed_data"]) == len(sample_smooth_data)

    def test_smooth_butter_success(self, client_with_analysis, sample_smooth_data):
        """测试巴特沃斯平滑成功。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/smooth",
            json={
                "y_data": sample_smooth_data,
                "method": "butter",
                "butter_lowcut": 0.1,
                "butter_order": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "smoothed_data" in data

    def test_smooth_default_parameters(self, client_with_analysis, sample_smooth_data):
        """测试默认参数平滑。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/smooth", json={"y_data": sample_smooth_data}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_smooth_invalid_method(self, client_with_analysis, sample_smooth_data):
        """测试无效平滑方法。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/smooth",
            json={"y_data": sample_smooth_data, "method": "invalid_method"},
        )

        assert response.status_code == 400

    def test_smooth_invalid_window_length(self, client_with_analysis, sample_smooth_data):
        """测试无效窗口长度。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/smooth",
            json={"y_data": sample_smooth_data, "method": "savgol", "window_length": 10},
        )

        assert response.status_code == 400

    def test_smooth_empty_data(self, client_with_analysis):
        """测试空数据平滑。"""
        response = client_with_analysis.post("/api/v1/analysis/smooth", json={"y_data": []})

        assert response.status_code == 400

    def test_smooth_small_data(self, client_with_analysis):
        """测试小数据集平滑。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/smooth",
            json={"y_data": [1.0, 2.0], "method": "savgol", "window_length": 3},
        )

        assert response.status_code == 400


class TestFitEndpoint:
    """测试曲线拟合端点。"""

    def test_fit_langevin_success(self, client_with_analysis):
        """测试Langevin拟合成功。"""
        h_field = np.linspace(0, 500, 50)
        moment = np.tanh(h_field / 100)

        response = client_with_analysis.post(
            "/api/v1/analysis/fit",
            json={"x_data": h_field.tolist(), "y_data": moment.tolist(), "model_type": "langevin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "fit_params" in data
        assert "fitted_y" in data
        assert "chi2" in data
        assert "redchi" in data

    def test_fit_linear_success(self, client_with_analysis, sample_fit_data):
        """测试线性拟合成功。"""
        x_data, y_data = sample_fit_data

        response = client_with_analysis.post(
            "/api/v1/analysis/fit",
            json={"x_data": x_data, "y_data": y_data, "model_type": "linear"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "slope" in data["fit_params"]
        assert "intercept" in data["fit_params"]

    def test_fit_default_model(self, client_with_analysis, sample_fit_data):
        """测试默认拟合模型。"""
        x_data, y_data = sample_fit_data

        response = client_with_analysis.post(
            "/api/v1/analysis/fit", json={"x_data": x_data, "y_data": y_data}
        )

        assert response.status_code == 200

    def test_fit_unsupported_model(self, client_with_analysis, sample_fit_data):
        """测试不支持的拟合模型。"""
        x_data, y_data = sample_fit_data

        response = client_with_analysis.post(
            "/api/v1/analysis/fit",
            json={"x_data": x_data, "y_data": y_data, "model_type": "unsupported"},
        )

        assert response.status_code == 400

    def test_fit_mismatched_data_length(self, client_with_analysis):
        """测试数据长度不匹配。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/fit",
            json={"x_data": [1.0, 2.0, 3.0], "y_data": [1.0, 2.0], "model_type": "linear"},
        )

        assert response.status_code == 400

    def test_fit_empty_data(self, client_with_analysis):
        """测试空数据拟合。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/fit", json={"x_data": [], "y_data": [], "model_type": "linear"}
        )

        assert response.status_code == 400


class TestHysteresisEndpoint:
    """测试磁滞回线分析端点。"""

    def test_hysteresis_analysis_success(self, client_with_analysis, sample_hysteresis_data):
        """测试磁滞回线分析成功。"""
        x_field, y_moment = sample_hysteresis_data

        response = client_with_analysis.post(
            "/api/v1/analysis/hysteresis",
            json={"x_field": x_field, "y_moment": y_moment, "subtract_background": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Hc" in data
        assert "Mr" in data
        assert "Ms" in data
        assert "background_params" in data
        assert "x_corrected" in data
        assert "y_corrected" in data

    def test_hysteresis_no_background_subtraction(
        self, client_with_analysis, sample_hysteresis_data
    ):
        """测试不扣除背景的磁滞回线分析。"""
        x_field, y_moment = sample_hysteresis_data

        response = client_with_analysis.post(
            "/api/v1/analysis/hysteresis",
            json={"x_field": x_field, "y_moment": y_moment, "subtract_background": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["background_params"] == {}

    def test_hysteresis_custom_saturation_threshold(
        self, client_with_analysis, sample_hysteresis_data
    ):
        """测试自定义饱和场阈值。"""
        x_field, y_moment = sample_hysteresis_data

        response = client_with_analysis.post(
            "/api/v1/analysis/hysteresis",
            json={"x_field": x_field, "y_moment": y_moment, "saturation_threshold": 800.0},
        )

        assert response.status_code == 200

    def test_hysteresis_default_parameters(self, client_with_analysis, sample_hysteresis_data):
        """测试默认参数磁滞回线分析。"""
        x_field, y_moment = sample_hysteresis_data

        response = client_with_analysis.post(
            "/api/v1/analysis/hysteresis", json={"x_field": x_field, "y_moment": y_moment}
        )

        assert response.status_code == 200

    def test_hysteresis_empty_data(self, client_with_analysis):
        """测试空数据磁滞回线分析。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/hysteresis", json={"x_field": [], "y_moment": []}
        )

        assert response.status_code == 400

    def test_hysteresis_mismatched_data_length(self, client_with_analysis):
        """测试数据长度不匹配。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/hysteresis", json={"x_field": [1.0, 2.0, 3.0], "y_moment": [1.0, 2.0]}
        )

        assert response.status_code == 400

    def test_hysteresis_result_values_reasonable(
        self, client_with_analysis, sample_hysteresis_data
    ):
        """测试磁滞回线分析结果值合理。"""
        x_field, y_moment = sample_hysteresis_data

        response = client_with_analysis.post(
            "/api/v1/analysis/hysteresis", json={"x_field": x_field, "y_moment": y_moment}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["Hc"] >= 0
        assert data["Mr"] >= 0
        assert data["Ms"] > 0
        assert data["Ms"] >= data["Mr"]


class TestAnalysisAPIValidation:
    """测试分析API输入验证。"""

    def test_smooth_missing_y_data(self, client_with_analysis):
        """测试缺少Y数据。"""
        response = client_with_analysis.post("/api/v1/analysis/smooth", json={})

        assert response.status_code == 422

    def test_fit_missing_data(self, client_with_analysis):
        """测试缺少拟合数据。"""
        response = client_with_analysis.post("/api/v1/analysis/fit", json={"model_type": "linear"})

        assert response.status_code == 422

    def test_hysteresis_missing_data(self, client_with_analysis):
        """测试缺少磁滞回线数据。"""
        response = client_with_analysis.post("/api/v1/analysis/hysteresis", json={})

        assert response.status_code == 422


class TestAnalysisAPIResponseFormat:
    """测试分析API响应格式。"""

    def test_smooth_response_format(self, client_with_analysis, sample_smooth_data):
        """测试平滑响应格式。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/smooth", json={"y_data": sample_smooth_data}
        )

        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "smoothed_data" in data

    def test_fit_response_format(self, client_with_analysis, sample_fit_data):
        """测试拟合响应格式。"""
        x_data, y_data = sample_fit_data

        response = client_with_analysis.post(
            "/api/v1/analysis/fit",
            json={"x_data": x_data, "y_data": y_data, "model_type": "linear"},
        )

        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "fit_params" in data
        assert "fitted_y" in data

    def test_hysteresis_response_format(self, client_with_analysis, sample_hysteresis_data):
        """测试磁滞回线响应格式。"""
        x_field, y_moment = sample_hysteresis_data

        response = client_with_analysis.post(
            "/api/v1/analysis/hysteresis", json={"x_field": x_field, "y_moment": y_moment}
        )

        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "Hc" in data
        assert "Mr" in data
        assert "Ms" in data


class TestAnalysisAPIEdgeCases:
    """测试分析API边界情况。"""

    def test_smooth_with_nan_values(self, client_with_analysis):
        """测试包含NaN值的平滑。"""
        y_data = [1.0, 2.0, 3.0, 4.0, 5.0]

        response = client_with_analysis.post(
            "/api/v1/analysis/smooth", json={"y_data": y_data}
        )

        assert response.status_code == 200

    def test_fit_with_constant_data(self, client_with_analysis):
        """测试常量数据拟合。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/fit",
            json={
                "x_data": [1.0, 2.0, 3.0, 4.0, 5.0],
                "y_data": [5.0, 5.0, 5.0, 5.0, 5.0],
                "model_type": "linear",
            },
        )

        assert response.status_code == 200

    def test_hysteresis_with_single_point(self, client_with_analysis):
        """测试单点数据磁滞回线分析。"""
        response = client_with_analysis.post(
            "/api/v1/analysis/hysteresis",
            json={"x_field": [100.0], "y_moment": [1.0]},
        )

        assert response.status_code == 200
