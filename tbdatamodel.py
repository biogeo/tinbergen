"""
Classes and functions supporting the Tinbergen data model for behavioral
observations.
"""

# Ethograms will look like:
# behavior: kind=moment name=instant-behavior
# behavior: kind=state name=state-behavior values=list,of,possible,values
# behavior: kind=binary name=binary-behavior
# behavior: kind=variable name=variable-name
# code: symbol=sym1 name=instant-behavior
# code: symbol=sym2 name=state-behavior value=list
# code: symbol=sym3 name=state-behavior value=of
# code: symbol=sym4 name=binary-behavior value=True
# code: symbol=sym5 name=binary-behavior value=False
# code: symbol=sym6 name=variable-name args=value
#
# Observation sets will look like:
# obs: time=t1 entry=sym1 name=instant-behavior kind=moment
# obs: time=t2 entry=sym2 name=state-behavior kind=state value=list
# obs: time=t3 entry=sym4 name=binary-behavior kind=binary value=True
# obs: time=t4 entry=sym6\ 4 name=variable-name kind=variable value=4
#
# For the time=t4 entry, the user would have entered "sym6 4"

import re
import os
import glob
import collections
import operator

observation_kinds = ('moment', 'state', 'binary', 'variable')
binary_values = ('True', 'False')
movie_suffixes = ('mp4', 'mov', 'mts', 'm4v', 'avi', 'mpg')
file_suffixes = {'ethogram': 'tbethogram',
                 'project': 'tbproject',
                 'observation': 'tbobs'}

def append_obs_suffix(filename):
    """
    Add the standard observation file suffix to the end of a string.
    """
    return filename + '.' + file_suffixes['observation']

def dictlist_lookup(dictlist, key, value):
    """
    From a list of dicts, retrieve those elements for which <key> is <value>.
    """
    return [el for el in dictlist if el.get(key)==value]

