function etho = tb_load_ethogram(ethoFile)
% Load data from a Tinbergen ethogram file
% Usage:
%   etho = tb_load_ethogram(ethoFile)
% Reads the data in the Tinbergen ethogram file (.tbethogram) identified by
% ethoFile and returns a struct with fields:
%   name: The value of the 'name' line; the name of the ethogram
%   behaviors: A list of all behaviors in the ethogram.
%   behaviorKinds: A list of the kinds for each behavior in the ethogram,
%     each item being one of 'moment', 'binary', 'state', or 'variable'
%   behaviorValues: A list of valid values for each behavior in the
%     ethogram. If the kind is not 'state', the item will be {}.
% See tb_loadall for a simple way to load the project file, ethogram file,
% and all observation files with one call.

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

lines = tb_readlines(ethoFile);

getScalarData = @(entry)lines.value{strcmp(lines.entry, entry)};
getListData = @(entry)lines.value(strcmp(lines.entry, entry));

etho = struct;
etho.name = getScalarData('name');

behavs = tb_parse_keyvals(getListData('behavior'));
etho.behaviors = tb_kvget(behavs, 'name', 'scalarval', 'listres');
etho.behaviorKinds = tb_kvget(behavs, 'kind', 'scalarval', 'listres');
etho.behaviorValues = tb_kvget(behavs, 'values', 'listval', 'listres');
