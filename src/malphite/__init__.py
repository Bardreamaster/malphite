import sharklog

from .camera import (
    Camera,
    CameraConfig,
    CameraConfigurationError,
    ManagedCamera,
    OpenCVCamera,
    OpenCVCameraConfig,
    SharedCamera,
    SharedCameraConfig,
)
from .data_server import SharedCameraServer
from .shared_memory import SharedMemory

sharklog.getLogger("malphite").addHandler(sharklog.NullHandler())

__all__ = [
    "Camera",
    "CameraConfig",
    "CameraConfigurationError",
    "ManagedCamera",
    "OpenCVCamera",
    "OpenCVCameraConfig",
    "SharedCamera",
    "SharedCameraConfig",
    "SharedCameraServer",
    "SharedMemory",
]
