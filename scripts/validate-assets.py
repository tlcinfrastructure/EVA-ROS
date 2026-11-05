#!/usr/bin/env python3
"""Static assets only. This does NOT parse theme syntax with GRUB."""
from pathlib import Path
from PIL import Image
import json, re

root=Path(__file__).resolve().parents[1];theme=root/'eva-ros'
def main():
    text=(theme/'theme.txt').read_text()
    assert len(re.findall(r'^\+ boot_menu\s*\{',text,re.M))==1
    assert Image.open(theme/'background.png').size==(1670,942)
    for prefix in ('item','selected_item'):
        for suffix in ('c','n','s','e','w','nw','ne','sw','se'):
            with Image.open(theme/f'{prefix}_{suffix}.png') as im:
                assert im.mode=='RGBA' and min(im.size)>0
    for name in ('ubuntu','windows','uefi','memtest','advanced'):
        with Image.open(theme/'icons'/f'{name}.png') as im:
            assert im.size==(48,48) and im.mode=='RGBA'
    for p in (root/'artwork').glob('preview-*.png'):
        assert Image.open(p).size==(1920,1080), p
    assert 'title-text: ""' in text
    assert '__timeout__' not in text
    assert not any(p.is_symlink() for p in theme.rglob('*'))
    normal=Image.open(theme/'item_c.png')
    selected=Image.open(theme/'selected_item_c.png')
    assert normal.tobytes()!=selected.tobytes()
    metadata=json.loads((root/'artwork/render-metadata.json').read_text())
    print('PASS: background dimensions, 18 slices, 5 icons, paths, distinct selection states.')
    print('Offline font source:',metadata['font_source_name'])
    print('NOT TESTED: GRUB renderer, accepted runtime font name, Secure Boot, scrolling, OS boot.')

if __name__=='__main__':main()
