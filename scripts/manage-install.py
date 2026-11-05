#!/usr/bin/env python3
"""Reviewable installer/rollback. Phase 2 gates deliberately remain closed.

Does not install bootloader binaries or write firmware/ESP. grub.cfg is
generated only by distro tools, never patched/copied by this program.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
DROP=Path('/etc/default/grub.d/99-eva-ros.cfg')
CFG=Path('/boot/grub/grub.cfg')
BACKUPS=Path('/var/backups/eva-ros')
REQUIRED=('grub_vm_passed','runtime_font_confirmed','layout_approved',
          'windows_chainloader_reviewed','recovery_plan_ready','icon_classes_verified','menu_order_verified')

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(condition,message):
    if not condition: raise RuntimeError(message)
def call(args,log):
    with log.open('ab') as out:
        out.write(('\n$ '+' '.join(map(str,args))+'\n').encode());out.flush()
        subprocess.run(list(map(str,args)),stdout=out,stderr=subprocess.STDOUT,check=True)
def headers(text):
    return {line.strip() for line in text.splitlines()
            if re.match(r'^\s*(menuentry|submenu)\s',line)}
def check_config(path,baseline,log):
    call(['/usr/bin/grub-script-check',path],log)
    text=path.read_text()
    missing=headers(baseline)-headers(text)
    require(not missing,'Generated configuration lost/changed existing entries: '+repr(sorted(missing)))
    require('Windows Boot Manager' in text,'No Windows Boot Manager entry in generated configuration.')

def restore_drop(backup):
    old=backup/'dropin-before.cfg'
    if old.exists(): shutil.copy2(old,DROP)
    else: DROP.unlink(missing_ok=True)

def install(args):
    print('EVA-ROS: plan only unless --apply is explicitly supplied.')
    print('Theme: /boot/grub/themes/EVA-ROS-<timestamp>/')
    print('Config: one owned drop-in; TIMEOUT_STYLE=menu, TIMEOUT=-1, DEFAULT=0, SAVEDEFAULT=false.')
    print('No forced GFXMODE/GFXPAYLOAD, no ESP/BootOrder/bootloader binary changes.')
    print('Generator may execute os-prober; --allow-os-prober is required for apply.')
    gates=json.loads((ROOT/'tests/acceptance.json').read_text())
    pending=[k for k in REQUIRED if gates.get(k) is not True]
    print('Pending acceptance checks: '+(', '.join(pending) if pending else 'none'))
    if not args.apply:
        print('DRY RUN: no system file was changed.');return
    require(not pending,'Installation locked until acceptance evidence is reviewed. Do not mark unchecked tests as passed.')
    require(args.allow_os_prober,'Review and explicitly authorize generator/os-prober side effects first.')
    require(os.geteuid()==0,'Run with sudo only after tests and installation approval.')
    require(Path('/sys/firmware/efi').is_dir(),'This installer was designed for the verified UEFI machine.')
    require(not DROP.is_symlink(),'Refusing symlink at owned drop-in path.')
    require(DROP.parent.is_dir(),'Missing GRUB drop-in directory.')
    source=ROOT/'eva-ros'
    require(not any(p.is_symlink() for p in source.rglob('*')),'Theme contains symlinks.')
    require(CFG.is_file(),'Missing existing grub.cfg; refusing to create a boot configuration from scratch.')
    local_path=ROOT/'config/local-machine.json'
    require(local_path.is_file(),'Private machine baseline missing; perform discovery and review before installation.')
    local=json.loads(local_path.read_text())
    expected_hash=local.get('grub_cfg_sha256','')
    expected_uuid=local.get('boot_filesystem_uuid','')
    require(re.fullmatch(r'[0-9a-f]{64}',expected_hash) is not None,'Invalid private grub.cfg baseline hash.')
    require(re.fullmatch(r'[0-9a-fA-F-]{36}',expected_uuid) is not None,'Invalid private boot filesystem UUID.')
    require(digest(CFG)==expected_hash,
            'GRUB baseline changed since discovery; refresh and review evidence before installation.')
    boot_uuid=subprocess.check_output(['/usr/bin/findmnt','-n','-T','/boot','-o','UUID'],text=True).strip()
    require(boot_uuid==expected_uuid,
            'This installer is scoped to the verified Ubuntu filesystem; target mismatch.')
    subprocess.run([sys.executable,str(ROOT/'scripts/validate-assets.py')],check=True)
    baseline=CFG.read_text()
    require('Windows Boot Manager' in baseline,'Existing Windows entry must be reviewed before installation.')
    for cmd in ['/usr/sbin/grub-mkconfig','/usr/sbin/update-grub','/usr/bin/grub-script-check']:
        require(os.access(cmd,os.X_OK),'Missing tool: '+cmd)
    print('This writes a theme/drop-in and regenerates GRUB, possibly probing other filesystems.')
    require(input('Type INSTALL EVA-ROS to proceed: ')=='INSTALL EVA-ROS','Cancelled.')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=BACKUPS/stamp
    backup.mkdir(parents=True,mode=0o700)
    backup.chmod(0o700)
    shutil.copy2('/etc/default/grub',backup/'defaults-before')
    shutil.copytree('/etc/default/grub.d',backup/'dropins-before',symlinks=True)
    shutil.copytree('/etc/grub.d',backup/'generators-before',symlinks=True)
    shutil.copy2(CFG,backup/'grub.cfg-before-evidence-only')
    if Path('/boot/grub/grubenv').exists():shutil.copy2('/boot/grub/grubenv',backup/'grubenv-before-evidence-only')
    if DROP.exists():shutil.copy2(DROP,backup/'dropin-before.cfg')
    log=backup/'operations.log'
    call(['/usr/bin/efibootmgr','-v'],log)
    destination=Path('/boot/grub/themes')/('EVA-ROS-'+stamp)
    require(not destination.exists(),'Versioned target already exists.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(source,destination)
    for p in destination.rglob('*'):p.chmod(0o755 if p.is_dir() else 0o644)
    destination.chmod(0o755)
    payload=(f'# EVA-ROS installation {stamp}\nGRUB_THEME="{destination}/theme.txt"\n'
             'GRUB_TIMEOUT_STYLE=menu\nGRUB_TIMEOUT=-1\nGRUB_DEFAULT=0\nGRUB_SAVEDEFAULT=false\n'
             'GRUB_RECORDFAIL_TIMEOUT=-1\n')
    # Every backup exists before any config source is changed.
    temp=DROP.with_name('.99-eva-ros.cfg.tmp')
    require(not temp.exists() and not temp.is_symlink(),'Temporary drop-in path is occupied.')
    generated=False
    state={'theme_path':str(destination),'dropin_sha256':hashlib.sha256(payload.encode()).hexdigest(),
           'defaults_sha256':digest(Path('/etc/default/grub')),'status':'pending'}
    (backup/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    try:
        with temp.open('x') as f:f.write(payload)
        temp.chmod(0o644);temp.replace(DROP)
        candidate=backup/'candidate.cfg'
        call(['/usr/sbin/grub-mkconfig','-o',candidate],log)
        check_config(candidate,baseline,log)
        require(str(destination) in candidate.read_text(),'A later configuration overrode GRUB_THEME.')
        generated=True
        call(['/usr/sbin/update-grub'],log)
        check_config(CFG,baseline,log)
        require(str(destination) in CFG.read_text(),'Generated active config does not reference installed theme.')
        state['status']='installed'
        state['active_config_sha256']=digest(CFG)
        (backup/'state.json').write_text(json.dumps(state,indent=2)+'\n')
        print('Installed. Backup session:',backup)
        print('Reboot and verify only when you are ready. Hardware acceptance is still required.')
    except Exception:
        temp.unlink(missing_ok=True)
        restore_drop(backup)
        if generated:
            try:
                call(['/usr/sbin/update-grub'],log);check_config(CFG,baseline,log)
            except Exception as recovery_error:
                print('AUTOMATIC RECOVERY FAILED. DO NOT REBOOT. Log:',log,recovery_error,file=sys.stderr)
        state['status']='failed; source restored; inspect logs before reboot'
        (backup/'state.json').write_text(json.dumps(state,indent=2)+'\n')
        raise

def rollback(args):
    require(args.backup is not None,'Provide --backup /var/backups/eva-ros/<session>.')
    backup=Path(args.backup).resolve()
    require(backup.parent==BACKUPS,'Backup must be a direct session under /var/backups/eva-ros.')
    print('Rollback sources from:',backup)
    if not args.apply:
        print('DRY RUN: no system file was changed.');return
    require(os.geteuid()==0,'Rollback apply requires sudo.')
    require(args.allow_os_prober,'Rollback regeneration may run os-prober; explicit authorization required.')
    state=json.loads((backup/'state.json').read_text())
    require(DROP.is_file() and not DROP.is_symlink() and digest(DROP)==state['dropin_sha256'],
            'Owned drop-in changed or missing; review later edits before restoring.')
    require(digest(Path('/etc/default/grub'))==state['defaults_sha256'],
            'Defaults changed since installation; review manually before rollback.')
    require(input('Type ROLLBACK EVA-ROS to proceed: ')=='ROLLBACK EVA-ROS','Cancelled.')
    restore_drop(backup)
    log=backup/'rollback.log'
    try:
        call(['/usr/sbin/update-grub'],log)
        check_config(CFG,(backup/'grub.cfg-before-evidence-only').read_text(),log)
    except Exception:
        print('Rollback regeneration needs attention. DO NOT REBOOT. Inspect:',log,file=sys.stderr)
        raise
    state['status']='rolled back; versioned theme retained for recovery'
    (backup/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    print('Configuration sources restored and regenerated. Theme assets retained, not deleted.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['install','rollback'])
    p.add_argument('--apply',action='store_true')
    p.add_argument('--allow-os-prober',action='store_true')
    p.add_argument('--backup')
    args=p.parse_args()
    if args.action=='install':install(args)
    else:rollback(args)

if __name__=='__main__':
    try:main()
    except (RuntimeError,subprocess.CalledProcessError,OSError,ValueError,EOFError) as error:
        print('STOP:',error,file=sys.stderr);sys.exit(1)
