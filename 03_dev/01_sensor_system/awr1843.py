"""
================================================================================
 * @file 	awr1843.py
 * @author 	Mitch Manning - s4532126
 * @date 	22-06-2021
 * @brief 	Functions which handle communication with the AWR1843 and parsing
 *          it's data.
================================================================================
"""
# Standard
from datetime import datetime
import time
import sys
# Non-Standard
import numpy as np  # 'numpy'
import serial as s  # 'pyserial'
from serial.tools import list_ports
# Custom
from jetson_gpio import * 


# Device Specific
MAGIC_WORD                  = '0102030405060708'
SDK_VERSION                 = '03050004'
DEV_PLATFORM                = '000A6843'
OUTPUT_MSG_SEGMENT_LEN      = 32
# TLV Type Indicators
DPIF_POINT_CLOUD_SPHERICAL  = 6
TARGET_LIST_3D              = 7
TARGET_INDEX                = 8
DPIF_POINT_CLOUD_SIDE_INFO  = 9
# Size of TLV Packets
SIZE_PKT_HEADER             = 52
SIZE_TLV_HEADER             = 8
SIZE_PC_SPHERICAL           = 16
SIZE_TARGET_LIST            = 112
SIZE_TARGET_INDEX           = 1
SIZE_PC_SIDE_INFO           = 4
# IDs Associated with Error
ID_NOT_ASSOCIATED           = [253, 254, 255]
# Baud Rates
DATA_BAUD                   = 921600
CLI_BAUD                    = 115200
# Chirp File Name
CHIRP_CONF                  = 'chirp_file.cfg'
# Transformation Matrices
WORD_16                     = [2**0, 2**8]
WORD_32                     = [2**0, 2**8, 2**16, 2**24]


def init_ports():
    """
    @brief  Opens the CLI and Data port connection with the AWR1843 device.
    @param  None
    @return The port references (empty if uninitialised).
    """
    cli_port = {}
    data_port = {}
    com_ports = list(list_ports.comports())
    
    # Linux Support
    if sys.platform.startswith('linux'):
        for port in com_ports:
            dev = port[0]
            name = port[1]
            if 'XDS110' in name and '/dev/ttyACM1' in port:
                data_port = s.Serial('/dev/ttyACM1', DATA_BAUD)
            elif 'XDS110' in name and '/dev/ttyACM0' in port:
                cli_port = s.Serial('/dev/ttyACM0', CLI_BAUD)

    # Windows Support
    elif sys.platform.startswith('win'):
        for port in com_ports:
            dev = port[0]
            name = port[1]
            if 'XDS110 Class Auxiliary Data Port' in name:
                data_port = s.Serial(dev, DATA_BAUD)
            elif 'XDS110 Class Application/User UART' in name:
                cli_port = s.Serial(dev, CLI_BAUD)

    time.sleep(0.1)
    return cli_port, data_port

def init_config(chirp_filename, cli_port):
    """
    @brief  Transmits the chirp configuration file to setup the AWR1843.
    @param  chirp_filename is the name of the chirp configuration file.
    @param  cli_port is the CLI port reference.
    @return None
    """
    config_params = [line.rstrip('\r\n') for line in open(chirp_filename)]
    for param in config_params:
        cli_port.write((param+'\n').encode())
        time.sleep(0.01)
    time.sleep(0.1)

def terminate(error_msg, cli_port, data_port):
    """
    @brief  Safely close COM Ports, deinits GPIO pins and terminates sensor 
            operation.
    @param  error_msg is the message printed to terminal.
    @param  cli_port is the CLI port reference.
    @param  data_port is the data port reference.
    @return None
    """
    if cli_port:
        cli_port.write(('sensorStop\n').encode())
        cli_port.close()
    if data_port:
        data_port.close()
    deinit_gpio()
    sys.exit(error_msg)

