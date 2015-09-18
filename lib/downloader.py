# coding: utf8

import sys, os, errno
import socket, time
import struct
import subprocess
import tempfile

class DownloaderError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

    def __repr__(self):
        msg, = self.args
        return 'DownloaderError: ' + msg


def is_sparse_file(filename):
    FH = open(filename, 'rb')
    header_bin = FH.read(28)
    header = struct.unpack('<I4H4I', header_bin)

    magic = header[0]
    major_version = header[1]
    minor_version = header[2]
    file_hdr_sz = header[3]
    chunk_hdr_sz = header[4]
    blk_sz = header[5]
    total_blks = header[6]
    total_chunks = header[7]
    image_checksum = header[8]

    if magic != 0xED26FF3A:
        return False

    if major_version != 1 or minor_version != 0:
        return False

    if file_hdr_sz != 28:
        return False

    if chunk_hdr_sz != 12:
        return False

    return True

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
        self.device.set_downloader(self)
        self.written = False

    def __enter__(self):
        Adb.forward(g.COMMAND_PORT)
        self.device.prepare_prebuilts()

        cmd = (g.ADB, '-s', Adb.SERIAL_NO, 'shell',
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
            if is_sparse_file(filename):
                with SparseImage(filename) as tempfile:
                    return f(self, device, tempfile)
            return f(self, device, filename)
        return wrap

    @detect_filetype
    def write(self, device, filename):
        """ Write file on block device on target

        Args:
            device (string): block device filename on target
            filename (string): filename on host

        Returns:
            int: If successed 0 or -1
        """
        if not os.access(filename, os.R_OK):
            raise OSError(errno.ENOENT, "no such filename")
        self.wait()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', g.COMMAND_PORT))
        cmd = 'write %s\n'%device
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
        self.written = True
        return p.returncode

    def system(self, command):
        """ Run command on target device and return stdout

        Args:
            command (string): command to run on target

        Returns:
            string: stdout when run command on target
        """
        self.wait()
        return self.cmd('run ' + command)

    def clear_partition(self, part, count = 4096):
        self.system('dd if=/dev/zero of=%s bs=1024 count=%d'%(part, count))

    def mount(self, part, mntpnt):
        self.system('mount -t ext4 %s %s'%(part, mntpnt))


