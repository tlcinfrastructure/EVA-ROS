from pathlib import Path
import os,subprocess
b=Path(__file__).resolve().parent;r=b/'runtime';env=os.environ.copy()
env['QEMU_MODULE_DIR']=str(r/'usr/lib/x86_64-linux-gnu/qemu');env['LD_LIBRARY_PATH']=str(r/'usr/lib/x86_64-linux-gnu')
args=[str(r/'usr/bin/qemu-system-x86_64'),'-machine','q35,smm=on,accel=tcg','-m','512','-nic','none','-display','none','-no-reboot','-vga','none','-device','VGA,romfile='+str(r/'usr/share/seabios/vgabios-stdvga.bin'),'-L',str(r/'usr/share/qemu'),'-drive','if=pflash,format=raw,readonly=on,file='+str(r/'usr/share/OVMF/OVMF_CODE_4M.secboot.fd'),'-drive','if=pflash,format=raw,file='+str(b/'OVMF_VARS_TEST.fd'),'-global','driver=cfi.pflash01,property=secure,value=on','-drive','format=raw,file=fat:rw:'+str(b/'esp'),'-qmp','unix:/tmp/eva-phase3-qmp.sock,server=on,wait=off','-serial','file:'+str(b/'serial.log')]
subprocess.run(args,env=env,check=True)
