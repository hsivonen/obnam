# Copyright 2013-2014  Lars Wirzenius
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
#
# =*= License: GPL-3+ =*=


import hashlib
import textwrap


class StructuredError(Exception):

    '''A structured error exception.

    A structured exception is meant to specify highly specific errors
    in its type. Rather than getting a formatted message string as its
    initialiser argument (e.g., "raise Exception('Something went
    wrong')"), the message is an attribute of the StructuredError
    subclass. Each message gets a separate sub-class: instead of a few
    fairly generic exceptions, you're expected to create very specific
    ones. For example, instead of, say, InputOutputError, you might
    define FileNotFoundError, or even ConfigFileDoesNotExistError, as
    well as ConfigFilePermissionDeniedError. More specific exceptions
    make it easier to handle specific error cases, whether by catching
    only specific ones, or by grepping log files for them.

    Structured errors get a set of keyword arguments to the
    initialiser, and use them to fill in templates in a message string
    attribute of the exception class. In addition, each structured
    exception has a unique ID, computed from the class name, which can
    be used, for example, as a user-visible error code. The ID is
    prepended to the message. The ID could also be used to look up
    translations, though that is not currently implemented. The ID
    will also make translated log files more greppable.

    The msg attribute is a format string. It can be arbitrarily long.
    The __str__ method returns the first line only, but the full
    message can be retrieved using the formatted() method. The
    convention is to have the first line be a short summary of the
    problem, and have the full message provide additional, helpful
    information to the user.

    The format string uses syntax according to the str.format
    specification (not the old % interpolation), in order to ease
    eventual migration to Python 3.

    To use structured error exceptions, subclass this class for each
    error condition, and add a msg attribute to the subclass. There is
    no such attribute in this base class, to prevent you from using it
    directly.

    Example:

        class NoLasagnaError(StructuredError):

            msg = 'Lunch is {lunch} instead of lasagna.'

    That's all the subclass needs to do. The caller must then provide
    the right keyword arguments: these are verified when the ``str``
    is called on the exception object. If the caller has not provided
    all the required arguments, an unformatted error message is
    provided, plus a note of what arguments are missing, and all the
    arguments that were provided. It's not an error to provide extra
    keyword arguments.

    '''

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @property
    def id(self):
        '''A semi-unique ID for this exception class.

        The ID is computed from the name of the class and the module
        it is in, using a checksum. There is no guarantee of
        uniqueness, but the likelihood of collisions is low.

        The ID is of the form RabcdeX, where abcde is five hexadecimal
        digits. The R prefix and the X suffix are there to make it
        easier to grep for the error code in large log files: they
        reduce the number of accidental hits compared to grepping just
        for the hexadecimal digits. R and X were chosen because they're
        pretty.

        '''

        summer = hashlib.md5()
        summer.update(self.__class__.__name__)
        summer.update(self.__class__.__module__)
        hash = summer.hexdigest()[:5]
        return 'R{0}X'.format(hash.upper())

    def _format_msg(self, template):
        # In case template is a docstring, remove leading whitespace
        # from lines.
        lines = template.splitlines(True)
        if len(lines) == 0:
            dedented = ''
        else:
            dedented = (textwrap.dedent(lines[0]) +
                        textwrap.dedent(''.join(lines[1:])))
 
        try:
            formatted_msg = dedented.format(**self.kwargs)
        except KeyError as e:
            # If there were any errors in the formatting of the message,
            # report them here. We do NOT want replace the actual error
            # message, because that would hide information from the user.
            # We do want to know there was an error, though.
            formatted_msg = '{0} (PROGRAMMING ERROR: {1} {2})'.format(
                dedented, repr(e), repr(self.kwargs))

        return '{0}: {1}'.format(self.id, formatted_msg)

    def formatted(self):
        '''Return the full formatted message.'''
        return self._format_msg(self.msg)

    def __str__(self):
        full = self.formatted()
        lines = full.splitlines()
        assert lines
        return lines[0]
