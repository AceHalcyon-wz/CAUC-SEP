"""
集成测试：实验工作流

测试内容：
- 完整实验流程
- 数据采集和存储
- 实验状态管理
- 数据导出
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from core.analysis import PhysicsAnalyzer
from core.dm2c_driver import LeadshineDM2C


class TestExperimentSetup:
    """测试实验设置。"""

    def test_create_experiment(self, temp_storage):
        """测试创建实验。"""
        exp_id = temp_storage.create_experiment(
            exp_name="测试实验", exp_type="hysteresis", user_id=None
        )

        assert exp_id > 0

        experiment = temp_storage.get_experiment(exp_id)
        assert experiment is not None
        assert experiment["exp_name"] == "测试实验"
        assert experiment["status"] == "pending"

    def test_start_experiment(self, temp_storage):
        """测试启动实验。"""
        exp_id = temp_storage.start_experiment(name="启动测试", description="测试启动实验")

        assert exp_id > 0

        experiment = temp_storage.get_experiment(exp_id)
        assert experiment["status"] == "running"
        assert experiment["started_at"] is not None

    def test_experiment_with_user(self, temp_storage):
        """测试带用户的实验。"""
        user_id = temp_storage.create_user(
            username="test_user", password_hash="hash123", role="operator"
        )

        exp_id = temp_storage.create_experiment(
            exp_name="用户实验", exp_type="measurement", user_id=user_id
        )

        experiment = temp_storage.get_experiment(exp_id)
        assert experiment["user_id"] == user_id


class TestExperimentDataCollection:
    """测试实验数据采集。"""

    def test_add_single_data_point(self, temp_storage):
        """测试添加单个数据点。"""
        exp_id = temp_storage.start_experiment(name="数据采集测试")

        record_id = temp_storage.add_data_record(
            experiment_id=exp_id,
            position_steps=1600,
            position_mm=1.0,
            field_value=100.0,
            current_value=0.5,
        )

        assert record_id > 0

        data = temp_storage.get_experiment_data(exp_id)
        assert len(data) == 1
        assert data[0]["position_mm"] == 1.0
        assert data[0]["field_value"] == 100.0

    def test_add_multiple_data_points(self, temp_storage):
        """测试添加多个数据点。"""
        exp_id = temp_storage.start_experiment(name="多点采集测试")

        num_points = 100
        for i in range(num_points):
            temp_storage.add_data_record(
                experiment_id=exp_id,
                position_steps=i * 160,
                position_mm=i * 0.1,
                field_value=i * 10.0,
                current_value=i * 0.05,
            )

        data = temp_storage.get_experiment_data(exp_id)
        assert len(data) == num_points

    def test_data_with_temperature(self, temp_storage):
        """测试带温度的数据。"""
        exp_id = temp_storage.start_experiment(name="温度测试")

        temp_storage.add_data_record(
            experiment_id=exp_id, position_mm=10.0, field_value=500.0, temperature=300.0
        )

        data = temp_storage.get_experiment_data(exp_id)
        assert data[0]["temperature"] == 300.0

    def test_data_with_extra_fields(self, temp_storage):
        """测试带额外字段的数据。"""
        exp_id = temp_storage.start_experiment(name="额外字段测试")

        extra_data = {"sample_id": "FeCo_001", "notes": "Test measurement", "operator": "user1"}

        temp_storage.add_data_record(
            experiment_id=exp_id, position_mm=5.0, field_value=200.0, extra_data=extra_data
        )

        data = temp_storage.get_experiment_data(exp_id)
        assert data[0]["extra_data"]["sample_id"] == "FeCo_001"


class TestExperimentStatusManagement:
    """测试实验状态管理。"""

    def test_experiment_status_transitions(self, temp_storage):
        """测试实验状态转换。"""
        exp_id = temp_storage.create_experiment(exp_name="状态转换测试", exp_type="test")

        experiment = temp_storage.get_experiment(exp_id)
        assert experiment["status"] == "pending"

        temp_storage.start_experiment(exp_id=exp_id)
        experiment = temp_storage.get_experiment(exp_id)
        assert experiment["status"] == "running"

        temp_storage.stop_experiment(status="completed")
        experiment = temp_storage.get_experiment(exp_id)
        assert experiment["status"] == "completed"

    def test_experiment_abort(self, temp_storage):
        """测试实验中止。"""
        exp_id = temp_storage.start_experiment(name="中止测试")

        temp_storage.stop_experiment(status="aborted")

        experiment = temp_storage.get_experiment(exp_id)
        assert experiment["status"] == "aborted"

    def test_experiment_error_status(self, temp_storage):
        """测试实验错误状态。"""
        exp_id = temp_storage.start_experiment(name="错误测试")

        temp_storage.stop_experiment(status="error")

        experiment = temp_storage.get_experiment(exp_id)
        assert experiment["status"] == "error"


class TestExperimentDataExport:
    """测试实验数据导出。"""

    def test_export_to_csv(self, temp_storage):
        """测试导出到CSV。"""
        exp_id = temp_storage.start_experiment(name="导出测试")

        for i in range(10):
            temp_storage.add_data_record(
                experiment_id=exp_id,
                position_mm=i * 0.5,
                field_value=i * 50.0,
                current_value=i * 0.1,
            )

        temp_storage.stop_experiment()

        fd, csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)

        try:
            result = temp_storage.export_to_csv(exp_id, csv_path)

            assert result is True
            assert os.path.exists(csv_path)

            with open(csv_path) as f:
                lines = f.readlines()
                assert len(lines) == 11
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_export_empty_experiment(self, temp_storage):
        """测试导出空实验。"""
        exp_id = temp_storage.start_experiment(name="空实验")
        temp_storage.stop_experiment()

        fd, csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)

        try:
            result = temp_storage.export_to_csv(exp_id, csv_path)

            assert result is False
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)


class TestExperimentListQuery:
    """测试实验列表查询。"""

    def test_list_all_experiments(self, temp_storage):
        """测试列出所有实验。"""
        for i in range(5):
            temp_storage.create_experiment(exp_name=f"实验{i+1}", exp_type="test")

        experiments = temp_storage.list_experiments()

        assert len(experiments) == 5

    def test_list_experiments_with_limit(self, temp_storage):
        """测试带限制的实验列表。"""
        for i in range(10):
            temp_storage.create_experiment(exp_name=f"实验{i+1}", exp_type="test")

        experiments = temp_storage.list_experiments(limit=5)

        assert len(experiments) == 5

    def test_list_experiments_by_user(self, temp_storage):
        """测试按用户列出实验。"""
        user_id = temp_storage.create_user(username="test_user", password_hash="hash")

        for i in range(3):
            temp_storage.create_experiment(exp_name=f"用户实验{i+1}", user_id=user_id)

        for i in range(2):
            temp_storage.create_experiment(exp_name=f"其他实验{i+1}", user_id=None)

        experiments = temp_storage.list_experiments(user_id=user_id)

        assert len(experiments) == 3


class TestExperimentDeletion:
    """测试实验删除。"""

    def test_delete_experiment(self, temp_storage):
        """测试删除实验。"""
        exp_id = temp_storage.create_experiment(exp_name="待删除实验", exp_type="test")

        result = temp_storage.delete_experiment(exp_id)

        assert result is True

        experiment = temp_storage.get_experiment(exp_id)
        assert experiment is None

    def test_delete_nonexistent_experiment(self, temp_storage):
        """测试删除不存在的实验。"""
        result = temp_storage.delete_experiment(99999)

        assert result is False


class TestCompleteExperimentWorkflow:
    """测试完整实验工作流。"""

    @pytest.mark.asyncio
    async def test_hysteresis_measurement_workflow(self, temp_storage):
        """测试磁滞回线测量工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            motor = LeadshineDM2C(device_id="test_motor", config={})
            await motor.connect()

            exp_id = temp_storage.start_experiment(
                name="磁滞回线测量", description="完整磁滞回线测量流程"
            )

            positions = np.linspace(-50, 50, 101)
            field_values = np.linspace(-1000, 1000, 101)

            for pos, field in zip(positions, field_values):
                await motor.move_abs(pos, 5.0, 1000.0, 1000.0)

                current = 0.001 * field + np.random.normal(0, 0.0001)

                temp_storage.add_data_record(
                    experiment_id=exp_id, position_mm=pos, field_value=field, current_value=current
                )

            temp_storage.stop_experiment()

            data = temp_storage.get_experiment_data(exp_id)
            assert len(data) == len(positions)

            analyzer = PhysicsAnalyzer()
            x_field = np.array([d["field_value"] for d in data])
            y_moment = np.array([d["current_value"] for d in data])

            result = analyzer.analyze_hysteresis_loop(x_field, y_moment)

            assert "Hc" in result
            assert "Mr" in result
            assert "Ms" in result

            await motor.disconnect()

    def test_data_analysis_workflow(self, temp_storage):
        """测试数据分析工作流。"""
        exp_id = temp_storage.start_experiment(name="数据分析测试", description="测试数据分析流程")

        import numpy as np

        h_field = np.linspace(-1000, 1000, 200)
        moment = np.tanh(h_field / 200)

        for h, m in zip(h_field, moment):
            temp_storage.add_data_record(
                experiment_id=exp_id, position_mm=0.0, field_value=h, current_value=m
            )

        temp_storage.stop_experiment()

        data = temp_storage.get_experiment_data(exp_id)

        analyzer = PhysicsAnalyzer()
        x_field = np.array([d["field_value"] for d in data])
        y_moment = np.array([d["current_value"] for d in data])

        y_smoothed = analyzer.smooth_signal(y_moment, method="savgol")
        assert len(y_smoothed) == len(y_moment)

        result = analyzer.analyze_hysteresis_loop(x_field, y_smoothed)
        assert result["Hc"] > 0


