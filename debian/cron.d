# /etc/cron.d/obnam -- run obnam at any time you desire (if enabled)

# Uncomment the line below to enable the cron job.
# You can also edit the time and other settings to decide exactly when
# to make backups.
# To set the directories that are backed up, edit /etc/default/obnam.
# Note that this cron job is enabled or disabled by commenting the line
# below, instead of setting ENABLE in /etc/default/obnam.

# 30 12 * * * root obnam backup $(. /etc/default/obnam && echo $DIRS)
