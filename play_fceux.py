import os

from PIL import Image
from pynput import keyboard

import fceux_gym.pyfceux as pyfceux

"""
just a script for testing the pyfceux connections with keyboard input
"""

KIRBY_PATH = os.path.abspath("/home/m/Personal/NES Games/Kirby.nes")
MM2_PATH = os.path.abspath("/home/m/Personal/NES Games/MM2.nes")
LUA_CON_PATH = os.path.abspath("/home/m/Personal/NES Games/lua_/connector_screen_v2.lua")

def trans(X):
    p = ''
    for x in X:
        p += " "+hex(ord(x)).replace("0x","").zfill(2)
    return p.replace("0x","")


def print_last(ram_list, off):
    print(" ")
    for i in range(len(ram_list)):
        print(trans(ram_list[i])[-off:])

def print_all(ram_list):
    print(" ")
    for i in range(len(ram_list)):
        print(trans(ram_list[i]))

def compare(r1, r2):
    indexes = []
    for i in range(len(r1)):
        print(i)
        if r1[i] != r2[i]:
            indexes.append(i)
    return indexes

def overall_compare(ram_list):
    X = compare(trans(ram_list[0]), trans(ram_list[1]))
    Y = compare(trans(ram_list[1]), trans(ram_list[2]))
    T = compare(trans(ram_list[2]), trans(ram_list[3]))
    # Collect all changes
    all_changes = []
    for idx in range(3,len(ram_list)-1):
        all_changes += compare(trans(ram_list[idx]), trans(ram_list[idx+1]))
    # For all changes:
    # Check if 1) in all later comparisons AND 2) not in first comparisons
    changes_in_all = []
    for change in all_changes:
        switch = True
        for idx in range(3, len(ram_list) - 1):
            if not change in compare(trans(ram_list[idx]), trans(ram_list[idx+1])):
                switch = False
        if switch:
            changes_in_all.append(change)
    left_overs = []
    for change in changes_in_all:
        if (not change in X) and (not change in Y) and (not change in T):
            left_overs.append(change)
    return left_overs



def gen_msg(key):
    global keymap
    msg = keymap.get(key, None)
    return msg


def send_msg(key, release=True):
    msg = gen_msg(key)
    prefix = "r" if release else "p"
    print(key)
    if msg is not None:
        if msg == "end":
            emu.stop()
            exit()
        else:
            connector.send_msg(prefix + msg)
            connector.advance_frame()
            response = connector.get_screen()
            img = Image.fromarray(response, 'L')
            img.save("img.png")
    elif key == keyboard.KeyCode.from_char("c") and release:
        ram = connector.get_ram(BLOCK_ID)
        ram_list.append(ram)


def on_press(key):
    send_msg(key, False)


def on_release(key):
    send_msg(key, True)


if __name__ == "__main__":
    emu = pyfceux.FCEUXopener(MM2_PATH, LUA_CON_PATH, 0)
    emu.start()

    # Prepare mapping from inputs to NES buttons
    # Up, Left, Down, Right, A, B, Start, Select
    # and also control signals
    # l
    keys = ["w", "a", "s", "d", "u", "i", "b", "n"]
    maps = ["u", "l", "d", "r", "A", "B", "t", "e"]
    assert ("x" not in keys)
    keymap = dict([(keyboard.KeyCode.from_char(k), str(i)) for k, i in zip(keys, maps)])
    keymap[keyboard.KeyCode.from_char("x")] = "end"

    # Prepare connection
    host = "localhost"
    udp_port = 9788
    tcp_port_screen = 9799
    tcp_port_ram = 9798
    connector = pyfceux.FCEUXconnector(host, udp_port, tcp_port_screen, tcp_port_ram)
    global connector

    BLOCK_ID = 6

    global BLOCK_ID

    ram_list = []
    global ram_list


    print("Press x to end")

    # Listen for keyboard inputs
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
