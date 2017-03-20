# fceux2openai
This project is alpha and meant to connect NES games to OpenAI's gym environments for Reinforcement Learning.

For this, the project currently contains three parts:
1) A lua script that has to be executed in FCEUX, which provides sockets for interprocess communication

2) Python classes that allow to interact with the emulator, e.g. start it, load a state, get the current image and RAM, ...

3) A wrapper that allows to use the emulator as an OpenAI environment as well as some specialized versions of the environment that
allow game-dependent interaction, e.g. it provides a health-based reward function for the popular "Mega Man 2"