class Project(object):
    """
    A representation of a Tinbergen project. Includes methods for retrieving
    and storing observations associated with a video file.
    
    Projects should be initialized with a project filename. That file defines
    a directory root where video files are stored, <video-root>, and a root
    observations are stored, <project-root>. Each video file to be coded should
    be in <video-root> or one of its subdirectories:
    
    <video-root>/a/b/video.ext
    
    The project also defines observers, with short observer-codes, <osr>.
    Observations for a given file will be saved in files like:
    
    <project-root>/a/b/video.ext.<osr>.tbobs
    
    Once created, saving any subsequent observations will move the original
    observation file to video.ext.<osr>.tbobs.N, where N begins at 1 and
    increments every time.
    """
    def __init__(self, project_filename):
        project_file_dir = os.path.dirname(project_filename)
        self.__project_root = ''
        self.__video_root = ''
        self.cur_file = ''
        self.__ethogram_file = ''
        self.observers = []
        self.video_files = []
        with open(project_filename) as project_file:
            for line in project_file:
                head,sep,tail = line.partition(':')
                head = head.strip()
                tail = tail.strip()
                if head=='video-root':
                    new_path = os.path.abspath(os.path.join(
                            project_file_dir, tail))
                    self.__video_root = new_path
                elif head=='project-root':
                    new_path = os.path.abspath(os.path.join(
                            project_file_dir, tail))
                    self.__project_root = new_path
                elif head=='current-file':
                    self.cur_file = tail
                elif head=='ethogram-file':
                    new_path = os.path.abspath(os.path.join(
                            project_file_dir, tail))
                    self.__ethogram_file = new_path
                elif head=='observer':
                    self.observers.append(parse_keyvals(tail))
        with open(self.__ethogram_file) as f:
            self.ethogram = Ethogram.new_from_file(f)
        self.update_video_list()
    
    def get_observer_name(self, code):
        """
        Given an observer code, retrieve the observer's name.
        """
        matches = [el for el in self.observers if el.get('code')==code]
        return matches[0]['name']
    
    def get_observer_code(self, name):
        """
        Given an observer's name, retrieve the code.
        """
        matches = [el for el in self.observers if el.get('name')==name]
        return matches[0]['code']
    
    def update_video_list(self):
        """
        Check the file system again for files descending from video_root.
        """
        full_list = []
        walker = os.walk(self.__video_root)
        for directory_entry in walker:
            subdir = self.rel_video_path(directory_entry[0])
            for dir_file in directory_entry[-1]:
                # Is there a better way to get file suffixes? This will yield
                # false positives for files named, eg, "mp4". Not ever going to
                # happen, so not worth special-casing, but irritating.
                # PS, if you're reading this because it did happen, sorry!
                suffix = dir_file.split('.')[-1]
                if dir_file[0]!='.' and suffix.lower() in movie_suffixes:
                    full_list.append(os.path.join(subdir, dir_file))
        self.video_files = full_list
    
    def get_video_observers(self, videoname):
        """
        Get all observers who have stored observations for a particular video.
        Returns a list of observer codes.
        """
        coders = []
        matchpattern = self.join_project_path(videoname) + '.*.tbobs'
        for obsfile in glob.glob(matchpattern):
            coders.append(obsfile.split('.')[-2])
        return coders
    
    def join_project_path(self, *pargs):
        """
        Returns inputs joined to project_root with os.path.join
        """
        return os.path.join(self.__project_root, *pargs)
    
    def join_video_path(self, *pargs):
        """
        Returns inputs joined to video_root with os.path.join
        """
        return os.path.join(self.__video_root, *pargs)
    
    def rel_project_path(self, path):
        """
        Converts a path to be relative to the project_root.
        """
        return os.path.relpath(path, self.__project_root)
    
    def rel_video_path(self, path):
        """
        Converts a path to be relative to video_root.
        """
        return os.path.relpath(path, self.__video_root)
    
    def get_obsfile(self, videofile, observer):
        """
        Attaches ".<obs>.tbobs" to a path, where <obs> is the observer code.
        """
        if videofile is None or observer is None:
            return ''
        else:
            return '.'.join([self.join_project_path(videofile),
                             observer, file_suffixes['observation']])
    
    def load_observations(self, filename=None):
        """
        Don't use this one.
        """
        if filename==None:
            filename = self.cur_file
        filepath = self.join_project_path(append_obs_suffix(filename))
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                obs = ObservationSet.new_from_file(self.ethogram, f)
        else:
            obs = ObservationSet(self.ethogram, self.observer, filename)
    
    def load_obs_from_file(self, videofile, observer):
        """
        For a video file and a particular observer, load a set of observations
        (if they exist). An observation set is a list of dict objects. To be
        valid, each observation must have at least the keys:
            'entry': the code entered by the observer
            'time': the time of the observation, relative to the video
        In general it should also include the keys produced by the parse_entry
        method of the ethogram called on 'entry':
            'kind': one of 'moment', 'binary', 'state', 'variable'
            'name': the name of the observed behavior
            'value': for binary, state, or variable behaviors
        Other keys are also permitted.
        """
        if videofile is None or observer is None:
            return []
        obsfile = self.get_obsfile(videofile, observer)
        obslist = []
        if os.path.exists(obsfile):
            with open(obsfile, 'r') as f:
                for line in f:
                    head,sep,tail = line.partition(':')
                    head = head.strip()
                    tail = tail.strip()
                    if head=='obs':
                        obs_dict = parse_keyvals(tail)
                        obslist.append(obs_dict)
        return obslist
    
    def save_obslist(self, videofile, observer, obslist):
        """
        For a particular video file and observer, save a list of observations.
        obslist is a list of dictionary objects, as in load_obs_from_file. The
        file will be saved in:
            <project-root>/path/to/video/file.ext.<obscode>.tbobs
        If a file already exists at this location, it will first be renamed by
        adding a .N suffix, where N is a number that starts at 1 and increments
        every time.
        """
        observer_name = self.get_observer_name(observer)
        obsfile = self.get_obsfile(videofile, observer)
        obsdir = os.path.dirname(obsfile)
        if not os.path.exists(obsdir):
            os.makedirs(obsdir)
        if os.path.exists(obsfile):
            cur_backups = glob.glob(obsfile + '.*')
            # This is terrible but will work for now
            if len(cur_backups) == 0:
                backup_N = 1
            else:
                backup_N = 1+max(int(s.rsplit('.',1)[-1]) for s in cur_backups)
            backup_path = obsfile + '.' + str(backup_N)
            os.rename(obsfile, backup_path)
        with open(obsfile, 'w') as f:
            f.write('observer: {0}\n'.format(observer_name))
            f.write('source: {0}\n'.format(videofile))
            for obs in obslist:
                try:
                    obsstr = as_keyvalstr(obs)
                    f.write('obs: {0}\n'.format(obsstr))
                except TypeError:
                    pass
    
    def save_observations(self, obs):
        """
        Don't use this.
        """
        filename = obs.obs_source
        filepath = self.join_project_path(append_obs_suffix(filename))
        dirpath = os.path.dirname(filepath)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        if os.path.exists(filepath):
            cur_backups = glob.glob(filepath + '.*')
            # This is hacky and susceptible to bugs, but it might work for now
            if len(cur_backups) == 0:
                backup_N = 1
            else:
                backup_N = max(int(s.split('.')[-1]) for s in cur_backups) + 1
            backup_path = filepath + '.' + str(backup_N)
            os.rename(filepath, backup_path)
        with open(filepath, 'w') as f:
            obs.save(f)
    
    def next_file(self):
        """
        The next/previous file interface isn't really being used.
        """
        # So this is kind of lame. I should probably figure out a real iterator
        # type thing at some point.
        if self.cur_file not in self.video_files:
            self.cur_file = self.video_files[0]
        else:
            fileind = self.video_files.index(self.cur_file)
            if fileind == len(self.video_files)-1:
                self.cur_file = self.video_files[0]
            else:
                self.cur_file = self.video_files[fileind+1]
    
    def prev_file(self):
        """
        Don't need to use this.
        """
        if self.cur_file not in self.video_files:
            self.cur_file = self.video_files[0]
        else:
            fileind = self.video_files.index(self.cur_file)
            if fileind == 0:
                self.cur_file = self.video_files[-1]
            else:
                self.cur_file = self.video_files[fileind-1]

