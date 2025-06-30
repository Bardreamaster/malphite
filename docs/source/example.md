# Example

## Server Example

Start a {class}`SharedCameraServer <malphite.data_server.SharedCameraServer>` to read frames from the real camera and write into shared memory in one terminal:

```python
import time

from malphite import OpenCVCameraConfig, SharedCameraServer

# Create server and configure camera
camera_server = SharedCameraServer()
camera_config = OpenCVCameraConfig(name="webcam", camera_path="/dev/video0", width=1280, height=480,)

# Add camera and get shared memory configuration
shared_config = camera_server.append_camera(camera_config)

# Start streaming
camera_server.activate_camera_streaming("webcam")

# Keep the server process running
while True:
    # do_something()
    time.sleep(1)
```

For detailed API documentation, see the {doc}`apidocs/index`.

## Client Example

Using a {class}`SharedCamera <malphite.camera.SharedCamera>` to read frames in another process:

```python
import cv2

from malphite import SharedCamera, SharedCameraConfig

# Create a SharedCameraConfig
# name, width, height should be the same as the config in server.
# Currently, you have to get these info manually.
# An api to get these info from server will be added later.
config = SharedCameraConfig(
    name="webcam",
    width=1280,
    height=480,
)
cam = SharedCamera(config)

while True:
    frame = cam.read_once()
    if frame is None:
        print("No frame received.")
        break

    cv2.imshow("Webcam", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
```
