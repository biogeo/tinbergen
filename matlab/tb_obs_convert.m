function obs = tb_obs_convert(obs, converters, convertBinary)
% Convert behavior values from strings
% All Tinbergen data is stored as text, and by default behavioral state
% values are loaded into Matlab as strings. Binary behavior values are
% probably more useful to treat as Matlab logicals, and other behaviors may
% have more useful representations as well. This function makes it
% convenient to convert the "value" field of behavioral observations from
% strings to other types.
% Usage:
%   obs = tb_obs_convert(obs)
%     obs is a struct representing a Tinbergen observation set, such as
%       produced by tb_load_obs, or stored in the 'obs' field returned by
%       tb_loadall. If obs is an array of struct, tb_obs_convert operates
%       elementwise. All behaviors of kind 'binary' are converted to
%       logical arrays. E.g. if obs.behav(i).kind is 'binary, and initially
%       obs.behav(i).value is {'True';'False';'True'}, then after it will
%       be logical([1;0;1])
%   obs = tb_obs_convert(obs, converters)
%     converters is an N-by-2 cell array. converters(:,1) is a list of
%       behavior names in obs, and converters(:,2) is a list of function
%       handles for converting the corresponding behaviors' values. Each
%       function handle must accept a cell array of strings and return an
%       array of the same size. The values fields for each behavior in obs
%       are replaced by the result of the appropriate converter function.
%       'binary' behaviors without a specified converter are converted to
%       logical, as above. Other behaviors with no converter are left
%       unchanged.
%         Example: Suppose there is a behavior 'Count', for which the
%           values are all numbers:
%             >> obs.behav(1).name
%             ans = 'Count'
%             >> obs.behav(1).value
%             ans = {'0'; '1'; '2'; '1'; '0'}
%             >> obs = tb_obs_convert(obs, {'Count', @str2double});
%             >> obs.behav(1).value
%             ans = [0; 1; 2; 1; 0]
%    obs = tb_obs_convert(obs, converters, convertBinary)
%      convertBinary specifies whether to convert 'binary' behavior values
%        to Matlab logicals as described above. true is the default, false
%        causes no conversion other than those specified in converters to
%        occur.

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

if ~exist('convertBinary', 'var') || isempty(convertBinary)
    convertBinary = true;
end

if ~exist('converters', 'var') || isempty(converters)
    converters = reshape({},0,2);
end

if ~isscalar(obs)
    % Work elementwise.
    for i=1:numel(obs)
        obs(i) = tb_obs_convert(obs(i), converters, convertBinary);
    end
    return;
end

behavs = {obs.behav.name};
isBinary = strcmp('binary', {obs.behav.kind});
[hasConverter, converterInd] = ismember(behavs, converters(:,1));

for i=1:numel(obs.behav)
    if hasConverter(i)
        converterFun = converters{converterInd(i), 2};
        sz = size(obs.behav(i).value);
        obs.behav(i).value = converterFun(obs.behav(i).value);
        if ~( ndims(obs.behav(i).value)==numel(sz) ...
                && all(size(obs.behav(i).value)==sz) )
            error('Converter function failed to preserve data size');
        end
    elseif convertBinary && isBinary(i)
        obs.behav(i).value = strcmpi('True', obs.behav(i).value);
    end
end