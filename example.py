from api import Detector
from PIL import Image

# Initialize detector
detector = Detector(model_name='rapid',
                    weights_path='./weights/pL1_MWHB1024_Mar11_4000.ckpt')

# A simple example to run on a single image and plt.imshow() it
image = detector.detect_one(img_path='./images/exhibition.jpg',
                    input_size=1024, conf_thres=0.3,
                    visualize=False, return_img=True)

im = Image.fromarray(image)
im.save("output.jpg")
