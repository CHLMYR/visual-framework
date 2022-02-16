r"""
Custom Dataset module.
Consist of Dataset that designed for different tasks.
"""
import cv2
from pathlib import Path

import torch
import numpy as np
from tqdm import tqdm
from torch.utils.data import Dataset, DataLoader

from utils.log import LOGGER
from utils.general import load_all_yaml
from utils.typeslib import _strpath

__all__ = ['DatasetDetect', 'get_path_and_check_datasets_yaml']

IMAGE_FORMATS = ('bmp', 'jpg', 'jpeg', 'jpe', 'png', 'tif', 'tiff', 'webp')  # acceptable image suffixes


# TODO upgrade Sampler in the future

class DatasetDetect(Dataset):
    # TODO upgrade val_from_train, test_from_train function in the future
    # TODO upgrade rectangular train shape for image model in the future reference to yolov5 rect=True
    # TODO upgrade .cache file in memory for faster training
    def __init__(self, path, img_size, prefix: str = ''):
        LOGGER.info('Initializing dataset...')
        self.img_size = img_size

        self.img_files = get_img_files(path)  # get the path list of image files
        # check img suffix and sort img_files(to str)
        self.img_files = sorted(str(x) for x in self.img_files if x.suffix.replace('.', '').lower() in IMAGE_FORMATS)
        if not self.img_files:
            raise FileNotFoundError('No images found')

        # get label_files that it is str and sorted with images_files
        self.label_files = img2label_files(self.img_files)
        # check images and labels then get labels which is [np.array, ...]
        self.label_files = self._check_img_get_label_detect(self.img_files, self.label_files, prefix)
        LOGGER.info(f'Load {len(self.img_files)} images and {len(self.label_files)} labels')
        LOGGER.info('Initialize dataset successfully')

    def __getitem__(self, index):
        # TODO upgrade mosaic, cutout, cutmix, mixup etc.
        # load image
        img_path = self.img_files[index]  # path str
        label = self.label_files[index]  # label ndarray [[class,x,y,w,h], ...]

        image = load_image(img_path, self.img_size)  # load image and resize it
        image = letterbox(image, self.img_size)  # pad image to shape or img_size

        # TODO upgrade augment
        image = np.transpose(image, (2, 0, 1))  # (h,w,c) to (c,h,w)
        image = np.ascontiguousarray(image)  # make image contiguous in memory
        image = torch.from_numpy(image)
        return image, label

    def __len__(self):
        return len(self.img_files)

    @staticmethod
    def _check_img_get_label_detect(images_files, labels_files, prefix: str = '', nlabel: int = 5):
        labels = []  # save labels
        channel = cv2.imread(images_files[0]).shape[-1]
        with tqdm(zip(images_files, labels_files),
                  desc=f'{prefix}: checking image and label',
                  total=len(images_files)) as pbar:
            for ip, lp in pbar:  # image path, label path
                # check image
                assert cv2.imread(ip).shape[
                           -1] == channel, f'The channel of the image {ip} do not match with {channel}'
                # check label and get read it to list
                with open(lp, 'r') as f:
                    label = [x.strip().split() for x in f.read().splitlines() if
                             x]  # label is [[class,x,y,w,h], ...]
                    label = np.array(label, dtype=np.float32)
                    label = np.unique(label, axis=0)  # remove the same one
                    assert len(label), f'The label {lp} is empty'
                    assert label.ndim == 2, f'There are format problem with label {lp}'
                    assert label.shape[1] == nlabel, f'The label require {nlabel} element {lp}'
                    assert (label >= 0).all(), f'The value in label should not be negative {lp}'
                    assert (label[:, 1:]).all(), f'Non-normalized or out of bounds coordinates {lp}'
                    labels.append(label)
        return labels


def letterbox(img, shape):
    # TODO 2022.2.17
    return img


def load_image(img_path: _strpath, img_size: int):
    r"""
    Load image and resize it which the largest edge is img_size.
    Args:
        img_path: _strpath = StrPath
        img_size: int = img_size for the largest edge

    Return image, (h0, w0), (h, w)
    """
    image = cv2.imread(img_path)  # (h,w,c) BGR
    image = image[..., ::-1]  # BGR to RGB
    if image is None:
        raise FileNotFoundError(
            f'The image is None, path error or image error {img_path}')

    # TODO the process(or rect) may be faster for training in __init__ in the future
    h0, w0 = image.shape[:2]  # original hw
    r = img_size / max(h0, w0)  # ratio for resize
    h, w = int(w0 * r), int(h0 * r)

    if r != 1:
        # todo: args can change
        image = cv2.resize(image, dsize=(w, h),  # cv2.resize dsize need (w, h)
                           interpolation=cv2.INTER_AREA if r < 1 else cv2.INTER_LINEAR)
    return image, (h0, w0), (h, w)


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

    datasets['train'], datasets['val'], datasets['test'] = train, val, test

    # check number of classes and name
    if not (datasets['nc'] == len(datasets['names'])):
        raise ValueError('There is no one-to-one correspondence '
                         'between the number of classes and its names')

    LOGGER.info('Get the path for training successfully')
    return datasets


def get_img_files(path):  # path is list or pathlike
    img_files = []
    for p in path if isinstance(path, list) else [path]:
        p = Path(p)
        if p.is_dir():
            img_files += [x for x in p.rglob('*.*')]
        elif p.is_file():
            with open(p, 'r') as f:
                f = f.read().splitlines()
                # local to global path
                parent = p.parent
                for element in f:
                    element = Path(element.strip())
                    if '\\' in element.parts:  # remove / in the front of it
                        element = parent / Path(*element[1:])
                        img_files.append(element)
                    else:
                        img_files.append(parent / element)
        else:
            raise TypeError(f'Something wrong with {p} in the type of file')
    return img_files


def img2label_files(img_files):
    r"""
    Change image path to label path from image paths.
    The file name must be 'images' and 'labels'.
    Args:
        img_files: = img_files

    Return label_files
    """
    # change 'images' to 'labels' and change suffix to '.txt'
    label_files = ['labels'.join(p.rsplit('images', 1)).rsplit('.', 1)[0] + '.txt' for p in img_files]
    return label_files
