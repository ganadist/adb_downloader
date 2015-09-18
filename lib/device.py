# coding: utf8

import os
from importlib.machinery import SourceFileLoader
from lib.downloader import DownloaderError

KNOWN_PART = ('boot', 'system', 'recovery', 'vendor', 'bootloader')

class Device:
    def __init__(self):
        self.abilist = []
        self.names = []
        self.tables = {}
        self.target_module = None
        self.prepare()
        self.load_fstab()

    def set_downloader(self, downloader):
        self.downloader = downloader

    def prepare(self):
        debuggable = Adb.getprop('ro.debuggable')
        if debuggable != '1':
            raise DownloaderError('android device is not writable')

        user = Adb.shell('id')
        if not user.startswith('uid=0'):
            Adb.root()
            Adb.wait()
            user = Adb.shell('id')
            if not user.startswith('uid=0'):
                raise DownloaderError('adb must be run with root, but output is ' + repr(user))

        config_path = self._get_config_path()
        try:
            target_module = SourceFileLoader('target', os.path.join(config_path,
                'target.py')).load_module()
            self.target_module  = target_module
        except:
            print ('not supported target device. run with fallback mode')
        self.config_path = config_path

    def prepare_prebuilts(self):
        Adb.shell('mkdir', '-p', g.DOWNLOAD_DIR)

        binaries = self.get_prebuilt_binaries()
        scripts = g.TARGET_COMMON_SCRIPTS

        for binary in binaries + scripts:
            Adb.push(binary, g.DOWNLOAD_DIR)
            Adb.shell('chmod', '755', g.DOWNLOAD_DIR + '/' + os.path.basename(binary))


    def has_target_attr(self, funcname):
        return self.target_module and hasattr(self.target_module, funcname)

    def load_fstab(self):
        if self.has_target_attr("get_partitions"):
            self.tables = self.target_module.get_partitions()
            if None in self.tables:
                # special value for whole disk
                g.BLK_DISK = self.tables.pop(None)
        else:
            # no target module
            # read partition tables from fstab on device
            hardware = Adb.getprop('ro.hardware')
            fstab = Adb.shell('cat', 'fstab.' + hardware)
            for line in fstab.split('\n'):
                line = line.strip()
                if not line.startswith('/dev/block'):
                    continue

                part, mnt_point, fstype, mnt_flags, fs_mgr_flags = line.split(None, 4)
                if mnt_point[0] == '/':
                    mnt_point = mnt_point[1:]
                self.tables[mnt_point] = part

            if 'data' in self.tables:
                self.tables['userdata'] = self.tables.pop('data')

    def get_partitions(self):
        return self.tables

    def get_part(self, partName):
        if partName in self.tables:
            return self.tables[partName]

    def get_abi(self):
        if not self.abilist:
            abilist = Adb.getprop('ro.product.cpu.abilist')
            if abilist:
                abilist = abilist.split(',')
            else:
                abilist = []
                for prop in ('ro.product.cpu.abi', 'ro.product.cpu.abi2'):
                    abi = Adb.getprop(prop)
                    if abi:
                        abilist.append(abi)
            self.abilist = abilist
        return self.abilist

    def get_names(self):
        if not self.names:
            props = ('ro.product.name', 'ro.product.device', 'ro.product.board', 'ro.board.platform')
            for prop in props:
                name = Adb.getprop(prop)
                if name and not name in self.names:
                    self.names.append(name)
        return self.names

    def get_prebuilt_path(self):
        for abi in self.get_abi():
            path = os.path.join(g.PREBUILTS_TARGET, abi)
            if os.path.isdir(path):
                return path
        else:
            raise DownloaderError('not supported abi:' + repr(self.abilist))

    def get_prebuilt_binaries(self):
        path = self.get_prebuilt_path()
        files = [os.path.join(path, filename) for filename in g.TARGET_PREBUILTS_BINARIES]

        if self.has_target_attr('get_prebuilt_binaries'):
            files += [os.path.join(self.config_path, filename) for filename in
                self.target_module.get_prebuilt_binaries()]

        return files

    def _get_config_path(self):
        names = self.get_names()
        for name in names:
            path = os.path.join(g.CONFIG_DIR, name)
            if os.path.isdir(path):
                return path
        else:
            raise DownloaderError('not supported platform:' + repr(names))

    def check_partition_files(self, parts):
        if 'all' in parts:
            parts = self.tables.keys()

        parts = set(parts).intersection(KNOWN_PART)
        files = map(lambda x: self.get_image_filename(x), parts)
        need_files_parts = tuple(filter(lambda x: not x, parts))
        if need_files_parts:
            raise Downloader("these files are needed:" + need_files_parts)

    def write_all(self):
        fdisk_cmd = os.path.join(self.config_path, 'fdisk_cmd')
        if os.access(fdisk_cmd, os.R_OK):
            Adb.push(fdisk_cmd, g.DOWNLOAD_DIR)
            self.downloader.system('%(busybox)s fdisk %(disk)s < %(fdisk_cmd)s'%{
                'busybox': g.DOWNLOAD_DIR + '/busybox',
                'disk': g.BLK_DISK,
                'fdisk_cmd': g.DOWNLOAD_DIR + '/fdisk_cmd'
            })

        for part in self.tables:
            self.write(part)


    def get_image_filename(self, part):
        filename = part + '.img'
        if not os.access(filename, os.R_OK):
            OUT = os.getenv('OUT', '')
            filename = os.path.join(OUT, filename)
            if not os.access(filename, os.R_OK):
                filename = ''

        return filename

    def write(self, part, filename = None):
        if not filename:
            filename = self.get_image_filename(part)

        device = self.tables[part]
        handler = None
        if self.has_target_attr("get_part_handler"):
            handler = self.target_module.get_part_handler(part)

        if handler:
            handler(self.downloader, device, filename)
        else:
            if part in KNOWN_PART:
                self.downloader.write(device, filename)
            else:
                self.downloader.clear_partition(device)

    def finalize(self):
        for part in ('system', 'cache', 'data'):
            if part == 'data':
                part = 'userdata'
                mntpnt = '/data'
            else:
                mntpnt = '/' + part

            block = self.get_part(part)
            self.downloader.mount(block, mntpnt)

        if self.has_target_attr('handle_exit'):
            self.target_module.handle_exit(self.downloader)