class Ethogram(object):
    """
    A set of possible behavioral observations, and symbols mapping to them.
    """
    def __init__(self, name=''):
        self.name = name
        self.__behaviors = dict()
        self.__codes = dict()
    
    @property
    def behaviors(self):
        """
        The behaviors currently registered in the ethogram. New behaviors must
        be added using the add_behavior method. behaviors is a mapping where
        each key is a registered behavior's name and the value is a dict with
        at least the keys:
            name: The name of the behavior
            kind: The kind of behavior (moment, state, binary, or variable)
        State behaviors also have:
            values: All possible values the state may take
        And binary behaviors always have:
            values: Always the tuple ('True', 'False')
        """
        return DictViewer(self.__behaviors)
    
    @property
    def codes(self):
        """
        The codes currently registered in the ethogram. New codes must be added
        using the add_code method. methods is a mapping where each key is a
        registered code and the value is a dict with at least the keys:
            symbol: The registered code's symbol
            name:   The name of the behavior identified by the code
        The code may also have the special key:
            args: A list of parameter names. If the user enters "sym a1 a2 a3",
                  the arguments are understood to fill in the parameters given
                  in args.
        The codes can also have any number of additional keys which give
        additional parameters to a behavioral observation. Of particular note:
            value: If name identifies a state behavior, value must be in the
                   behavior's values list. If it is a binary behavior, must be
                   either 'True' or 'False'.
        """
        return DictViewer(self.__codes)
    
    def add_behavior(self, kind, name, values=None):
        """
        Add a new behavior to the ethogram. The behavior kind must be one of:
            moment:   For instantaneous behaviors taking negligible time
            state:    For a set of mutually exclusive behaviors, one of which is
                      always occurring (eg, Arousal as sleeping, resting, or
                      moving)
            binary:   Like a state, but for behaviors that simply either occur
                      or don't.
            variable: For tracking changes in some value over time, eg, number
                      of animals.
        State behaviors require the additional values parameter, which is a list
        of the various values the state may take. This parameter is ignored for
        other kinds.
        """
        if kind not in observation_kinds:
            raise ValueError('Invalid observation kind')
        new_behavior = {'name': name, 'kind': kind}
        if kind=='state':
            new_behavior['values'] = NameSet(values)
        elif kind=='binary':
            new_behavior['values'] = NameSet(binary_values)
        self.__behaviors[name] = DictViewer(new_behavior)
    
    def add_code(self, symbol, name, args=None, **kargs):
        """
        Add a new code to the ethogram. A code is a symbolic shorthand for
        referencing a behavior, optionally with additional parameters specified.
        """
        if re.search(r'\s', symbol):
            raise ValueError('Symbols cannot contain whitespace')
        if name not in self.__behaviors:
            raise CodeError('Symbol maps to nonexistent name')
        behavior = self.__behaviors[name]
        new_code = {'symbol': symbol, 'name': name}
        if args != None:
            new_code['args'] = NameSet(args)
        new_code.update(kargs)
        #self.__validate_obs(new_code)
        # We may want to validate the code in the future
        self.__codes[symbol] = DictViewer(new_code)
    
    def get_prototype(self, entry):
        """
        Create a prototype dict for a behavioral observation based on a code.
        The entry must take the form "symbol arg1 arg2 arg3 ...". "symbol"
        identifies a code in the ethogram. All "argN" are optional, and their
        meaning is specified by the args parameter of the code identified by the
        symbol.
        """
        entry_items = entry.split()
        symbol = entry_items[0]
        args = entry_items[1:]
        code = self.__codes[symbol]
        behavior = self.__behaviors[code['name']]
        new_proto = {'entry': entry,
                     'name': behavior['name'],
                     'kind': behavior['kind']}
        for key in (set(code.keys()) - set(['symbol', 'name', 'args'])):
            new_proto[key] = code[key]
        if 'args' in code:
            new_proto.update(zip(code['args'], args))
        self.__validate_obs(new_proto)
        return new_proto
    
    def parse_entry(self, entry):
        """
        Given a string, return a mapping representing the observation coded by
        that string in the ethogram. The observation string should take the
        form "sym a1 a2 a3..." where aN are optional. "sym" is a symbol
        identifying a code in the ethogram. aN are additional arguments,
        interpreted according to the "args" parameter of the code.
        
        Only limited error checking is performed, so the observation is not
        guaranteed to be valid according to the ethogram. In particular, if
        "sym" is not in the ethogram, a dummy "observation" is returned. Invalid
        values for state and binary behaviors are also permitted. To verify that
        the observation is valid, use validate_obs().
        """
        obs_entry = {'entry': entry}
        if len(entry) == 0:
            return obs_entry
        entry_items = entry.split()
        symbol = entry_items[0]
        entry_args = entry_items[1:]
        code = self.__codes.get(symbol,{})
        behavior = self.__behaviors.get(code.get('name'),{})
        obs_behavior = keys_keep(behavior, {'name','kind'})
        obs_code = keys_lose(code, {'symbol','name','args'})
        obs_args = dict(zip(code.get('args',[]), entry_args))
        return join_dicts(obs_entry, obs_behavior, obs_code, obs_args)
    
    def validate_obs(obs):
        """
        Check an observation against the ethogram. If the observation is valid
        under the ethogram, returns an empty list. If the observation is not
        valid, returns a list of the keys in the observation that conflict with
        the ethogram.
        """
        name = obs.get('name')
        if name not in self.__behaviors:
            return ['name']
        conflicts = []
        behavior = self.__behaviors[name]
        kind = behavior['kind']
        if kind != obs.get('kind'):
            conflicts.append('kind')
        if (kind in ('state', 'binary') and 
                obs.get('value') not in behavior['values']):
            conflicts.append('value')
        return conflicts
    
    def save(self):
        raise NotImplementedError
    
    @staticmethod
    def new_from_file(fileobj):
        """
        Load an ethogram from a text file. The file format should look something
        like this:
        
        name: Name of the ethogram
        behavior: kind=moment name=instant-behavior
        behavior: kind=state name=state-behavior values=list,of,possible,values
        behavior: kind=binary name=binary-behavior
        behavior: kind=variable name=variable-name
        code: symbol=sym1 name=instant-behavior
        code: symbol=sym2 name=state-behavior value=list
        code: symbol=sym3 name=state-behavior value=of
        code: symbol=sym4 name=binary-behavior value=True
        code: symbol=sym5 name=binary-behavior value=False
        code: symbol=sym6 name=variable-name args=value
        """
        ethogram = Ethogram()
        for line in fileobj:
            head,sep,tail = line.partition(':')
            head = head.strip()
            tail = tail.strip()
            if head.startswith('#'):
                pass
            elif head == 'name':
                ethogram.name = tail
            elif head == 'behavior':
                behav_def = parse_keyvals(tail)
                ethogram.add_behavior(**behav_def)
            elif head == 'code':
                code_def = parse_keyvals(tail)
                ethogram.add_code(**code_def)
        return ethogram
    
    def __validate_obs(self, obs):
        behavior = self.__behaviors[obs['name']]
        obs_kind = obs['kind']
        if obs_kind != behavior['kind']:
            raise ValueError('Observation kind does not match behavior kind')
        if obs_kind in ('state', 'binary') and 'value' in obs:
            value = obs['value']
            valid_values = behavior.get('values', [])
            if value not in valid_values:
                raise ValueError('Observation value not valid for behavior')

