# Copyright (C) 2009-2015  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import time

import obnamlib


class BackupProgress(object):

    def __init__(self, ts):
        self.file_count = 0
        self.backed_up_count = 0
        self.uploaded_bytes = 0
        self.scanned_bytes = 0
        self.started = None
        self.errors = False

        self._ts = ts
        self._ts['current-file'] = ''
        self._ts['scanned-bytes'] = 0
        self._ts['uploaded-bytes'] = 0

        if hasattr(self._ts, 'start_new_line'):
            self._ts.format(
                '%ElapsedTime() Backing up: '
                'found %Counter(current-file) files, '
                '%ByteSize(scanned-bytes); '
                'uploaded: %ByteSize(uploaded-bytes)\n'
                '%String(what)'
            )
        else:
            self._ts.format(
                '%ElapsedTime() '
                '%Counter(current-file) '
                'files '
                '%ByteSize(scanned-bytes) scanned: '
                '%String(what)')

    def clear(self):
        self._ts.clear()

    def error(self, msg, exc=None):
        self.errors = True

        logging.error(msg)
        if exc:
            logging.error(repr(exc))
        self._ts.error('ERROR: %s' % msg)

    def what(self, what_what):
        if self.started is None:
            self.started = time.time()
        self._ts['what'] = what_what
        self._ts.flush()

    def update_progress(self):
        self._ts['not-shown'] = 'not shown'

    def update_progress_with_file(self, filename, metadata):
        self._ts['what'] = filename
        self._ts['current-file'] = filename
        self.file_count += 1

    def update_progress_with_scanned(self, amount):
        self.scanned_bytes += amount
        self._ts['scanned-bytes'] = self.scanned_bytes

    def update_progress_with_upload(self, amount):
        self.uploaded_bytes += amount
        self._ts['uploaded-bytes'] = self.uploaded_bytes

    def update_progress_with_removed_checkpoint(self, gen):
        self._ts['checkpoint'] = gen

    def report_stats(self, fs):
        duration = time.time() - self.started
        duration_string = obnamlib.humanise_duration(duration)

        chunk_amount, chunk_unit = obnamlib.humanise_size(
            self.uploaded_bytes)

        ul_amount, ul_unit = obnamlib.humanise_size(fs.bytes_written)

        dl_amount, dl_unit = obnamlib.humanise_size(fs.bytes_read)

        overhead_bytes = (
            fs.bytes_read + (fs.bytes_written - self.uploaded_bytes))
        overhead_bytes = max(0, overhead_bytes)
        overhead_amount, overhead_unit = obnamlib.humanise_size(
            overhead_bytes)
        if fs.bytes_written > 0:
            overhead_percent = 100.0 * overhead_bytes / fs.bytes_written
        else:
            overhead_percent = 0.0

        speed_amount, speed_unit = obnamlib.humanise_speed(
            self.uploaded_bytes, duration)

        logging.info(
            'Backup performance statistics:')
        logging.info(
            '* files found: %s',
            self.file_count)
        logging.info(
            '* files backed up: %s',
            self.backed_up_count)
        logging.info(
            '* uploaded chunk data: %s bytes (%s %s)',
            self.uploaded_bytes, chunk_amount, chunk_unit)
        logging.info(
            '* total uploaded data (incl. metadata): %s bytes (%s %s)',
            fs.bytes_written, ul_amount, ul_unit)
        logging.info(
            '* total downloaded data (incl. metadata): %s bytes (%s %s)',
            fs.bytes_read, dl_amount, dl_unit)
        logging.info(
            '* transfer overhead: %s bytes (%s %s)',
            overhead_bytes, overhead_amount, overhead_unit)
        logging.info(
            '* duration: %s s (%s)',
            duration, duration_string)
        logging.info(
            '* average speed: %s %s',
            speed_amount, speed_unit)

        scanned_amount, scanned_unit = obnamlib.humanise_size(
            self.scanned_bytes)

        self._ts.notify(
            'Backed up %d files (of %d found), containing %.1f %s.' %
            (self.backed_up_count,
             self.file_count,
             scanned_amount,
             scanned_unit))
        self._ts.notify(
            'Uploaded %.1f %s file data in %s at %.1f %s average speed.' %
            (chunk_amount,
             chunk_unit,
             duration_string,
             speed_amount,
             speed_unit))
        self._ts.notify(
            'Total download amount %.1f %s.' %
            (dl_amount,
             dl_unit))
        self._ts.notify(
            'Total upload amount %.1f %s. Overhead was %.1f %s (%.1f %%).' %
            (ul_amount,
             ul_unit,
             overhead_amount,
             overhead_unit,
             overhead_percent))
