
import os

def get_env():
    """Get the environment variables for the current platform."""
    env = os.environ.copy()
    env['GODOT_VERSION_STATUS'] = 'moonskrive'
    return env