class CodeError(ValueError):
    pass

class ObservationSet(collections.Sequence):
    """
    Deprecated. Observation sets right now are just represented as lists of
    dict objects. I may try to resuscitate an actual class for this later.
    """
    def __init__(self, ethogram, observer, obs_source):
        """
        Create a new observation set using an ethogram
        """
        self.ethogram = ethogram
        self.observer = observer
        self.obs_source = obs_source
        self.__observations = []
    
    def __getitem__(self, index):
        return self.__observations[index]
    
    def __len__(self):
        return len(self.__observations)
    
    def __iter__(self):
        return iter(self.__observations)
    
    def __delitem__(self, index):
        del self.__observations[index]
    
    def add_observation(self, time, entry):
        new_obs = self.ethogram.get_prototype(entry)
        new_obs['time'] = time
        self.__observations.append(new_obs)
    
    def save(self, fileobj):
        fileobj.write('observer: ' + self.observer + '\n')
        fileobj.write('obs_source: ' + self.obs_source + '\n')
        for obs in self.__observations:
            fileobj.write('obs: ' + as_keyvalstr(obs) + '\n')
    
    @staticmethod
    def new_from_file(ethogram, fileobj):
        new_obs_set = ObservationSet(ethogram, '', '')
        for line in fileobj:
            head,sep,tail = line.partitition(':')
            head = head.strip()
            tail = tail.strip()
            if head=='observer':
                new_obs_set.observer = tail
            elif head=='obs_source':
                new_obs_set.obs_source = tail
            elif head=='obs':
                obs_dict = parse_keyvals(tail)
                new_obs_set.__observations.append(obs_dict)
        return new_obs_set

