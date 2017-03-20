import os
import socket
import subprocess
from time import sleep
import numpy as np

"""
This file contains the classes used to interface with the FCEUX emulator.
"""


class FCEUXopener(object):
    """
    This class offers functionality to open an instance of
    the FCEUX emulator
    """
    def __init__(self, game_path, lua_path, load_state=None):
        self.game_path = game_path
        self.lua_path = lua_path
        self.load_state = load_state
        self.process = None
        self.stdout_file = open("stdout_emu.txt", "w")
        self.stderr_file = open("stderr_emu.txt", "w")

    def start(self):
        devnull = open(os.devnull, 'wb')  # use this in python < 3.3
        if self.load_state is not None:
            command = ["fceux", "--loadlua", self.lua_path, "--loadstate", str(self.load_state), self.game_path]
        else:
            command = ["fceux", "--loadlua", self.lua_path, self.game_path]
        self.process = subprocess.Popen(command, stdin=devnull, stdout=self.stdout_file, stderr=self.stderr_file)
        sleep(1)

    def stop(self):
        self.process.terminate()
        self.stdout_file.close()
        self.stderr_file.close()

    def __del__(self):
        self.stop()


class FCEUXconnector(object):
    def __init__(self, host, udp_port, tcp_port_screen, tcp_port_ram, color_mode='luminosity', screen_msg_len=245771,
                 pp_length=0, verbose=True, *args, **kwargs):
        self.pp_length = pp_length
        self.screen_msg_len = screen_msg_len
        self.ram_msg_len = 256
        self.width = 256
        self.n_channels = 4
        self.height = self.screen_msg_len / (self.n_channels * self.width)
        self.color_mode = color_mode
        if color_mode in ["luminosity", "average"]:
            self.output_shape = (self.height, self.width)
        elif color_mode in ["rgb_array"]:
            self.output_shape = (self.height, self.width, 3)
        elif color_mode in ["argb_array"]:
            self.output_shape = (self.height, self.width, 4)
        self.initial_observation = None
        # Initialize IPC
        self.verbose = verbose
        self.host = host
        self.udp_port = udp_port
        self.tcp_port_screen = tcp_port_screen
        self.tcp_port_ram = tcp_port_ram
        self.udp_socket = None
        self.tcp_socket_screen = None
        self.tcp_socket_ram = None
        self._initialize_ipc()

    # IPC functions
    def _initialize_ipc(self):
        """
            Initialize connections for Interprocess/Network communication
        """
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket_screen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket_ram = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket_screen.setblocking(1)
        self.tcp_socket_ram.setblocking(1)
        self.tcp_socket_screen.settimeout(2)
        self.tcp_socket_ram.settimeout(2)
        if self.verbose:
            print("Host: " + str(self.host))
            print("UDP Port: " + str(self.udp_port))
            print("Screen TCP Port: " + str(self.tcp_port_screen))
            print("RAM TCP Port: " + str(self.tcp_port_ram))
        # Establish TCP connections
        self.tcp_socket_screen.connect((self.host, self.tcp_port_screen))
        if self.verbose:
            print("Connected screen.")
        self.tcp_socket_ram.connect((self.host, self.tcp_port_ram))
        if self.verbose:
            print("Connected ram.")

    def _collect_package(self, tcp_socket, msg_len, buffer_size=4096):
        """
            This collects chunks of data belonging to a TCP response
            and puts them together
        """
        package = ""
        while len(package) < msg_len + 2 * self.pp_length:
            chunk = tcp_socket.recv(buffer_size)
            package += chunk
        return package

    def receive_screen_response(self):
        """
            Collect response after dispatching a command via UDP
        """
        response = self._collect_package(self.tcp_socket_screen, self.screen_msg_len)
        if len(response) != self.screen_msg_len + 2 * self.pp_length:
            if self.verbose:
                print("Skipped, len is "+str(len(response)))
            return None
        if self.pp_length > 0:
            response = response[self.pp_length + 11:-self.pp_length]
        else:
            response = response[11:]
        return self._response2np(response)

    def receive_ram_response(self):
        """
            Collect RAM reponse
        """
        response = self._collect_package(self.tcp_socket_ram, self.ram_msg_len, 128)
        return response

    def _response2np(self, response):
        """
            Translate raw response string into a numpy array in correspondence
            to the given color_mode
        """
        tmp = np.array(map(ord, response), dtype=np.uint8).reshape((self.height, self.width, self.n_channels))
        if self.color_mode == "luminosity":
            tmp = np.average(tmp[:, :, 1:], axis=2, weights=[0.21, 0.72, 0.07]).astype(np.uint8)
        elif self.color_mode == "average":
            tmp = tmp[:, :, 1:].mean(axis=2).astype(np.uint8)
        elif self.color_mode == "lightness":
            pass
        elif self.color_mode == "rgb_array":
            tmp = tmp[:, :, 1:]
        elif self.color_mode == "argb_array":
            pass
        return tmp

    def send_msg(self, msg):
        """
            Send a msg via UDP to established host
        """
        self.udp_socket.sendto(msg, (self.host, self.udp_port))

    def send_fin(self):
        self.send_msg("F")

    def load_state(self, slot=1):
        self.send_msg("cL"+str(slot))
        self.send_msg("cV0")
        self.advance_frame()
        self.initial_observation = self.get_screen()
        return self.initial_observation

    def get_ram(self, block_id):
        block_id %= 8
        self.send_msg("cM"+str(block_id))
        ram_page = self.receive_ram_response()
        #self.send_fin()
        return ram_page

    def get_screen(self):
        msg = "cV0"
        self.send_msg(msg)
        screen_response = self.receive_screen_response()
        #self.send_fin()
        return screen_response

    def advance_frame(self, n_frames=1):
        msg = "cA"+str(n_frames)
        self.send_msg(msg)
