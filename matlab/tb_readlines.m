function lineTable = tb_readlines(filename)
% Utility for Tinbergen functions
% Usage:
%   lineTable = tb_readlines(filename)
% Opens the specified file containing Tinbergen data. Each line contains
% data as the string '<type>: <value>', or is a comment starting with #.
% Returns a struct with fields 'type' and 'value' giving the data from each
% line.

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

% Read all data
contents = fileread(filename);
lines = textscan(contents, '%s', ...
    'Delimiter', sprintf('\n'), 'MultipleDelimsAsOne', true);
lines = lines{1};
lines = strtrim(lines);
isComment = strncmp(lines, '#', 1);
lines = lines(~isComment);

[lineHead, lineTail] = strtok(lines, ':');
lineTail = cellfun(@(s)s(2:end), lineTail, 'UniformOutput', false);
lineTail = strtrim(lineTail);

lineTable = struct('entry', {lineHead}, 'value', {lineTail});
