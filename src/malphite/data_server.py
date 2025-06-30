from __future__ import annotations

from multiprocessing import Process
from threading import Event
from typing import Union, overload

import numpy as np

from .camera import CameraConfig, ManagedCamera, SharedCameraConfig
from .shared_memory import SharedMemory


class SharedCameraServer:
    """Server to manage cameras for streaming using shared memory.

    This server allows you to manage multiple cameras, stream their data to shared memory,
    and access the camera feeds from other processes. Each camera runs in its own process.

    # Examples

    Basic usage with a single camera:

    ```python
    import time

    from malphite import OpenCVCameraConfig, SharedCameraServer

    # Create server and configure camera
    camera_server = SharedCameraServer()
    camera_config = OpenCVCameraConfig(name="webcam", camera_path="/dev/video0")

    # Add camera and get shared memory configuration
    shared_config = camera_server.append_camera(camera_config)

    # Start streaming
    camera_server.activate_camera_streaming("webcam")

    # Keep the server process running
    while True:
        # do_something()
        time.sleep(1)
    ```

    Multiple cameras with different activation patterns:

    ```python
    # Initialize with multiple cameras
    configs = [
        OpenCVCameraConfig(name="cam1", camera_path="/dev/video0"),
        OpenCVCameraConfig(name="cam2", camera_path="/dev/video1")
    ]
    server = SharedCameraServer(configs)

    # Activate all cameras at once
    server.activate_all_camera_streaming()

    # Or activate specific cameras
    server.activate_camera_streaming(["cam1", "cam2"])
    server.activate_camera_streaming("cam1")  # Single camera
    server.activate_camera_streaming(0)       # By index
    ```

    # Note

    The server process must remain alive while cameras are streaming.
    After the server process down, all shared memory will be closed and unlinked.
    """

    def __init__(self, camera_configs: list[CameraConfig] = None):
        self._cameras: list[ManagedCamera] = []
        self._streaming_processes: list[Process | None] = []

        if camera_configs:
            for config in camera_configs:
                self.append_camera(config)

    def contains_camera(self, camera_name: str) -> bool:
        """
        Checks if a camera with the given name exists in the server.

        Parameters:
            camera_name (str): The name of the camera to check.
        """
        return any(cam._config.name == camera_name for cam in self._cameras)

    def append_camera(
        self, camera_config: CameraConfig, shared_memory_name: str = None
    ) -> SharedCameraConfig:
        """Appends a camera to the server.

        Args:
            camera_config (CameraConfig): The configuration for the camera.
            shared_memory_name (str, optional): The name of the shared memory segment. Defaults to be the same as the camera name in `camera_config`.

        Raises:
            ValueError: If a camera with the same name already exists.

        Returns:
            SharedCameraConfig: The shared camera configuration which can be used to access the camera data from other processes.
        """
        if self.contains_camera(camera_config.name):
            raise ValueError(f"Camera with name '{camera_config.name}' already exists.")
        camera = ManagedCamera(camera_config, shared_memory_name)
        self._cameras.append(camera)
        self._streaming_processes.append(None)
        return camera.export_shared_camera_config()

    def extend_cameras(
        self, camera_configs: list[CameraConfig]
    ) -> list[SharedCameraConfig]:
        """
        Extends the server with multiple cameras.

        Args:
            camera_configs (list[CameraConfig]): The list of camera configurations.

        Returns:
            list[SharedCameraConfig]: The list of shared camera configurations.
        """
        return [self.append_camera(config) for config in camera_configs]

    @overload
    def remove_camera(self, camera_name: str) -> None:
        """Remove a camera by name.

        Args:
            camera_name (str): The name of the camera to remove.
        """
        ...

    @overload
    def remove_camera(self, index: int) -> None:
        """Remove a camera by index.

        Args:
            index (int): The index of the camera to remove.
        """
        ...

    @overload
    def remove_camera(self, camera_names: list[str]) -> None:
        """Remove multiple cameras by names.

        Args:
            camera_names (list[str]): The list of camera names to remove.
        """
        ...

    @overload
    def remove_camera(self, indices: list[int]) -> None:
        """Remove multiple cameras by indices.

        Args:
            indices (list[int]): The list of camera indices to remove.
        """
        ...

    def remove_camera(
        self,
        camera_name: Union[str, list[str], None] = None,
        index: Union[int, list[int], None] = None,
    ) -> None:
        """Remove camera(s) from the server by name(s) or index/indices.

        Args:
            camera_name (Union[str, list[str], None], optional): The name(s) of the camera(s) to remove.
            index (Union[int, list[int], None], optional): The index/indices of the camera(s) to remove.

        Raises:
            ValueError: If camera name is not found or if both camera_name and index are provided.
            IndexError: If camera index is out of range.
            TypeError: If neither camera_name nor index is provided, or if invalid types are provided.
            RuntimeError: If trying to remove a camera that is currently streaming.
        """
        if camera_name is not None and index is not None:
            raise ValueError("Cannot specify both camera_name and index parameters.")

        if camera_name is None and index is None:
            raise TypeError("Must provide either camera_name or index parameter.")

        # Handle single camera name
        if isinstance(camera_name, str):
            self._remove_single_camera_by_name(camera_name)

        # Handle list of camera names
        elif isinstance(camera_name, list) and all(
            isinstance(name, str) for name in camera_name
        ):
            # Remove in reverse order of indices to avoid index shifting issues
            indices_to_remove = []
            for name in camera_name:
                idx = self._find_camera_index_by_name(name)
                indices_to_remove.append(idx)

            # Sort indices in descending order to remove from end to beginning
            indices_to_remove.sort(reverse=True)
            for idx in indices_to_remove:
                self._remove_camera_by_index(idx)

        # Handle single index
        elif isinstance(index, int):
            self._remove_camera_by_index(index)

        # Handle list of indices
        elif isinstance(index, list) and all(isinstance(idx, int) for idx in index):
            # Validate all indices first
            for idx in index:
                if idx < 0 or idx >= len(self._cameras):
                    raise IndexError(f"Camera index {idx} out of range.")

            # Sort indices in descending order to remove from end to beginning
            sorted_indices = sorted(set(index), reverse=True)
            for idx in sorted_indices:
                self._remove_camera_by_index(idx)

        else:
            raise TypeError("Invalid type for camera_name or index parameter.")

    def _find_camera_index_by_name(self, camera_name: str) -> int:
        """Find the index of a camera by name.

        Args:
            camera_name (str): The name of the camera to find.

        Returns:
            int: The index of the camera.

        Raises:
            ValueError: If the camera name is not found.
        """
        for i, cam in enumerate(self._cameras):
            if cam._config.name == camera_name:
                return i
        raise ValueError(f"Camera with name '{camera_name}' not found.")

    def _remove_single_camera_by_name(self, camera_name: str) -> None:
        """Remove a single camera by name.

        Args:
            camera_name (str): The name of the camera to remove.
        """
        idx = self._find_camera_index_by_name(camera_name)
        self._remove_camera_by_index(idx)

    def _remove_camera_by_index(self, index: int) -> None:
        """Remove a camera by index.

        Args:
            index (int): The index of the camera to remove.

        Raises:
            IndexError: If the index is out of range.
            RuntimeError: If the camera is currently streaming.
        """
        if index < 0 or index >= len(self._cameras):
            raise IndexError(f"Camera index {index} out of range.")

        # Check if camera is currently streaming
        if self._streaming_processes[index] is not None:
            raise RuntimeError(
                f"Cannot remove camera '{self._cameras[index]._config.name}' while it is streaming. "
                "Please deactivate streaming first."
            )

        # Remove the camera and its corresponding streaming process slot
        self._cameras.pop(index)
        self._streaming_processes.pop(index)

    def activate_all_camera_streaming(
        self,
    ) -> None:
        for i, cam in enumerate(self._cameras):
            if self._streaming_processes[i] is None:
                self.activate_camera_streaming(cam._config.name)

    @overload
    def activate_camera_streaming(self, camera_name: str) -> None:
        """Activate the camera streaming for a given camera name.

        Args:
            camera_name (str): The name of the camera to activate.
        """
        ...

    @overload
    def activate_camera_streaming(self, index: int) -> None:
        """Activate the camera streaming for a given camera index.

        Args:
            index (int): The index of the camera to activate.
        """
        ...

    @overload
    def activate_camera_streaming(self, camera_names: list[str]) -> None:
        """Activate the camera streaming for multiple cameras by names.

        Args:
            camera_names (list[str]): The list of camera names to activate.
        """
        ...

    @overload
    def activate_camera_streaming(self, indices: list[int]) -> None:
        """Activate the camera streaming for multiple cameras by indices.

        Args:
            indices (list[int]): The list of camera indices to activate.
        """
        ...

    def activate_camera_streaming(
        self,
        camera_name: Union[str, list[str], None] = None,
        index: Union[int, list[int], None] = None,
    ) -> None:
        """
        Activates the camera streaming for specific camera(s) by name(s) or index/indices.

        Args:
            camera_name (Union[str, list[str], None], optional): The name(s) of the camera(s) to activate.
            index (Union[int, list[int], None], optional): The index/indices of the camera(s) to activate.

        Raises:
            ValueError: If both camera_name and index are provided, or if camera name is not found.
            IndexError: If camera index is out of range.
            TypeError: If neither camera_name nor index is provided, or if invalid types are provided.
            RuntimeError: If trying to activate a camera that is already streaming.
        """
        if camera_name is not None and index is not None:
            raise ValueError("Cannot specify both camera_name and index parameters.")

        if camera_name is None and index is None:
            raise TypeError("Must provide either camera_name or index parameter.")

        # Handle single camera name
        if isinstance(camera_name, str):
            self._activate_single_camera_by_name(camera_name)

        # Handle list of camera names
        elif isinstance(camera_name, list) and all(
            isinstance(name, str) for name in camera_name
        ):
            for name in camera_name:
                self._activate_single_camera_by_name(name)

        # Handle single index
        elif isinstance(index, int):
            self._activate_camera_by_index(index)

        # Handle list of indices
        elif isinstance(index, list) and all(isinstance(idx, int) for idx in index):
            # Validate all indices first
            for idx in index:
                if idx < 0 or idx >= len(self._cameras):
                    raise IndexError(f"Camera index {idx} out of range.")

            # Activate all cameras
            for idx in index:
                self._activate_camera_by_index(idx)

        else:
            raise TypeError("Invalid type for camera_name or index parameter.")

    def _activate_single_camera_by_name(self, camera_name: str) -> None:
        """Activate a single camera by name.

        Args:
            camera_name (str): The name of the camera to activate.

        Raises:
            ValueError: If the camera name is not found.
        """
        idx = self._find_camera_index_by_name(camera_name)
        self._activate_camera_by_index(idx)

    def _activate_camera_by_index(self, idx: int) -> None:
        """Activate a camera by index.

        Args:
            idx (int): The index of the camera to activate.

        Raises:
            IndexError: If the index is out of range.
            RuntimeError: If the camera is already streaming.
        """
        if idx < 0 or idx >= len(self._cameras):
            raise IndexError(f"Camera index {idx} out of range.")

        if self._streaming_processes[idx] is not None:
            raise RuntimeError(
                f"Camera '{self._cameras[idx]._config.name}' is already streaming."
            )

        def stream_camera(camera: ManagedCamera, stop_event: Event) -> None:
            shm = SharedMemory(
                name=camera.shared_memory_name,
                size=camera.shared_memory_size,
                track=True,  # TODO: add a way to disable tracking
                create=True,
            )
            image_array = np.ndarray(
                (camera._config.height, camera._config.width, 3),
                dtype=np.uint8,
                buffer=shm.buf,
            )
            try:
                while True:
                    if stop_event.is_set():
                        break
                    image_array[:] = camera.read_once()
            except KeyboardInterrupt:
                pass
            except Exception as e:
                raise RuntimeError(
                    f"Error while streaming camera '{camera._config.name}': {e}"
                ) from e
            finally:
                shm.close()
                shm.unlink()

        process = Process(
            target=stream_camera, args=(self._cameras[idx], stop_event := Event())
        )
        process.stop_event = (
            stop_event  # Store the stop event in the process for later use
        )
        process.start()
        self._streaming_processes[idx] = process

    def deactivate_all_camera_streaming(
        self,
    ) -> None:
        for i, cam in enumerate(self._cameras):
            if self._streaming_processes[i] is not None:
                self.deactivate_camera_streaming(cam._config.name)

    @overload
    def deactivate_camera_streaming(self, camera_name: str) -> None: ...

    @overload
    def deactivate_camera_streaming(self, index: int) -> None: ...

    @overload
    def deactivate_camera_streaming(self, camera_names: list[str]) -> None:
        """Deactivate the camera streaming for multiple cameras by names.

        Args:
            camera_names (list[str]): The list of camera names to deactivate.
        """
        ...

    @overload
    def deactivate_camera_streaming(self, indices: list[int]) -> None:
        """Deactivate the camera streaming for multiple cameras by indices.

        Args:
            indices (list[int]): The list of camera indices to deactivate.
        """
        ...

    def deactivate_camera_streaming(
        self,
        camera_name: Union[str, list[str], None] = None,
        index: Union[int, list[int], None] = None,
    ) -> None:
        """
        Deactivates the camera streaming for specific camera(s) by name(s) or index/indices.

        Args:
            camera_name (Union[str, list[str], None], optional): The name(s) of the camera(s) to deactivate.
            index (Union[int, list[int], None], optional): The index/indices of the camera(s) to deactivate.

        Raises:
            ValueError: If both camera_name and index are provided, or if camera name is not found.
            IndexError: If camera index is out of range.
            TypeError: If neither camera_name nor index is provided, or if invalid types are provided.
            RuntimeError: If trying to deactivate a camera that is not streaming.
        """
        if camera_name is not None and index is not None:
            raise ValueError("Cannot specify both camera_name and index parameters.")

        if camera_name is None and index is None:
            raise TypeError("Must provide either camera_name or index parameter.")

        # Handle single camera name
        if isinstance(camera_name, str):
            self._deactivate_single_camera_by_name(camera_name)

        # Handle list of camera names
        elif isinstance(camera_name, list) and all(
            isinstance(name, str) for name in camera_name
        ):
            for name in camera_name:
                self._deactivate_single_camera_by_name(name)

        # Handle single index
        elif isinstance(index, int):
            self._deactivate_camera_by_index(index)

        # Handle list of indices
        elif isinstance(index, list) and all(isinstance(idx, int) for idx in index):
            # Validate all indices first
            for idx in index:
                if idx < 0 or idx >= len(self._cameras):
                    raise IndexError(f"Camera index {idx} out of range.")

            # Deactivate all cameras
            for idx in index:
                self._deactivate_camera_by_index(idx)

        else:
            raise TypeError("Invalid type for camera_name or index parameter.")

    def _deactivate_single_camera_by_name(self, camera_name: str) -> None:
        """Deactivate a single camera by name.

        Args:
            camera_name (str): The name of the camera to deactivate.

        Raises:
            ValueError: If the camera name is not found.
        """
        idx = self._find_camera_index_by_name(camera_name)
        self._deactivate_camera_by_index(idx)

    def _deactivate_camera_by_index(self, idx: int) -> None:
        """Deactivate a camera by index.

        Args:
            idx (int): The index of the camera to deactivate.

        Raises:
            IndexError: If the index is out of range.
            RuntimeError: If the camera is not streaming.
        """
        if idx < 0 or idx >= len(self._cameras):
            raise IndexError(f"Camera index {idx} out of range.")

        if self._streaming_processes[idx] is None:
            raise RuntimeError(
                f"Camera '{self._cameras[idx]._config.name}' is not streaming."
            )

        self._streaming_processes[idx].stop_event.set()
        self._streaming_processes[idx].join()
        self._streaming_processes[idx] = None

    def __del__(self):
        self.deactivate_all_camera_streaming()
