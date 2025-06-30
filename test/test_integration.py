"""
Integration tests for the SharedCameraServer with real streaming scenarios.

These tests simulate more realistic usage patterns and test the integration
between different components.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from malphite.data_server import SharedCameraServer
from test.conftest import MockCameraConfig


class TestSharedCameraServerIntegration:
    """Integration tests for SharedCameraServer."""

    def test_full_lifecycle_single_camera(self):
        """Test complete lifecycle of adding, streaming, and removing a camera."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="lifecycle_test", width=640, height=480)

        # Add camera
        shared_config = server.append_camera(config)
        assert server.contains_camera("lifecycle_test")
        assert shared_config.name == "lifecycle_test"

        # Mock streaming to avoid actual process creation
        with patch("malphite.data_server.Process") as mock_process:
            mock_process_instance = MagicMock()
            mock_process.return_value = mock_process_instance

            # Activate streaming
            server.activate_camera_streaming("lifecycle_test")
            assert server._streaming_processes[0] is mock_process_instance
            mock_process_instance.start.assert_called_once()

            # Deactivate streaming
            mock_stop_event = MagicMock()
            mock_process_instance.stop_event = mock_stop_event
            server.deactivate_camera_streaming("lifecycle_test")
            mock_stop_event.set.assert_called_once()
            mock_process_instance.join.assert_called_once()

        # Remove camera
        server.remove_camera("lifecycle_test")
        assert not server.contains_camera("lifecycle_test")
        assert len(server._cameras) == 0

    def test_multiple_cameras_workflow(self):
        """Test workflow with multiple cameras."""
        server = SharedCameraServer()
        configs = [
            MockCameraConfig(name=f"cam_{i}", width=640, height=480) for i in range(3)
        ]

        # Add all cameras
        shared_configs = server.extend_cameras(configs)
        assert len(server._cameras) == 3
        assert len(shared_configs) == 3

        with patch("malphite.data_server.Process") as mock_process:
            mock_process_instances = [MagicMock() for _ in range(3)]
            mock_process.side_effect = mock_process_instances

            # Activate some cameras
            server.activate_camera_streaming(["cam_0", "cam_2"])
            assert mock_process.call_count == 2

            # Activate remaining camera
            server.activate_camera_streaming("cam_1")
            assert mock_process.call_count == 3

            # Deactivate all
            for i, mock_instance in enumerate(mock_process_instances):
                mock_stop_event = MagicMock()
                mock_instance.stop_event = mock_stop_event
                server._streaming_processes[i] = mock_instance

            server.deactivate_all_camera_streaming()
            assert all(proc is None for proc in server._streaming_processes)

    def test_server_initialization_with_cameras_and_streaming(self):
        """Test server initialization with cameras and immediate streaming."""
        configs = [
            MockCameraConfig(name="init_cam1"),
            MockCameraConfig(name="init_cam2"),
        ]
        server = SharedCameraServer(configs)

        assert len(server._cameras) == 2
        assert server.contains_camera("init_cam1")
        assert server.contains_camera("init_cam2")

        with patch("malphite.data_server.Process") as mock_process:
            mock_process_instances = [MagicMock(), MagicMock()]
            mock_process.side_effect = mock_process_instances

            server.activate_all_camera_streaming()
            assert mock_process.call_count == 2

    def test_mixed_operations_sequence(self):
        """Test a sequence of mixed operations."""
        server = SharedCameraServer()

        # Add initial cameras
        configs = [MockCameraConfig(name=f"seq_cam_{i}") for i in range(4)]
        server.extend_cameras(configs)

        with patch("malphite.data_server.Process") as mock_process:
            mock_process_instances = [MagicMock() for _ in range(4)]
            mock_process.side_effect = mock_process_instances

            # Activate first two
            server.activate_camera_streaming(index=[0, 1])

            # Remove one streaming camera (should fail)
            mock_stop_event = MagicMock()
            mock_process_instances[0].stop_event = mock_stop_event
            server._streaming_processes[0] = mock_process_instances[0]

            with pytest.raises(RuntimeError):
                server.remove_camera(index=0)

            # Deactivate and then remove
            server.deactivate_camera_streaming(index=0)
            server.remove_camera(index=0)  # This should now work

            # Add new camera
            new_config = MockCameraConfig(name="new_camera")
            server.append_camera(new_config)

            # Final state verification
            assert len(server._cameras) == 4  # 3 original + 1 new - 1 removed
            assert not server.contains_camera("seq_cam_0")  # Removed
            assert server.contains_camera("new_camera")  # Added

    def test_error_recovery_scenarios(self):
        """Test error recovery in various scenarios."""
        server = SharedCameraServer()
        config = MockCameraConfig(name="error_test")
        server.append_camera(config)

        # Test recovery from failed activation
        with patch("malphite.data_server.Process") as mock_process:
            mock_process.side_effect = Exception("Process creation failed")

            with pytest.raises(Exception):
                server.activate_camera_streaming("error_test")

            # Server should still be in consistent state
            assert server.contains_camera("error_test")
            assert server._streaming_processes[0] is None

        # Test successful activation after failure
        with patch("malphite.data_server.Process") as mock_process:
            mock_process_instance = MagicMock()
            mock_process.return_value = mock_process_instance

            server.activate_camera_streaming("error_test")
            assert server._streaming_processes[0] is mock_process_instance

    def test_shared_memory_configuration_integration(self):
        """Test shared memory configuration in integrated scenarios."""
        server = SharedCameraServer()

        # Test with different sized cameras
        configs = [
            MockCameraConfig(name="small", width=320, height=240),
            MockCameraConfig(name="medium", width=640, height=480),
            MockCameraConfig(name="large", width=1920, height=1080),
        ]

        shared_configs = []
        for config in configs:
            shared_config = server.append_camera(config)
            shared_configs.append(shared_config)

        # Verify shared memory sizes
        assert shared_configs[0].shared_memory_size == 320 * 240 * 3
        assert shared_configs[1].shared_memory_size == 640 * 480 * 3
        assert shared_configs[2].shared_memory_size == 1920 * 1080 * 3

        # Verify unique shared memory names
        shm_names = [config.shared_memory_name for config in shared_configs]
        assert len(set(shm_names)) == len(shm_names)  # All unique

    def test_concurrent_activation_deactivation(self):
        """Test concurrent activation and deactivation patterns."""
        server = SharedCameraServer()
        configs = [MockCameraConfig(name=f"concurrent_{i}") for i in range(5)]
        server.extend_cameras(configs)

        with patch("malphite.data_server.Process") as mock_process:
            mock_instances = [MagicMock() for _ in range(5)]
            mock_process.side_effect = mock_instances

            # Activate odd indices
            server.activate_camera_streaming(index=[1, 3])

            # Activate even indices
            server.activate_camera_streaming(index=[0, 2, 4])

            # Verify all are active
            assert mock_process.call_count == 5

            # Setup for deactivation
            for i, mock_instance in enumerate(mock_instances):
                mock_stop_event = MagicMock()
                mock_instance.stop_event = mock_stop_event
                server._streaming_processes[i] = mock_instance

            # Deactivate in different pattern
            server.deactivate_camera_streaming(
                camera_name=["concurrent_1", "concurrent_3"]
            )
            server.deactivate_camera_streaming(index=[0, 2, 4])

            # Verify all are deactivated
            assert all(proc is None for proc in server._streaming_processes)


