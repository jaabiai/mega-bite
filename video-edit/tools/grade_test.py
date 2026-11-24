"""Grade candidates on real frames of the Equal AI main video: tiles + face / skin / background measurements."""
import sys, json, subprocess, numpy as np, cv2
sys.path.insert(0, '/home/user/mega-bite/video-edit/lib')
from grade_moody import MoodyGrader
import mist as MS
SP = '/tmp/claude-0/-home-user-mega-bite/45115ae6-2f29-576b-94d3-cacaedb79616/scratchpad'
FT = json.load(open('/home/user/mega-bite/video-edit/projects/equal-ai-assistant/face_track.json'))
FW, FH, W, H = 2880, 1620, 1920, 1080
def raw(t):
    p = subprocess.run(['ffmpeg','-v','error','-ss',f'{t:.3f}','-i',f'{SP}/src12/Main.mp4','-frames:v','1','-vf',f'scale={FW}:{FH}:flags=lanczos',
                        '-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True)
    return np.frombuffer(p.stdout,np.uint8).reshape(FH,FW,3)
def crop(src, t, zoom, tx, ty=0.44):
    fx=float(np.interp(t,FT['t'],FT['x'])); fy=float(np.interp(t,FT['t'],FT['y']))
    s=max(W/FW,H/FH)*zoom; x0=min(max(fx*FW*s-tx*W,0),FW*s-W); y0=min(max(fy*FH*s-ty*H,0),FH*s-H)
    M=np.array([[s,0,-x0],[0,s,-y0]],np.float32)
    fr=cv2.warpAffine(src,M,(W,H),flags=cv2.INTER_AREA).astype(np.float32)/255
    return fr,((fx*FW*s-x0)/W,(fy*FH*s-y0)/H)
def stats(img, fx, fy):
    L=img@np.array([0.2126,0.7152,0.0722],np.float32)
    x,y=int(fx*W),int(fy*H)
    face=img[y-60:y+90, x-80:x+80]; fL=float((face@np.array([0.2126,0.7152,0.0722])).mean())
    hsv=cv2.cvtColor(np.clip(face,0,1).astype(np.float32),cv2.COLOR_RGB2HSV)
    body=img[int(H*0.80):, int(W*0.40):int(W*0.80)]; bL=float((body@np.array([0.2126,0.7152,0.0722])).mean())
    bg=img[:, :int(W*0.30)]; gL=float((bg@np.array([0.2126,0.7152,0.0722])).mean())
    dark=float((L<0.06).mean())
    return f"face L {fL:.2f} sat {hsv[...,1].mean():.2f} hue {hsv[...,0].mean():.0f} | body L {bL:.2f} | left L {gL:.2f} | <6% {dark*100:.0f}%"
if __name__=='__main__':
    cands=json.load(open(sys.argv[1])); times=[(float(a),float(b),float(c)) for a,b,c in (x.split(':') for x in sys.argv[2].split(','))]
    out=sys.argv[3]
    rows=[]
    srcs={t:raw(t) for t,_,_ in times}
    for name,c in cands.items():
        g=MoodyGrader(W,H,c['grade'])
        sh=MS.side_shade(W,H,False,strength=c.get('shade',0.55))
        tiles=[]
        for t,z,tx in times:
            fr,(fx,fy)=crop(srcs[t],t,z,tx)
            if name=='RAW': o=fr
            else: o=np.clip(g(fr,face=(fx,fy-0.02,0.20,0.30),center=(fx,0.5))*sh,0,1)
            print(name,t,stats(o,fx,fy))
            im=cv2.cvtColor((o*255).astype(np.uint8),cv2.COLOR_RGB2BGR)
            im=cv2.resize(im,(640,360),interpolation=cv2.INTER_AREA)
            cv2.putText(im,f"{name} {t}",(10,30),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,255),2)
            tiles.append(im)
        rows.append(np.hstack(tiles))
    cv2.imwrite(out,np.vstack(rows),[cv2.IMWRITE_JPEG_QUALITY,90])
