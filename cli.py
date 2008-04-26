#!/usr/bin/python
#
# Copyright (C) 2006, 2007, 2008  Lars Wirzenius <liw@iki.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""A backup program"""


import logging
import sys

import obnam


def main():
    try:
        context = obnam.context.Context()
        args = obnam.config.parse_options(context.config, sys.argv[1:])
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)
        context.be.set_progress_reporter(context.progress)
        app = obnam.Application(context)
    
        obnam.log.setup(context.config)

        logging.info("%s %s starting up" % (obnam.NAME, obnam.VERSION))

        try:
            factory = obnam.OperationFactory(app)
            oper = factory.get_operation(args)
            oper.do_it(args[1:])
        
            logging.info("Store I/O: %d kB read, %d kB written" % 
                         (context.be.get_bytes_read() / 1024,
                          context.be.get_bytes_written() / 1024))
            logging.info("Obnam finishing")
            context.progress.final_report()
            if app.get_store():
                app.get_store().close()
        except KeyboardInterrupt:
            logging.warning("Obnam interrupted by Control-C, aborting.")
            logging.warning("Note that backup has not been completed.")
            if app.get_store():
                app.get_store().close()
            sys.exit(1)
    except obnam.ObnamException, e:
        logging.error("%s" % str(e))
        if app.get_store():
            app.get_store().close()
        sys.exit(1)
    except BaseException, e:
        logging.error("%s" % str(e))
        if app.get_store():
            app.get_store().close()
        sys.exit(1)


if __name__ == "__main__":
    main()
