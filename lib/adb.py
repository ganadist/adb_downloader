# coding: utf8

import sys, os
import subprocess

class AdbException(Exception):
    def __init__(self, code, msg):
        Exception.__init__(self, code, msg)

    def __repr__(self):
        code, msg = self.args
        return 'AdbException: code:%s %s'%(code, msg)


class Adb:
    SERIAL_NO = None
    def adb(f):
        def wrap(*args, **kwds):
            cmd = f(*args, **kwds)
            if not cmd:
                cmd = (f.__name__, ) + args

            if Adb.SERIAL_NO:
                cmd = (g.ADB, '-s', Adb.SERIAL_NO) + cmd
            else:
                cmd = (g.ADB, ) + cmd

            proc = subprocess.Popen(cmd, stdout = subprocess.PIPE)
            proc.wait()
            output = proc.stdout.read().strip().decode('utf8')
            if proc.returncode != 0:
                raise AdbException(proc.returncode, output)
            return output
        return wrap

    @staticmethod
    @adb
    def devices(*args): pass

    @staticmethod
    @adb
    def push(*args): pass

    @staticmethod
    @adb
    def root(*args): pass

    @staticmethod
    @adb
    def shell(*args): pass

    @staticmethod
    @adb
    def forward(src, dst = None):
        if dst is None:
            dst = src
        return ('forward', 'tcp:%d'%src, 'tcp:%d'%dst)

    @staticmethod
    @adb
    def getprop(*args):
        return ('shell', 'getprop') + args

    @staticmethod
    @adb
    def serial(*args):
        return ('get-serialno', )

    @staticmethod
    @adb
    def wait(*args):
        return ('wait-for-device', )

def select_device(serial_no = None):
    devices = tuple(map(lambda x: x.split()[0], Adb.devices().split('\n')[1:]))
    if not devices:
        raise AdbException(-1, 'there is no connected android device')

    if not serial_no:
        serial_no = os.getenv('ANDROID_SERIAL', devices[0])
        print('selected device is', serial_no)

    if not serial_no in devices:
        raise AdbException(-1, 'android device named %s is not connected'%serial_no)

    return serial_no

