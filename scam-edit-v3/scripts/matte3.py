import sys, subprocess, time, json
import numpy as np, onnxruntime as ort
src, out, model, ds = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
ss = float(sys.argv[5]) if len(sys.argv)>5 else 0.0
dur = float(sys.argv[6]) if len(sys.argv)>6 else 0.0   # 0 = to end
W,H=1920,1080
TM="scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags=accurate_rnd+full_chroma_int,format=rgb24"
cmd=["ffmpeg","-v","error","-ss",str(ss)]+(["-t",str(dur)] if dur>0 else [])+["-i",src,"-vf",TM,"-f","rawvideo","-pix_fmt","rgb24","-"]
dec=subprocess.Popen(cmd,stdout=subprocess.PIPE,bufsize=W*H*3*2)
enc=subprocess.Popen(["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","gray","-s",f"{W}x{H}","-r","30","-i","-","-c:v","ffv1","-level","3","-g","1",out],stdin=subprocess.PIPE)
so=ort.SessionOptions(); so.intra_op_num_threads=4; so.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
sess=ort.InferenceSession(f"/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/assets/models/{model}.onnx",so,providers=["CPUExecutionProvider"])
rec=[np.zeros((1,1,1,1),np.float32) for _ in range(4)]
dr=np.array([ds],np.float32)
n=0; t0=time.time()
while True:
    buf=dec.stdout.read(W*H*3)
    if len(buf)<W*H*3: break
    x=(np.frombuffer(buf,np.uint8).reshape(H,W,3).astype(np.float32)/255.0).transpose(2,0,1)[None]
    fgr,pha,*rec=sess.run(None,{"src":x,"r1i":rec[0],"r2i":rec[1],"r3i":rec[2],"r4i":rec[3],"downsample_ratio":dr})
    a=(np.clip(pha[0,0],0,1)*255+0.5).astype(np.uint8)
    enc.stdin.write(a.tobytes()); n+=1
    if n%100==0: print(f"{n} frames {n/(time.time()-t0):.2f} fps",flush=True)
enc.stdin.close(); enc.wait(); dec.wait()
print(f"DONE {n} frames in {time.time()-t0:.1f}s = {n/(time.time()-t0):.2f} fps",flush=True)
