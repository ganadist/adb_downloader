# coding: utf8

import sys, os
__all__ = ["adb", "downloader", "device"]


class g:
    pass

g.DIRNAME = os.path.dirname(sys.argv[0])
g.PREBUILTS_HOST = os.path.join(g.DIRNAME, 'prebuilts', 'host', sys.platform)
g.PREBUILTS_TARGET = os.path.join(g.DIRNAME, 'prebuilts', 'target')
g.TARGET_SCRIPT_DIR = os.path.join(g.DIRNAME, 'scripts')
g.CONFIG_DIR = os.path.join(g.DIRNAME, 'config')
g.TARGET_PREBUILTS_BINARIES = ('busybox', 'installer')
TARGET_COMMON_SCRIPTS = ('prepare', )
g.TARGET_COMMON_SCRIPTS = [os.path.join(g.TARGET_SCRIPT_DIR, x) for x in TARGET_COMMON_SCRIPTS]

g.ADB = os.path.join(g.PREBUILTS_HOST, 'adb')
g.SIMG2IMG = os.path.join(g.PREBUILTS_HOST, 'simg2img')
g.COMMAND_PORT = 9123

g.DOWNLOAD_DIR = '/dev/d/'
g.BLK_DISK = '/dev/block/mmcblk0'

import builtins
from lib.adb import Adb
from lib.device import Device
from lib.downloader import Downloader

builtins.__dict__['g'] = g
builtins.__dict__['Adb'] = Adb
builtins.__dict__['Device'] = Device
builtins.__dict__['Downloader'] = Downloader
