"""
Comprehensive tests for SharedCameraServer functionality.

This module tests all aspects of the SharedCameraServer including:
- Camera management (add/remove)
- Streaming activation/deactivation
- Error handling
- Multiple camera scenarios
"""

import time
from multiprocessing import Process
from unittest.mock import MagicMock, patch

import pytest

from malphite.camera import SharedCameraConfig
from malphite.data_server import SharedCameraServer
from test.conftest import FailingMockCameraConfig, MockCameraConfig


class TestSharedCameraServerBasics:
    """Test basic functionality of SharedCameraServer."""

    def test_empty_server_initialization(self):
        """Test creating an empty server."""
        server = SharedCameraServer()
        assert len(server._cameras) == 0
        assert len(server._streaming_processes) == 0

    def test_server_initialization_with_cameras(self):
        """Test creating a server with initial cameras."""
        configs = [
            MockCameraConfig(name="cam1"),
            MockCameraConfig(name="cam2", width=1280, height=720),
        ]
        server = SharedCameraServer(configs)
        assert len(server._cameras) == 2
        assert len(server._streaming_processes) == 2
        assert server.contains_camera("cam1")
        assert server.contains_camera("cam2")


class TestCameraManagement:
    """Test camera management operations."""

    def test_append_camera(self):
        """Test adding a single camera."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="test_cam", width=640, height=480)

        shared_config = server.append_camera(config)

        assert len(server._cameras) == 1
        assert len(server._streaming_processes) == 1
        assert server.contains_camera("test_cam")
        assert isinstance(shared_config, SharedCameraConfig)
        assert shared_config.name == "test_cam"
        assert shared_config.width == 640
        assert shared_config.height == 480

    def test_append_duplicate_camera_name(self):
        """Test that adding a camera with duplicate name raises ValueError."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="duplicate")

        server.append_camera(config)

        with pytest.raises(
            ValueError, match="Camera with name 'duplicate' already exists"
        ):
            server.append_camera(config)

    def test_extend_cameras(self):
        """Test adding multiple cameras at once."""
        server = SharedCameraServer()
        configs = [
            MockCameraConfig(name="cam1"),
            MockCameraConfig(name="cam2"),
            MockCameraConfig(name="cam3"),
        ]

        shared_configs = server.extend_cameras(configs)

        assert len(server._cameras) == 3
        assert len(shared_configs) == 3
        assert all(isinstance(config, SharedCameraConfig) for config in shared_configs)
        assert server.contains_camera("cam1")
        assert server.contains_camera("cam2")
        assert server.contains_camera("cam3")

    def test_contains_camera(self):
        """Test checking if camera exists."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="test_cam")

        assert not server.contains_camera("test_cam")
        server.append_camera(config)
        assert server.contains_camera("test_cam")
        assert not server.contains_camera("nonexistent")


class TestCameraRemoval:
    """Test camera removal operations."""

    def test_remove_camera_by_name(self):
        """Test removing a camera by name."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="remove_me")
        server.append_camera(config)

        assert server.contains_camera("remove_me")
        server.remove_camera(camera_name="remove_me")
        assert not server.contains_camera("remove_me")
        assert len(server._cameras) == 0

    def test_remove_camera_by_index(self):
        """Test removing a camera by index."""
        server = SharedCameraServer()
        configs = [
            MockCameraConfig(name="cam1"),
            MockCameraConfig(name="cam2"),
            MockCameraConfig(name="cam3"),
        ]
        server.extend_cameras(configs)

        server.remove_camera(index=1)  # Remove cam2
        assert len(server._cameras) == 2
        assert server.contains_camera("cam1")
        assert not server.contains_camera("cam2")
        assert server.contains_camera("cam3")

    def test_remove_multiple_cameras_by_names(self):
        """Test removing multiple cameras by names."""
        server = SharedCameraServer()
        configs = [
            MockCameraConfig(name="cam1"),
            MockCameraConfig(name="cam2"),
            MockCameraConfig(name="cam3"),
        ]
        server.extend_cameras(configs)

        server.remove_camera(camera_name=["cam1", "cam3"])
        assert len(server._cameras) == 1
        assert not server.contains_camera("cam1")
        assert server.contains_camera("cam2")
        assert not server.contains_camera("cam3")

    def test_remove_multiple_cameras_by_indices(self):
        """Test removing multiple cameras by indices."""
        server = SharedCameraServer()
        configs = [
            MockCameraConfig(name="cam1"),
            MockCameraConfig(name="cam2"),
            MockCameraConfig(name="cam3"),
            MockCameraConfig(name="cam4"),
        ]
        server.extend_cameras(configs)

        server.remove_camera(index=[0, 2])  # Remove cam1 and cam3
        assert len(server._cameras) == 2
        assert not server.contains_camera("cam1")
        assert server.contains_camera("cam2")
        assert not server.contains_camera("cam3")
        assert server.contains_camera("cam4")

    def test_remove_camera_invalid_name(self):
        """Test removing non-existent camera by name."""
        server = SharedCameraServer()

        with pytest.raises(
            ValueError, match="Camera with name 'nonexistent' not found"
        ):
            server.remove_camera(camera_name="nonexistent")

    def test_remove_camera_invalid_index(self):
        """Test removing camera with invalid index."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="cam1")
        server.append_camera(config)

        with pytest.raises(IndexError, match="Camera index 5 out of range"):
            server.remove_camera(index=5)

        with pytest.raises(IndexError, match="Camera index -1 out of range"):
            server.remove_camera(index=-1)

    def test_remove_camera_invalid_parameters(self):
        """Test remove_camera with invalid parameter combinations."""
        server = SharedCameraServer()

        # Both parameters provided
        with pytest.raises(
            ValueError, match="Cannot specify both camera_name and index parameters"
        ):
            server.remove_camera(camera_name="cam1", index=0)

        # Neither parameter provided
        with pytest.raises(
            TypeError, match="Must provide either camera_name or index parameter"
        ):
            server.remove_camera()

        # Invalid types
        with pytest.raises(
            TypeError, match="Invalid type for camera_name or index parameter"
        ):
            server.remove_camera(camera_name=123)


class TestStreamingActivation:
    """Test camera streaming activation."""

    def setup_method(self):
        """Set up test with a server and cameras."""
        self.server = SharedCameraServer()
        configs = [
            MockCameraConfig(name="cam1"),
            MockCameraConfig(name="cam2"),
            MockCameraConfig(name="cam3"),
        ]
        self.server.extend_cameras(configs)

    def teardown_method(self):
        """Clean up after tests."""
        self.server.deactivate_all_camera_streaming()

    @patch("malphite.data_server.Process")
    def test_activate_camera_by_name(self, mock_process):
        """Test activating camera streaming by name."""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance

        self.server.activate_camera_streaming(camera_name="cam1")

        mock_process.assert_called_once()
        mock_process_instance.start.assert_called_once()
        assert self.server._streaming_processes[0] is mock_process_instance

    @patch("malphite.data_server.Process")
    def test_activate_camera_by_index(self, mock_process):
        """Test activating camera streaming by index."""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance

        self.server.activate_camera_streaming(index=1)

        mock_process.assert_called_once()
        mock_process_instance.start.assert_called_once()
        assert self.server._streaming_processes[1] is mock_process_instance

    @patch("malphite.data_server.Process")
    def test_activate_multiple_cameras_by_names(self, mock_process):
        """Test activating multiple cameras by names."""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance

        self.server.activate_camera_streaming(camera_name=["cam1", "cam3"])

        assert mock_process.call_count == 2
        assert mock_process_instance.start.call_count == 2
        assert self.server._streaming_processes[0] is mock_process_instance
        assert self.server._streaming_processes[2] is mock_process_instance

    @patch("malphite.data_server.Process")
    def test_activate_multiple_cameras_by_indices(self, mock_process):
        """Test activating multiple cameras by indices."""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance

        self.server.activate_camera_streaming(index=[0, 2])

        assert mock_process.call_count == 2
        assert mock_process_instance.start.call_count == 2
        assert self.server._streaming_processes[0] is mock_process_instance
        assert self.server._streaming_processes[2] is mock_process_instance

    @patch("malphite.data_server.Process")
    def test_activate_all_cameras(self, mock_process):
        """Test activating all cameras at once."""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance

        self.server.activate_all_camera_streaming()

        assert mock_process.call_count == 3
        assert mock_process_instance.start.call_count == 3
        assert all(
            proc is mock_process_instance for proc in self.server._streaming_processes
        )

    def test_activate_invalid_camera_name(self):
        """Test activating non-existent camera by name."""
        with pytest.raises(
            ValueError, match="Camera with name 'nonexistent' not found"
        ):
            self.server.activate_camera_streaming(camera_name="nonexistent")

    def test_activate_invalid_camera_index(self):
        """Test activating camera with invalid index."""
        with pytest.raises(IndexError, match="Camera index 5 out of range"):
            self.server.activate_camera_streaming(index=5)

    def test_activate_invalid_parameters(self):
        """Test activate_camera_streaming with invalid parameters."""
        # Both parameters provided
        with pytest.raises(
            ValueError, match="Cannot specify both camera_name and index parameters"
        ):
            self.server.activate_camera_streaming(camera_name="cam1", index=0)

        # Neither parameter provided
        with pytest.raises(
            TypeError, match="Must provide either camera_name or index parameter"
        ):
            self.server.activate_camera_streaming()

    @patch("malphite.data_server.Process")
    def test_activate_already_streaming_camera(self, mock_process):
        """Test activating a camera that's already streaming."""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance

        self.server.activate_camera_streaming(camera_name="cam1")

        with pytest.raises(RuntimeError, match="Camera 'cam1' is already streaming"):
            self.server.activate_camera_streaming(camera_name="cam1")