class TestPerformanceAndScalability:
    """Test performance and scalability aspects."""

    def test_many_cameras_management(self):
        """Test managing many cameras efficiently."""
        num_cameras = 50
        server = SharedCameraServer()

        # Add many cameras
        configs = [MockCameraConfig(name=f"perf_cam_{i}") for i in range(num_cameras)]

        start_time = time.time()
        server.extend_cameras(configs)
        end_time = time.time()

        # Adding 50 cameras should be fast (< 1 second)
        assert end_time - start_time < 1.0
        assert len(server._cameras) == num_cameras

        # Test bulk operations
        with patch("malphite.data_server.Process") as mock_process:
            mock_instances = [MagicMock() for _ in range(num_cameras)]
            mock_process.side_effect = mock_instances

            start_time = time.time()
            server.activate_all_camera_streaming()
            end_time = time.time()

            # Activating all should be reasonably fast
            assert end_time - start_time < 2.0
            assert mock_process.call_count == num_cameras

    def test_repeated_operations(self):
        """Test repeated add/remove operations."""
        server = SharedCameraServer()

        # Repeatedly add and remove cameras
        for i in range(10):
            config = MockCameraConfig(name=f"repeat_{i}")
            server.append_camera(config)
            assert server.contains_camera(f"repeat_{i}")

            server.remove_camera(camera_name=f"repeat_{i}")
            assert not server.contains_camera(f"repeat_{i}")

        # Server should be empty
        assert len(server._cameras) == 0


if __name__ == "__main__":
    pytest.main([__file__])
