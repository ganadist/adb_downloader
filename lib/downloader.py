# coding: utf8

import sys, os
import socket, time
import subprocess
import tempfile

class DownloaderError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

    def __repr__(self):
        msg, = self.args
        return 'DownloaderError: ' + msg


class SparseImage(tempfile.TemporaryDirectory):
    def __init__(self, src):
        tempfile.TemporaryDirectory.__init__(self)
        self.src = src

    def __enter__(self):
        tempname = tempfile.TemporaryDirectory.__enter__(self)
        dst = os.path.join(tempname, os.path.basename(self.src))
        cmd = '%s %s %s'%(g.SIMG2IMG, self.src, dst)
        os.system(cmd)
        return dst


class Downloader:
    def __init__(self, device):
        self.proc = None
        self.device = device
        self.written = False
        self.device.set_downloader(self)

    def __enter__(self):
        Adb.forward(g.COMMAND_PORT)
        self.device.prepare_prebuilts()

        cmd = (ADB, '-s', Adb.SERIAL_NO, 'shell',
                'exec', g.DOWNLOAD_DIR + '/prepare')
        self.proc = subprocess.Popen(cmd)
        self.wait()
        return self

    def __exit__(self, type, value, traceback):
        written = self.written
        self.device.finalize()

        self.cmd('setprop ctl.start console')
        if written:
            self.cmd('reboot')
        self.cmd('exit')
        self.proc.wait()

    def cmd(self, cmd):
        print('send cmd:', cmd)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', g.COMMAND_PORT))
        cmd = cmd + '\n'
        cmd = cmd.encode('utf8')
        sock.send(cmd)
        buf = b''
        try:
            buf = sock.recv(4096)
            sock.close()
        except: pass
        return buf.decode('utf8')

    def wait(self):
        while True:
            out = self.cmd('ping')
            if out == 'pong':
                return
            time.sleep(1)

    def detect_filetype(f):
        def wrap(self, device, filename):
            if False:
                with SparseImage(filename) as tempfile:
                    return f(self, device, tempfile)
            return f(self, device, filename)
        return wrap

    @detect_filetype
    def write(self, device, filename):
        if not os.access(filename, os.R_OK):
            print('no such file:', filename)
            return
        self.wait()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', g.COMMAND_PORT))
        cmd = 'write %s\n'%device
        print('send cmd:', cmd)
        cmd = cmd + '\n'
        cmd = cmd.encode('utf8')
        sock.send(cmd)

        gzip = ('gzip', '-c', '-9', filename)

        p = subprocess.Popen(gzip, stdout = subprocess.PIPE)
        while True:
            buf = p.stdout.read(16 * 1024)
            if not buf:
                break
            sock.send(buf)
        print('gzip result:', p.wait())
        self.written = True

    def run(self, cmd):
        self.wait()
        self.cmd('run ' + cmd)

    def fdisk(self):
        self.run('%(busybox)s fdisk %(disk)s < %(fdisk_cmd)s'%{
            'busybox': g.DOWNLOAD_DIR + '/busybox',
            'disk': g.BLK_DISK,
            'fdisk_cmd': g.DOWNLOAD_DIR + '/fdisk_cmd'
        })

    def clear_partition(self, part, count = 4096):
        self.run('dd if=/dev/zero of=%s bs=1024 count=%d'%(part, count))

    def mount(self, part, mntpnt):
        self.run('mount -t ext4 %s %s'%(part, mntpnt))


