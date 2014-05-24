function val = tb_kvget(kv, key, varargin)
% Retrieve a value from one or more keyval sets
% Usage:
%   val = tb_kvget(kv, key)
%   val = tb_kvget(kv, key, flag1, flag2, ...)
%     kv is an array of structs with fields 'key' and 'val', as created by
%       tb_parse_keyvals.
%     key is the key associated with the value to retrieve
%     val is the value associated with key. Its structure depends on the
%       supplied flags and the type of data in kv.
% If kv is a struct array with N items, then there are N results
% retrieved by tb_kvget (the value of the key in each of the N keyvals).
% Each result (the 'val') is a list of M items. The exact structure of the
% data varies depending on whether N or M are 1, and what flags are set.
% Flags set special modes for the value and the result:
%   Value mode:
%     default (no flag)
%       For each value, if M (the number of items in the val list) is 1,
%       let the value be a string (e.g., 'value'). Otherwise, let it be a
%       cell array of strings (e.g., {'value1';'value2'}).
%     'listval'
%       Each value is always a cell array of strings even if the value is
%       a scalar (e.g., {'value'}).
%     'scalarval'
%       Each value is always a string. If the value was actually a list,
%       throw an error.
%   Result mode:
%     default (no flag)
%       If isscalar(kv), returns a single value (e.g., 'value', or
%       {'value1';'value2'}). Otherwise, returns a cell array of values
%       (e.g., {'value'; {'value1';'value2'}}).
%     'listres'
%       Always return a cell array of values even if only one keyval is
%       supplied (e.g., {'value'} or {{'value1';'value2'}}).
%     'scalarres'
%       Always return a single value. If multiple keyvals were supplied,
%       throw an error.
% Default modes are more useful in interactive mode, but specifying list or
% scalar modes when the intended format of the data is known will produce
% more reliable results.

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

listval = false;
scalarval = false;
if ismember('listval', varargin)
    listval = true;
elseif ismember('scalarval', varargin)
    scalarval = true;
end

listres = false;
scalarres = false;
if ismember('listres', varargin)
    listres = true;
elseif ismember('scalarres', varargin)
    scalarres = true;
end

if scalarres && ~isscalar(kv)
    error('Flag ''scalarres'' set, but kv is not scalar');
end

val = cell(size(kv));
for i=1:numel(kv)
    [tf, ind] = ismember(key, kv(i).key);
    if tf
        list = kv(i).val{ind};
        if scalarval && ~isscalar(list)
            error('Flag ''scalarval'' set, but list value found');
        elseif listval
            val{i} = list;
        else
            % Automatic or scalarval mode
            val{i} = list{1};
        end
    else
        % No such key was found: supply a default value
        if listval
            val{i} = {};
        else
            val{i} = '';
        end
    end
end

if isscalar(val) && ~listres
    val = val{1};
end

