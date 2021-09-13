from os import path as op
import yaml, os

CONFIG_FILEPATH = op.join(op.abspath(op.dirname(__file__)), "config.yml")

CONFIG_KEY_ROBOT_DOF = "robot_dof"

def load_config() -> dict:
    try:
        with open(CONFIG_FILEPATH, "r") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
    except:
        data = {
            CONFIG_KEY_ROBOT_DOF: 6
        }
        save_config(data)
    return data


def save_config(data, no_retry=False):
    try:
        with open(CONFIG_FILEPATH, "w") as f:
            yaml.dump(data, f)
    except Exception as err:
        print(err)
        if no_retry:
            return
        os.remove(CONFIG_FILEPATH)
        save_config(data, True)