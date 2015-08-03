function fixed = de_gradient(image, gradient_limit)
	width = 206;  % width
	height = 156; % height

	persistent offset = zeros(height,width);

	% Take the mean of each 4x4 block of pixels
	% Then the mean of each 4x4 block of the previous mean (16x16 overall)
	% Dropping the edges to keep full blocks
	sm_off_x = ceil(rem(width,16)/2);
	sm_off_y = ceil(rem(height,16)/2);
	small_mean = blockproc(image(sm_off_y+1:height-sm_off_y, sm_off_x+1:width-sm_off_x), [4,4], @mean2);
	big_mean = blockproc(small_mean, [4,4], @mean2);

	% Find the biggest variation between each small block in a big block
	range2 = @(block) range(block(:));
	max_range = max(blockproc(small_mean, [4,4], range2)(:));
	max_range

	if (max_range < gradient_limit)
		% Interpolate the averaged points out to cover the full image
		[Xi,Yi] = meshgrid(1:1/16:size(big_mean,1), 1:1/16:size(big_mean,2));
		temp_buf = zeros(height, width);
		offx = ceil((height - size(Xi,2))/2);
		offy = ceil((width  - size(Xi,1))/2);

		% Fill the center of the image with the interpolated points
		% Each edge is is in by the discarded big and half the 16 pixel block size
		temp_buf(offx:height-offx, offy:width-offy) = interp2(big_mean, Yi, Xi)';

		% Stretch the edges out
		temp_buf(1:offx,:)             = repmat(temp_buf(offx,:),offx,1);
		temp_buf(height-offx:height,:) = repmat(temp_buf(height-offx,:),offx+1,1);
		temp_buf(:,1:offy)             = repmat(temp_buf(:,offy),1,offy);
		temp_buf(:,width-offy:width)   = repmat(temp_buf(:,width-offy),1,offy+1);

		offset = (temp_buf + 7*offset)/8;
	end

	fixed = image - offset;
