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

    # Create the config file, if it doesn't already exist.
    local conf="$DATADIR/$name.conf"
    if [ ! -e "$conf" ]
    then
        add_to_config "$name" client-name "$name"
    fi

    # Always turn off weak-random, or else anything that uses
    # encryption will take a long time. We don't need strong random
    # numbers for tests.
    add_to_config "$name" weak-random yes

    (
        if [ -e "$DATADIR/$name.env" ]
        then
            . "$DATADIR/$name.env"
        fi
        "$SRCDIR/obnam" --no-default-config --config "$conf" \
            --quiet --log-level debug --log "$DATADIR/obnam.log" "$@"
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


# Add a setting to the configuration file for a given client.

add_to_config()
{
    local client="$1"
    local filename="$DATADIR/$client.conf"
    local key="$2"
    local value="$3"

    if [ ! -e "$filename" ]
    then
        printf '[config]\n' > "$filename"
        printf 'client-name = %s\n' "$client" >> "$filename"
    fi
    printf '%s = %s\n' "$key" "$value" >> "$filename"
}


# Attempt to run a command, which may fail. Capture its stdout,
# stderr, and exit code.

attempt()
{
    if "$@" \
        > "$DATADIR/attempt.stdout" \
        2> "$DATADIR/attempt.stderr"
    then
        exit=0
    else
        exit=$?
    fi
    echo "$exit" > "$DATADIR/attempt.exit"
}


# Match captured output from attempt against a regular expression.

attempt_matches()
{
    grep "$2" "$DATADIR/attempt.$1"
}


# Check exit code of latest attempt.

attempt_exit_was()
{
    grep -Fx "$1" "$DATADIR/attempt.exit"
}


# Normalise time fields in a manifest that vary uncontrollably on
# some filesystems.

normalise_manifest_times()
{
    sed '/^Mtime:/s/\.[0-9]* / /' "$@"
}


# Create a manifest with summain of a file or a directory.

manifest()
{
    summain -r "$1" --exclude Ino --exclude Dev | normalise_manifest_times
}