class TestExperimentConcurrency:
    """测试实验并发。"""

    def test_multiple_experiments_sequential(self, temp_storage):
        """测试多个顺序实验。"""
        exp_ids = []

        for i in range(3):
            exp_id = temp_storage.start_experiment(name=f"顺序实验{i+1}")

            for j in range(5):
                temp_storage.add_data_record(
                    experiment_id=exp_id, position_mm=j * 0.1, field_value=j * 10.0
                )

            temp_storage.stop_experiment()
            exp_ids.append(exp_id)

        assert len(exp_ids) == 3
        assert len(set(exp_ids)) == 3

        for exp_id in exp_ids:
            data = temp_storage.get_experiment_data(exp_id)
            assert len(data) == 5


class TestExperimentMetadata:
    """测试实验元数据。"""

    def test_experiment_with_metadata(self, temp_storage):
        """测试带元数据的实验。"""
        metadata = {
            "sample": "FeCo thin film",
            "thickness": "10 nm",
            "substrate": "Si/SiO2",
            "temperature": "300 K",
        }

        exp_id = temp_storage.create_experiment(
            exp_name="元数据测试", exp_type="thin_film", experiment_metadata=metadata
        )

        experiment = temp_storage.get_experiment(exp_id)
        assert experiment["experiment_metadata"]["sample"] == "FeCo thin film"

    def test_experiment_with_sequence_config(self, temp_storage):
        """测试带序列配置的实验。"""
        sequence_config = {
            "steps": [
                {"action": "move", "position": 0.0},
                {"action": "move", "position": 10.0},
                {"action": "move", "position": 20.0},
            ],
            "repeat": 5,
        }

        exp_id = temp_storage.create_experiment(
            exp_name="序列测试", sequence_config=sequence_config
        )

        experiment = temp_storage.get_experiment(exp_id)
        assert experiment["sequence_config"]["repeat"] == 5


import numpy as np
