from gym.envs.registration import register


# This script registers my FCEUX environments to OpenAI's gym framework,
# so that it created via gym's "make" method

register(
    id='NESKirby-v0',
    entry_point='fceux_gym.openai_fceux:FceuxKirby',
)

register(
    id='NESMM2Boss-v0',
    entry_point='fceux_gym.openai_fceux:FceuxMM2Boss',
)

#register(
#    id='NESMM2-v0',
#    entry_point='fceux:openai_fceux:FceuxMM2Boss',
#)