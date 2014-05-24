% The Tinbergen MATLAB toolbox
% A suite of functions for accessing Tinbergen data in MATLAB.
% 
% To use the Tinbergen MATLAB toolbox, first add the matlab subdirectory of
% Tinbergen to your MATLAB path. This will make available several functions
% with names starting with 'tb_' which you can use to access your Tinbergen
% data.
% 
% First a few examples, then a quick overview of the functions:
% 
% Example basic usage:
%   Suppose you have a Tinbergen project stored in the directory
%     /path/to/my/project
%   There, your project file is myProject.tbproj, your ethogram file is
%   myProject.tbethogram, and your observation files are stored in the
%   subdirectory observations.
%   To load all of your data, simply issue the command
%   
%   >> projectFilePath = '/path/to/my/project/myProject.tbproj'
%   >> proj = tb_loadall(projectFilePath)
%   
%   (If you have a large number of observation sets, this may take a few
%   seconds to complete.)
%   Now `proj` is a struct with all of your data stored in its fields.
%   
%   >> proj.obs(1)
%   returns a struct describing the first observation set in the project
%   >> proj.obs(1).behav(1)
%   returns a struct describing the first behavior in the first observation
%   set in the project
%   >> proj.obs(1).behav(1).name
%   is the name of the first behavior
%   >> proj.obs(1).behav(1).time
%   is a column vector of observation times for the behavior
%   >> proj.obs(1).behav(1).values
%   is a column vector of observation values for the behavior at those
%   times
%   
%   See `help tb_loadall` for more information.
% 
% Example usage with custom value conversion:
%   Suppose your project includes behaviors with values that you would like
%   to treat as something other than strings. For example, behaviors
%   'Count' and 'Ratio', which are behaviors of kind 'variable' which take
%   values that are always numbers. Then call tb_loadall with converter
%   functions:
%   
%   >> proj = tb_loadall(projectFilePath, 'Converters', {
%          'Count', @str2double;
%          'Ratio', @str2double;
%          })
%   
%   Now the `str2double` function will be applied to the values of those
%   two behaviors. Note that for behaviors of kind 'binary', the values are
%   already converted to logicals by default.
%
% Example usage for making tables of behavior values across time:
%   Tinbergen stores simple lists of observations, which can yield a list
%   of values at specific times. But, for the "stative" behavioral kinds
%   ('binary', 'state', and 'variable'), it can be more useful for analysis
%   to have a time series of values throughout the file. The Tinbergen
%   toolbox makes this not too challenging.
%   First, you will need to get the video file durations and frame rates
%   for each video file in the project. Suppose you then have three
%   variables:
%     movieFilename
%     movieDuration
%     movieFPS
%   (Make sure movieFilename has the paths relative to the Tinbergen
%   project's videoRoot directory.)
%   
%   With the Tinbergen project loaded using tb_loadall, you can obtain the
%   duration and frame rate per-observation by doing the following:
%   
%   >> [~, movieInd] = ismember({proj.obs.source}, movieFilename);
%   >> obsDuration = movieDuration(movieInd);
%   >> obsFPS = movieFPS(movieInd);
%   
%   Then, issue the command:
%
%   >> tables = tb_obs2table(proj.obs, 0, obsDuration, obsFPS)
%
%   tables is now a struct array such that tables(i) contains data from
%   proj.obs(i), having a field for each behavior that gives a list of
%   values through time at obsFPS(i) samples per second.
%   
%   E.g., suppose there is a single behavior in the ethogram, and
%   >> proj.obs(1).behav
%        name: 'Count'
%        kind: 'variable'
%        time: [0; 1.4; 2.2]
%       value: [1; 2; 3]
%   >> obsDuration(1)
%       3.0
%   >> obsFPS(1)
%       5
%   Then:
%   >> tables(1)
%        time: [0;0.2;0.4;0.6;0.8;1.0;1.2;1.4;1.6;1.8;2.0;2.2;2.4;2.6;2.8]
%       Count: [1;  1;  1;  1;  1;  1;  1;  2;  2;  2;  2;  3;  3;  3;  3]
%   
%   There are a number of caveats; see `help tb_obs2table` for more
%   information.
% 
% Function overview:
%   For most cases, the only functions needed will be:
%     tb_loadall       -- load all data from a Tinbergen project
%     tb_obs2table     -- create tables of "stative" behavior values
%   Slightly lower level but still potentially useful are:
%     tb_load_proj     -- load data from the Tinbergen project file only
%     tb_load_ethogram -- load data from the Tinbergen ethogram file only
%     tb_load_obs      -- load data from one Tinbergen observation file
%     tb_obs_convert   -- convert observation values from strings
%   Functions for internal use by other Tinbergen functions:
%     tb_kvget, tb_parse_keyvals, tb_readlines
%   Additionally, there are utility functions included in the Tinbergen
%   toolbox which aren't actually Tinbergen-specific in their usage:
%     tb_listfiles     -- slight improvement on `dir` for listing files
%     tb_resample      -- resample a discrete signal
% 
% This file and all others in the Tinbergen toolbox copyright 2014 Geoffrey
% Adams. See the LICENSE file accompanying Tinbergen for licensing.