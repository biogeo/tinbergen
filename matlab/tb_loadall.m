function proj = tb_loadall(projFile, varargin)
% Read all of the data for a Tinbergen project
% Usage:
%   proj = tb_loadall(projFile)
%    projFile is the path to the Tinbergen project file. If the full
%      Tinbergen directory structure is still intact (aside from video-root
%      which is not required), all of the data for the project is loaded.
%    proj is a struct with fields:
%     projectRoot
%       The value of 'project-root' in the project file, the directory
%       relative to projFile where observations are stored
%     videoRoot
%       The value of 'video-root' in the project file, the directory
%       relative to projFile where videos were stored during coding
%     ethogramFile
%       The value of 'ethogram-file' in the project file, the filename of
%       the project's ethogram file
%     observerNames
%       An N-by-1 list of observers' names from the ethogram file
%     observerCodes
%       An N-by-1 list of observers' short codes from the ethogram file
%     ethogramName
%       The value of 'name' in the ethogram file
%     behaviors
%       An M-by-1 list of behavior names
%     behaviorKinds
%       An M-by-1 list of corresponding behavior kinds ('moment', 'binary',
%       'state', or 'variable')
%     behaviorValues
%       An M-by-1 list of lists of behavior values (only used for state
%       behaviors)
%     obs: a struct array of observation sets, with fields:
%         observer
%           The name of the observer that coded these observations
%         source
%           The file name of the coded movie
%         behav: an M-by-1 struct array of observations for behaviors:
%             name
%               The name of a behavior in the ethogram
%             kind
%               The kind of the behavior
%             time
%               A P-by-1 vector of observation timestamps for the behavior
%             value
%               A P-by-1 list of observed values of the behavior at each
%               time. By default, this is a logical array for 'binary'
%               behaviors, and a cell array of strings for all other
%               behaviors, but this behavior can be customized by supplying
%               additional parameters (see below).
%   proj = tb_loadall(projFile, 'Param', value, ...)
%     Valid parameter-value pairs (with valid values in [brackets] and
%     default values starred*) are:
%       'Converters' [ P-by-2 cell array | {}* ]
%         Converters(:,1) is a list of behavior names in the ethogram, and
%         Converters(:,2) is a list of function handles for converting the
%         corresponding behaviors' values. Each function handle must accept
%         a cell array of strings and return an array of the same size. For
%         each behavior with a converter, proj.obs(i).behav(j).value is
%         replaced by the result of its converter function. If no converter
%         is supplied but the behavior kind is 'binary', the values may be
%         converted to logical as specifed by the 'ConvertBinary' parameter
%         (below).
%         Example:
%           If there is a behavior 'Count' which always takes numeric
%           values, the values can be converted to Matlab doubles with the
%           call
%             proj = tb_loadall(projFile, {'Count', @str2double})
%         See `help tb_obs_convert` for more information.
%       'ConvertBinary' [ true* | false ]
%         Whether to automatically convert 'binary' behavior values to
%         logicals. When true, is equivalent to supplying the function
%           @(s)strcmpi(s,'True')
%         as a converter for each 'binary' behavior.

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

p = inputParser;
p.addParamValue('Converters', {});
p.addParamValue('ConvertBinary', true);
p.parse(varargin{:});
converters = p.Results.Converters;
convertBinary = p.Results.ConvertBinary;

projPath = fileparts(projFile);

proj = tb_load_proj(projFile);
ethoFile = fullfile(projPath, proj.ethogramFile);
ethogram = tb_load_ethogram(ethoFile);
proj.ethogramName = ethogram.name;
proj.behaviors = ethogram.behaviors;
proj.behaviorKinds = ethogram.behaviorKinds;
proj.behaviorValues = ethogram.behaviorValues;

obsPath = fullfile(projPath, proj.projectRoot);

obsFiles = sort(fullfile(obsPath, tb_listfiles(obsPath, '*.tbobs', true)));

allObs = cell(size(obsFiles));
for i=1:numel(obsFiles)
    allObs{i} = tb_load_obs(obsFiles{i}, ...
        proj.behaviors, proj.behaviorKinds);
end
proj.obs = vertcat(allObs{:});
if convertBinary || ~isempty(converters)
    proj.obs = tb_obs_convert(proj.obs, converters, convertBinary);
end
