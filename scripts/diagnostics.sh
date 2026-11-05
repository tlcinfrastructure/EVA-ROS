#!/usr/bin/env bash
# EVA-ROS Phase 1. Reads system state; emits a report to stdout.
# No config files are sourced. No probing/mounting/rebooting/installing.
# Optional protected reads use sudo -n, never request or collect passwords.
set -u
set -o pipefail
export LC_ALL=C

privileged=0
case "${1:-}" in
  '') ;;
  --privileged-read) privileged=1 ;;
  --help|-h)
    printf '%s\n' 'Usage: bash diagnostics.sh [--privileged-read]' \
      'Default: readable files only. Optional flag: sudo -n for protected reads.' \
      'Run sudo -v yourself first in a normal Ubuntu terminal if needed.' \
      'Output can contain filesystem UUIDs and EFI paths; review before sharing.'
    exit 0 ;;
  *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
esac
if (( $# > 1 )); then
  printf 'Only one optional argument is supported.\n' >&2
  exit 2
fi

section() { printf '\n## %s\n' "$1"; }
run() {
  printf '\n$'; printf ' %q' "$@"; printf '\n'
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '[UNAVAILABLE] Command is not installed or not on PATH.\n'
    return 0
  fi
  local rc=0
  "$@" 2>&1 || rc=$?
  if (( rc != 0 )); then printf '[UNVERIFIED] exit=%s\n' "$rc"; fi
  return 0
}
read_file() {
  local p=$1
  if [[ -r "$p" ]]; then run cat -- "$p"
  elif [[ -e "$p" && "$privileged" == 1 ]]; then run sudo -n cat -- "$p"
  else printf '[UNVERIFIED] Cannot read or missing: %s\n' "$p"; fi
}
filter_file() {
  local pattern=$1 p=$2
  if [[ -r "$p" ]]; then run grep -nE -- "$pattern" "$p"
  elif [[ -e "$p" && "$privileged" == 1 ]]; then run sudo -n grep -nE -- "$pattern" "$p"
  else printf '[UNVERIFIED] Cannot read or missing: %s\n' "$p"; fi
}

printf 'EVA-ROS Phase 1 — read-only discovery\n'
run date -Is
run id
section 'Operating system / hardware'
read_file /etc/os-release
run uname -srmo
read_file /sys/class/dmi/id/sys_vendor
read_file /sys/class/dmi/id/product_name
read_file /sys/class/dmi/id/product_version
run systemd-detect-virt
printf 'Note: virtualization detection alone cannot rule out a sandbox.\n'

section 'GRUB / installed tools'
# --version only; does not install a bootloader.
run grub-install --version
run dpkg-query -W '-f=${db:Status-Abbrev}\t${Package}\t${Version}\n' \
  grub-common grub2-common grub-efi-amd64 grub-efi-amd64-bin \
  grub-efi-amd64-signed shim-signed os-prober efibootmgr \
  qemu-system-x86 ovmf xorriso
for tool in grub-mkfont grub-script-check grub-mkrescue qemu-system-x86_64 xorriso; do
  run which "$tool"
done

section 'UEFI / Secure Boot / NVRAM (read only)'
if [[ -d /sys/firmware/efi ]]; then
  printf 'BOOT_MODE=UEFI\n'
else
  printf 'UEFI sysfs not visible; Legacy vs sandbox visibility is UNVERIFIED.\n'
fi
if (( privileged == 1 )); then
  run sudo -n efibootmgr -v
  run sudo -n mokutil --sb-state
else
  run efibootmgr -v
  run mokutil --sb-state
fi

section 'Disks / mounts / available space'
run lsblk -e 7 -o NAME,TYPE,SIZE,FSTYPE,FSVER,LABEL,PARTLABEL,PARTTYPE,UUID,PARTUUID,MOUNTPOINTS
run findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS /
run findmnt --mountpoint /boot/efi -o TARGET,SOURCE,FSTYPE,OPTIONS
run df -h /boot /boot/efi
read_file /etc/fstab
printf 'Disk names may change across boots. Use verified UUID/PARTUUID later.\n'
printf 'No Windows partition or unmounted ESP is mounted by this script.\n'

section 'GRUB source configuration (read, never source/execute)'
filter_file '^[[:space:]]*GRUB_' /etc/default/grub
run ls -la /etc/default/grub.d
for p in /etc/default/grub.d/*.cfg; do
  [[ -f "$p" ]] || continue
  printf '\nDrop-in: %s\n' "$p"
  filter_file '^[[:space:]]*GRUB_' "$p"
done
run ls -l /etc/grub.d
read_file /etc/grub.d/40_custom
read_file /etc/grub.d/41_custom
filter_file 'GRUB_DISABLE_OS_PROBER|default/grub.d|GRUB_TERMINAL_OUTPUT' /usr/sbin/grub-mkconfig
filter_file 'GRUB_DISABLE_OS_PROBER|adjust_timeout|timeout|osprober' /etc/grub.d/30_os-prober
filter_file 'themedir|[.]pf2|GRUB_THEME|GRUB_RECORDFAIL_TIMEOUT' /etc/grub.d/00_header

section 'Generated boot entries / classes / runtime branches'
run ls -l /boot/grub/grub.cfg /boot/grub/grubenv
filter_file '^[[:space:]]*(menuentry|submenu)[[:space:]]|osprober|[Ww]indows|fwsetup|timeout|recordfail|saved_entry|next_entry|set default|gfxmode|gfxterm|theme=|loadfont|configfile|custom[.]cfg' /boot/grub/grub.cfg
if [[ -e /boot/grub/custom.cfg ]]; then
  filter_file '^[[:space:]]*(menuentry|submenu)[[:space:]]|configfile|source[[:space:]]' /boot/grub/custom.cfg
fi
if [[ -r /boot/grub/grubenv ]]; then
  run grub-editenv /boot/grub/grubenv list
elif (( privileged == 1 )); then
  run sudo -n grub-editenv /boot/grub/grubenv list
else
  printf '[UNVERIFIED] Cannot read grubenv.\n'
fi
read_file /boot/efi/EFI/ubuntu/grub.cfg
run ls -l /boot/efi/EFI/ubuntu /boot/efi/EFI/BOOT

section 'Graphics (Linux modes are NOT GRUB videoinfo)'
run lspci -nn
read_file /boot/grub/x86_64-efi/video.lst
for p in /sys/class/drm/card*-*/status /sys/class/drm/card*-*/modes; do
  [[ -r "$p" ]] || continue
  read_file "$p"
done
printf '\nGRUB GOP modes: UNVERIFIED until videoinfo is run in GRUB.\n'
printf 'Windows version, BitLocker state and boot success: UNVERIFIED.\n'

section 'Baseline hashes (not a restorable backup)'
for p in /etc/default/grub /etc/default/grub.d/*.cfg /boot/grub/grub.cfg \
  /boot/grub/grubenv /boot/efi/EFI/ubuntu/grub.cfg; do
  [[ -f "$p" ]] || continue
  if [[ -r "$p" ]]; then run sha256sum -- "$p"
  elif (( privileged == 1 )); then run sudo -n sha256sum -- "$p"
  else printf '[UNVERIFIED] Cannot hash: %s\n' "$p"; fi
done
printf '\nEND. Individual UNVERIFIED items do not mean the machine is damaged.\n'
