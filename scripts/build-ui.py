#!/usr/bin/env python3
"""Generate code-defined UI assets and an OFFLINE layout simulation.

Background restoration is imagegen output, not performed by this script.
This is not a GRUB renderer and cannot certify theme.txt geometry.
"""
from pathlib import Path
import json, math, struct
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / 'eva-ros'
ART = ROOT / 'artwork'
CANVAS = (1920, 1080)
W, H = 625, 100

def capsule(selected=False):
    scale=3
    size=(W*scale,H*scale)
    mask=Image.new('L',size)
    d=ImageDraw.Draw(mask)
    d.rounded_rectangle((5*scale,5*scale,(W-5)*scale,(H-5)*scale),radius=(H-10)*scale/2,fill=255)
    a=np.zeros((size[1],size[0],4),dtype=np.uint8)
    for y in range(size[1]):
        f=y/size[1]
        shine=math.exp(-((f-.08)/.15)**2)*35+math.exp(-((f-.92)/.17)**2)*14
        if selected: rgb=(28+shine,3+shine*.22,6+shine*.27)
        else: rgb=(3+shine*.65,5+shine*.7,7+shine*.75)
        a[y,:,:3]=[int(v) for v in rgb]
        a[y,:,3]=225 if selected else 205
    panel=Image.fromarray(a)
    panel.putalpha(ImageChops.multiply(panel.getchannel('A'),mask))
    stroke=Image.new('RGBA',size)
    sd=ImageDraw.Draw(stroke)
    sd.rounded_rectangle((5*scale,5*scale,(W-5)*scale,(H-5)*scale),radius=(H-10)*scale/2,
                         outline=(255,110,125,255) if selected else (170,180,188,145),width=2*scale if selected else scale)
    out=Image.new('RGBA',size)
    if selected:
        out=Image.alpha_composite(out,stroke.filter(ImageFilter.GaussianBlur(3*scale)))
    out=Image.alpha_composite(out,panel)
    out=Image.alpha_composite(out,stroke)
    d=ImageDraw.Draw(out)
    d.line(((W-44)*scale,(H/2-8)*scale,(W-36)*scale,H/2*scale,(W-44)*scale,(H/2+8)*scale),
           fill=(255,255,255,245) if selected else (180,185,190,180),width=3*scale,joint='curve')
    return out.resize((W,H),Image.Resampling.LANCZOS)

def slices(im,prefix):
    # 48 px end caps, 11 px upper/lower edges; no magic painted OS labels.
    x=(0,48,W-48,W); y=(0,11,H-11,H)
    names=(('nw','n','ne'),('w','c','e'),('sw','s','se'))
    for row in range(3):
        for col in range(3):
            im.crop((x[col],y[row],x[col+1],y[row+1])).save(THEME/f'{prefix}_{names[row][col]}.png')

def icon(name):
    s=4; im=Image.new('RGBA',(48*s,48*s));d=ImageDraw.Draw(im)
    if name=='ubuntu':
        d.ellipse((1*s,1*s,47*s,47*s),fill='#E95420')
        d.ellipse((12*s,12*s,36*s,36*s),outline='white',width=3*s)
        for angle in (-90,30,150):
            r=math.radians(angle);x=24+14*math.cos(r);y=24+14*math.sin(r)
            d.ellipse(((x-4)*s,(y-4)*s,(x+4)*s,(y+4)*s),fill='white',outline='#E95420',width=s)
    elif name=='windows':
        for x in (4,25):
            for y in (5,26): d.rectangle((x*s,y*s,(x+18)*s,(y+18)*s),fill='#00B8FF')
    elif name in ('uefi','advanced'):
        pts=[]
        for i in range(48):
            a=i*math.pi/24;r=22 if i%6 in (1,2,3,4) else 17
            pts.append(((24+r*math.cos(a))*s,(24+r*math.sin(a))*s))
        d.polygon(pts,fill='#D5D8DE')
        d.ellipse((15*s,15*s,33*s,33*s),fill=(0,0,0,0))
    elif name=='memtest':
        d.rounded_rectangle((9*s,9*s,39*s,39*s),radius=3*s,fill='#777F8A')
        d.rectangle((15*s,15*s,33*s,33*s),outline='#D7DCE4',width=2*s)
        for k in (14,24,34):
            for box in [(4,k-1,9,k+1),(39,k-1,44,k+1),(k-1,4,k+1,9),(k-1,39,k+1,44)]:
                d.rectangle(tuple(v*s for v in box),fill='#A2A9B4')
    return im.resize((48,48),Image.Resampling.LANCZOS)

