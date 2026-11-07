#!/bin/sh
# TuneD [script] helper used by every desktop-smooth-* profile in place of the
# [acpi] plugin.
#
# The [acpi] plugin rolls back on every profile switch: it first writes the
# value it saw at the previous apply (always "balanced" here), then the new
# one. On the Legion that is two firmware mode changes ~20 ms apart, and right
# after an Fn+Q press the second write was sometimes lost (GNOME on Power
# Saver, LED white). This helper writes once, and only when the firmware is
# not already in the wanted mode, so following an Fn+Q press writes nothing.
#
# The wanted mode comes from the profile's [variables]
# desktop_smooth_platform_profile, which TuneD exports as
# TUNED_desktop_smooth_platform_profile. Like [acpi], "a|b" means the first
# one the firmware offers. "stop" does nothing on purpose (no rollback).

profile=/sys/firmware/acpi/platform_profile
choices_file=/sys/firmware/acpi/platform_profile_choices

[ "$1" = start ] || exit 0
[ -w "$profile" ] && [ -r "$choices_file" ] || exit 0
wanted=${TUNED_desktop_smooth_platform_profile:-}
[ -n "$wanted" ] || { echo "desktop_smooth_platform_profile is not set" >&2; exit 0; }

current=$(cat "$profile")
choices=" $(cat "$choices_file") "
old_ifs=$IFS
IFS='|'
for want in $wanted; do
	case "$choices" in
	*" $want "*)
		IFS=$old_ifs
		[ "$current" = "$want" ] || printf '%s\n' "$want" > "$profile"
		exit 0
		;;
	esac
done
echo "none of '$wanted' is offered by the firmware ($choices)" >&2
exit 0
