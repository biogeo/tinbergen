function [yr, it] = tb_resample(y, t, tr, init)
% Resample a signal with discrete value transition times
% Usage:
%    [yr, it] = tb_resample(y, t, tr)
%    [yr, it] = tb_resample(y, t, tr, init)
%   y and t together represent a signal that takes only discrete values,
%     changing at times t to values y. y can be any indexable type,
%     including cell arrays.
%   tr is a set of timestamps at which to resample the signal.
%   init is an initial or default value of the signal for the interval
%     (-inf, min(t)). If any(tr) < min(t), init must be supplied. In effect
%     it is the same as setting y = [init, y] and t = [-inf, t]. If y is a
%     cell array and init is not, then init is coerced to be a cell array
%     element (ie, y = [{init}, y]).
%   yr is the values of the signal at times tr.
%   it is the indices of resampling, such that yr = y(it). If init is used,
%     it = 0 for init values.
% (tb_resample is a version of a general-purpose helper function packaged
% with Tinbergen.)

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

if numel(t) ~= numel(y)
    error('y and t must have the same number of elements');
end

% Handle the case that tr is empty
if isempty(tr)
    yr = y([]);
    it = [];
    return;
end

% Handle the case that t and y are empty
if isempty(t)
    if ~exist('init', 'var')
        error('Resampling out of range, and no initial value supplied');
    end
    if isscalar(init)
        yr = repmat(init, size(tr));
        it = zeros(size(tr));
    else
        yr = repmat({init}, size(tr));
        it = zeros(size(tr));
    end
    return;
end

% Outputs will be reshaped to match requested tr
sz = size(tr);

% Guarantee column vectors
t = t(:);
y = y(:);

if any(tr < min(t))
    % t is guaranteed to be sorted now
    % If any tr are before the first t, we need to use init
    if ~exist('init', 'var') || isempty(init)
        error('tb_resample:noInit', ...
            'Resampling out of range, and no initial value supplied');
    end
    if iscell(y) && ~iscell(init)
        init = {init};
    end
    t = [-inf; t];
    y = [init; y];
    useInit = true;
else
    useInit = false;
end

% Sort the input times, if necessary
if ~issorted(t)
    [t,t1SortI] = sort(t);
    useSort = true;
else
    useSort = false;
end

% Use histc to get the indices of tr in bins defined by t
[~,inds] = histc(tr(:), [t; inf]);

if useSort
    yr = y(t1SortI(inds));
else
    yr = y(inds);
end
yr = reshape(yr, sz);

if nargout >= 2
    % User requested index output it -- if it wasn't requested, save
    % ourselves a little time by not bothering with these steps.
    if useSort
        it = t1SortI(inds);
    else
        it = inds;
    end
    if useInit
        % We added -inf to the beginning of t, so it is actually the
        % original index plus 1. Correct for that.
        it = it-1;
    end
    it = reshape(it, sz);
end
