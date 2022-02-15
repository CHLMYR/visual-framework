r"""
General utils.
Consist of some general function.
"""

import yaml
import torch
import random
import numpy as np
from pathlib import Path

from utils.log import LOGGER
from utils.typeslib import _int_or_None, _strpath

__all__ = ['to_tuplex', 'delete_list_indices', 'load_all_yaml', 'save_all_yaml', 'init_seed', 'select_one_device',
           'get_path_and_check_datasets_yaml']


def to_tuplex(value, n: int):
    r"""
    Change value to (value, ...).
    Args:
        value: = any
        n: int = integral number

    Return (value, ...)
    """
    return (value,) * abs(n)


def delete_list_indices(list_delete: list, indices_delete: list):
    r"""
    Delete list element according to its indices.
    Args:
        list_delete: list = [element, ...]
        indices_delete: list = [int, ...], int must >= 0

    Return list_delete
    """
    assert len(list_delete) >= len(indices_delete), \
        f'The len of two args: {len(list_delete)} must be greater than or equal to {len(indices_delete)}'
    if (np.asarray(indices_delete) < 0).any():
        raise ValueError('The int in indices_delete can not be less than 0')

    for offset, index in enumerate(indices_delete):
        list_delete.pop(index - offset)
    return list_delete


def load_all_yaml(*args: _strpath):
    r"""
    Load all *.yaml to dict from the path.
    Args:
        args: _strpath = path, ...

    Return tuple(dict, ...) or dict(when only one yaml to load)
    """
    LOGGER.info('Loading all yaml dict...')
    yaml_list = []
    for path in args:
        with open(path, 'r') as f:  # todo: args can change
            yaml_dict = yaml.safe_load(f)  # load yaml dict
            yaml_list.append(yaml_dict)
    # return dict or tuple(dict, dict, ...)
    if len(yaml_list) == 1:
        yaml_list = yaml_list[0]
    else:
        yaml_list = tuple(yaml_list)
    LOGGER.info('Load all yaml dict successfully')
    return yaml_list


def save_all_yaml(*args):
    r"""
    Save all dict to *.yaml in the path.
    Args:
        args: = (dict_yaml, path), ...
    """
    LOGGER.info('Saving all dict yaml...')
    for dict_yaml, path in args:
        with open(path, 'w') as f:  # todo: args can change
            # save yaml dict without sorting
            yaml.safe_dump(dict_yaml, f, sort_keys=False)
    LOGGER.info('Save all dict yaml successfully')


def init_seed(seed: _int_or_None = None):
    r"""
    Initialize the seed of torch(CPU), torch(GPU), random, numpy by manual or auto(seed=None).
    Args:
        seed: _int_or_None =  integral number less than 32 bit better, Default=None(auto)
    """
    if seed is None:
        LOGGER.info('Setting seed(auto get) for all generator...')
        seed = torch.seed()
        random.seed(seed)
        np.random.seed(_deal_seed_by_bit(seed))
    else:
        seed = abs(seed)
        LOGGER.info(f'Setting seed(manual): {seed} for all generator...')
        torch.manual_seed(seed)
        random.seed(seed)
        np.random.seed(_deal_seed_by_bit(seed))
    LOGGER.info(f'Set seed: {seed} successfully')


def select_one_device(device_name: str):
    r"""
    Set only one device cpu or cuda:x.
    Args:
        device_name: str = one of 'cpu', 'cuda:0', '0', '1' etc.

    Return device
    """
    LOGGER.info('Selecting device...')
    device_name = device_name.lower().replace('cuda', '').replace('CUDA', '').replace(' ', '').replace(':', '')
    if device_name == 'cpu':
        # TODO: Upgrade for somewhere in the future
        # for multi cpu
        device = torch.device(device_name, index=0)  # todo: args can change
        LOGGER.info(f'{torch.__version__} CPU:{device.index}')
    elif isinstance(int(device_name), int):
        assert torch.cuda.is_available(), f'CUDA unavailable, invalid device {device_name} requested'
        device = torch.device(int(device_name))

        # get CUDA properties
        cuda = torch.cuda.get_device_properties(device)
        capability = torch.cuda.get_device_capability(device)
        memory = cuda.total_memory / 1024 ** 2
        LOGGER.info(f'{torch.__version__} CUDA:{device_name} ({cuda.name}, {memory:.0f}MB) (Capability: {capability})')
    else:
        raise ValueError(f"The non-standard input of device, please input 'cpu', 'cuda:0', '0' .etc")
    LOGGER.info('Select device successfully')
    return device


def get_path_and_check_datasets_yaml(path: _strpath):
    r"""
    Get path of datasets yaml for training and check datasets yaml.
    Args:
        path: _strpath = path

    Return path_dict
    """
    LOGGER.info('Checking and loading the datasets yaml file...')
    # check path and get them
    datasets: dict = load_all_yaml(path)
    parent_path = Path(datasets['path'])
    train, val, test = datasets['train'], datasets.get('val'), datasets.get('test')

    # deal str or list for train, val, test
    tvt = []  # to save (train, val, test) dealt
    for file in (train, val, test):
        if file is None:
            pass
        elif isinstance(file, str):
            tvt.append(parent_path / file)
        elif isinstance(file, (list, tuple)):
            save_tem = []
            for element in file:
                save_tem.append(parent_path / element)
            tvt.append(save_tem)
        else:
            raise TypeError(f'The type of {file} is wrong, '
                            f'please reset in the {path}')
    # get the value dealt
    train, val, test = tvt
    del tvt

    # train must exist
    if train is None:
        raise FileExistsError(f'The path train must not None, '
                              f'please reset it in the {path}')

    # check whether train, val, test exist
    for path in (train, val, test):
        for p in path if isinstance(path, list) else [path]:
            if not p.exists():
                raise FileExistsError(f'The path {path} do not exists, '
                                      f'please reset in the {path}')

    path_dict = {'train': train, 'val': val, 'test': test}
    LOGGER.info('Get the path for training successfully')
    return path_dict


def _deal_seed_by_bit(seed: int, bit: int = 32):
    r"""
    Deal seed that make it.bit_length() < bit by truncating its str.
    Args:
        seed: int =  integral number
        bit: int =  integral number, Default=32

    Return seed(int)
    """
    seed = abs(seed)  # get positive number
    if seed.bit_length() > bit:
        # todo: args can change
        seed = int(str(seed)[0:9])  # [0:9] is for 32 bit
    return seed


if __name__ == '__main__':
    pass
