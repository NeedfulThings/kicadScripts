'''
	A python script to create Nice looking board previews.

	These can be used for textures in MCAD tools to cever up the bland STEP board model.
'''

import sys
import os
import time

import re
import logging
import shutil
import subprocess

import xml.etree.ElementTree as ET


from datetime import datetime
from shutil import copy

try:
    import pcbnew
    from pcbnew import *
except:
    print("PCBNew not found, are you using KiCAD included Python ?")
    exit()
    

greenStandard = {
	'Copper' : ['#E8D959',0.85],
	'CopperInner' : ['#402400',0.80],
	'SolderMask' : ['#1D5D17',0.80],
	'Paste' : ['#9E9E9E',0.95],
	'Silk' : ['#eaebe5',1.00],
	'Edge' : ['#000000',0.20],
	'BackGround' : ['#998060']
}

oshPark = {
	'Copper' : ['#E8D959',0.85],
	'SolderMask' : ['#3a0e97',0.83],
	'Paste' : ['#9E9E9E',0.05],
	'Silk' : ['#d8dae7',1.00],
	'Edge' : ['#000000',0.20],
	'BackGround' : ['#3a0e97']
}

# Black and white colours to be used for texture/bump mapping
bumpMap = {
	'Copper' : ['#666',0.85],
	'SolderMask' : ['#777',0.80],
	'Paste' : ['#FFF',0.95],
	'Silk' : ['#bbb',1.00],
	'Edge' : ['#eeeeee',0.20],
	'BackGround' : ['#555555']
}

colours = greenStandard

def unique_prefix():
	unique_prefix.counter += 1
	return "pref_" + str(unique_prefix.counter)
unique_prefix.counter = 0

def ki2dmil(val):
	return val / 2540

def kiColour(val):
	return (val & 0xFF0000 >> 24) / 255


