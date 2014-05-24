function kv = tb_parse_keyvals(str)
% Parse Tinbergen "keyval" strings
% Usage:
%   kv = tb_parse_keyvals(str)
% str can be a single string or cell array of strings, each of the form
%   'key1=val1 key2=val2 key3=val3 ...'
% where each keyI is a string with no whitespace and not containing the
% character '=', or with whitespace or '=' escaped with '\', or fully
% enclosed by double quotes as in "keyI". Each valI is a string of the same
% form, or a comma-separated list of items (where commas can be escaped as
% well).
%   kv is an array of struct with fields 'key' and 'val', such that
%     kv(i).key{j}
%   is the j'th key in the i'th keyval string, and
%     kv(i).val{j}{k}
%   is the k'th list item in the j'th value in the i'th keyval string.
% Example:
%   s1 = 'alpha=one beta="two"';
%   s2 = '"ga ma"=three,four delta=five\,six epsilon=';
%   kv = tb_parse_keyvals({s1, s2});
%   kv(1)
%       key: {'alpha'; 'beta'}
%       val: {{'one'}; {'two'}}
%   kv(2)
%       key: {'ga ma';          'delta';      'epsilon'}
%       val: {{'three';'four'}; {'five,six'}; {}}
% This is basically a workaround for the fact that Matlab arbitrarily
% requires valid identifiers for struct field names instead of allowing any
% string. Use tb_kvget to retrieve val by key.

% Copyright 2014 Geoffrey Adams. See the accompanying LICENSE file for
% licensing information.

str = cellstr(str);

% Expression matching single valid "words" (key or value)
word_expr = '"(?:\\.|[^"])*"|(?:\\.|[^\s=])+';
% Expression matching a single valid key=value pairs
keyval_expr = ['(?<key>' word_expr ')=(?<val>' word_expr ')?'];
% Expression matching words surrounded by quotes and capturing the quoted
% part
quoted_expr = '"((?:\\.|[^"])*)"';
% Expression matching items in a comma-separated list
list_expr = [quoted_expr '|' '(?:\\.|[^,])*'];
% Expression matching backslash escape sequences and capturing the escaped
% character
escape_expr = '\\(.)';

% From a set of words, extract from quotes and de-escape:
tidy_words = @(s) regexprep( ...
    regexprep(s, quoted_expr, '$1'), ...
    escape_expr, '$1' );

% Match key=val substrings as a struct array with fields key & val:
kvsets = regexp(str, keyval_expr, 'names');
kv = struct('key', cell(size(kvsets)), 'val', []);
for i=1:numel(kvsets)
    thiskv = struct;
    thiskv.key = {kvsets{i}.key}';
    thiskv.val = {kvsets{i}.val}';
    
    thiskv.key = tidy_words(thiskv.key);
    
    % Get values as lists and then tidy them up
    thiskv.val = regexp(thiskv.val, list_expr, 'match');
    thiskv.val = cellfun(tidy_words, thiskv.val, 'UniformOutput', false);
    
    kv(i) = thiskv;
end

%keyvals = cell2struct({items.val}, {items.key}, 2);