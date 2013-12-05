# Copyright 2013  Lars Wirzenius
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


# Set variables to help referring to common things in $DATADIR.
REPO="$DATADIR/repo"


# Run Obnam in a safe way that ignore's any configuration files outside
# the test.

run_obnam()
{
    "$SRCDIR/obnam" --no-default-config --quiet "$@"
}


# Create a manifest with summain of a directory.

manifest()
{
    summain -r "$1" --exclude Ino --exclude Dev |
    sed '/^Mtime:/s/\.[0-9]* / /'
}