class NameSet(frozenset):
    """
    A helper datatype to represent a set of names, mostly for the "values" field
    for state behaviors in the ethogram. If the initialization value is a string
    or a non-iterable, essentially becomes a frozenset of length 1 containing
    the input. If initialized with some other iterable, the same as calling
    frozenset on the iterable.
    """
    def __new__(cls, initial):
        if isinstance(initial, str):
            initial = [initial]
        elif isinstance(initial, collections.Iterable):
            initial = (str(s) for s in initial)
        else:
            initial = [str(initial)]
        return frozenset.__new__(cls, initial)

class DictViewer(collections.Mapping):
    """
    A helper datatype to give a read-only view of a dictionary.
    """
    def __init__(self, dictobj):
        self.__dictobj = dictobj
    
    def __contains__(self, element):
        return element in self.__dictobj
    
    def __len__(self):
        return len(self.__dictobj)
    
    def __iter__(self):
        return iter(self.__dictobj)
    
    def __getitem__(self, key):
        return self.__dictobj[key]
    
    def __repr__(self):
        return repr(self.__dictobj)

def parse_keyvals_orig(keyvalstr):
    r"""
    Convert a string of the form 'a=b c=d' to a dict with key=value. These 
    characters must be escaped with a \:
        Keys:   whitespace = \
        Values: whitespace , \
    All keys are interpreted as strings. Values are also interpreted as strings
    unless they contain an unescaped comma, in which case they are a tuple of
    strings split at the commas.
    """
    # Regular expression to match the pattern 'key=value' delimited on either
    # side by whitespace, and allowing backslash to escape = or whitespace:
    keyrex = r'((?:\\[\\\s=]|[^=\s])+)'
    valrex = r'((?:\\[\\\s]|\S)*)'
    rex = keyrex + '=' + valrex
    keyvals = re.findall(rex, keyvalstr)
    newdict = dict()
    for key,val in keyvals:
        # Unescape escaped characters:
        key = re.sub(r'\\(.)', r'\1', key)
        # Regular expression to split the value at unescaped commas:
        val_list = re.findall(r'(?:\\[\\,]|[^,])*', val)[::2]
        # Unescape escaped characters in each element of the list:
        val_list = [re.sub(r'\\(.)', r'\1', el) for el in val_list]
        if len(val_list) == 1:
            val = val_list[0]
        else:
            val = tuple(val_list)
        newdict[key] = val
    return newdict

