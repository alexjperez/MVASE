#!/usr/bin/env python

'''
Runs MVASE (Multiple View Automatic Segmentation Enhancement).
'''

import os
import sys
import glob
import numpy as np
from PIL import Image
from scipy import ndimage, misc
from optparse import OptionParser

def parse_args():
    global p
    p = OptionParser(usage = "%prog [options] /path/to/unrotated_data")
    p.add_option("--dirs", dest = "dirs", metavar = "DIRECTORIES",
                 help = "Comma-separated list of all directories containing "
                        "rotated segmentation stacks.")
    p.add_option("--x", dest = "xangles", metavar = "ANGLES",
                 help = "Comma-separated list of X rotation angles "
                        "corresponding to the entries given to the --dirs "
                        "flag.")
    p.add_option("--y", dest = "yangles", metavar = "ANGLES",
                 help = "Comma-separated list of Y rotation angles "
                        "corresponding to the entries given to the --dirs " 
                        "flag.")
    p.add_option("--z", dest = "zangles", metavar = "ANGLES",
                 help = "Comma-separated list of Z rotation angles "
                        "corresponding to the entries given to the --dirs "
                        "flag.")
    (opts, args) = p.parse_args()
    dirRef = check_args(args)
    return opts, dirRef

def check_args(args):
    if len(args) is not 1:
        usage("Improper number of arguments.")
    dirRef = args[0]
    if not os.path.isdir(dirRef):
        usage("{0} is not a valid directory".format(dirRef))
    return dirRef

# Print error messages and exit
def usage(errstr):
    print ""
    print "ERROR: {0}".format(errstr)
    print ""
    p.print_help()
    print ""
    exit(1)

def parse_dir_for_images(dir):
    imgs = sorted(glob.glob1(dir, '*.tif'))
    if not imgs:
        imgs = sorted(glob.glob1(dir, '*.png'))
    if not imgs:
        usage("{0} does not contain valid images (.tif, .png)".format(dir))
    nImgs = len(imgs)
    return imgs, nImgs

def img2numpy(fname):
    img = ndimage.imread(fname)
    if not img.shape:
        img = Image.open(fname)
        dim1, dim2 = img.size
        img = np.asarray(img.getdata())
        if img.shape[1] > 1:
            img = img[:,0]
        img = img.reshape(dim1, dim2)
    return img

if __name__ == '__main__':
    opts, dirRef = parse_args()
    imgsRef, nImgsRef = parse_dir_for_images(dirRef)  

    imgRef = img2numpy(os.path.join(dirRef, imgsRef[0]))
    nRowRef, nColRef = imgRef.shape
    volRef = nRowRef * nColRef * nImgsRef

    print "Reference: 0,0,0 deg, Path: {0}".format(dirRef)
    print "Reference stack dimensions: {0} x {1} x {2}".format(nColRef, nRowRef,
        nImgsRef)
    print "Reference stack volume: {0} voxels".format(volRef)
    print ""

    views = opts.dirs.split(',')
    nViews = len(views)

    xdeg = [int(x) for x in opts.xangles.split(',')]
    nx = len(xdeg)
 
    ydeg = [int(x) for x in opts.yangles.split(',')]
    ny = len(ydeg)

    zdeg = [int(x) for x in opts.zangles.split(',')]
    nz = len(zdeg)

    if not nx == ny == nz == nViews:
        usage("Mismatching numbers of angles and paths.")    

    # Print run info at the beginning
    for N in range(nViews):
        imgsView, nImgsView = parse_dir_for_images(views[N])
        imgView = img2numpy(os.path.join(views[N], imgsView[0]))
        nRowView, nColView = imgView.shape
        volView = nRowView * nColView * nImgsView
         
        # Print view properties
        print "View {0}".format(N+1)
        print "======"
        print "View {0} angles (X,Y,Z): {1}, {2}, {3}".format(N+1, xdeg[N],
            ydeg[N], zdeg[N])
        print "View {0} path: {1}".format(N+1, views[N])
        print "View {0} stack dimensions: {1} x {2} x {3}".format(N+1, nColView,
            nRowView, nImgsView)
        print "View {0} volume: {1} voxels".format(N+1, volView)

        # Check that the volume of the view stack matches that of the reference
        # stack.
        if volView != volRef:
            usage("Volume of view stack does not match that of the reference.")
  
        # Initialize empty numpy array to load view images into
        print "Initializing NumPy array..."
        stackView = np.zeros([nImgsView, nRowView, nColView], dtype = 'uint8')
        for i in range(nImgsView):
            fname = os.path.join(views[N], imgsView[i])
            imgi = img2numpy(fname)
            nRowi, nColi = imgi.shape
            if (nRowi == nRowView) and (nColi == nColView):
                stackView[i,:,:] = imgi
                lastGoodSlice = i
                print "Reading View {0}, Image {1}: {2}".format(N+1, i+1, fname)
            else:
                stackView[i,:,:] = stackView[lastGoodSlice,:,:]
                print "WARNING: Improper dimensions for View {0}, Image {1}: {2}".format(N+1,
                    i+1, fname)
                print "WARNING: Replacing with Image {0}".format(lastGoodSlice + 1)

        axes = [] 
        if xdeg[N] == 90 and ydeg[N] == 0:
            axes = [0, 1]
        elif xdeg[N] == 0 and ydeg[N] == 90:
            axes = [0, 2]

        if axes:
            print "Rotating NumPy array..."
            stackView = ndimage.interpolation.rotate(stackView, -90, axes)

        for i in range(100):
            misc.imsave(str(i).zfill(3) + '.png', stackView[i,:,:])
 
        print ""
 
