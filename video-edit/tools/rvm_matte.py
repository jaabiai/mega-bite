"""Run Robust Video Matting over the main video -> lossless gray8 alpha matte (ffv1)."""
import sys, subprocess, time, numpy as np, onnxruntime as ort
SP, src, out, threads = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
W, H = 1920, 1080
so = ort.SessionOptions(); so.intra_op_num_threads = threads
sess = ort.InferenceSession(f"{SP}/models/rvm_mobilenetv3_fp32.onnx", so, providers=["CPUExecutionProvider"])
dec = subprocess.Popen(["ffmpeg","-v","error","-i",src,"-f","rawvideo","-pix_fmt","rgb24","-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","gray","-s",f"{W}x{H}","-r","30","-i","-","-c:v","ffv1","-level","3",out], stdin=subprocess.PIPE)
st = [np.zeros((1,1,1,1),np.float32) for _ in range(4)]
ratio = np.array([0.4], np.float32)
n = 0; t0 = time.time(); fsz = W*H*3
while True:
    buf = dec.stdout.read(fsz)
    if len(buf) < fsz: break
    img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    x = (img.astype(np.float32)/255).transpose(2,0,1)[None]
    reps = 3 if n == 0 else 1          # let recurrent state settle on frame 0
    for _ in range(reps):
        fgr, pha, *st = sess.run(None, {"src": x, "r1i": st[0], "r2i": st[1], "r3i": st[2], "r4i": st[3], "downsample_ratio": ratio})
    enc.stdin.write((np.clip(pha[0,0],0,1)*255).astype(np.uint8).tobytes())
    n += 1
    if n % 300 == 0: print(n, f"{(time.time()-t0)/n*1000:.0f} ms/frame", flush=True)
enc.stdin.close(); enc.wait(); print("done", n)
