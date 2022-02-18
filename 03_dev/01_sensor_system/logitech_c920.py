"""
================================================================================
 * @file 	logitech_c920.py
 * @author 	Mitch Manning - s4532126
 * @date 	04-07-2021
 * @brief 	Functions which initialise and handle object detection.
================================================================================
"""
# Standard
import sys
import pickle
# Non-Standard
import numpy as np              # 'numpy'
import jetson.inference as ji   # 'jetson.inference'
import jetson.utils as ju       # 'jetson.utils'


# Trained Model Info
TRAINED_MODEL   = 'ssd-mobilenet-v2'
THRESHOLD       = 0.5
# Camera Info
CAM_DEV         = '/dev/video0'
# Class IDs of Interest
VALID_ID        = [2, 3, 4, 6, 8]


def init_obj_detect():
    """
    @brief  Initialises the trained network and camera feed.
    @param  None
    @return The reference to the trained network and camera. 
    """
    net = ji.detectNet(network=TRAINED_MODEL, threshold=THRESHOLD)
    camera = ju.videoSource(CAM_DEV)
    return net, camera

def parse_capture(img, detections):
    """
    @brief  Parses and formats the detected objects.
    @param  img is the image captured from the video stream.
    @param  detections is the list of objects detected from the trained network.
    @return The parsed image packet.
    """
    img_pkt = {'img': img, 'img_data': ju.cudaToNumpy(img), 'objs': []}
    for det in detections:
        if det.ClassID in VALID_ID:
            obj = {'Area': det.Area,
                'Bottom': det.Bottom,
                'Center': det.Center,
                'ClassID': det.ClassID,
                'Confidence': det.Confidence,
                'Height': det.Height,
                'Instance': det.Instance,
                'Left': det.Left,
                'Right': det.Right,
                'Top': det.Top,
                'Width': det.Width}
            img_pkt['objs'].append(obj)
    return img_pkt

def img_request(net, camera):
    """
    @brief  Captures a frame from the video stream and applies the trained 
            network.
    @param  net is the reference to the trained network.
    @param  camera is the reference to the video stream.
    @return The parsed image packet.
    """
    img = camera.Capture()
    detections = net.Detect(img)
    img_pkt = parse_capture(img, detections)
    return img_pkt


if __name__ == '__main__':
    # Initialise the trained network and camera feed
    try:
        net, camera = init_obj_detect()
        display = ju.videoOutput()
    except:
        sys.exit('[LOGITECH C920] Camera is Unavailable.')

    try:
        while True:
            # Capture a frame and detect objects
            img_pkt = img_request(net, camera)
            display.Render(img_pkt['img'])

    except KeyboardInterrupt:
        sys.exit('[LOGITECH C920] Terminated.')