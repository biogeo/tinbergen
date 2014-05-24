function obs = tb_load_obs(obsFile, behaviors, kinds)
% Load a Tinbergen observation set file
% Usage:
%   obs = tb_load_obs(obsFile)
%     Read all the data from a Tinbergen observation set file (.tbobs) and
%     return a struct with fields:
%       observer: The name of the observer who coded the observations
%       source: The source of observations (video file name)
%       behav: a struct array with the following fields
%         name: The name of a behavior in the ethogram
%         kind: The behavior's kind
%         time: A column vector of observation times for the behavior
%         value: A column vector of observed values for the behavior
%   obs = tb_load_obs(obsFile, behaviors)
%     behaviors is a list of behaviors to load data for. obs will include a
%     behav entry for each item in behaviors, even if no observations for
%     that behavior are present in the file. Behaviors for which no data is
%     present will have kind='', time=[], values={}.
%   obs = tb_load_obs(obsFile, behaviors, kinds)
%     Additionally specifies behavior kinds (which can override the kinds
%     specified in the file). Most useful for ensuring the 'kind' field is
%     properly set even if no observations exist for a behavior.
% See tb_loadall for a simple way to load the project file, ethogram file,
% and all observation files with one call.

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

lines = tb_readlines(obsFile);

getScalarData = @(entry)lines.value{strcmp(lines.entry, entry)};
getListData = @(entry)lines.value(strcmp(lines.entry, entry));

obs = struct;
obs.observer = getScalarData('observer');
obs.source = getScalarData('source');

obsData = tb_parse_keyvals(getListData('obs'));

obsBehav = tb_kvget(obsData, 'name', 'scalarval', 'listres');
obsTime = tb_kvget(obsData, 'time', 'scalarval', 'listres');
obsValue = tb_kvget(obsData, 'value', 'scalarval', 'listres');
obsKind = tb_kvget(obsData, 'kind', 'scalarval', 'listres');

[obsTime, ix] = sort(str2double(obsTime));
obsBehav = obsBehav(ix);
obsValue = obsValue(ix);
obsKind = obsKind(ix);

if ~exist('behaviors', 'var')
    behaviors = unique(obsBehav);
end
if ~exist('kinds', 'var')
    kinds = repmat({''}, size(behaviors));
end

obs.behav = struct( ...
    'name', behaviors, 'kind', kinds, ...
    'time', [], 'value', {{}});

for i=1:numel(obs.behav)
    isBehav = strcmp(obs.behav(i).name, obsBehav);
    if isempty(obs.behav(i).kind) && any(isBehav)
        obs.behav(i).kind = obsKind{find(isBehav,1)};
    end
    obs.behav(i).time = obsTime(isBehav);
    obs.behav(i).value = obsValue(isBehav);
end