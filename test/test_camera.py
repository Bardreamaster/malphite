"""
Tests for camera components including MockCamera, SharedCamera, and ManagedCamera.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from malphite.camera import (
    Camera,
    CameraConfig,
    ManagedCamera,
    SharedCamera,
    SharedCameraConfig,
)
from test.conftest import FailingMockCameraConfig, MockCamera, MockCameraConfig


class TestMockCamera:
    """Test the MockCamera implementation."""

    def test_mock_camera_creation(self):
        """Test creating a mock camera."""
        config = MockCameraConfig(name="test", width=640, height=480, fps=30.0)
        camera = MockCamera(config)

        assert camera.name == "test"
        assert camera.width == 640
        assert camera.height == 480
        assert camera.fps == 30.0
        assert camera.is_opened is True

    def test_mock_camera_read_once(self):
        """Test reading frames from mock camera."""
        config = MockCameraConfig(name="test", width=320, height=240)
        camera = MockCamera(config)

        frame1 = camera.read_once()
        frame2 = camera.read_once()

        assert frame1.shape == (240, 320, 3)
        assert frame2.shape == (240, 320, 3)
        assert frame1.dtype == np.uint8

        # Frame counter should increment
        assert not np.array_equal(frame1, frame2)

    def test_mock_camera_close(self):
        """Test closing mock camera."""
        config = MockCameraConfig(name="test")
        camera = MockCamera(config)

        camera.close()
        assert camera.is_opened is False

        with pytest.raises(RuntimeError, match="Camera is not opened"):
            camera.read_once()

    def test_failing_mock_camera(self):
        """Test the failing mock camera."""
        config = FailingMockCameraConfig(name="failing")
        camera = config.target_class(config)

        with pytest.raises(RuntimeError, match="Simulated camera failure"):
            camera.read_once()


class TestMockCameraConfig:
    """Test MockCameraConfig functionality."""

    def test_default_values(self):
        """Test default values are set correctly."""
        config = MockCameraConfig(name="test")

        assert config.name == "test"
        assert config.width == 640
        assert config.height == 480
        assert config.fps == 30.0
        assert config.type == "mock"
        assert config.target_class == MockCamera

    def test_custom_values(self):
        """Test custom values are preserved."""
        config = MockCameraConfig(name="custom", width=1920, height=1080, fps=60.0)

        assert config.name == "custom"
        assert config.width == 1920
        assert config.height == 1080
        assert config.fps == 60.0


class TestManagedCamera:
    """Test ManagedCamera functionality."""

    def test_managed_camera_creation(self):
        """Test creating a managed camera."""
        config = MockCameraConfig(name="managed", width=640, height=480)
        managed_camera = ManagedCamera(config)

        assert managed_camera.name == "managed"
        assert managed_camera.width == 640
        assert managed_camera.height == 480
        assert managed_camera.shared_memory_name == "managed"
        assert managed_camera.shared_memory_size == 640 * 480 * 3

    def test_managed_camera_custom_shared_memory_name(self):
        """Test managed camera with custom shared memory name."""
        config = MockCameraConfig(name="managed")
        managed_camera = ManagedCamera(config, shared_memory_name="custom_shm")

        assert managed_camera.shared_memory_name == "custom_shm"

    def test_managed_camera_read_once(self):
        """Test reading from managed camera."""
        config = MockCameraConfig(name="managed", width=320, height=240)
        managed_camera = ManagedCamera(config)

        frame = managed_camera.read_once()

        assert frame.shape == (240, 320, 3)
        assert frame.dtype == np.uint8

    def test_export_shared_camera_config(self):
        """Test exporting shared camera configuration."""
        config = MockCameraConfig(name="export_test", width=800, height=600, fps=25.0)
        managed_camera = ManagedCamera(config)

        shared_config = managed_camera.export_shared_camera_config()

        assert isinstance(shared_config, SharedCameraConfig)
        assert shared_config.name == "export_test"
        assert shared_config.width == 800
        assert shared_config.height == 600
        assert shared_config.fps == 25.0
        assert shared_config.shared_memory_name == "export_test"
        assert shared_config.shared_memory_size == 800 * 600 * 3


class TestSharedCamera:
    """Test SharedCamera functionality."""

    def test_shared_camera_creation(self):
        """Test creating a shared camera."""
        config = SharedCameraConfig(
            name="shared",
            width=640,
            height=480,
            shared_memory_name="test_shm",
            shared_memory_size=640 * 480 * 3,
        )

        with patch("malphite.camera.SharedMemory") as mock_shm:
            mock_shm_instance = MagicMock()
            mock_shm_instance.buf = bytearray(640 * 480 * 3)
            mock_shm.return_value = mock_shm_instance

            camera = SharedCamera(config)

            assert camera.name == "shared"
            assert camera.width == 640
            assert camera.height == 480
            assert camera.shared_memory_name == "test_shm"
            assert camera.shared_memory_size == 640 * 480 * 3
            mock_shm.assert_called_once_with(
                name="test_shm", size=640 * 480 * 3, track=False
            )

    def test_shared_camera_missing_parameters(self):
        """Test SharedCamera with missing required parameters."""
        with pytest.raises(ValueError, match="Width and height must be provided"):
            config = SharedCameraConfig(name="incomplete")

    def test_shared_camera_read_once(self):
        """Test reading from shared camera."""
        config = SharedCameraConfig(
            name="shared",
            width=320,
            height=240,
            shared_memory_name="test_shm",
            shared_memory_size=320 * 240 * 3,
        )

        with patch("malphite.camera.SharedMemory") as mock_shm:
            # Create a mock buffer with some data
            buffer_data = bytearray(320 * 240 * 3)
            for i in range(len(buffer_data)):
                buffer_data[i] = i % 256

            mock_shm_instance = MagicMock()
            mock_shm_instance.buf = buffer_data
            mock_shm.return_value = mock_shm_instance

            camera = SharedCamera(config)
            frame = camera.read_once()

            assert frame.shape == (240, 320, 3)
            assert frame.dtype == np.uint8
            # Verify it's a copy, not the original array
            original_frame = camera.image_frame
            assert not np.shares_memory(frame, original_frame)


class TestSharedCameraConfig:
    """Test SharedCameraConfig functionality."""

    def test_shared_camera_config_post_init(self):
        """Test SharedCameraConfig post-initialization."""
        config = SharedCameraConfig(name="test", width=640, height=480)

        assert config.shared_memory_name == "test"
        assert config.shared_memory_size == 640 * 480 * 3

    def test_shared_camera_config_custom_shared_memory_name(self):
        """Test SharedCameraConfig with custom shared memory name."""
        config = SharedCameraConfig(
            name="test", width=640, height=480, shared_memory_name="custom_name"
        )

        assert config.shared_memory_name == "custom_name"

    def test_shared_camera_config_missing_dimensions(self):
        """Test SharedCameraConfig without width/height."""
        with pytest.raises(ValueError, match="Width and height must be provided"):
            SharedCameraConfig(name="test")

    def test_shared_camera_config_custom_size(self):
        """Test SharedCameraConfig with custom shared memory size."""
        config = SharedCameraConfig(
            name="test", width=640, height=480, shared_memory_size=1000000
        )

        assert config.shared_memory_size == 1000000


if __name__ == "__main__":
    pytest.main([__file__])
