import sys
from PIL import Image
def sheet(paths,out,scale=0.5):
    ims=[Image.open(p) for p in paths]
    w,h=ims[0].size; w2,h2=int(w*scale),int(h*scale)
    s=Image.new("RGB",(w2*len(ims)+8*(len(ims)-1),h2),(40,40,40))
    for i,im in enumerate(ims): s.paste(im.resize((w2,h2),Image.LANCZOS),(i*(w2+8),0))
    s.save(out)
if __name__=="__main__":
    sheet(sys.argv[2:],sys.argv[1],0.5)