class TestStreamingDeactivation:
    """Test camera streaming deactivation."""

    def setup_method(self):
        """Set up test with a server and cameras."""
        self.server = SharedCameraServer()
        configs = [
            MockCameraConfig(name="cam1"),
            MockCameraConfig(name="cam2"),
            MockCameraConfig(name="cam3"),
        ]
        self.server.extend_cameras(configs)

    def teardown_method(self):
        """Clean up after tests."""
        self.server.deactivate_all_camera_streaming()

    def test_deactivate_camera_by_name(self):
        """Test deactivating camera streaming by name."""
        # Mock a streaming process
        mock_process = MagicMock()
        mock_stop_event = MagicMock()
        mock_process.stop_event = mock_stop_event
        self.server._streaming_processes[0] = mock_process

        self.server.deactivate_camera_streaming(camera_name="cam1")

        mock_stop_event.set.assert_called_once()
        mock_process.join.assert_called_once()
        assert self.server._streaming_processes[0] is None

    def test_deactivate_camera_by_index(self):
        """Test deactivating camera streaming by index."""
        # Mock a streaming process
        mock_process = MagicMock()
        mock_stop_event = MagicMock()
        mock_process.stop_event = mock_stop_event
        self.server._streaming_processes[1] = mock_process

        self.server.deactivate_camera_streaming(index=1)

        mock_stop_event.set.assert_called_once()
        mock_process.join.assert_called_once()
        assert self.server._streaming_processes[1] is None

    def test_deactivate_multiple_cameras_by_names(self):
        """Test deactivating multiple cameras by names."""
        # Mock streaming processes
        for i in [0, 2]:
            mock_process = MagicMock()
            mock_stop_event = MagicMock()
            mock_process.stop_event = mock_stop_event
            self.server._streaming_processes[i] = mock_process

        self.server.deactivate_camera_streaming(camera_name=["cam1", "cam3"])

        assert self.server._streaming_processes[0] is None
        assert self.server._streaming_processes[2] is None

    def test_deactivate_all_cameras(self):
        """Test deactivating all camera streaming."""
        # Mock all streaming processes
        for i in range(3):
            mock_process = MagicMock()
            mock_stop_event = MagicMock()
            mock_process.stop_event = mock_stop_event
            self.server._streaming_processes[i] = mock_process

        self.server.deactivate_all_camera_streaming()

        assert all(proc is None for proc in self.server._streaming_processes)

    def test_deactivate_not_streaming_camera(self):
        """Test deactivating a camera that's not streaming."""
        with pytest.raises(RuntimeError, match="Camera 'cam1' is not streaming"):
            self.server.deactivate_camera_streaming(camera_name="cam1")

    def test_deactivate_invalid_camera_name(self):
        """Test deactivating non-existent camera by name."""
        with pytest.raises(
            ValueError, match="Camera with name 'nonexistent' not found"
        ):
            self.server.deactivate_camera_streaming(camera_name="nonexistent")

    def test_deactivate_invalid_parameters(self):
        """Test deactivate_camera_streaming with invalid parameters."""
        # Both parameters provided
        with pytest.raises(
            ValueError, match="Cannot specify both camera_name and index parameters"
        ):
            self.server.deactivate_camera_streaming(camera_name="cam1", index=0)

        # Neither parameter provided
        with pytest.raises(
            TypeError, match="Must provide either camera_name or index parameter"
        ):
            self.server.deactivate_camera_streaming()


