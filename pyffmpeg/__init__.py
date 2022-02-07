# -*- coding: utf-8 -*-
"""
Created on Wed Mar 25 15:07:19 2020
"""

import os
import threading
from time import sleep
from typing import Optional
from subprocess import Popen, PIPE, STDOUT
from platform import system
from lzma import decompress
from base64 import b64decode, b64encode

from .pseudo_ffprobe import FFprobe
from .misc import Paths, fix_splashes


class FFmpeg():


    """
    Provide methods for working with FFmpeg
    """


    def __init__(self, directory="."):
        """
        Init function
        """

        self.save_dir = directory
        self.overwrite = True
        self.loglevels = (
            'quiet', 'panic', 'fatal', 'error', 'warning',
            'info', 'verbose', 'debug', 'trace')
        self.loglevel = 'fatal'
        self._log_level_stmt = '-loglevel'
        if self.overwrite:
            self._over_write = '-y'
        else:
            self._over_write = '-n'

        # Progress
        self.report_progress = True
        self.in_duration: float = 0.0
        self._progress: int = 0
        self.onProgressChanged = self.progressChangeMock

        # instances are store according to function names
        self._ffmpeg_instances = {}
        self._ffmpeg_file = Paths().load_ffmpeg_bin()
        self.error = ''

    def convert(self, input_file, output_file):

        """
        Converts and input file to the output file
        """

        if os.path.isabs(output_file):
            # absolute file
            out = output_file
        else:
            # not an absolute file
            out = os.path.join(self.save_dir, output_file)

        inf = input_file.replace("\\", "/")

        if self.loglevel not in self.loglevels:
            msg = 'Warning: "{}" not an ffmpeg loglevel flag.' +\
             ' Using fatal instead'
            print(msg.format(self.loglevel))
            self.loglevel = 'fatal'

        options = "{} -loglevel {} "
        options = options.format(self._ffmpeg_file, self.loglevel)
        options += "{} -i {} {}"
        options = options.format(self._over_write, inf, out)

        if self.report_progress:
            f = FFprobe(inf)
            d = f.duration.replace(':', '')
            self.in_duration = float(d)
            self.monitor(out)

        outP = Popen(options, shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        self._ffmpeg_instances['convert'] = outP
        self.error = str(outP.stderr.read(), 'utf-8')
        return out

    def get_ffmpeg_bin(self):

        """
        Get the ffmpeg executable file. This is the fullpath to the
        binary distributed with pyffmpeg. There is only one at a time.
        """

        return self._ffmpeg_file

    def get_fps(self, input_file):
        """
        Returns the frame per second rate of an input file
        """
        fprobe = FFprobe(input_file)
        fps = fprobe.fps
        return fps

    def monitor(self, fn: str):
        m_thread = threading.Thread(target=self._monitor, args=[fn])
        m_thread.daemon = True
        m_thread.start()

    def _monitor(self, fn: str):
        print('Monitoring Spirit started')
        sleep(1)
        dura = 0.0
        while dura < self.in_duration:
            try:
                f = FFprobe(fn)
                d = f.duration.replace(':', '')
                dura = float(d)
            except:
                dura = 0.0
            self.progress = dura / self.in_duration * 100
            sleep(0.1)

    def options(self, opts):

        """
        Allows user to pass any other command line options to the FFmpeg executable
        eg.: command line options of 'ffmpeg -i a.mp4 b.mp3'
        will be passed by user as: opts: '-i a.mp4 b.mp3'
        """

        if isinstance(opts, list):
            options = fix_splashes(opts)

            # Add ffmpeg and overwrite variable
            options.insert(0, self._over_write)
            if self.loglevel not in self.loglevels:
                msg = 'Warning: "{}" not an ffmpeg loglevel flag.' +\
                 ' Using fatal instead'
                print(msg.format(self.loglevel))
                self.loglevel = 'fatal'

            options = ' '.join(options)
            options = ' '.join(['-loglevel', self.loglevel, options])

        else:
            options = opts

            # Add ffmpeg and overwrite variable

            # handle overwrite
            if self._over_write not in options:
                options = " ".join([self._over_write, options])

            # handle loglevel
            if self._log_level_stmt not in options:
                if self.loglevel not in self.loglevels:
                    msg = 'Warning: "{}" not an ffmpeg loglevel flag.' +\
                     ' Using fatal instead'
                    print(msg.format(self.loglevel))
                    self.loglevel = 'fatal'

                if self.loglevel != 'fatal':
                    options = " ".join(
                        [options])

        # add ffmpeg
        options = " ".join([self._ffmpeg_file, options])

        out = Popen(options, shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        self._ffmpeg_instances['options'] = out
        self.error = str(out.stderr.read(), 'utf-8')
        return True

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, percent):
        self._progress = int(percent)
        self.onProgressChanged(self._progress)

    def progressChangeMock(self, progress):
        print('progress: ', progress)

    def quit(self, function: Optional[str] = ''):
        """
        Allows for any running process of ffmpeg started by pyffmpeg
        to be terminated
        """
        if function:
            inst = self._ffmpeg_instances[function]
            output = inst.communicate(b'q')
        # Quit all instances
        else:
            for inst in self._ffmpeg_instances.values():
                output = inst.communicate(b'q')
                print('out: ', output)
