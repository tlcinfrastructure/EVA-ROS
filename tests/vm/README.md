# VM-only harness

This config contains echo/sleep test entries, not OS boot commands. It must never replace a real system grub.cfg.

The executed runtime remains in work/phase3 in the development workspace: run-vm.py, qmp.py, type-vm.py, extracted packages and a copied OVMF VARS. It uses QEMU TCG/q35/SMM, no network, a synthetic FAT directory and a local QMP socket. Signed shim/GRUB and OVMF/QEMU binaries are not redistributed in this source snapshot. Full one-command environment preparation remains pending.