def restart(cli_port, data_port):
    """
    @brief  Restarts and re-initialises the AWR1843 device.
    @param  cli_port is the CLI port reference.
    @param  data_port is the data port reference.
    @return The port references.
    """
    # Close connections
    if cli_port:
        cli_port.close()
    if data_port:
        data_port.close()
    
    # Restart AWR1843
    toggle_gpio()

    # Re-initialise the device
    cli_port, data_port = init_ports()
    if not cli_port or not data_port:
        terminate("[AWR1843] COM Ports are Unavailable.", cli_port, data_port)
    init_config(CHIRP_CONF, cli_port)
    return cli_port, data_port

def data_request(cli_port, data_port):
    """
    @brief  Requests and receives a new data packet from the AWR1843.
    @param  cli_port is the CLI port reference.
    @param  data_port is the data port reference.
    @return The data buffer.
    """
    # Request new data packet
    cli_port.write(('dataRequest\n').encode())
    time.sleep(0.25)
    # Read response
    data_buf = data_port.read(data_port.in_waiting)
    return data_buf

def parse_header(data_arr, pos):
    """
    @brief  Parses the packet header.
    @param  data_arr contains the data from the AWR1843.
    @param  pos is the position in the current parsing position in data_arr.
    @return The formatted packet header and a new buffer pointer position.
    """
    # Parse through the header info
    magic_num   = ''
    for i in range(4):
        magic_num       += format(np.matmul(data_arr[pos:pos+2], WORD_16), \
                        '04X'); pos+=2
    version             = format(np.matmul(data_arr[pos:pos+4], WORD_32), \
                        '08X'); pos+=4
    platform            = format(np.matmul(data_arr[pos:pos+4], WORD_32), \
                        '08X'); pos+=4
    time_stamp          = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4
    total_pkt_len       = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4
    frame_num           = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4
    subframe_num        = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4
    chirp_proc_margin   = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4
    frame_proc_margin   = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4
    track_proc_time     = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4
    uart_send_time      = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4
    num_tlv             = np.matmul(data_arr[pos:pos+2], WORD_16); pos+=2
    checksum            = np.matmul(data_arr[pos:pos+2], WORD_16); pos+=2

    # Store the data in a dictionary
    header = {'magic_num': magic_num,
        'version': version, 
        'platform': platform, 
        'time_stamp': time_stamp, 
        'total_pkt_len': total_pkt_len, 
        'frame_num': frame_num, 
        'subframe_num': subframe_num, 
        'chirp_proc_margin': chirp_proc_margin, 
        'frame_proc_margin': frame_proc_margin, 
        'track_proc_time': track_proc_time, 
        'uart_send_time': uart_send_time, 
        'num_tlv': num_tlv,
        'checksum': checksum
    }

    return header, pos