class PF2:
    def __init__(self,path):
        self.data=Path(path).read_bytes();self.chars={};i=0
        while i+8<=len(self.data):
            typ=self.data[i:i+4];n=int.from_bytes(self.data[i+4:i+8],'big');v=self.data[i+8:i+8+n]
            if typ==b'NAME': self.name=v.rstrip(b'\0').decode()
            if typ==b'CHIX':
                for k in range(0,n,9):
                    cp,flags,offset=struct.unpack('>IBI',v[k:k+9])
                    if flags&7==0:self.chars[cp]=offset
            if n==0xffffffff:break
            i+=8+n
    def draw(self,im,text,x,baseline,color):
        for char in text:
            offset=self.chars.get(ord(char),self.chars[ord('?')])
            w,h,xo,yo,advance=struct.unpack('>HHhhh',self.data[offset:offset+10])
            if w*h:
                bits=self.data[offset+10:offset+10+(w*h+7)//8]
                pixels=[255 if bits[k//8]&(128>>(k%8)) else 0 for k in range(w*h)]
                mask=Image.new('L',(w,h));mask.putdata(pixels)
                im.paste(color,(x+xo,baseline-yo-h,x+xo+w,baseline-yo),mask)
            x+=advance
        return x

def preview(name,entries,selected,font):
    # 1920x1080 OFFLINE simulation, not framebuffer evidence.
    bg=Image.open(THEME/'background.png').convert('RGBA')
    if bg.size!=(1670,942):
        raise RuntimeError('Unexpected imagegen dimensions; review layout before rendering')
    fitted=ImageOps.contain(bg,CANVAS,Image.Resampling.LANCZOS)
    bg=Image.new('RGBA',CANVAS,(3,4,6,255))
    bg.alpha_composite(fitted,((CANVAS[0]-fitted.width)//2,(CANVAS[1]-fitted.height)//2))
    for i,(title,cls) in enumerate(entries):
        x=299;y=292+i*118
        bg.alpha_composite(capsule(i==selected),(x,y))
        if cls:bg.alpha_composite(icon(cls).resize((56,56),Image.Resampling.LANCZOS),(x+48,y+22))
        font.draw(bg,title,x+118,y+56,(255,255,255,255) if i==selected else (228,230,234,255))
    bg.convert('RGB').save(ART/f'{name}.png')

def main():
    THEME.mkdir(exist_ok=True);ART.mkdir(exist_ok=True)
    for selected in (False,True):
        prefix='selected_item' if selected else 'item'
        im=capsule(selected);slices(im,prefix);im.save(ART/f'{prefix}-whole.png')
    for cls in ('ubuntu','windows','uefi','memtest','advanced'):icon(cls).save(THEME/'icons'/f'{cls}.png')
    font=PF2('/usr/share/grub/unicode.pf2')
    preview('preview-layout-ubuntu',[('Ubuntu','ubuntu'),('Windows Boot Manager','windows'),('UEFI Firmware Settings','uefi')],0,font)
    preview('preview-layout-windows',[('Ubuntu','ubuntu'),('Windows Boot Manager','windows'),('UEFI Firmware Settings','uefi')],1,font)
    preview('preview-actual-top',[('Ubuntu','ubuntu'),('Advanced options for Ubuntu',None),('Memory test (memtest86+x64.efi)','memtest')],0,font)
    preview('preview-actual-windows',[('Memory test (memtest86+x64.efi, serial console)','memtest'),('Windows Boot Manager (on /dev/nvme1n1p1)','windows'),('UEFI Firmware Settings',None)],1,font)
    preview('preview-target-top',[('Ubuntu','ubuntu'),('Windows Boot Manager','windows'),('UEFI Firmware Settings','uefi')],0,font)
    preview('preview-target-windows',[('Ubuntu','ubuntu'),('Windows Boot Manager','windows'),('UEFI Firmware Settings','uefi')],1,font)
    ref=Image.open(ROOT/'references/EVA-ROS-approved-reference.png').convert('RGB')
    clean=Image.open(THEME/'background.png').convert('RGB')
    a=np.array(ref,dtype=np.int16);b=np.array(clean,dtype=np.int16)
    outside=np.ones(a.shape[:2],dtype=bool);outside[235:565,235:830]=False
    delta=np.abs(a-b)
    metrics={'font_source_name':font.name,'font_size':16,'canvas':list(CANVAS),
             'outside_menu_mean_absolute_channel_difference':float(delta[outside].mean()),
             'outside_menu_changed_pixel_fraction':float(np.any(delta>0,axis=2)[outside].mean()),
             'note':'AI edit is not pixel-identical outside the menu. Preview is a software layout simulation, not GRUB.'}
    (ART/'render-metadata.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print(json.dumps(metrics,indent=2))

if __name__=='__main__':main()
