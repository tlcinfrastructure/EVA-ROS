# Installation draft

No real installation is recommended from this Phase 2 snapshot. `bash install.sh` is a read-only plan.

A future apply requires reviewed acceptance evidence, a private local baseline, root access, explicit operator confirmation and authorization for generator/os-prober side effects. `config/local-machine.example.json` contains placeholders, not machine data. Do not commit a real local-machine.json or diagnostics.

The manager is designed to back up configuration before modifications, install a versioned theme folder, write one owned GRUB defaults drop-in, validate a generated candidate and use Ubuntu update-grub. It does not patch/copy active grub.cfg by hand, run grub-install or modify ESP/NVRAM. The apply logic has not yet been tested end to end.

Rollback accepts a backup session under /var/backups/eva-ros, checks for intervening changes, restores the owned drop-in and regenerates configuration. Assets are retained. Real rollback and recovery still need testing; if generation fails, resolve it before rebooting.

This snapshot replaces hardcoded private UUID/hash values with a local baseline file requirement. That keeps the refusal behavior without publishing one user's machine identifiers. No acceptance gate has been relaxed.
