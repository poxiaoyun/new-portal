from PIL import Image
import sys
src=sys.argv[1]; out=sys.argv[2]; n=int(sys.argv[3])
im=Image.open(src)
W,H=im.size
step=(H+n-1)//n
for i in range(n):
    top=i*step; bot=min(H,top+step)
    if bot<=top: break
    c=im.crop((0,top,W,bot))
    sc=1100/W
    c=c.resize((1100,int((bot-top)*sc)), Image.LANCZOS)
    c.save(f"{out}-{i:02d}.png")
    print(out, i, top, bot)
