import matplotlib.image as mpimg
import matplotlib.pyplot as plt


def image(path):
    im = mpimg.imread(path)
    height, width = im.shape[:2]
    plt.figure(figsize=(height // 100, width // 100))
    plt.imshow(im)
