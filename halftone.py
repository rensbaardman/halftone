import sys
import numpy as np
import math
import svgwrite
from PIL import Image, ImageDraw


def ensure_RGB(image):
	'''
	ensure RGB, even if original mode is RGBA
	'''

	if image.mode == 'RGB':
		return image
	elif image.mode in ['RGBA', 'L']:
		return image.convert("RGB")
	else:
		print('expected image mode RGB(A), got', image.mode)
		raise


def load_pixels(filepath):
	image = Image.open(filepath)
	image = ensure_RGB(image)

	# loading from tobytes() is faster than
	# loading from getdata() (see https://stackoverflow.com/a/42036542/7770056)
	pixels = np.fromstring(image.tobytes(), dtype=np.uint8)
	pixels = pixels.reshape((image.size[1], image.size[0], 3))
	
	return pixels


def image_to_halftone_matrix(pixels, blocksize):

	width = pixels.shape[1]
	height = pixels.shape[0]

	halftone = np.empty((width // blocksize, height // blocksize))

	# scan rows
	for j in range(0, height // blocksize):

		y_begin = j * blocksize
		y_end = (j + 1) * blocksize

		# scan columns within row
		for i in range(0, width // blocksize):
			x_begin = i * blocksize
			x_end = (i + 1) * blocksize

			# block: a blocksize*blocksize numpy (sub)matrix
			# with rgb values (3-item lists)
			block = pixels[y_begin:y_end, x_begin:x_end]

			# monochrome / luminosity average (over all RGB colors)
			avg = np.average(block)
			halftone[i, j] = 1 - avg / 256

	return halftone


def curve(x):
	'''
	this is nice to add contrast
	TODO: experiment / make variable
	'''
	
	# x is between 0 and 1

	# this adds contrast, bit hacky but works nicely
	return math.sin(math.pi * (x - 0.5)) / 2 + 0.5

def halftone_to_png(halftone, output_size, blocksize, filename):

	# scaling_factor is for anti-aliasing (see https://stackoverflow.com/questions/14350645/is-there-an-antialiasing-method-for-python-pil)
	scaling_factor = 4

	size = (output_size[0] * scaling_factor, output_size[1] * scaling_factor)

	output = Image.new('RGBA', size)
	draw = ImageDraw.Draw(output)
	
	# clear canvas by filling with white
	# draw.rectangle([(0,0), size], fill=(255, 255, 255))

	# darkness_factor:
	# 	0: if completely black, dot is inscribed circle of block
	#	1: if completely black, dot is circumcircle of block
	darkness_factor = 0
	# use pythagoras: the radius of the circumcircle is sqrt(2) * blocksize
	base_radius = (0.5 * blocksize + darkness_factor * (0.5 * (2 ** 0.5) - 0.5) * blocksize) * scaling_factor

	for j in range(0, halftone.shape[1]):

		for i in range(0, halftone.shape[0]):

			x = (i + 0.5) * blocksize * scaling_factor
			y = (j + 0.5) * blocksize * scaling_factor

			intensity = halftone[i, j]

			# TODO: consider some contrast curve here
			# area scales quadratically with radius
			radius = base_radius * (curve(intensity) ** 0.5)

			draw.ellipse(((x - radius, y - radius), (x + radius, y + radius)), fill=(0,0,0))

	filename += '.png'
	output.resize(output_size, resample=Image.BILINEAR).save(filename, 'png')


def get_filename(filepath, blocksize):
	return 'out/' + '.'.join(filepath.split('.')[:-1]) + '-' + str(blocksize)


def halftone_to_svg(halftone, output_size, blocksize, filename):

	filename += '.svg'

	drawing = svgwrite.Drawing(filename, size = output_size)
	group = drawing.add(drawing.g())

	# darkness_factor:
	# 	0: if completely black, dot is inscribed circle of block
	#	1: if completely black, dot is circumcircle of block
	darkness_factor = 0
	# use pythagoras: the radius of the circumcircle is sqrt(2) * blocksize
	base_radius = (0.5 * blocksize + darkness_factor * (0.5 * (2 ** 0.5) - 0.5) * blocksize)

	for j in range(0, halftone.shape[1]):

		for i in range(0, halftone.shape[0]):

			x = (i + 0.5) * blocksize
			y = (j + 0.5) * blocksize

			intensity = halftone[i, j]

			# area scales quadratically with radius
			radius = base_radius * (curve(intensity) ** 0.5)

			group.add(drawing.circle(center = (x, y), r = radius, fill = svgwrite.rgb(0, 0, 0, '%')))

	drawing.save()




def main():

	try:
		filepath = sys.argv[1]
	except IndexError:
		raise 'specify a path to the file you want to convert'
	try:
		blocksize = int(sys.argv[2])
	except IndexError:
		print('no blocksize specified, assuming default blocksize 8')
		blocksize = 8

	pixels = load_pixels(filepath)
	halftone = image_to_halftone_matrix(pixels, blocksize)

	filename = get_filename(filepath, blocksize)

	halftone_to_png(halftone, (pixels.shape[1], pixels.shape[0]), blocksize, filename)
	halftone_to_svg(halftone, (pixels.shape[1], pixels.shape[0]), blocksize, filename)

main()


# TODO:
# - option to scale up before applying it (gives better results)
# - option to adjust contrast curves
# - option to go to different format
# - toggle alpha/white in PNG
# - give a color
# - have smarter way to infer blocksize
# - rethink 'darkness factor'
# - different shapes
# - more than 1 color? (maybe not)
# - under an angle
# - hexagonal grid
# - more types: with lines, ... ?
# - what to do with the 'edge'?
# - have to consider dithering?
# - (do more research into halftoning algorithms - possibly also 'overlapping submatrices/blocks?')
# - optimize / profile
# - opts parsing
# - make into a library/module
# - make into a standalone executable
# - consider a GUI
# - package in an Illustrator plugin
# - more options: scaling factor & scaling algorithm; SVG optimizations
# - check are.na channel for inspiration: also that one where you both have black dots, and white dots! How is that possible?
# - do some cool things with animating: different blocksizes, different scaling factors / algorithms, changing angle, changing form, etc. (also good for researching darkness factor, contrast curve etc.)
# - non-integer block sizes?