def check_header(header, data_buf):
    """
    @brief  Verifies the device specific variables and checksum.
    @param  header is the parsed packet header data.
    @param  data_buf is the original data buffer from the AWR1843.
    @return True if valid, false otherwise.
    """
    # Calculate Header Checksum
    cs_arr = np.frombuffer(data_buf, dtype='uint16')[:(SIZE_PKT_HEADER//2)]
    cs_sum = np.uint32(0)
    for val in cs_arr:
        cs_sum += val
    cs_sum = (cs_sum >> 16) + (cs_sum & 0xFFFF)
    cs_sum += (cs_sum >> 16)
    calc_cs = np.uint16(~cs_sum)

    # Determine Validity
    if header['magic_num'] != MAGIC_WORD or \
            header['version'] != SDK_VERSION or \
            header['platform'] != DEV_PLATFORM or \
            header['total_pkt_len'] != len(data_buf) or \
            calc_cs != 0:
        return False
    else:
        return True

def parse_pc_sph_data(data_arr, tlv_len, pos):
    """
    @brief  Parses the Point Cloud Sphereical data and formats the info.
    @param  data_arr contains the data from the AWR1843.
    @param  tlv_len is the length specified  in the TLV header.
    @param  pos is the position in the current parsing position in data_arr.
    @return The formatted data and a new buffer pointer position.
    """
    num_objs    = tlv_len // SIZE_PC_SPHERICAL
    # Initialise arrays for data
    ranges      = np.zeros(num_objs, dtype=np.float32)
    azimuth     = np.zeros(num_objs, dtype=np.float32)
    elevation   = np.zeros(num_objs, dtype=np.float32)
    doppler     = np.zeros(num_objs, dtype=np.float32)
    # Parse and store data
    for obj in range(num_objs):
        ranges[obj]     = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        azimuth[obj]    = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        elevation[obj]  = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        doppler[obj]    = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4

    # Store the data in a dictionary
    pc_sph_data = {'num_objs': num_objs, 
        'ranges': ranges, 
        'azimuth': azimuth, 
        'elevation': elevation, 
        'doppler': doppler
    }

    return pc_sph_data, pos

def parse_target_data(data_arr, tlv_len, pos):
    """
    @brief  Parses the Target data and formats the info.
    @param  data_arr contains the data from the AWR1843.
    @param  tlv_len is the length specified  in the TLV header.
    @param  pos is the position in the current parsing position in data_arr.
    @return The formatted data and a new buffer pointer position.
    """
    num_objs    = tlv_len // SIZE_TARGET_LIST
    # Initialise arrays for data
    tid         = np.zeros(num_objs, dtype=np.uint32)
    posX        = np.zeros(num_objs, dtype=np.float32)
    posY        = np.zeros(num_objs, dtype=np.float32)
    posZ        = np.zeros(num_objs, dtype=np.float32)
    velX        = np.zeros(num_objs, dtype=np.float32)
    velY        = np.zeros(num_objs, dtype=np.float32)
    velZ        = np.zeros(num_objs, dtype=np.float32)
    accX        = np.zeros(num_objs, dtype=np.float32)
    accY        = np.zeros(num_objs, dtype=np.float32)
    accZ        = np.zeros(num_objs, dtype=np.float32)
    ec          = np.zeros((num_objs, 16), dtype=np.float32)
    g           = np.zeros(num_objs, dtype=np.float32)
    conf_lvl    = np.zeros(num_objs, dtype=np.float32)
    # Parse and store data
    for obj in range(num_objs):
        tid[obj]        = data_arr[pos:pos+4].view(dtype=np.uint32); pos+=4
        posX[obj]       = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        posY[obj]       = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        posZ[obj]       = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        velX[obj]       = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        velY[obj]       = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        velZ[obj]       = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        accX[obj]       = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        accY[obj]       = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        accZ[obj]       = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        for i in range(len(ec[0])):
            ec[obj][i]  = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        g[obj]          = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4
        conf_lvl[obj]   = data_arr[pos:pos+4].view(dtype=np.float32); pos+=4

    # Store the data in a dictionary
    target_data = {'num_objs': num_objs, 
        'tid': tid, 
        'posX': posX, 
        'posY': posY, 
        'posZ': posZ,
        'velX': velX, 
        'velY': velY, 
        'velZ': velZ, 
        'accX': accX, 
        'accY': accY, 
        'accZ': accZ,
        'ec': ec, 
        'g': g, 
        'conf_lvl': conf_lvl
    }

    return target_data, pos

def parse_tgt_id_data(data_arr, tlv_len, pos):
    """
    @brief  Parses the Target Index data and formats the info.
    @param  data_arr contains the data from the AWR1843.
    @param  tlv_len is the length specified  in the TLV header.
    @param  pos is the position in the current parsing position in data_arr.
    @return The formatted data and a new buffer pointer position.
    """
    num_objs    = tlv_len // SIZE_TARGET_INDEX
    # Initialise arrays for data
    target_id   = np.zeros(num_objs, dtype=np.uint8)
    # Parse and store data
    for obj in range(num_objs):
        target_id[obj] = data_arr[pos:pos+1].view(dtype=np.uint8); pos+=1

    # Store the data in a dictionary
    tgt_id_data = {'num_objs': num_objs, 
        'target_id': target_id
    }

    return tgt_id_data, pos

def parse_pc_sid_data(data_arr, tlv_len, pos):
    """
    @brief  Parses the Point Cloud Side Info data and formats the info.
    @param  data_arr contains the data from the AWR1843.
    @param  tlv_len is the length specified  in the TLV header.
    @param  pos is the position in the current parsing position in data_arr.
    @return The formatted data and a new buffer pointer position.
    """
    num_objs    = tlv_len // SIZE_PC_SIDE_INFO
    # Initialise arrays for data
    snr         = np.zeros(num_objs, dtype=np.int16)
    noise       = np.zeros(num_objs, dtype=np.int16)
    # Parse and store data
    for obj in range(num_objs):
        snr[obj]    = data_arr[pos:pos+2].view(dtype=np.int16); pos+=2
        noise[obj]  = data_arr[pos:pos+2].view(dtype=np.int16); pos+=2

    # Store the data in a dictionary
    pc_sid_data = {'num_objs': num_objs, 
        'snr': snr, 
        'noise': noise
    }

    return pc_sid_data, pos

def parse_pkt(data_buf):
    """
    @brief  Parse data packet into a formatted dictionary.
    @param  data_buf is the original data buffer from the AWR1843.
    @return The parsed data.
    """
    # Initialise Variables
    pos         = 0
    pc_sph_data = {}
    target_data = {}
    tgt_id_data = {}
    pc_sid_data = {}
    data_arr    = np.frombuffer(data_buf, dtype='uint8')

    # Parse Header Information
    header, pos = parse_header(data_arr, pos)
    valid_header = check_header(header, data_buf)
    if not valid_header:
        return {}

    # Parse Packet Contents
    for tlv_id in range(header['num_tlv']):
        tlv_type    = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4
        tlv_len     = np.matmul(data_arr[pos:pos+4], WORD_32); pos+=4

        if tlv_type == DPIF_POINT_CLOUD_SPHERICAL:
            pc_sph_data, pos = parse_pc_sph_data(data_arr, tlv_len, pos)
        elif tlv_type == TARGET_LIST_3D:
            target_data, pos = parse_target_data(data_arr, tlv_len, pos)
        elif tlv_type == TARGET_INDEX:
            tgt_id_data, pos = parse_tgt_id_data(data_arr, tlv_len, pos)
        elif tlv_type == DPIF_POINT_CLOUD_SIDE_INFO:
            pc_sid_data, pos = parse_pc_sid_data(data_arr, tlv_len, pos)
        else:
            break

    # Verify all data was parsed - consider padding bytes
    pos += OUTPUT_MSG_SEGMENT_LEN - (pos & (OUTPUT_MSG_SEGMENT_LEN-1))
    if (pos != header['total_pkt_len']):
        return {}

    # Time stamp data and finalise packet format
    current_time = datetime.now()
    data_pkt = {'time': current_time, 
        'header': header, 
        'pc_sph_data': pc_sph_data, 
        'target_data': target_data, 
        'tgt_id_data': tgt_id_data, 
        'pc_sid_data': pc_sid_data
    }

    return data_pkt


if __name__ == '__main__':
    # Initialise the Jetson GPIO pins and restart the AWR1843
    init_gpio()
    toggle_gpio()

    # Initalise the CLI and Data ports with the AWR1843
    cli_port, data_port = init_ports()
    if not cli_port or not data_port:
        terminate("[AWR1843] COM Ports are Unavailable.", cli_port, data_port)

    # Transmit the chirp configuration file
    init_config(CHIRP_CONF, cli_port)

    try:
        # Main Program Loop
        while True:
            # Request new data packet
            data_buf = data_request(cli_port, data_port)
            if len(data_buf) == 0:
                cli_port, data_port = restart(cli_port, data_port)
                continue
            
            # Parse data packet
            data_pkt = parse_pkt(data_buf)
            if not data_pkt:
                continue

    except KeyboardInterrupt:
        terminate('[AWR1843] Terminate Program.', cli_port, data_port)