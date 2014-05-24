function proj = tb_load_proj(projFile)
% Load data from a Tinbergen project file
% Usage:
%   proj = tb_load_proj(projFile)
% Reads the data in the Tinbergen project file (.tbproj) identified by
% projFile and returns a struct with fields:
%   projectRoot: The value of the 'project-root' line
%   videoRoot: The value of the 'video-root' line
%   ethogramFile: The value of the 'ethogram-file' line
%   observerNames: A list of the 'name' values for each 'observer' line
%   observerCodes: A list of the 'code' values for each 'observer' line
% See tb_loadall for a simple way to load the project file, ethogram file,
% and all observation files with one call.

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

lines = tb_readlines(projFile);

getScalarData = @(entry)lines.value{strcmp(lines.entry, entry)};
getListData = @(entry)lines.value(strcmp(lines.entry, entry));

proj = struct;
proj.projectRoot = getScalarData('project-root');
proj.videoRoot = getScalarData('video-root');
proj.ethogramFile = getScalarData('ethogram-file');

obsData = tb_parse_keyvals(getListData('observer'));
proj.observerNames = tb_kvget(obsData, 'name', 'listres', 'scalarval');
proj.observerCodes = tb_kvget(obsData, 'code', 'listres', 'scalarval');
