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


# Run Obnam in a safe way that ignore's any configuration files
# outside the test. The first argument MUST be the client name. The
# configuration file $DATADIR/$1.conf is used, if it exists. In addition,
# the environment variables specified in $DATADIR/$1.env are added for
# the duration of running Obnam.

run_obnam()
{
    local name="$1"
    shift
    (
        if [ -e "$DATADIR/$name.env" ]
        then
            . "$DATADIR/$name.env"
        fi
        "$SRCDIR/obnam" --no-default-config --config "$DATADIR/$name.conf" \
            --quiet --client-name="$name" \
            --log-level debug --log "$DATADIR/obnam.log" "$@"
    )
}


# Add an environment variable to the Obnam run.

add_to_env()
{
    local user="$1"
    local var="$2"
    local value="$3"
    printf 'export %s=%s\n' "$var" "$value" >> "$DATADIR/$user.env"
}


# Add a setting to an Obnam configuration file.

add_to_config()
{
    local filename="$1"
    local key="$2"
    local value="$3"

    if [ ! -e "$filename" ]
    then
        printf '[config]\n' > "$filename"
    fi
    printf '%s = %s\n' "$key" "$value" >> "$filename"
}


# Create a manifest with summain of a directory.

manifest()
{
    summain -r "$1" --exclude Ino --exclude Dev |
    sed '/^Mtime:/s/\.[0-9]* / /'
}
