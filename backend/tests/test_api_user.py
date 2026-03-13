"""
用户认证与管理 API 测试模块。

测试功能：
    - 用户登录/登出
    - JWT令牌验证
    - 用户信息管理
    - 密码修改
    - 偏好设置
    - 操作历史

作者：Test Debugger Agent
创建日期：2026-03-08
依赖：pytest, httpx
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.user import (
    LoginRequest,
    create_access_token,
    decode_token,
    get_password_hash,
    router,
    verify_password,
)
from models import Base
from models.user import User


class TestPasswordHashing:
    """密码哈希功能测试。"""

    def test_password_hash_generation(self):
        """测试密码哈希生成。"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")

    def test_password_verification_success(self):
        """测试密码验证成功。"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_password_verification_failure(self):
        """测试密码验证失败。"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_different_passwords_different_hashes(self):
        """测试不同密码生成不同哈希。"""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # bcrypt每次生成不同的哈希（由于salt）
        assert hash1 != hash2
        # 但都能验证原密码
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTToken:
    """JWT令牌功能测试。"""

    def test_create_access_token(self):
        """测试创建访问令牌。"""
        data = {"sub": 1, "role": "admin"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token_success(self):
        """测试解码令牌成功。"""
        data = {"sub": 1, "role": "admin"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload["sub"] == 1
        assert payload["role"] == "admin"
        assert "exp" in payload
        assert "jti" in payload

    def test_decode_token_invalid(self):
        """测试解码无效令牌。"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid_token")

        assert exc_info.value.status_code == 401

    def test_token_blacklist(self):
        """测试令牌黑名单。"""
        from fastapi import HTTPException

        from api.user import _token_blacklist

        data = {"sub": 1}
        token = create_access_token(data)
        payload = decode_token(token)
        jti = payload.get("jti")

        # 添加到黑名单
        _token_blacklist.add(jti)

        # 解码应该失败
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)

        assert exc_info.value.status_code == 401

        # 清理
        _token_blacklist.discard(jti)


class TestLoginRequest:
    """登录请求模型测试。"""

    def test_valid_login_request(self):
        """测试有效的登录请求。"""
        request = LoginRequest(username="testuser", password="password123")

        assert request.username == "testuser"
        assert request.password == "password123"

    def test_username_too_short(self):
        """测试用户名过短。"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LoginRequest(username="ab", password="password123")

    def test_password_too_short(self):
        """测试密码过短。"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LoginRequest(username="testuser", password="12345")


class TestUserAPI:
    """用户API集成测试。"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_user.db")
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(bind=engine)
            yield engine

    @pytest.fixture
    def test_client(self, temp_db):
        """创建测试客户端。"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        # 覆盖数据库依赖
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=temp_db)

        def override_get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        from api.user import get_db

        app.dependency_overrides[get_db] = override_get_db

        # 创建默认管理员
        with SessionLocal() as db:
            admin = User(
                username="admin",
                email="admin@test.local",
                password_hash=get_password_hash("admin123"),
                role="admin",
            )
            db.add(admin)
            db.commit()

        with TestClient(app) as client:
            yield client

    def test_login_success(self, test_client):
        """测试登录成功。"""
        response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == "admin"

    def test_login_wrong_password(self, test_client):
        """测试密码错误。"""
        response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "wrongpassword"},
        )

        assert response.status_code == 401

    def test_login_user_not_found(self, test_client):
        """测试用户不存在。"""
        response = test_client.post(
            "/api/v1/user/login",
            json={"username": "nonexistent", "password": "password123"},
        )

        assert response.status_code == 401

    def test_get_current_user_info(self, test_client):
        """测试获取当前用户信息。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 获取用户信息
        response = test_client.get(
            "/api/v1/user/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_get_current_user_without_token(self, test_client):
        """测试无令牌获取用户信息。"""
        response = test_client.get("/api/v1/user/me")

        assert response.status_code == 403

    def test_logout(self, test_client):
        """测试登出。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 登出
        response = test_client.post(
            "/api/v1/user/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_update_profile(self, test_client):
        """测试更新用户资料。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 更新资料
        response = test_client.put(
            "/api/v1/user/profile",
            json={"email": "newemail@test.local"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@test.local"

    def test_change_password(self, test_client):
        """测试修改密码。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 修改密码
        response = test_client.put(
            "/api/v1/user/password",
            json={"old_password": "admin123", "new_password": "newpassword123"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # 验证新密码可以登录
        new_login = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "newpassword123"},
        )
        assert new_login.status_code == 200

    def test_change_password_wrong_old(self, test_client):
        """测试修改密码时原密码错误。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 尝试用错误的原密码修改
        response = test_client.put(
            "/api/v1/user/password",
            json={"old_password": "wrongpassword", "new_password": "newpassword123"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    def test_get_preferences(self, test_client):
        """测试获取偏好设置。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 获取偏好设置
        response = test_client.get(
            "/api/v1/user/preferences",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "theme" in data
        assert "language" in data

    def test_update_preferences(self, test_client):
        """测试更新偏好设置。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 更新偏好设置
        response = test_client.put(
            "/api/v1/user/preferences",
            json={"theme": "dark", "language": "en-US"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # 验证更新
        get_response = test_client.get(
            "/api/v1/user/preferences",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = get_response.json()
        assert data["theme"] == "dark"
        assert data["language"] == "en-US"

    def test_get_history(self, test_client):
        """测试获取操作历史。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 获取操作历史
        response = test_client.get(
            "/api/v1/user/history",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    def test_create_history(self, test_client):
        """测试创建操作历史。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 创建操作历史
        response = test_client.post(
            "/api/v1/user/history",
            json={"operation_type": "login", "operation_detail": {"test": "data"}},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_clear_history(self, test_client):
        """测试清除操作历史。"""
        # 先登录
        login_response = test_client.post(
            "/api/v1/user/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # 清除操作历史
        response = test_client.delete(
            "/api/v1/user/history",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True


class TestUserModel:
    """用户模型测试。"""

    def test_user_creation(self, temp_db):
        """测试用户创建。"""

        Session = sessionmaker(bind=temp_db)
        db = Session()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            role="user",
        )
        db.add(user)
        db.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.role == "user"
        assert user.is_active is True

        db.close()

    def test_user_preferences(self, temp_db):
        """测试用户偏好设置。"""

        Session = sessionmaker(bind=temp_db)
        db = Session()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            role="user",
        )
        db.add(user)
        db.commit()

        # 设置偏好
        user.set_preferences({"theme": "dark", "language": "zh-CN"})
        db.commit()

        # 获取偏好
        prefs = user.get_preferences()
        assert prefs["theme"] == "dark"
        assert prefs["language"] == "zh-CN"

        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
