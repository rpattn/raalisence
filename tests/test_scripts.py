"""Tests for utility scripts."""

import pytest
import subprocess
import sys
import tempfile
import os
from unittest.mock import patch, Mock


class TestKeyGenerationScript:
    """Test the key generation script."""
    
    def test_gen_keys_script(self):
        """Test the gen_keys.py script."""
        # Test that the script can be imported and run
        try:
            from scripts.gen_keys import main
            # Should not raise an exception
            assert callable(main)
        except ImportError:
            pytest.skip("gen_keys script not available")
    
    def test_gen_keys_functionality(self):
        """Test key generation functionality."""
        from python_raalisence.crypto.sign import generate_pem_keys
        
        private_pem, public_pem = generate_pem_keys()
        
        # Should generate valid PEM keys
        assert "-----BEGIN EC PRIVATE KEY-----" in private_pem
        assert "-----END EC PRIVATE KEY-----" in private_pem
        assert "-----BEGIN PUBLIC KEY-----" in public_pem
        assert "-----END PUBLIC KEY-----" in public_pem
        
        # Keys should be different
        assert private_pem != public_pem


class TestAdminKeyHashScript:
    """Test the admin key hash generation script."""
    
    def test_gen_script(self):
        """Test the gen.py script."""
        try:
            from scripts.gen import main
            assert callable(main)
        except ImportError:
            pytest.skip("gen script not available")
    
    def test_bcrypt_hash_generation(self):
        """Test bcrypt hash generation."""
        import bcrypt
        
        test_key = "test-admin-key"
        hash_bytes = bcrypt.hashpw(test_key.encode('utf-8'), bcrypt.gensalt())
        hash_str = hash_bytes.decode('utf-8')
        
        # Should generate valid bcrypt hash
        assert hash_str.startswith("$2")
        
        # Should verify correctly
        assert bcrypt.checkpw(test_key.encode('utf-8'), hash_bytes)
        
        # Should not verify with wrong key
        assert not bcrypt.checkpw("wrong-key".encode('utf-8'), hash_bytes)


class TestSetupScript:
    """Test the setup script."""
    
    def test_setup_script_import(self):
        """Test that setup script can be imported."""
        try:
            from scripts.setup import main
            assert callable(main)
        except ImportError:
            pytest.skip("setup script not available")
    
    def test_python_version_check(self):
        """Test Python version checking."""
        from scripts.setup import check_python_version
        
        # Should not raise an exception for valid Python version
        check_python_version()
    
    @patch('scripts.setup.subprocess.check_call')
    def test_dependency_installation(self, mock_check_call):
        """Test dependency installation."""
        from scripts.setup import install_dependencies
        
        # Should call pip install
        install_dependencies()
        mock_check_call.assert_called_once()
        
        # Check the call was made with correct arguments
        call_args = mock_check_call.call_args[0][0]
        assert sys.executable in call_args
        assert "-m" in call_args
        assert "pip" in call_args
        assert "install" in call_args
        assert "-r" in call_args
        assert "requirements.txt" in call_args


class TestBatchScripts:
    """Test Windows batch scripts."""
    
    def test_batch_script_files_exist(self):
        """Test that batch script files exist."""
        script_files = [
            "scripts/dev_db_up.bat",
            "scripts/dev_db_down.bat", 
            "scripts/dev_sqlite_up.bat",
            "scripts/gen_keys.bat",
            "scripts/gen.bat",
            "scripts/run.bat",
            "scripts/test.bat",
            "scripts/setup.bat"
        ]
        
        for script_file in script_files:
            if os.path.exists(script_file):
                # Check that file is readable
                with open(script_file, 'r') as f:
                    content = f.read()
                    assert len(content) > 0
            else:
                pytest.skip(f"Batch script {script_file} not found")


class TestPowerShellScripts:
    """Test PowerShell scripts."""
    
    def test_powershell_script_files_exist(self):
        """Test that PowerShell script files exist."""
        script_files = [
            "scripts/dev_db_up.ps1",
            "scripts/dev_db_down.ps1",
            "scripts/dev_sqlite_up.ps1", 
            "scripts/gen_keys.ps1",
            "scripts/gen.ps1",
            "scripts/run.ps1",
            "scripts/test.ps1",
            "scripts/setup.ps1"
        ]
        
        for script_file in script_files:
            if os.path.exists(script_file):
                # Check that file is readable
                with open(script_file, 'r') as f:
                    content = f.read()
                    assert len(content) > 0
            else:
                pytest.skip(f"PowerShell script {script_file} not found")


class TestScriptIntegration:
    """Integration tests for scripts."""
    
    def test_script_execution_environment(self):
        """Test that scripts can be executed in the current environment."""
        # Test that Python can import the required modules
        try:
            import fastapi
            import uvicorn
            import cryptography
            import bcrypt
            import yaml
            import pydantic
            assert True  # All imports successful
        except ImportError as e:
            pytest.skip(f"Required module not available: {e}")
    
    def test_script_paths(self):
        """Test that scripts reference correct paths."""
        # Check that scripts reference existing Python modules
        script_files = [
            "scripts/gen_keys.py",
            "scripts/gen.py", 
            "scripts/setup.py"
        ]
        
        for script_file in script_files:
            if os.path.exists(script_file):
                with open(script_file, 'r') as f:
                    content = f.read()
                    # Should reference the python_raalisence module
                    assert "python_raalisence" in content
