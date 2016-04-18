#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014-2015 SUSE LLC
#
# Licensed under the Apache License, Version
#
# Author: Duncan Mac-Vicar P. <dmacvicar@suse.de>
#
'''
Watch files and translate the changes into salt events
'''

import collections
import logging
import pyinotify

log = logging.getLogger(__name__)

__virtualname__ = 'managedwatch'


class ManagedFile:
    def __init__(self, id, env, sls):
        self.id = id
        self.env = env
        self.sls = sls

    def path(self):
        # TODO lie
        return self.id

    def diff(self):
        ret = __salt__['state.sls_id'](self.id,
                                       self.sls, saltenv=self.env, test=True)
        log.debug(ret)
        vals = ret.values()
        if len(vals) != 1:
            log.warning('More than one sls for the id: %s' % self.id)
            return ""
        if 'changes' in vals[0] and 'diff' in vals[0]['changes']:
            return vals[0]['changes']['diff']
        return ""

    def event_dict(self):
        data = dict()
        data['id'] = self.id
        data['path'] = self.path()
        data['env'] = self.env
        data['sls'] = self.sls
        data['diff'] = self.diff()
        return data


def _get_managed_files():
    highstate = __salt__['state.show_highstate']()
    files = []
    # TODO: check if this works with files specified
    # with a normal id and the path in name:
    for id, props in highstate.iteritems():
        if 'file' not in props:
            continue
        filedata = ManagedFile(id, props['__env__'], props['__sls__'])
        files.append(filedata)
    return files


class EventHandler(pyinotify.ProcessEvent):
    def __init__(self):
        self.stats = pyinotify.Stats()
        log.info("Initialize notifier...")
        self.queue = collections.deque()
        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(
            self.wm, default_proc_fun=self)
        self.managed_files = _get_managed_files()
        log.warning("adding %d watches", len(self.managed_files))

        for mf in self.managed_files:
            log.warning("Add watch for %s" % mf.path())
            self.wm.add_watch(
                mf.path(), pyinotify.IN_MODIFY | pyinotify.IN_DELETE_SELF,
                auto_add=True)
        self.notifier.start()

    def process_IN_IGNORED(self, event):
        # Re-init the watch after IN_IGNORED
        log.debug("IN_IGNORED: re-init the watch for: %s" % event.pathname)
        self.wm.add_watch(
            event.pathname, pyinotify.IN_MODIFY | pyinotify.IN_DELETE_SELF,
            auto_add=True)

    def process_default(self, event):
        # Does nothing, just to demonstrate how stuffs could be done
        # after having processed statistics.
        log.debug("inotify event: %s" % event)
        for mf in self.managed_files:
            if event.pathname == mf.path():
                log.debug("send: %s", mf.event_dict())
                self.queue.append(mf.event_dict())


def _get_handler():
    if 'managedwatch.handler' not in __context__:
        handler = EventHandler()
        __context__['managedwatch.handler'] = handler
    return __context__['managedwatch.handler']


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
          managedwatch:
            managed:
              lock: True
    '''
    handler = _get_handler()
    log.debug("bacon accessed: handler %s" % id(handler))
    events = []

    try:
        while True:
            item = handler.queue.pop()
            events.append(item)
    except IndexError:
        pass
    return events
