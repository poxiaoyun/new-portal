from PIL import Image
import sys
a,b,out,n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
A,B = Image.open(a), Image.open(b)
H = max(A.size[1], B.size[1])
step = (H + n - 1)//n
for i in range(n):
    top = i*step; bot = min(H, top+step)
    if bot <= top: break
    canvas = Image.new('RGB', (A.size[0]+B.size[0]+2, bot-top), (255,0,255))
    for img, x in ((A,0),(B,A.size[0]+2)):
        seg = img.crop((0, top, img.size[0], min(img.size[1], bot)))
        canvas.paste(seg, (x, 0))
    sc = min(1.0, 1200/canvas.size[0])
    canvas = canvas.resize((int(canvas.size[0]*sc), int(canvas.size[1]*sc)), Image.LANCZOS)
    canvas.save(f'{out}-{i:02d}.png')
print('ok')
