"""Test utilities and mock objects for testing the malphite library."""

from dataclasses import dataclass

import numpy as np

from malphite.camera import Camera, CameraConfig


class MockCamera(Camera):
    """A mock camera implementation for testing purposes."""

    def __init__(self, camera_config: "MockCameraConfig"):
        super().__init__(camera_config)
        self._frame_counter = 0
        self.is_opened = True

    def read_once(self) -> np.ndarray:
        """Return a mock frame with incrementing values."""
        if not self.is_opened:
            raise RuntimeError("Camera is not opened")

        # Create a test frame with incrementing counter
        frame = np.full(
            (self.height, self.width, 3), self._frame_counter % 256, dtype=np.uint8
        )
        self._frame_counter += 1
        return frame

    def close(self):
        """Close the mock camera."""
        self.is_opened = False


@dataclass
class MockCameraConfig(CameraConfig):
    """Configuration for a mock camera."""

    type: str = "mock"
    target_class: type = MockCamera

    def __post_init__(self):
        # Set default values if not provided
        if self.width is None:
            self.width = 640
        if self.height is None:
            self.height = 480
        if self.fps is None:
            self.fps = 30.0


class FailingMockCamera(MockCamera):
    """A mock camera that fails on read_once for testing error scenarios."""

    def read_once(self) -> np.ndarray:
        raise RuntimeError("Simulated camera failure")


@dataclass
class FailingMockCameraConfig(CameraConfig):
    """Configuration for a failing mock camera."""

    type: str = "failing_mock"
    target_class: type = FailingMockCamera

    def __post_init__(self):
        if self.width is None:
            self.width = 640
        if self.height is None:
            self.height = 480
        if self.fps is None:
            self.fps = 30.0
