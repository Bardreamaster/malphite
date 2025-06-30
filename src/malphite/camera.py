from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import cv2
import numpy as np

from .shared_memory import SharedMemory


class CameraConfigurationError(Exception):
    """Raised when camera configuration parameters cannot be set."""

    pass


class Camera(ABC):

    def __init__(self, camera_config: CameraConfig):
        """Initialize the camera with the given configuration.

        Args:
            camera_config (CameraConfig): The configuration for the camera.
        """
        self._config = camera_config
        self.name = self._config.name
        self.width = self._config.width
        self.height = self._config.height
        self.fps = self._config.fps

    @abstractmethod
    def read_once(self) -> np.ndarray:
        """Reads a single frame from the camera.

        Returns:
            np.ndarray: The captured frame.
        """
        ...


@dataclass
class CameraConfig(ABC):
    """Base configuration class for cameras."""

    name: str | None = None
    """The name of the camera. """

    width: int | None = None
    """The width of the camera image in pixels."""

    height: int | None = None
    """The height of the camera image in pixels."""

    fps: float | None = None
    """The frames per second (FPS) of the camera."""

    type: str | None = None

    target_class: type = Camera
    """The target class to instantiate with. This should be a subclass of `Camera`."""


class OpenCVCamera(Camera):
    """
    A camera class that uses OpenCV to capture images.
    """

    def __init__(self, camera_config: OpenCVCameraConfig):
        super().__init__(camera_config)
        self.camera_path = camera_config.camera_path
        self.capture = cv2.VideoCapture(self.camera_path)
        if self.fps is not None:
            self.capture.set(cv2.CAP_PROP_FPS, self.fps)
        if self.width is not None:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height is not None:
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        actual_fps = self.capture.get(cv2.CAP_PROP_FPS)
        actual_width = self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)

        if self.fps is not None and not math.isclose(
            self.fps, actual_fps, rel_tol=1e-3
        ):
            raise CameraConfigurationError(
                f"Can't set {self.fps=} for OpenCVCamera({self.camera_path}). Actual value is {actual_fps}."
            )
        if self.width is not None and not math.isclose(
            self.width, actual_width, rel_tol=1e-3
        ):
            raise CameraConfigurationError(
                f"Can't set {self.width=} for OpenCVCamera({self.camera_path}). Actual value is {actual_width}."
            )
        if self.height is not None and not math.isclose(
            self.height, actual_height, rel_tol=1e-3
        ):
            raise CameraConfigurationError(
                f"Can't set {self.height=} for OpenCVCamera({self.camera_path}). Actual value is {actual_height}."
            )

        self.fps = round(actual_fps)
        self.width = round(actual_width)
        self.height = round(actual_height)
        self._config.width = self.width
        self._config.height = self.height
        self._config.fps = self.fps

    def read_once(self) -> np.ndarray:
        """
        Reads a single frame from the camera.
        """
        if not self.capture.isOpened():
            raise RuntimeError("Camera is not opened.")

        ret, frame = self.capture.read()
        if not ret:
            raise RuntimeError("Failed to read frame from camera.")

        return np.array(frame)


@dataclass
class OpenCVCameraConfig(CameraConfig):
    """Configuration for an OpenCV camera."""

    camera_path: str = None
    """The path to the camera device, e.g., '/dev/video0'."""

    type: str = "opencv"

    target_class: type = OpenCVCamera


class SharedCamera(Camera):
    """
    A camera class that uses shared memory to capture images.
    """

    def __init__(self, camera_config: SharedCameraConfig):
        super().__init__(camera_config)
        self.shared_memory_name = camera_config.shared_memory_name
        self.shared_memory_size = camera_config.shared_memory_size
        if not self.shared_memory_name or not self.shared_memory_size:
            raise ValueError("Shared memory name and size must be provided.")
        self.shared_memory = SharedMemory(
            name=self.shared_memory_name, size=self.shared_memory_size, track=False
        )
        self.image_frame = np.ndarray(
            (camera_config.height, camera_config.width, 3),
            dtype=np.uint8,
            buffer=self.shared_memory.buf,
        )

    def read_once(self) -> np.ndarray:
        """
        Reads a single frame from the shared memory.
        """
        return np.copy(self.image_frame)


@dataclass
class SharedCameraConfig(CameraConfig):
    type: str = "shared"
    target_class: type = SharedCamera

    shared_memory_name: str | None = None
    """The name of the shared memory segment.
    """
    shared_memory_size: int | None = None
    """The size of the shared memory segment in bytes.

    For example, if the camera resolution is width x height and the image is in 8-bit RGB format, the size can be calculated as:

    ```python
    shared_memory_size = int(width * height * 3  * np.uint8().itemsize)
    ```
    """

    def __post_init__(self):
        # TODO: parse the name to fit the shared memory naming conventions
        self.shared_memory_name = (
            self.name if self.shared_memory_name is None else self.shared_memory_name
        )
        if not self.shared_memory_size:
            if self.width is None or self.height is None:
                raise ValueError(
                    "Width and height must be provided for `SharedCameraConfig`."
                )
            self.shared_memory_size = int(
                self.width * self.height * 3 * np.uint8().itemsize
            )


class ManagedCamera(Camera):
    _instance: Camera = None

    def __init__(self, camera_config: CameraConfig, shared_memory_name: str = None):
        super().__init__(camera_config)

        self._config = camera_config
        self._instance = self._config.target_class(self._config)

        self._config.width = self._instance.width
        self._config.height = self._instance.height
        self._config.fps = self._instance.fps

        self.shared_memory_name = getattr(self._instance, "shared_memory_name", None)
        if self.shared_memory_name is None:
            if shared_memory_name:
                self.shared_memory_name = shared_memory_name
            else:
                self.shared_memory_name = self._config.name
        self.shared_memory_size = getattr(
            self._instance,
            "shared_memory_size",
            int(self._config.width * self._config.height * 3 * np.uint8().itemsize),
        )

    def read_once(self) -> np.ndarray:
        """
        Reads a single frame from the camera.
        """
        return self._instance.read_once()

    def export_shared_camera_config(self) -> SharedCameraConfig:
        """
        Exports the camera configuration as a `SharedCameraConfig`.
        """
        return SharedCameraConfig(
            name=self._config.name,
            width=self._config.width,
            height=self._config.height,
            fps=self._config.fps,
            shared_memory_name=self.shared_memory_name,
            shared_memory_size=self.shared_memory_size,
        )
