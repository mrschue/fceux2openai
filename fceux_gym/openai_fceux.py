import os
import socket

import gym
import numpy as np
from gym import spaces

import pyfceux

"""
This file contains the wrappers for the FCEUX interface to make it available as
environment in OpenAI. It also contains reward functions designed on information
contained in the emulated RAM
"""

KIRBY_PATH = os.path.abspath("/home/m/Personal/NES Games/Kirby.nes")
MM2_PATH = os.path.abspath("/home/m/Personal/NES Games/MM2.nes")
LUA_CON_PATH = os.path.abspath("/home/m/Personal/NES Games/lua_/connector_screen_v2.lua")


def ram_translate(ram_block):
    p = ""
    for r in ram_block:
        p += hex(ord(r)).replace("0x", "").zfill(2)
    return p


class FceuxEnv(gym.Env):
    """
    This class wraps the pyfceux interface in a way that makes it registrable
    to the OpenAI gym framework.
    """
    metadata = {'render.modes': ['rgb_array', 'average', 'luminosity'], 'hosts': ['localhost', '127.0.0.1'],
                'button_codes': ["u", "l", "d", "r", "A", "B", "t", "e"], 'button_prefixes': ['r', 'p']}
    reward_range = (-np.inf, np.inf)
    action_space = spaces.Discrete(6 * 2)  # with start & select

    def __init__(self, game_path, lua_path=LUA_CON_PATH, load_state=1, host="localhost",
                 tcp_port_screen=9799, tcp_port_ram=9798, udp_port=9788, render_mode='luminosity'):
        self.game_path = game_path
        self.lua_path = lua_path
        self.load_state = load_state
        self.host = host
        self.tcp_port_screen = tcp_port_screen
        self.tcp_port_ram = tcp_port_ram
        self.udp_port = udp_port
        self.render_mode = render_mode
        if host in self.metadata['hosts']:
            self.emulator = pyfceux.FCEUXopener(game_path, lua_path, load_state)
            self.emulator.start()
        self.connector = pyfceux.FCEUXconnector(host, udp_port, tcp_port_screen, tcp_port_ram, color_mode=render_mode)
        # Configure observation space
        self.observation_space = spaces.Box(0, 255, shape=self.connector.output_shape)

    def _seed(self, seed=None):
        pass

    def _close(self):
        pass

    def _step(self, action):
        if action < 6:
            prefix = self.metadata['button_prefixes'][1]
        else:
            prefix = self.metadata['button_prefixes'][0]
        msg = prefix + self.metadata['button_codes'][action % 6]
        # Send action
        self.connector.send_msg(msg)
        # Step fceux emulator
        self.connector.advance_frame()
        # Receive observation
        observation = self.connector.get_screen()
        info = {}
        return observation, None, None, info

    def _render(self, mode='luminosity', close=False):
        pass

    def _reset(self):
        obs = self.connector.load_state(self.load_state)
        # Clean the 'pipes'
        try:
            self.connector.receive_screen_response()
        except socket.timeout:
            pass
        try:
            self.connector.receive_ram_response()
        except socket.timeout:
            pass
        self.accumulated_damage = 0
        return obs

    def _get_ram(self, block_id):
        return self.connector.get_ram(block_id)


class FceuxMM2Boss(FceuxEnv):
    def __init__(self, game_path=MM2_PATH, agent_health_address=int('6C0', 16), boss_health_adress=int('6C1', 16),
                 agent_damage_weight=4, boss_damage_weight=1, agent_invincible=True, boss_invincible=False):
        super(FceuxMM2Boss, self).__init__(game_path=game_path)
        self.agent_health_block = int(agent_health_address / 256)
        self.agent_health_offset = agent_health_address % (self.agent_health_block * 256)
        self.boss_health_block = int(boss_health_adress / 256)
        self.boss_health_offset = boss_health_adress % (self.boss_health_block * 256)
        self.agent_damage_weight = agent_damage_weight
        self.boss_damage_weight = boss_damage_weight
        if agent_invincible:
            self.connector.send_msg("cI1")
        if boss_invincible:
            # Todo: implement boss invincibility
            pass

    def _step(self, action):
        # Get pre-step RAM
        agent_pre_ram = self._get_ram(self.agent_health_block)
        boss_pre_ram = self._get_ram(self.boss_health_block)

        obs, __, __, info = super(FceuxMM2Boss, self)._step(action)

        # Get post-step RAM
        agent_post_ram = self._get_ram(self.agent_health_block)
        if self.agent_health_block != self.boss_health_block:
            boss_post_ram = self._get_ram(self.boss_health_block)
        else:
            boss_post_ram = agent_post_ram
        # Extract Health info from RAM
        agent_post_health = ord(agent_post_ram[self.agent_health_offset])
        boss_post_health = ord(boss_post_ram[self.boss_health_offset])
        agent_pre_health = ord(agent_pre_ram[self.agent_health_offset])
        boss_pre_health = ord(boss_pre_ram[self.boss_health_offset])
        # Calculate reward
        agent_damage = agent_pre_health - agent_post_health
        boss_damage = boss_pre_health - boss_post_health
        reward = self.boss_damage_weight * boss_damage - self.agent_damage_weight * agent_damage
        # See if episode ended
        if boss_post_health == 0:
            reward += 20
        if agent_post_health == 0:
            reward -= 20
        done = (agent_post_health == 0) or (boss_post_health == 0)
        info['agent_health'] = agent_post_health
        info['boss_health'] = boss_post_health
        return obs, reward, done, info


class FceuxKirby(FceuxEnv):
    def __init__(self, game_path=KIRBY_PATH):
        super(FceuxKirby, self).__init__(game_path=game_path)


class FceuxMM2(FceuxEnv):
    def __init__(self, game_path=MM2_PATH):
        super(FceuxMM2, self).__init__(game_path=game_path)
