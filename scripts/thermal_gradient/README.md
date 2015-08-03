This script documents the process used to correct the gradient error in the Seek Thermal cameras.

This is based on the technique used by Seek but is a non-faithful reproduction to document the method. It is hoped that it will provide a launching point for alternative clients to work around the hardware error.

The script is tested with GNU Octave 3.8.2, it should also work with Matlab.

Useful invocations:

	% Load the data files
	load('data/floor.mat');
	floor = flipud(fliplr(medfilt2(raw-cal)))(:,3:206+2)
	load('data/face.mat');
	face = flipud(fliplr(medfilt2(raw-cal)))(:,3:206+2)
	
	% Reset the gradient filter
	clear de_gradient
	
	% Prime the low-pass-filter
	for i=1:20 de_gradient(floor); end
	
	% Generate the corrected face
	corrected = de_gradient(face);
