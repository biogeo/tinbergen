function [files, info] = tb_listfiles(base, filepat, dirpat, doRegex)
% Get a list of files in a directory, but do it better than ls or dir
% Usage:
%   [files, info] = tb_listfiles(base, filepat, dirpat, doRegex)
% The return results for ls and dir are often not immediately useful,
% requiring additional filtering steps which are repetitive and can lead to
% bugs. Since Mathworks hasn't seen fit to provide us with a better
% solution, this helper provides a little extra processing on top of dir to
% get a list of files in a directory.
%   All input arguments are optional:
%     base: the path to the directory to list files within. If not supplied
%         or set as empty, defaults to the current working directory.
%     filepat: the pattern to match, e.g., '*.m'. Defaults to '' (match all
%         files). Only files, not directories, are matched.
%     dirpat: Controls whether to recursively list files in subdirectories,
%         and gives the pattern for subdirectories to list. If not
%         supplied, empty, or false, does not list files in subdirectories.
%         Otherwise searches all subdirectories matching the pattern.
%         Supplying true searches all subdirectories (equivalent to '*').
%         As a caveat, if there are links that create cycles in your
%         directory structure, Matlab will recurse until the recursion
%         limit is reached.
%     doRegex: If true, matches file names treating the pattern as a
%         regular expression instead of a glob-style pattern. Default is
%         false (glob-style).
% The returned values are:
%     files: A cell array of strings giving all file names that matched.
%         The paths are relative to the base directory.
%     info: An array of struct such as returned by the dir function for
%         each file.
% (tb_listfiles is a version of a general-purpose helper function packaged
% with Tinbergen.)

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

if ~exist('doRegex', 'var') || isempty(doRegex)
    doRegex = false;
end
if ~exist('dirpat','var') || isempty(dirpat) ...
        || (islogical(dirpat) && ~dirpat)
    dirpat = '';
elseif islogical(dirpat) && dirpat
    dirpat = '*';
end
if ~exist('filepat','var') || isempty(filepat)
    filepat = '';
end
if ~exist('base','var') || isempty(base)
    base = pwd;
end

info = dirmatching(base, filepat, doRegex);
info = info(~[info.isdir]);
files = {info.name}';

if ~isempty(dirpat)
    dirinfo = dirmatching(base, dirpat, doRegex);
    dirinfo = dirinfo([dirinfo.isdir]);
    
    subfiles = cell(size(dirinfo));
    subinfo = cell(size(dirinfo));
    for i=1:numel(dirinfo)
        [subfiles{i}, subinfo{i}] = tb_listfiles(...
            fullfile(base, dirinfo(i).name), filepat, dirpat, doRegex);
        subfiles{i} = fullfile(dirinfo(i).name, subfiles{i});
    end
    files = vertcat(files, subfiles{:});
    info = vertcat(info, subinfo{:});
end


function s = dirmatching(base, pat, doRegex)
if ~doRegex
    % Identify files that match by glob pattern
    s = dir(fullfile(base, pat));
    [~, is] = setdiff({s.name}', {'.';'..'});
    s = s(is);
else
    % Identify files that match by regular expression
    s = dir(base);
    [~, is] = setdiff({s.name}', {'.';'..'});
    s = s(is);
    matches = regexp({s.name}', pat, 'once');
    ismatch = ~cellfun(@isempty, matches);
    s = s(ismatch);
end