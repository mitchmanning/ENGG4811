"""
================================================================================
 * @file 	sensor_system.py
 * @author 	Mitch Manning - s4532126
 * @date 	03-07-2021
 * @brief 	Main loop which handles sesnor communication, calculations and
            result transmission.
================================================================================
"""
# Custom
from awr1843 import *
from logitech_c920 import *
from network_server import *


def get_net_pkt(data_pkt, img_pkt):
    """
    @brief  Retrieves necessary information from the data and image packets.
    @param  data_pkt is the data received from the AWR1843.
    @param  img_pkt is the iimage received from the Logitech C920.
    @return The necessary information stored in a dictionary.
    """
    net_pkt = {'time': data_pkt['time'],
        'img_objs': len(img_pkt['objs']),
       'img_data': img_pkt['img_data']}
    
    if data_pkt['pc_sph_data']:
        net_pkt['pc_sph_data'] = {'ranges': data_pkt['pc_sph_data']['ranges'], 
            'azimuth': data_pkt['pc_sph_data']['azimuth'], 
            'elevation': data_pkt['pc_sph_data']['elevation']}

    return net_pkt


if __name__ == '__main__':
   
    # Initialise the Jetson GPIO pins and restart the AWR1843
    init_gpio()
    toggle_gpio()

    # Initialise the trained network and camera feed
    try:
        net, camera = init_obj_detect()
    except:
        terminate("[LOGITECH C920] Camera is Unavailable.", None, None)

    # Initalise the CLI and Data ports with the AWR1843
    cli_port, data_port = init_ports()
    if not cli_port or not data_port:
        terminate("[AWR1843] COM Ports are Unavailable.", cli_port, data_port)

    # Transmit the chirp configuration file
    init_config(CHIRP_CONF, cli_port)

    # Initialise data save file and server
    # data_file = init_save_file()
    server = Network_Server()

    try:
        # Main Program Loop
        while True:
            # Capture a frame and detect objects
            img_pkt = img_request(net, camera)
            
            # Request new data packet
            data_buf = data_request(cli_port, data_port)
            if len(data_buf) == 0:
                cli_port, data_port = restart(cli_port, data_port)
                continue
            
            # Parse data packet
            data_pkt = parse_pkt(data_buf)
            if not data_pkt:
                continue

            # Transmit and save data
            net_pkt = get_net_pkt(data_pkt, img_pkt)
            if server.connection:
                server.queue.put(net_pkt)
                time.sleep(0.5)
            # p.dump(net_pkt, data_file)

    except KeyboardInterrupt:
        server.clean_up()
        # data_file.close()
        print("[SERVER] Closed.")
        terminate("[JETSON NANO] Terminate Program.", cli_port, data_port)