class svgObject(object):
	# Open an SVG file
	def openSVG(self, filename):
		prefix = unique_prefix() + "_"
		root = ET.parse(filename)
		
		# We have to ensure all Ids in SVG are unique. Let's make it nasty by
		# collecting all ids and doing search & replace
		# Potentially dangerous (can break user text)
		ids = []
		for el in root.getiterator():
			if "id" in el.attrib and el.attrib["id"] != "origin":
				ids.append(el.attrib["id"])
		with open(filename) as f:
			content = f.read()
		for i in ids:
			content = content.replace("#"+i, "#" + prefix + i)

		root = ET.fromstring(content)
		# Remove SVG namespace to ease our lifes and change ids
		for el in root.getiterator():
			if "id" in el.attrib and el.attrib["id"] != "origin":
				el.attrib["id"] = prefix + el.attrib["id"]
			if '}' in str(el.tag):
				el.tag = el.tag.split('}', 1)[1]
		self.svg = root



		

	# Create a Blank SVG
	def createSVG(self):
		self.et = ET.ElementTree(ET.fromstring("""<svg width="29.7002cm" height="21.0007cm" viewBox="0 0 116930 82680 ">
<title>Picutre generated by pcb2svg</title>
<desc>Picture generated by pcb2svg</desc>
<defs> </defs>
</svg>"""))
		self.svg = self.et.getroot()
		defs = self.svg.find('defs')

		newMask = ET.SubElement(defs,'mask', id="boardMask", 
		width="{}".format(ki2dmil(bb.GetWidth())),
		height="{}".format(ki2dmil(bb.GetHeight())),
		x="{}".format(ki2dmil(bb.GetX())),
		y="{}".format(ki2dmil(bb.GetY())))
		if bMirrorMode:
			newMask.attrib['transform'] = "scale(-1,1)"
		
		rect = ET.SubElement(newMask, 'rect',  
		width="{}".format(ki2dmil(bb.GetWidth())),
		height="{}".format(ki2dmil(bb.GetHeight())),
		x="{}".format(ki2dmil(bb.GetX())),
		y="{}".format(ki2dmil(bb.GetY())),
		style="fill:#FFFFFF; fill-opacity:1.0;")

	# Wrap all image data into a group and return that group
	def extractImageAsGroup(self):
		wrapper = ET.Element('g', 
		width="{}".format(ki2dmil(bb.GetWidth())),
		height="{}".format(ki2dmil(bb.GetHeight())),
		x="{}".format(ki2dmil(bb.GetX())),
		y="{}".format(ki2dmil(bb.GetY())),
		style="fill:#000000; fill-opacity:1.0; stroke:#000000; stroke-opacity:1.0;")
		wrapper.extend(self.svg.iter('g'))
		return wrapper

	def reColour(self, transform_function):
		wrapper = self.extractImageAsGroup()
		# Set fill and stroke on all groups
		for group in wrapper.iter():
			svgObject._apply_transform(group, {
				'fill': transform_function,
				'stroke': transform_function,
			})
		self.svg = wrapper

	@staticmethod
	def _apply_transform(node, values):
		try:
			original_style = node.attrib['style']
			for (k,v) in values.items():
				escaped_key = re.escape(k)
				m = re.search(r'\b' + escaped_key + r':(?P<value>[^;]*);', original_style)
				if m:
					transformed_value = v
					original_style = re.sub(
						r'\b' + escaped_key + r':[^;]*;',
						k + ':' + transformed_value + ';',
						original_style)
			node.attrib['style'] = original_style
		except Exception as e: 
			style_string = "stroke:"+ values['fill'] +";"
			node.attrib['style'] = style_string
			pass

	
	
	def addholes(self, holeData):
		holeData.attrib['mask'] =  "url(#boardMask);"
		if bMirrorMode:
			holeData.attrib['transform'] = "scale(-1,1)"
		self.svg.append(holeData)

	def addSvgImageInvert(self, svgImage, colour):
		defs = self.svg.find('defs')
		newMask = ET.SubElement(defs,'mask', id="test-a", 
		width="{}".format(ki2dmil(bb.GetWidth())),
		height="{}".format(ki2dmil(bb.GetHeight())),
		x="{}".format(ki2dmil(bb.GetX())),
		y="{}".format(ki2dmil(bb.GetY())))
		if bMirrorMode:
			newMask.attrib['transform'] = "scale(-1,1)"
		
		
		imageGroup = svgImage.extractImageAsGroup()
		newMask.append(imageGroup)

		rect = ET.SubElement(newMask, 'rect',  
		width="{}".format(ki2dmil(bb.GetWidth())),
		height="{}".format(ki2dmil(bb.GetHeight())),
		x="{}".format(ki2dmil(bb.GetX())),
		y="{}".format(ki2dmil(bb.GetY())),
		style="fill:#FFFFFF; fill-opacity:1.0;")


		#create a rectangle to mask through
		wrapper = ET.SubElement(self.svg, 'g',
		style="fill:{}; fill-opacity:0.75;".format(colour))
		rect = ET.SubElement(wrapper, 'rect', 
		width="{}".format(ki2dmil(bb.GetWidth())),
		height="{}".format(ki2dmil(bb.GetHeight())),
		x="{}".format(ki2dmil(bb.GetX())),
		y="{}".format(ki2dmil(bb.GetY())))


		wrapper.attrib['mask'] =  "url(#test-a);"

		if bMirrorMode:
			wrapper.attrib['transform'] = "scale(-1,1)"

	def addSvgImage(self, svgImage, colour):
		
		#create a rectangle to mask through
		wrapper = ET.SubElement(self.svg, 'g',
		style="fill:{}; fill-opacity:1.0;".format(colour))
		
		imageGroup = svgImage.extractImageAsGroup()
		wrapper.append(imageGroup)

		for group in wrapper.iter():
			svgObject._apply_transform(group, {
				'fill': colour,
				'stroke': colour,
			})
		if bMirrorMode:
			wrapper.attrib['transform'] = "scale(-1,1)"



	def write(self, filename):
		with open(filename, 'wb') as output_file:
			self.et.write(output_file)




