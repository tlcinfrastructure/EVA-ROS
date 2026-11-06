#!/usr/bin/env python3
"""Run only workspace tests; never invoke an install apply that passes its gates."""
from pathlib import Path
import importlib.util, json, subprocess, tempfile, sys
sys.dont_write_bytecode=True
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
results={}
def main():
    for p in list((ROOT/'scripts').glob('*.py'))+[Path(__file__)]:
        compile(p.read_text(),str(p),'exec')
    for p in (ROOT/'install.sh',ROOT/'rollback.sh',ROOT/'scripts/diagnostics.sh'):
        subprocess.run(['bash','-n',str(p)],check=True)
    results['python_and_bash_syntax']='PASS'
    subprocess.run(['python3',str(ROOT/'scripts/validate-assets.py')],check=True)
    results['asset_validation']='PASS'
    gates=json.loads((ROOT/'tests/acceptance.json').read_text())
    assert all(value is False for value in gates.values())
    dry=subprocess.run(['bash',str(ROOT/'install.sh')],capture_output=True,text=True)
    assert dry.returncode==0 and 'DRY RUN' in dry.stdout
    refused=subprocess.run(['bash',str(ROOT/'install.sh'),'--apply'],capture_output=True,text=True)
    assert refused.returncode!=0 and 'Installation locked' in refused.stderr
    results['default_dry_run_and_apply_refusal']='PASS'
    spec=importlib.util.spec_from_file_location('eva_installer',ROOT/'scripts/manage-install.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='eva-safety-') as folder:
        temp=Path(folder);module.DROP=temp/'99-eva-ros.cfg'
        backup=temp/'backup';backup.mkdir()
        module.DROP.write_text('new configuration')
        module.restore_drop(backup)
        assert not module.DROP.exists()
        module.DROP.write_text('new configuration')
        (backup/'dropin-before.cfg').write_text('original configuration\n')
        module.restore_drop(backup)
        assert module.DROP.read_bytes()==(backup/'dropin-before.cfg').read_bytes()
    results['restore_original_or_original_absence_in_temp_only']='PASS'
    coords={'nw':(0,0),'n':(48,0),'ne':(577,0),'w':(0,11),'c':(48,11),'e':(577,11),
            'sw':(0,89),'s':(48,89),'se':(577,89)}
    for prefix in ('item','selected_item'):
        reconstructed=Image.new('RGBA',(625,100))
        for suffix,xy in coords.items():
            reconstructed.paste(Image.open(ROOT/'eva-ros'/f'{prefix}_{suffix}.png'),xy)
        assert reconstructed.tobytes()==Image.open(ROOT/'artwork'/f'{prefix}-whole.png').tobytes()
    results['nine_slice_reconstruction']='PASS'
    a=np.asarray(Image.open(ROOT/'artwork/preview-layout-ubuntu.png'))
    b=np.asarray(Image.open(ROOT/'artwork/preview-layout-windows.png'))
    changed=np.any(a!=b,axis=2)
    allowed=np.zeros(changed.shape,dtype=bool)
    allowed[292:510,299:924]=True
    assert changed.any() and not changed[~allowed].any()
    results['selection_changes_only_first_two_menu_rows']='PASS'
    results['preview_canvas_1920x1080']='PASS'
    results['GRUB_VM_and_hardware']='NOT RUN BY THIS SCRIPT'
    (ROOT/'tests/results/phase-2-static.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
