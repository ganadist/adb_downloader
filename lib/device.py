# coding: utf8

from importlib.machinery import SourceFileLoader
from lib import adb
from lib.downloader import DownloaderError

class Device:
    def __init__(self, serial_no = None):
        self.abilist = []
        self.names = []
        self.tables = {}
        Adb.SERIAL_NO = adb.select_device(serial_no)
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

        config_path = self.get_config_path()
        try:
            target_module = SourceFileLoader('target', os.path.join(config_path,
                'target.py')).load_module()
        except:
            raise DownloaderError('not supported platform')
        self.target = target_module.Target()

    def prepare_prebuilts(self):
        Adb.shell('mkdir', '-p', g.DOWNLOAD_DIR)

        binaries = self.get_prebuilt_binaries()

        common_path = ''
        scripts = g.TARGET_COMMON_SCRIPTS

        target_module_path = self.get_config_path()
        target_binaries = [os.path.join(target_module_path, filename) for filename in
                self.target.get_prebuilt_binaries()]

        for binary in binaries + scripts + target_binaries:
            Adb.push(binary, g.DOWNLOAD_DIR)
            Adb.shell('chmod', '755', g.DOWNLOAD_DIR + '/' + os.path.basename(binary))


    def load_fstab(self):
        hardware = Adb.getprop('ro.hardware')
        fstab = Adb.shell('cat', 'fstab.' + hardware)
        for line in fstab.split('\n'):
            line = line.strip()
            if not line.startswith('/dev/block'):
                continue

            part, mnt_point, fstype, mnt_flags, fs_mgr_flags = line.split(None, 4)
            self.tables[mnt_point[1:]] = part

        self.tables.update(self.target.get_partitions())

        if 'data' in self.tables:
            self.tables['userdata'] = self.tables['data']

    def get_partitions(self):
        return self.tables

    def get_part(self, partName):
        if partName in self.tables:
            return self.tables[partName]

        # XXX
        platform_busname = 'msm_sdcc.1'
        if partName == 'data':
            partName = 'userdata'
        return '/dev/block/platform/' + platform_busname + '/by-name/' + partname

    def get_abi(self):
        if not self.abilist:
            abilist = Adb.getprop('ro.product.cpu.abilist')
            print(abilist)
            if abilist:
                abilist = abilist.split(',')
            else:
                abilist = []
                for prop in ('ro.product.cpu.abi', 'ro.product.cpu.abi2'):
                    abi = Adb.getprop(prop)
                    print(abi)
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

        return files

    def get_config_path(self):
        names = self.get_names()
        for name in names:
            path = os.path.join(g.CONFIG_DIR, name)
            if os.path.isdir(path):
                return path
        else:
            raise DownloaderError('not supported platform:' + repr(names))

    def write_all(self):
        pass

    def write(self, part, filename = None):
        if not filename:
            filename = part + '.img'

        if not os.path.dirname(filename):
            OUT = os.getenv('OUT', '')
            filename = os.path.join(OUT, filename)

        target_downloader = self.target.get_part_handler(part)
        if target_downloader:
            target_downloader(self.downloader, part, filename)
        else:
            KNOWN_PART = ('boot', 'system', 'recovery')
            if part in KNOWN_PART:
                self.downloader.write(part, filename)
            else:
                self.downloader.clear_partition(part)

    def finalize(self):
        for part in ('system', 'cache', 'data'):
            block = self.get_part(part)
            mntpnt = '/' + part
            self.downloader.mount(block, mntpnt)

        self.target.handle_exit(self.downloader)


