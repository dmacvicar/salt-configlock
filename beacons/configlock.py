# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright (c) 2014-2015 SUSE LLC
#
# Licensed under the Apache License, Version
#
# Based on fanotify python module
#   Copyright (c) 2015 Adam Jacob Muller
#   Licensed under the MIT license.
#
# Author: Duncan Mac-Vicar P. <dmacvicar@suse.de>
#
'''
Watch files and translate the changes into salt events
'''
import ctypes
import os
from ctypes.util import find_library
import collections
import threading

import logging
log = logging.getLogger(__name__)

__virtualname__ = 'configlock'

class FanotifyEventMetadata(ctypes.Structure):
    _fields_ = [
        ('event_len', ctypes.c_uint32),
        ('vers', ctypes.c_uint8),
        ('reserved', ctypes.c_uint8),
        ('metadata_len', ctypes.c_uint16),
        ('mask', ctypes.c_uint64),
        ('fd', ctypes.c_int32),
        ('pid', ctypes.c_int32)
    ]

class Fanotify:
    FAN_ACCESS = 1
    FAN_MODIFY = 2
    FAN_CLOSE_WRITE = 8
    FAN_CLOSE_NOWRITE = 16
    FAN_OPEN = 32

    FAN_CLOEXEC = 1
    FAN_NONBLOCK = 2
    FAN_CLASS_NOTIF = 0
    FAN_CLASS_CONTENT = 4
    FAN_CLASS_PRE_CONTENT = 8

    FAN_UNLIMITED_QUEUE = 16
    FAN_UNLIMITED_MARKS = 32

    FAN_MARK_ADD = 1
    FAN_MARK_REMOVE = 2
    FAN_MARK_DONT_FOLLOW = 4
    FAN_MARK_ONLYDIR = 8
    FAN_MARK_MOUNT = 16
    FAN_MARK_IGNORED_MASK = 32
    FAN_MARK_IGNORED_SURV_MODIFY = 64
    FAN_MARK_FLUSH = 128

    mark_flags = [
        dict(
            name='dont_follow',
            default=False,
            value=FAN_MARK_DONT_FOLLOW
        ),
        dict(
            name='onlydir',
            default=False,
            value=FAN_MARK_ONLYDIR
        ),
        dict(
            name='mount',
            default=False,
            value=FAN_MARK_MOUNT
        )
    ]
    mark_masks = [
        dict(
            name='access',
            default=False,
            value=FAN_ACCESS
        ),
        dict(
            name='modify',
            default=False,
            value=FAN_MODIFY
        ),
        dict(
            name='close_write',
            default=False,
            value=FAN_CLOSE_WRITE
        ),
        dict(
            name='close_nowrite',
            default=False,
            value=FAN_CLOSE_NOWRITE
        ),
        dict(
            name='open',
            default=False,
            value=FAN_OPEN
        )
    ]

    def __init__(self, nonblock=False, 
                       unlimited_queue=False,
                       unlimited_marks=False,
                       get_process_names=True):
        self.libc = ctypes.cdll.LoadLibrary(find_library("c"))
        self.nonblock = nonblock
        self.unlimited_queue = unlimited_queue
        self.unlimited_marks = unlimited_marks
        self.get_process_names = get_process_names
        flags = self.FAN_CLOEXEC
        if self.unlimited_queue: 
            flags = flags | self.FAN_UNLIMITED_QUEUE
        if self.unlimited_marks:
            flags = flags | self.FAN_UNLIMITED_MARKS
        if self.nonblock: 
            flags = flags | self.FAN_NONBLOCK
        event_flags = 0
        self.fd = self.libc.fanotify_init(flags, event_flags)

    def mark(self, path, **kwargs):
        flags = self.FAN_MARK_ADD
        for flag in self.mark_flags:
            flag_enabled = flag['default']
            if flag['name'] in kwargs:
                flag_enabled = kwargs[flag['name']]
            if flag_enabled is True:
                flags = flags | flag['value']

        masks = 0
        for mask in self.mark_masks:
            mask_enabled = mask['default']
            if mask['name'] in kwargs:
                mask_enabled = kwargs[mask['name']]
            if mask_enabled is True:
                masks = masks | mask['value']
        rc = self.libc.fanotify_mark(self.fd, flags, masks, 0, path)

    def read(self, debug=False):
        while True:
            data = os.read(self.fd, 24)
            bb = ctypes.create_string_buffer(data)
            metadata = FanotifyEventMetadata()
            ctypes.memmove(ctypes.addressof(metadata), ctypes.addressof(bb), len(data))
            filename = os.readlink("/proc/self/fd/%d" % (metadata.fd))
            if filename[-10:] == " (deleted)":
                deleted = True
                filename = filename[:-10]
            else:
                deleted = False
            try:
                cmdline_fh = open("/proc/%d/cmdline" % metadata.pid, "r")
                cmdline = cmdline_fh.read()
                cmdline = cmdline.split(chr(0))
            except IOError:
                cmdline = None
            if debug:
                print "event_len: %d" % metadata.event_len
                print "vers: %d" % metadata.vers
                print "fd: %d" % metadata.fd
                print "pid: %d" % metadata.pid
                print "filename: %s" % filename
                print "cmdline: %s" % (cmdline)
                print "--------------------------------------------------------------------"
            os.close(metadata.fd)
            yield FanotifyEvent(metadata.pid, filename, cmdline, deleted=deleted)


class FanotifyEvent:
    def __init__(self, pid=None, filename=None, cmdline=None, deleted=False):
        self.pid = pid
        self.filename = filename
        self.cmdline = cmdline
        self.deleted = deleted

    def __repr__(self):
        if self.cmdline is None:
            cmdstr = ''
        else:
            cmdstr = '[%s]' % (self.cmdline[0])
        if self.deleted:
            delstr = " deleted file"
        else:
            delstr = ""
        return "<fanotify_event for%s %s by %d%s>" % (delstr, self.filename, self.pid, cmdstr)


def _get_notifier():
    '''
    Check the context for the notifier and construct it if not present
    '''
    if 'configlock.fanotify' not in __context__:
        log.info("Initialize notifier...")
        __context__['configlock.fanotify'] = Fanotify()
    return __context__['configlock.fanotify']


def _get_queue():
    if 'configlock.queue' not in __context__:
        __context__['configlock.queue'] = collections.deque()
    return __context__['configlock.queue']


def _start_notifier_thread(n, q):
    log.info("Initialize notifier thread...")
    if 'configlock.thread' not in __context__:
        __context__['configlock.thread'] = threading.Thread(target=_fanotify_thread, args=(n, q,))
        __context__['configlock.thread'].start()


def _get_managed_files():
    if 'configlock.managedfiles' not in __context__:
        highstate = __salt__['state.show_highstate']()
        names = []
        for id, props in highstate.iteritems():
            names.append(id)
        __context__['configlock.managedfiles'] = names
    return __context__['configlock.managedfiles']


def _fanotify_thread(n, q):
    n.mark("/", mount=True, close_write=True)
    managed_files = _get_managed_files()

    for event in n.read():
        if event.filename in managed_files:
            q.append(event)


def validate(config):
    '''
    Validate the beacon configuration
    '''
    return True


def beacon(config):
    '''
    Watch the configured files

    Example Config

    .. code-block:: yaml

        beacons:
          configlock:
            managed:
              lock: True
    '''
    log.info("bacon accessed")
    q = _get_queue()
    n = _get_notifier()
    _start_notifier_thread(n, q)
    events = []
    try:
        while True:
            item = q.pop()
            data = dict()
            data['filename'] = item.filename
            events.append(data)
    except IndexError:
        return events
    return []