def parse_keyvals(keyvalstr):
    r"""
    Convert a string of the form 'a=b c=d' to a dict with key=value. These 
    characters must be escaped with a \:
        Keys:   whitespace = \
        Values: whitespace , \
    All keys are interpreted as strings. Values are also interpreted as strings
    unless they contain an unescaped comma, in which case they are a tuple of
    strings split at the commas. Alternatively, values may begin and end with a
    double-quote ", in which case only double-quotes must be escaped.
    """
    # Find everything of the form key=value:
    word_ex = r'"(?:\\.|[^"])*"|(?:\\.|[^\s=])+'
    keyval_rex = r'(?P<key>{0})=(?P<val>{0})?'.format(word_ex)
    items = re.finditer(keyval_rex, keyvalstr)
    strip_escapes = lambda s: re.sub(r'\\(.)', r'\1', s)
    newdict = dict()
    for match in items:
        key = match.group('key')
        if key[0]=='"':
            key = key[1:-1]
        key = strip_escapes(key)
        val = match.group('val')
        if val[0]=='"':
            # Value has the form '"some string"'
            val = strip_escapes(val[1:-1])
        elif ',' in val:
            # Value has the form 'list,of,items'
            # Potential bug: if every comma is escaped, we're still tuple-ing
            val = re.findall(r'(?:\A|,)((?:\\.|[^,])*)', val)
            val = tuple(strip_escapes(elem) for elem in val)
        else:
            # Value has the form 'word'
            val = strip_escapes(val)
        newdict[key] = val
    return newdict

def as_keyvalstr(dictobj):
    r"""
    Get a key=value string representation of a dictionary object. All keys and
    values are converted to strings, with some special characters escaped with
    \:
        Keys:   whitespace = \
        Values: whitespace , \
    Additionally, if a value is an iterable and not a string, it is written as a
    comma-separated list with each element escaped according to the rules for
    values.
    """
    keyvals = []
    for key,val in dictobj.items():
        keystr = re.sub(r'([\s\\=])', r'\\\1', key)
        if not isinstance(val, str) and isinstance(val, collections.Iterable):
            val_list = [re.sub(r'([\s\\,])', r'\\\1', str(v)) for v in val]
            valstr = ','.join(val_list)
        else:
            valstr = re.sub(r'([\s\\,])', r'\\\1', str(val))
        keyvals.append(keystr + '=' + valstr)
    return ' '.join(keyvals)

def join_dicts(*pargs, **kargs):
    """
    Convenience function to construct one dict from many. The result has all
    the keys from the inputs, with values taken from those inputs. If a key
    appears in two or more inputs, its value is taken from the leftmost input.
    """
    new_dict = kargs
    for item in reversed(pargs):
        new_dict.update(item)
    return new_dict

def keys_keep(dictobj, keep):
    """
    Convenience function to construct a new dict from an existing one, keeping
    only certain keys if present.
    """
    return dictkeys_setop(operator.and_, dictobj, keep)

def keys_lose(dictobj, lose):
    """
    Convenience function to construct a new dict from an existing one,
    discarding certain keys if present.
    """
    return dictkeys_setop(operator.sub, dictobj, lose)

def dictkeys_setop(op, a, b):
    """
    Perform set operations on two dicts based on their keys.
    """
    if isinstance(b,collections.Mapping):
        return dict((key, a.get(key, b.get(key))) for key in op(set(a),set(b)))
    else:
        return dict((key, a.get(key)) for key in op(set(a),set(b)))

