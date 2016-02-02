#!/usr/bin/env python

'''
Runs MVASE (Multiple View Automatic Segmentation Enhancement).
'''

import os
import sys
import glob
import operator
import numpy as np
from PIL import Image
from scipy import ndimage, misc
from optparse import OptionParser
from functools import reduce

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
                 help = "Comma-separated list of Z rotation angles " "corresponding to the entries given to the --dirs "
                        "flag.")
    p.add_option("--mode", dest = "mode", metavar = "MODE",
                 help = "Mode for combining probabilities from all views. "
                        "    mean  = Arithmetic mean "
                        "    gmean = Geometric mean "
                        "    max   = Maximum probability")

    p.add_option("--write_intermediates", action = "store_true", dest = "write_inter",
                 help = "Enables the writing of rotated intermediate image "
                         "stacks.")
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

def load_stack(pathImgs, xdeg, ydeg, zdeg, nameStr):
    imgs, nImgs = parse_dir_for_images(pathImgs)
    img = img2numpy(os.path.join(pathImgs, imgs[0]))
    nRow, nCol = img.shape
    vol = nRow * nCol * nImgs

    # Print view properties
    print nameStr
    print "========="
    print "{0} angles (X,Y,Z): {1}, {2}, {3}".format(nameStr, xdeg, ydeg, zdeg)
    print "{0} path: {1}".format(nameStr, pathImgs)
    print "{0} stack dimensions: {1} x {2} x {3}".format(nameStr, nCol, nRow,
        nImgs)
    print "{0} volume: {1} voxels".format(nameStr, vol)

    # Check that the volume of the view stack matches that of the reference
    # stack.
    if vol != volRef:
        usage("Volume of view stack does not match that of the reference.")

    # Initialize empty numpy array to load view images into
    print "Initializing NumPy array..."
    stack = np.zeros([nImgs, nRow, nCol], dtype = 'uint16')
    for i in range(nImgs):
        fname = os.path.join(pathImgs, imgs[i])
        imgi = img2numpy(fname)
        nRowi, nColi = imgi.shape
        if (nRowi == nRow) and (nColi == nCol):
            stack[i,:,:] = imgi
            lastGoodSlice = i
            print "Reading {0}, Image {1}: {2}".format(nameStr, i+1, fname)
        else:
            stack[i,:,:] = stack[lastGoodSlice,:,:]
            print "WARNING: Improper dimensions for {0}, Image {1}: {2}".format(nameStr,
                i+1, fname)
            print "WARNING: Replacing with Image {0}".format(lastGoodSlice + 1)
    return stack

def rotate_stack(stack, xdeg, ydeg, zdeg):
    axes = []
    if xdeg == 90 and ydeg == 0 and zdeg == 0:
        axes = [0, 1]
    elif xdeg == 0 and ydeg == 90 and zdeg == 0:
        axes = [0, 2]
    if axes:
        print "Rotating NumPy array..."
        stack = ndimage.interpolation.rotate(stack, -90, axes)
    return stack

def write_stack(arrList, N, dirOut):
    os.makedirs(dirOut)
    for i in range(arrList[N].shape[0]):
        fnameout = os.path.join(dirOut, str(i).zfill(5) + '.tif')
        print "Writing image {0}".format(fnameout)
        misc.imsave(fnameout, arrList[N][i,:,:].astype('uint8'))

if __name__ == '__main__':
    global volRef

    opts, dirRef = parse_args()
    imgsRef, nImgsRef = parse_dir_for_images(dirRef)  

    imgRef = img2numpy(os.path.join(dirRef, imgsRef[0]))
    nRowRef, nColRef = imgRef.shape
    volRef = nRowRef * nColRef * nImgsRef

    if not opts.mode:
        opts.mode = 'mean'

    print "Multiple View Automatic Segmentation Enhancement (MVASE)"
    print "========================================================"
    print ""
    print "Mode: {0}".format(opts.mode)
    print ""
    print "Reference path: {0}".format(dirRef)
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

    # Load all view stacks as Numpy arrays, and append them to a list
    stackList = []
    for N in range(nViews):
        stackList.append(load_stack(views[N], xdeg[N], ydeg[N], zdeg[N], 'View {0}'.format(N+1)))
        stackList[-1] = rotate_stack(stackList[-1], xdeg[N], ydeg[N], zdeg[N])
        if opts.write_inter:
            write_stack(stackList, N, 'view_' + str(N+1).zfill(2))

    # Append reference stack to the list
    stackList.append(load_stack(dirRef, 0, 0, 0, 'Reference'))

    if opts.mode == 'mean':
        print "Calculating the arithmetic mean of all views."
        stackList[-1] = sum(stackList) / len(stackList)
    elif opts.mode == 'gmean':
        print "Calculating the geometric mean of all views."
        stackList[-1] = reduce(operator.mul, stackList, 1) ** (1/len(stackList))
    elif opts.mode == 'max':
        print "Calculating the max of all views."
        stackList[-1] = np.amax(stackList, axis = 0)
    else:
        print "Calculating the arithmetic mean of all views."
        stackList[-1] = sum(stackList) / len(stackList)

    # Save the averaged image stack to disk
    write_stack(stackList, nViews, 'gmean')
