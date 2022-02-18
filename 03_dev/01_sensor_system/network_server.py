"""
================================================================================
 * @file 	network_server.py
 * @author 	Mitch Manning - s4532126
 * @date 	08-08-2021
 * @brief 	Functionality for communicating as a server (Jetson Nano Side).
================================================================================
"""
# Standard
import os
import sys
import time
import queue as q
import socket as s
import pickle as p
import threading as t
import subprocess as sp
from datetime import datetime


# Server Characteristics
PORT            = 4811
SPACING         = 16
FORMAT          = 'utf-8'
PREAMBLE        = 'ENGG4811'


class Network_Server(object):
    """
    @brief  Handles all functionality relating to managing the server.
    @param  None
    @return None
    """
    def __init__(self):
        """
        @brief  Initialises the class variables for the server.
        @param  self is the instance of the class.
        @return None
        """
        print('[SERVER] Starting...')
        # Initialise the server
        self.server_ip = self.get_host_ip()
        self.server = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.server.bind((self.server_ip, PORT))
        print(f'[SERVER] IP Address: {self.server_ip}')

        # Client connection status
        self.connection = False

        # Create a data queue
        self.queue = q.Queue(maxsize=1)

        # Initialise the thread
        self.thread = t.Thread(target=self.server_func)
        self.thread.daemon = True
        self.thread.start()

    def server_func(self):
        """
        @brief  Server functionality listens for connections and handles 
                messages with 1 client (or visualiser).
        @param  self is the instance of the class.
        @return None
        """
        # Listens for 1 connection
        self.server.listen(1)
        print('[SERVER] Listening...')
        
        while True:
            # Accept new clients when not currently connected to one
            self.conn, addr = self.server.accept()
            self.connection = True
            print(f'[SERVER] New Connection: {addr}')

            # Handle messages with client
            while self.connection:
                # Handle client disconnecting
                try:
                    data = self.queue.get()
                    header, payload = self.make_pkt(data)
                    self.send_pkt(header, payload)

                except (ConnectionResetError, ConnectionAbortedError, 
                        BrokenPipeError):
                    self.conn.close()
                    self.connection = False
                    print(f'[SERVER] Close Connection: {addr}')

    def send_pkt(self, header, payload):
        """
        @brief  Sends all the data in a packet.
        @param  self is the instance of the class.
        @param  header is the encoded header string to be sent.
        @param  payload is the data from the sensors.
        @return None
        """
        self.conn.sendall(header)
        pos = 0
        while pos < len(payload):
            bytes_sent = self.conn.send(payload[pos:])
            pos += bytes_sent

    def make_pkt(self, data):
        """
        @brief  Constructs the packet for transmission.
        @param  self is the instance of the class.
        @param  data is the data to transmit.
        @return The packet ready for transmission.
        """
        payload     = p.dumps(data)
        payload_len = f'{len(payload):>{SPACING}}'
        header      = str(PREAMBLE + payload_len).encode(FORMAT)

        return header, payload

    def clean_up(self):
        """
        @brief  Cleans up the resources used by the server thread.
        @param  self is the instance of the class.
        @return None.
        """
        if self.connection:
            self.conn.close()

    def get_host_ip(self):
        """
        @brief  Obtains the IPv4 Address of the server.
        @param  self is the instance of the class.
        @return The IPv4 Address of the server.
        """
        if sys.platform.startswith('linux'):
            # Command: ifconfig eth0
            ifconfig = sp.Popen(['ifconfig', 'eth0'], stdin=sp.PIPE, \
                stdout=sp.PIPE, stderr=sp.STDOUT)
            ip_addr = ifconfig.communicate()[0].decode('ascii').rsplit()[5]
        else:
            ip_addr = s.gethostbyname(s.gethostname())
        return ip_addr
    
def init_save_file():
    """
    @brief  Initialises the file for saving data packets.
    @param  None
    @return The file object for saving data.
    """
    try:
        if sys.platform.startswith('linux'):
            dir_path = '/media/mitch/My Passport/data/'
        elif sys.platform.startswith('win'):
            dir_path = 'E:\\data\\'
        recording_num = len(os.listdir(dir_path)) + 1
        data_file = open(f'{dir_path}Recording{recording_num}.pkl', 'wb')
        return data_file

    except FileNotFoundError:
        sys.exit('[JETSON] Data storage device not connected.')


if __name__ == '__main__':

    try:
        data_file = init_save_file()
        server = Network_Server()

        while True:
            data = {'Time': datetime.now()}
            if server.connection:
                server.queue.put(data)
            p.dump(data, data_file)
            time.sleep(1)
        
    except KeyboardInterrupt:
        server.clean_up()
        data_file.close()
        sys.exit('[SERVER] Closed.')