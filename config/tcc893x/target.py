# coding: utf8

BLK_BASE = "/dev/block/platform/bdm/by-num/"
BLK_DISK = '/dev/block/platform/bdm/mmcblk0'

BLK_BOOT = BLK_BASE + "p1"
BLK_SYSTEM = BLK_BASE + "p2"
BLK_USERDATA = BLK_BASE + "p3"
# p4 is extended partition
BLK_CACHE = BLK_BASE + "p5"
BLK_RECOVERY = BLK_BASE + "p6"

def get_partitions():
    return {
        None: BLK_DISK,
        'boot': BLK_BOOT,
        'system': BLK_SYSTEM,
        'userdata': BLK_USERDATA,
        'cache': BLK_CACHE,
        'recovery': BLK_RECOVERY,
        }

def get_part_handler(part):
    if part in ('userdata', 'cache'):
        return wipe_partition


def wipe_partition(downloader, device, filename):
    downloader.clear_partition(device)

