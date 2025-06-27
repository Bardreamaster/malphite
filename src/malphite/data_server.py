from __future__ import annotations

from multiprocessing import Process
from threading import Event
from typing import TYPE_CHECKING, overload

import numpy as np

from .camera import CameraConfig, ManagedCamera, SharedCameraConfig
from .shared_memory import SharedMemory


class SharedCameraServer:
    cameras: list[ManagedCamera] = []
    streaming_processes: list[Process | None] = []

    def __init__(self, camera_configs: list[CameraConfig] = None):
        if camera_configs:
            for config in camera_configs:
                self.append_camera(config)

    def contains_camera(self, camera_name: str) -> bool:
        """
        Checks if a camera with the given name exists in the server.

        Parameters:
            camera_name (str): The name of the camera to check.
        """
        return any(cam._config.name == camera_name for cam in self.cameras)

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
        self.cameras.append(camera)
        self.streaming_processes.append(None)
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

    # TODO: Implement a method to remove a camera by name or index

    # TODO:
    # @overload
    # def activate_camera_streaming(self,) -> None:
    #     pass

    @overload
    def activate_camera_streaming(self, camera_name: str) -> None:
        pass

    @overload
    def activate_camera_streaming(self, index: int) -> None:
        pass

    def activate_camera_streaming(
        self, camera_name: str | None = None, index: int | None = None
    ) -> None:
        """
        Activates the camera streaming for a specific camera by name or index.
        """
        if isinstance(camera_name, str):  # TODO: validate camera_name
            idx = next(
                (
                    i
                    for i, cam in enumerate(self.cameras)
                    if cam._config.name == camera_name
                ),
                None,
            )
        elif isinstance(index, int):
            if index < 0 or index >= len(self.cameras):
                raise IndexError("Camera index out of range.")
            idx = index
        else:
            raise TypeError(
                "Input must be either a camera name (str) or an index (int)."
            )

        if self.streaming_processes[idx] is not None:
            raise RuntimeError(
                f"Camera '{self.cameras[idx]._config.name}' is already streaming."
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
            target=stream_camera, args=(self.cameras[idx], stop_event := Event())
        )
        process.stop_event = (
            stop_event  # Store the stop event in the process for later use
        )
        process.start()
        self.streaming_processes[idx] = process

    def deactivate_camera_streaming(self, camera_name: str | int) -> None:
        """
        Deactivates the camera streaming for a specific camera by name or index.
        """
        if isinstance(camera_name, str):
            idx = next(
                (
                    i
                    for i, cam in enumerate(self.cameras)
                    if cam._config.name == camera_name
                ),
                None,
            )
        elif isinstance(camera_name, int):
            if camera_name < 0 or camera_name >= len(self.cameras):
                raise IndexError("Camera index out of range.")
            idx = camera_name
        else:
            raise TypeError(
                "Input must be either a camera name (str) or an index (int)."
            )

        if self.streaming_processes[idx] is None:
            raise RuntimeError(
                f"Camera '{self.cameras[idx]._config.name}' is not streaming."
            )

        self.streaming_processes[idx].stop_event.set()
        self.streaming_processes[idx].join()
        self.streaming_processes[idx] = None

    def __del__(self):
        for process in self.streaming_processes:
            if process is not None:
                process.stop_event.set()
                process.join()
        self.cameras.clear()
        self.streaming_processes.clear()