class TestRemovalOfStreamingCameras:
    """Test removal of cameras that are currently streaming."""

    def setup_method(self):
        """Set up test with a server and cameras."""
        self.server = SharedCameraServer()
        config = MockCameraConfig(name="streaming_cam")
        self.server.append_camera(config)

    def teardown_method(self):
        """Clean up after tests."""
        self.server.deactivate_all_camera_streaming()

    def test_remove_streaming_camera_by_name(self):
        """Test that removing a streaming camera raises RuntimeError."""
        # Mock a streaming process
        mock_process = MagicMock()
        self.server._streaming_processes[0] = mock_process

        with pytest.raises(
            RuntimeError,
            match="Cannot remove camera 'streaming_cam' while it is streaming",
        ):
            self.server.remove_camera(camera_name="streaming_cam")

    def test_remove_streaming_camera_by_index(self):
        """Test that removing a streaming camera by index raises RuntimeError."""
        # Mock a streaming process
        mock_process = MagicMock()
        self.server._streaming_processes[0] = mock_process

        with pytest.raises(
            RuntimeError,
            match="Cannot remove camera 'streaming_cam' while it is streaming",
        ):
            self.server.remove_camera(index=0)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_type_parameters(self):
        """Test various invalid parameter types."""
        server = SharedCameraServer()

        # Invalid camera_name types for activation
        with pytest.raises(
            TypeError, match="Invalid type for camera_name or index parameter"
        ):
            server.activate_camera_streaming(camera_name=123)

        with pytest.raises(
            TypeError, match="Invalid type for camera_name or index parameter"
        ):
            server.activate_camera_streaming(camera_name=[123, "valid"])

        # Invalid index types for activation
        with pytest.raises(
            TypeError, match="Invalid type for camera_name or index parameter"
        ):
            server.activate_camera_streaming(index="not_int")

        with pytest.raises(
            TypeError, match="Invalid type for camera_name or index parameter"
        ):
            server.activate_camera_streaming(index=[1, "not_int"])

    def test_empty_lists(self):
        """Test behavior with empty lists."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="cam1")
        server.append_camera(config)

        # Empty list should not raise errors but also not do anything
        server.activate_camera_streaming(camera_name=[])
        server.activate_camera_streaming(index=[])
        server.deactivate_camera_streaming(camera_name=[])
        server.deactivate_camera_streaming(index=[])
        server.remove_camera(camera_name=[])
        server.remove_camera(index=[])


class TestSharedMemoryConfiguration:
    """Test shared memory configuration aspects."""

    def test_custom_shared_memory_name(self):
        """Test camera with custom shared memory name."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="cam1")

        shared_config = server.append_camera(config, shared_memory_name="custom_shm")

        assert shared_config.shared_memory_name == "custom_shm"

    def test_default_shared_memory_name(self):
        """Test camera with default shared memory name."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="cam1")

        shared_config = server.append_camera(config)

        assert shared_config.shared_memory_name == "cam1"

    def test_shared_memory_size_calculation(self):
        """Test that shared memory size is calculated correctly."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="cam1", width=640, height=480)

        shared_config = server.append_camera(config)

        expected_size = 640 * 480 * 3  # width * height * 3 channels
        assert shared_config.shared_memory_size == expected_size


class TestConcurrentOperations:
    """Test concurrent operations and thread safety aspects."""

    def test_multiple_servers_with_same_camera_names(self):
        """Test multiple servers with cameras having same names (should not conflict)."""
        server1 = SharedCameraServer()
        server2 = SharedCameraServer()

        config1 = MockCameraConfig(name="same_name")
        config2 = MockCameraConfig(name="same_name")

        shared_config1 = server1.append_camera(config1)
        shared_config2 = server2.append_camera(config2)

        # Both should succeed as they're different server instances
        assert server1.contains_camera("same_name")
        assert server2.contains_camera("same_name")
        assert shared_config1.shared_memory_name == "same_name"
        assert shared_config2.shared_memory_name == "same_name"


class TestServerCleanup:
    """Test server cleanup and resource management."""

    def test_server_destructor_cleanup(self):
        """Test that server properly cleans up on destruction."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="cleanup_test")
        server.append_camera(config)

        # Mock a streaming process
        mock_process = MagicMock()
        mock_stop_event = MagicMock()
        mock_process.stop_event = mock_stop_event
        server._streaming_processes[0] = mock_process

        # Manually call destructor
        server.__del__()

        # Verify cleanup was called
        mock_stop_event.set.assert_called_once()
        mock_process.join.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
