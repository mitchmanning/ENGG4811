# Sensing the World
Welcome to Sensing the World!
This repository contains code and documentation relating to parking management and control through the use of a sensor network. The development and deployment environment was windows, and the relevant non-standard libraries, programs and guides are listed below.
The system runs in two modes - live and playback. To run the system in live mode, ensure the sensor network has all the code in 01_sensor_system loaded, and simply run sensor_system.py. By default this will record all data to a storage device for playback mode. Separately, ensure all the code in 02_visualiser is loaded on your local system, and simply run visualiser.py. This program takes in the X and Y characteristics of your parking environment, the height of the sensor system, and either an IPv4 address of the system for live mode, or the data file for playback mode.

## Non-Standard Libraries
1. pyserial
2. numpy
3. Jetson.GPIO
4. matplotlib
5. pillow
6. scipy
7. pandas
8. sklearn
9. kneed

## Programs and Installs
1. [Code Composer Studio](https://www.ti.com/tool/CCSTUDIO)
2. [mmWave Industrial Toolbox](https://dev.ti.com/tirex/explore/content/mmwave_industrial_toolbox_4_7_0/docs/readme.html)
3. [Uniflash](https://www.ti.com/tool/UNIFLASH)
4. [TI mmWave SDK](http://software-dl.ti.com/ra-processors/esd/MMWAVE-SDK/latest/index_FDS.html)
5. [SD Card Formatter](https://www.sdcard.org/downloads/formatter_4/eula_windows/)
6. [Etcher](https://www.balena.io/etcher)

## Setup Guides
1. [AWR1843 Setup Guide](https://dev.ti.com/tirex/explore/node?a=VLyFKFf__4.7.0&node=AFX52y3KwfxdmIN5Nkcfjg__VLyFKFf__4.7.0&r=VLyFKFf__LATEST)
2. [Jetson Nano Setup Guide](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit#intro)
3. [Logitech C920 Setup Guide](https://github.com/dusty-nv/jetson-inference/blob/master/docs/detectnet-example-2.md)
4. [TP-Link Setup Guide](https://www.tp-link.com/au/support/faq/1323/)

## Folder Structure
```
engg4811-s4532126
├── 01_proposal
│   ├── s4532126_proposal.docx
│   └── s4532126_proposal.pdf
├── 02_seminar
│   └── s4532126_seminar.pptx
├── 03_dev
│   ├── 01_sensor_system
|   |   ├── ti_awr1843
|   |   |   └── awr1843_flash.bin
|   |   ├── awr1843.py
|   |   ├── chirp_file.cfg
|   |   ├── jetson_gpio.py
|   |   ├── logitech_c920.py
|   |   ├── network_server.py
|   |   └── sensor_system.py
│   └── 02_visualiser
|       ├── outputs
|       |   ├── CaptureSummary_DEMO1.png
|       |   └── CaptureSummary_DEMO2.png
|       ├── raw_data
|       |   ├── DEMO1.pkl
|       |   └── DEMO2.pkl
|       ├── network_client.py
|       └── visualiser.py
├── 04_demo
│   ├── s4532126_demo.pptx
│   └── s4532126_poster.pptx
├── 05_thesis_paper
│   └── s4532126_thesis_paper.docx
├── .gitignore
└── README.md
```