def get_hole_mask(board):
	mask = ET.Element( "g", id="hole-mask")
	container = ET.SubElement(mask, "g", style="opacity:0.8;")

	# Print all Drills
	for mod in board.GetModules():
		for pad in mod.Pads():
			pos = pad.GetPosition()
			pos_x = ki2dmil(pos.x)
			pos_y = ki2dmil(pos.y)
			size = ki2dmil(min(pad.GetDrillSize())) # Tracks will fail with Get Drill Value

			length = 1
			if pad.GetDrillSize()[0] != pad.GetDrillSize()[1]:
				length = ki2dmil(max(pad.GetDrillSize()) - min(pad.GetDrillSize()))

			#length = 200
			stroke = size
			print(str(size) + " " +  str(length) + " " + str(pad.GetOrientation()))
			
			points = "{} {} {} {}".format(0, -length / 2, 0, length / 2)
			if pad.GetDrillSize()[0] >= pad.GetDrillSize()[1]:
				points = "{} {} {} {}".format(length / 2, 0, -length / 2, 0)
			el = ET.SubElement(container, "polyline")
			el.attrib["stroke-linecap"] = "round"
			el.attrib["stroke"] = "black"
			el.attrib["stroke-width"] = str(stroke)
			el.attrib["points"] = points
			el.attrib["transform"] = "translate({} {})".format(
				pos_x, pos_y)	
			el.attrib["transform"] += "rotate({})".format(
				-pad.GetOrientation()/10)	


	# Print all Vias
	for track in board.GetTracks():
		try:
			pos = track.GetPosition()
			pos_x = ki2dmil(pos.x)
			pos_y = ki2dmil(pos.y)
			size = ki2dmil(track.GetDrillValue()) # Tracks will fail with Get Drill Value
		except:
			continue
		stroke = size
		length = 1
		points = "{} {} {} {}".format(0, -length / 2, 0, length / 2)
		el = ET.SubElement(container, "polyline")
		el.attrib["stroke-linecap"] = "round"
		el.attrib["stroke"] = "black"
		el.attrib["stroke-width"] = str(stroke)
		el.attrib["points"] = points
		el.attrib["transform"] = "translate({} {})".format(
			pos_x, pos_y)
		
		

	return mask


def plot_layer(layer_info):
	pctl.SetLayer(layer_info[0])
	pctl.OpenPlotfile("", PLOT_FORMAT_SVG, "")
	pctl.PlotLayer()
	time.sleep(0.01)
	pctl.ClosePlot()
	return pctl.GetPlotFileName()


def render(plot_plan, output_filename):
	canvas = svgObject()
	canvas.createSVG()
	for layer_info in plot_plan:

		print(layer_info)
		plot_layer(layer_info)
		
		svgData = svgObject()
		svgData.openSVG(pctl.GetPlotFileName())

		if layer_info[1] == "Invert":
			canvas.addSvgImageInvert(svgData, colours[layer_info[2]][0]);
		else:
			canvas.addSvgImage(svgData,colours[layer_info[2]][0])

	# Drills are seperate from Board layers. Need to be handled differently
	canvas.addholes(get_hole_mask(board))
	
	print('Merging layers...')
	final_svg = os.path.join(temp_dir, project_name + '-merged.svg')
	canvas.write(final_svg)

	print('Rasterizing...')
	final_png = os.path.join(output_directory, output_filename)

	# x0,y0 are bottom LEFT corner
	dpi = 1200

	scale = 3.779
	mmscale = 1000000.0

	yMax = 210070000

	x0 = (bb.GetX() / mmscale) * scale
	y0 = ((yMax - (bb.GetY() + bb.GetHeight())) / mmscale) * scale
	x1 = ((bb.GetX() + bb.GetWidth()) / mmscale) * scale
	y1 = ((yMax - (bb.GetY())) / mmscale) * scale

	#x0 -= 10
	#y0 -= 10
	#x1 += 10
	#y1 += 10

	if bMirrorMode:
		x0 = -x0
		x1 = -x1

	# Hack your path to add a bunch of plausible locations for inkscape
	pathlist = [
		'C:\\Program Files\\Inkscape',
		'C:\\Program Files (x86)\\Inkscape',
		'/usr/local/bin',
		'/usr/bin/'
	]
	os.environ["PATH"] += os.pathsep + os.pathsep.join(pathlist)
	#try:
	print(os.environ["PATH"])

	version = subprocess.check_output(['inkscape', '--version'], stderr=None).split()
	if len(version) > 1 and version[1].decode("utf-8").startswith("0."):
		print("Detected Inkscape version < 1.0")
		subprocess.check_call([
			'inkscape',
			'--export-area={}:{}:{}:{}'.format(x0,y0,x1,y1),
			'--export-dpi={}'.format(dpi),
			'--export-png', final_png,
			'--export-background', colours['BackGround'][0],
			final_svg,
		])
	else:
		print("Detected Inkscape version 1.0+")
		subprocess.check_call([
			'inkscape',
			'--export-area={}:{}:{}:{}'.format(x0,y0,x1,y1),
			'--export-dpi={}'.format(dpi),
			'--export-type=png',
			'--export-filename={}'.format(final_png),
			'--export-background', colours['BackGround'][0],
			final_svg,
		])
	#except Exception as e:
