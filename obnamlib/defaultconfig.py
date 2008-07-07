# This module has the default config values. It will be overwritten by
# "make install". The values here are suitable for development purposes,
# but not for real use.

items = (
    ("backup", "host-id", ""),
    ("backup", "block-size", "%d" % (1024 * 1024)),
    ("backup", "cache", "tmp.cache"),
    ("backup", "store", "tmp.store"),
    ("backup", "ssh-key", "ssh-key"),
    ("backup", "target-dir", "."),
    ("backup", "object-cache-size", "0"),
    ("backup", "log-file", ""),
    ("backup", "log-level", "warning"),
    ("backup", "gpg-home", "sample-gpg-home"),
    ("backup", "gpg-encrypt-to", "490C9ED1"),
    ("backup", "gpg-sign-with", "490C9ED1"),
    ("backup", "no-gpg", "false"),
    ("backup", "exclude", ""),
    ("backup", "report-progress", "false"),
    ("backup", "generation-times", "false"),
    ("backup", "snapshot-bytes", "0"),
)

default_paths = []
