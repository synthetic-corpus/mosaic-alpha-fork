from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity as ssim

# 1. Create a fake 100x100 image
data = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
img = Image.fromarray(data)
img.save("test.jpg")

# 2. Try to reload and SSIM it
reloaded = np.array(Image.open("test.jpg"))
try:
    score = ssim(reloaded, reloaded, channel_axis=-1)
    print(f"SSIM Success! Score: {score}")
except Exception as e:
    print(f"SSIM Failed on this hardware: {e}")
