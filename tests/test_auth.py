"""
认证模块测试
"""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import AuthManager


class TestAuthManager:
    """认证管理器测试"""
    
    def setup_method(self):
        """每个测试前创建临时数据库"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.auth = AuthManager(db_path=self.temp_db.name, secret_key="test-secret-key-123456")
    
    def teardown_method(self):
        """测试后清理"""
        self.auth.close()
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_create_user(self):
        """测试创建用户"""
        user_id = self.auth.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )
        
        assert user_id is not None
        assert len(user_id) > 0
    
    def test_create_duplicate_user(self):
        """测试重复创建用户"""
        self.auth.create_user("testuser", "pass", "test@example.com")
        
        with pytest.raises(ValueError):
            self.auth.create_user("testuser", "pass2", "test2@example.com")
    
    def test_authenticate_success(self):
        """测试成功认证"""
        self.auth.create_user("testuser", "testpass123")
        
        user = self.auth.authenticate("testuser", "testpass123")
        
        assert user is not None
        assert user.username == "testuser"
    
    def test_authenticate_wrong_password(self):
        """测试密码错误"""
        self.auth.create_user("testuser", "correctpass")
        
        user = self.auth.authenticate("testuser", "wrongpass")
        
        assert user is None
    
    def test_authenticate_nonexistent_user(self):
        """测试不存在的用户"""
        user = self.auth.authenticate("nonexistent", "pass")
        
        assert user is None
    
    def test_create_access_token(self):
        """测试创建访问令牌"""
        user_id = self.auth.create_user("testuser", "pass")
        
        token = self.auth.create_access_token(user_id)
        
        assert token is not None
        assert len(token) > 0
    
    def test_verify_token(self):
        """测试验证令牌"""
        user_id = self.auth.create_user("testuser", "pass")
        token = self.auth.create_access_token(user_id)
        
        verified_id = self.auth.verify_token(token)
        
        assert verified_id == user_id
    
    def test_verify_invalid_token(self):
        """测试无效令牌"""
        verified_id = self.auth.verify_token("invalid-token")
        
        assert verified_id is None
    
    def test_api_key(self):
        """测试 API Key"""
        user_id = self.auth.create_user("testuser", "pass")
        
        api_key = self.auth.create_api_key(user_id, "test-key")
        
        assert api_key.startswith("ink_")
        
        # 验证 API Key
        verified_id = self.auth.verify_api_key(api_key)
        assert verified_id == user_id
    
    def test_verify_invalid_api_key(self):
        """测试无效 API Key"""
        verified = self.auth.verify_api_key("invalid-key")
        assert verified is None
        
        verified = self.auth.verify_api_key("")
        assert verified is None
