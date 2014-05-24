function [tab, names] = tb_obs2table(obs, startT, endT, fSamp, varargin)
% Produce a table of values over time from an observation set
% Usage:
%   tab = obs2table(obs, startT, endT, fSamp)
%     For a single observation set obs (such as returned by tb_load_obs or
%       contained in the 'obs' field of tb_loadall), convert the set of
%       observations of value changes into a table of values over time.
%     obs is a struct with fields:
%         observer: The name of the person who coded the observations
%         source: The source of observations (video file name)
%         behav: An N-by-1 struct array with fields:
%           name: The name of the observed behavior
%           kind: The kind of behavior (moment, binary, state, or variable)
%           time: A vector of observation times
%           value: The values of the behavior at the observed times
%     tb_obs2table resamples each behavior of kind binary, state, or
%       variable (not moment) to get the values between times startT and
%       endT, with sampling rate fSamp (which should be the original video
%       framerate).
%     tab is then a struct with P fields, where P = (total number of
%       behaviors) - (number of moment behaviors) + 1. One field is 'time',
%       a column vector of sample times. The remaining fields are column
%       vectors giving the values for each non-moment behavior. Because
%       Matlab arbitrarily enforces restrictions on struct field names, the
%       field names are derived from the behavior names using these rules:
%       1. Replace any character that is not alphanumeric or '_' with '_'
%       2. If the first character is numeric or '_', prepend with 'B'
%       For example, a behavior 'Look-away' would be stored in a field
%       'Look_away'. Then tab.Look_away(i) is the value of 'Look-away' at
%       time tab.time(i).
%       (If for some reason there is a behavior 'time', then the 'time'
%       field will contain values for this behavior instead of timestamps.)
%     obs can also be a struct array of multiple observation sets, in which
%       case tb_obs2table operates elementwise. If startT or endT are
%       vectors of the same length as obs, then the values are used
%       elementwise as well.
%   [tab, names] = tb_obs2table(obs, startT, endT, fSamp)
%     names is a cell array of the original behavior names in tab before
%       conversion to valid Matlab field names. If
%         fields = fieldnames(tab)
%       then names{i} is the original behavior name for the values in
%         tab.(fields{i})
%   tab = tb_obs2table(..., 'Param1', value1, ...)
%     Supply optional parameter-value pairs. Valid pairs (with valid values
%     in [brackets] and default values starred*) are:
%       'InitialValues' [ N-by-2 cell array | {}* ]
%         Supplies initial values for the observed behaviors. If
%         startT < min(obs.behav(i).time) for some behavior, an initial
%         value must be supplied. InitialValues(:,1) is a list of strings
%         naming behaviors in obs, and InitialValues(:,2) is a list of
%         corresponding initial values. For behaviors of kind 'binary', if
%         no initial value is explicitly supplied, the initial value is
%         set by the 'InitialBinary' parameter.
%       'InitialBinary' [ true | false* | [] ]
%         What value to use as the initial value for 'binary' behaviors.
%         [] denotes no initial value.
%     The following parameters are unlikely to need to be set but are
%     if needed:
%       'SampleBinSide' [ 'left' | 'right'* ]
%         When tb_obs2table is resampling behavior values, whether to have
%         the value at the left (low) or right (high) end of a time bin
%         define the value of the bin. (For coded videos, 'right' is almost
%         always the correct choice, accounting for options "during" a
%         frame.)
%       'SampleBinTol' [ numeric scalar, .01* ]
%         How far from the true edge of a bin to sample behavior, in
%         fraction of bin width. If exactly 0, could be sensitive to
%         floating point round-off problems.

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

if ~isscalar(obs)
    % Handle multiple observation sets via recursion
    tab = cell(size(obs));
    names = cell(size(obs));
    if isscalar(startT)
        startT = repmat(startT, size(obs));
    end
    if isscalar(endT)
        endT = repmat(endT, size(obs));
    end
    for i=1:numel(obs)
        [tab{i}, names{i}] = tb_obs2table(obs(i), startT(i), endT(i), ...
            fSamp, varargin{:});
    end
    try
        tab = vertcat(tab{:});
        names = names{1};
    catch e
        if strcmp(e.identifier, 'MATLAB:catenate:structFieldBad')
            % Couldn't vertcat tab because each observation set had
            % different behaviors.
            % We'll just leave tab as a cell array of structs -- eat the
            % error and move on.
        else
            rethrow(e);
        end
    end
    return;
end

p = inputParser;
% Take the value for a bin to be the value at the start (left) or end
% (right) of the bin (default right)
p.addParamValue('SampleBinSide', 'right', ...
    @(s)ismember(s,{'left','right'}));
% Floating point slop could push observations at exactly the bin edge
% either direction. This gives a little bit of offset to the bin edges to
% compensate.
p.addParamValue('SampleBinTol', .01);
% Initial behavior values, an N-by-2 cell array where the first column
% gives behavior names and the second column gives (post-conversion) values
% to use prior to the first observation. If no initial value is given and
% the start of the sampling interval is before the first observation for a
% behavior, an error will occur.
p.addParamValue('InitialValues', {});
% Initial value to use for binary behaviors if no specific initial value is
% supplied. Can be true, false, or [] (for no initial value).
p.addParamValue('InitialBinary', false);

p.parse(varargin{:});
binSide = p.Results.SampleBinSide;
binTol = p.Results.SampleBinTol;
inits = p.Results.InitialValues;
initBinary = p.Results.InitialBinary;
if isempty(inits)
    inits = reshape(inits, [], 2);
end

startBin = floor(startT * fSamp + binTol);
endBin = floor(endT * fSamp + binTol) - 1;
if strcmp(binSide, 'left')
    binOffset = binTol;
else
    binOffset = 1-binTol;
end

binT = (startBin:endBin)'/fSamp;
sampleT = ((startBin:endBin)' + binOffset)/fSamp;

behavSet = obs.behav;
kinds = {behavSet.kind};
useBehavior = ismember(kinds, {'binary', 'state', 'variable'});
behavSet = behavSet(useBehavior);
names = {behavSet.name};
isBinary = strcmp('binary', {behavSet.kind});
% Come up with field names representing the original behavior names by:
% 1. Replace any character that is not alphanumeric or '_' with '_'
% 2. If the first character is numeric or '_', prepend with 'B'
fields = regexprep(names, '\W', '_');
fields = regexprep(fields, '^([\d_])', 'B$1');

data = cell(size(behavSet));
for i=1:numel(behavSet)
    time = behavSet(i).time;
    value = behavSet(i).value;
    
    [hasInit, initInd] = ismember(names{i}, inits(:,1));
    try
        if hasInit
            data{i} = tb_resample(value, time, sampleT, inits{initInd,2});
        elseif isBinary(i) && ~isempty(initBinary)
            data{i} = tb_resample(value, time, sampleT, initBinary);
        else
            data{i} = tb_resample(value, time, sampleT);
        end
    catch e
        if strcmp(e.identifier, 'tb_resample:noInit')
            error(['Observation of ''%s'' from ''%s'' by ''%s'' has ' ...
                'no value at time %d, and no initial value was given.'], ...
                behavSet(i).name, obs.source, obs.observer, startT);
        else
            rethrow(e);
        end
    end
end

tab = cell2struct(data, fields, 1);
if ~ismember('time', fields)
    tab.time = binT;
    tab = orderfields(tab, [{'time'}, fields]);
    names = [{'time'}, names];
end