#		print("Inkscape is most likely not in your path")



#Slight hack for etree. to remove 'ns0:' from output
ET.register_namespace('', "http://www.w3.org/2000/svg")


filename=sys.argv[1]
project_name = os.path.splitext(os.path.split(filename)[1])[0]
project_path = os.path.abspath(os.path.split(filename)[0])

output_directory = os.path.join(project_path,'plot')

temp_dir = os.path.join(output_directory, 'temp')
shutil.rmtree(temp_dir, ignore_errors=True)
try:
	os.makedirs(temp_dir)
except:
	print('folder exists')

today = datetime.now().strftime('%Y%m%d_%H%M%S')

board = LoadBoard(filename)

pctl = PLOT_CONTROLLER(board)

popt = pctl.GetPlotOptions()

popt.SetOutputDirectory(temp_dir)

# Set some important plot options:
popt.SetPlotFrameRef(False)
popt.SetLineWidth(FromMM(0.35))

popt.SetAutoScale(False)
popt.SetScale(1)
popt.SetMirror(False)
popt.SetUseGerberAttributes(False)
popt.SetExcludeEdgeLayer(True);
popt.SetScale(1)
popt.SetUseAuxOrigin(False)
popt.SetNegative(False)
popt.SetPlotReference(True)
popt.SetPlotValue(True)
popt.SetPlotInvisibleText(False)
popt.SetDrillMarksType(PCB_PLOT_PARAMS.FULL_DRILL_SHAPE)
pctl.SetColorMode(False)

# This by gerbers only (also the name is truly horrid!)
popt.SetSubtractMaskFromSilk(False) #remove solder mask from silk to be sure there is no silk on pads

bb = board.GetBoardEdgesBoundingBox()


# Plot Various layer to generate Front View
bMirrorMode = False
plot_plan = [
	( In1_Cu, "",'CopperInner' ),
	( F_Cu, "",'Copper' ),
	( F_Mask, 'Invert','SolderMask' ),
	( F_Paste, "" , 'Paste' ),
	( F_SilkS, "" ,'Silk' ),
	( Edge_Cuts, ""  ,'Edge' ),
]

render(plot_plan, project_name + '-Front.png')


# Fli layers and generate Back View
bMirrorMode = True
plot_plan = [
	( In2_Cu, "",'CopperInner' ),
	( B_Cu, "",'Copper' ),
	( B_Mask, "Invert" ,'SolderMask' ),
	( B_Paste, "" , 'Paste' ),
	( B_SilkS, "" ,'Silk' ),
	( Edge_Cuts, ""  ,'Edge' ),
]
render(plot_plan, project_name + '-Back.png')

# Experiments to render out various texture maps
#colours = bumpMap
#plot_plan = [
#	( F_Cu, "",'Copper' ),
#	( F_Mask, 'Invert','SolderMask' ),
#	( F_Paste, "" , 'Paste' ),
#	( F_SilkS, "" ,'Silk' ),
#	( Edge_Cuts, ""  ,'Edge' ),
#]
#render(plot_plan, project_name + '-Bump.png')

shutil.rmtree(temp_dir, ignore_errors=True)
