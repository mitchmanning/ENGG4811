"""
================================================================================
 * @file 	network_client.py
 * @author 	Mitch Manning - s4532126
 * @date 	08-08-2021
 * @brief 	Functionality for communicating as a client (GUI Side).
================================================================================
"""
# Standard
import os
import sys
import time
import socket as s
import pickle as p


# Client Characteristics
SPACING         = 16
PREAMBLE_SIZE   = 8
HEADER_SIZE     = PREAMBLE_SIZE + SPACING
PORT            = 4811
FORMAT          = 'utf-8'
PREAMBLE        = 'ENGG4811'
REQUEST_MSG     = 'DATA_REQ'.encode(FORMAT)


class Network_Client(object):
    """
    @brief  Handles all functionality relating to reading messages from the 
            server.
    @param  None
    @return None
    """
    def __init__(self, server_ip):
        """
        @brief  Initialises the class variables for the client.
        @param  self is the instance of the class.
        @param  server_ip is the IP Address of the host server.
        @return None
        """
        print('[CLIENT] Starting...')
        self.client = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.client.connect((server_ip, PORT))

    def data_received(self):
        """
        @brief  Read and interprets data from the server.
        @param  self is the instance of the class.
        @return The data or None if the server disconnected.
        """
        data = None
        # Read the packet header and check a full header was received
        header = self.client.recv(HEADER_SIZE).decode(FORMAT)
        if len(header) == HEADER_SIZE:
            
            # Set header parameters
            preamble = header[:PREAMBLE_SIZE]
            payload_len = int(header[PREAMBLE_SIZE:])
            
            # There was data in the queue on the server
            if preamble == PREAMBLE and payload_len:
                # Read correct amount of data
                payload = self.recv_payload(payload_len)
                
                if len(payload) == payload_len:
                    data = p.loads(payload)

        return data

    def recv_payload(self, payload_len):
        """
        @brief  Receives a full payload from the server.
        @param  self is the instance of the class.
        @param  payload_len is the number of bytes in the payload.
        @return The payload received.
        """
        payload = b''
        remaining_bytes = payload_len
        while remaining_bytes > 0:
            payload += self.client.recv(remaining_bytes)
            remaining_bytes = payload_len - len(payload)
        return payload

    def clean_up(self):
        """
        @brief  Cleans up the resources used by the client.
        @param  self is the instance of the class.
        @return None
        """
        self.client.close()


if __name__ == '__main__':

    try:
        server_ip = s.gethostbyname(s.gethostname())
        if sys.platform.startswith('linux'):
            dir_path = '/media/mitch/My Passport/data/'
        elif sys.platform.startswith('win'):
            dir_path = 'E:\\data\\'
        recording_num = len(os.listdir(dir_path))
        filename = f'data/Recording{recording_num}.pkl'

        if server_ip:
            client = Network_Client(server_ip)
        elif filename:
            data_file = open(filename, 'rb')
        else:
            sys.exit('[CLIENT] No IP Address or Filename given.')
        
        while True:
            time.sleep(1)
            if server_ip:
                data = client.data_received()
            elif filename:
                data = p.load(data_file)

            if data == None:
                raise KeyboardInterrupt

    except (KeyboardInterrupt, EOFError):
        if server_ip:
            client.clean_up()
        elif filename:
            data_file.close()
        sys.exit('[CLIENT] Closed.')