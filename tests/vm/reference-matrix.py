from pathlib import Path
import subprocess,socket,json,time,sys
b=Path(__file__).resolve().parent;cfg=b/'esp/boot/grub/grub.cfg';original=cfg.read_bytes()
def quit_vm():
 try:
  s=socket.socket(socket.AF_UNIX);s.settimeout(2);s.connect('/tmp/eva-phase3-qmp.sock');f=s.makefile('rb');f.readline();s.sendall(b'{"execute":"qmp_capabilities"}\n');f.readline();s.sendall(b'{"execute":"quit"}\n');s.close()
 except OSError:pass
quit_vm();time.sleep(1)
try:
 for n in (3,4,5):
  cfg.write_bytes((cfg.parent/f'case-{n}.cfg').read_bytes())
  log=(b/f'matrix-{n}.log').open('wb')
  process=subprocess.Popen([sys.executable,str(b/'run-vm.py')],stdout=log,stderr=log)
  try:
   time.sleep(12)
   require_keys=[] if n==3 else ['end']
   subprocess.run([sys.executable,str(b/'qmp.py'),f'matrix-{n}']+require_keys,check=True,timeout=10)
   print('Captured independent boot case',n,flush=True)
  finally:
   quit_vm()
   try:process.wait(timeout=4)
   except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=3)
   log.close();time.sleep(.5)
finally:cfg.write_bytes(original)
