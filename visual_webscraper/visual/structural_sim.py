
# USAGE
# python compare.py

# import the necessary packages
from skimage.measure import compare_ssim
import matplotlib.pyplot as plt
import numpy as np
import cv2


def mse(imageA, imageB):
    # the 'Mean Squared Error' between the two images is the
    # sum of the squared difference between the two images;
    # NOTE: the two images must have the same dimension
    err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
    err /= float(imageA.shape[0] * imageA.shape[1])

    # return the MSE, the lower the error, the more "similar"
    # the two images are
    return err


def compare_images(imageA, imageB, title):
    # compute the mean squared error and structural similarity
    # index for the images
    m = mse(imageA, imageB)
    s = compare_ssim(imageA, imageB)
    return s
    # # setup the figure
    # fig = plt.figure(title)
    # plt.suptitle("MSE: %.2f, SSIM: %.2f" % (m, s))
    #
    # # show first image
    # ax = fig.add_subplot(1, 2, 1)
    # plt.imshow(imageA, cmap = plt.cm.gray)
    # plt.axis("off")
    #
    # # show the second image
    # ax = fig.add_subplot(1, 2, 2)
    # plt.imshow(imageB, cmap = plt.cm.gray)
    # plt.axis("off")
    #
    # # show the images
    # plt.show()

# load the images -- the original, the original + contrast,
# and the original + photoshop

image_dir = '/home/ross/Downloads/python-compare-two-images/images'
from os.path import join as join_path


original_fp = join_path(image_dir, "jp_gates_original.png")
original = cv2.imread(original_fp)
contrast = cv2.imread(
    join_path(image_dir, "jp_gates_contrast.png")
)
shopped = cv2.imread(
    join_path(image_dir, "jp_gates_photoshopped.png")
)

# convert the images to grayscale

original = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
contrast = cv2.cvtColor(contrast, cv2.COLOR_BGR2GRAY)
shopped = cv2.cvtColor(shopped, cv2.COLOR_BGR2GRAY)

# initialize the figure
fig = plt.figure("Images")
images = ("Original", original), ("Contrast", contrast), ("Photoshopped", shopped)

# # loop over the images
# for (i, (name, image)) in enumerate(images):
#     # show the image
#     ax = fig.add_subplot(1, 3, i + 1)
#     ax.set_title(name)
#     plt.imshow(image, cmap = plt.cm.gray)
#     plt.axis("off")
#
# # show the figure
# plt.show()

#from PIL import Image
#orig = Image.open(original_fp).convert('L')

# compare the images
s1 = compare_ssim(original, original) #, "Original vs. Original")
s2 = compare_ssim(original, contrast) #, "Original vs. Contrast")
s3 = compare_ssim(original, shopped) #, "Original vs. Photoshopped")


import pdb; pdb.set_trace()
