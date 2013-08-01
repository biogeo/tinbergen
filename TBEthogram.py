# TBEthogram.py
# A class for representing Tinbergen ethograms

import yaml
import operator
import collections
import copy

class FrozenDict(collections.Mapping):
    def __init__(self, data):
        self._data = dict(copy.deepcopy(data))
    
    def __len__(self):
        return len(self._data)
    
    def __iter__(self):
        return iter(self._data)
    
    def __getitem__(self, key):
        return self._data.get(key)
    
    def __repr__(self):
        return type(self).__name__ + "(" + repr(self._data) + ")"

class Ethogram(object):
    """
    A representation of a Tinbergen ethogram.
    """
    
    def __init__(self):
        self.name = ''
        self.description = ''
        self.events = []
        self.codes = []
        self.interactions = []
    
    @classmethod
    def load_yaml(cls, filename):
        ethogram = cls()
        with open(filename) as f:
            raw = yaml.load(f)
        if 'name' in raw:
            ethogram.name = raw['name']
        if 'description' in raw:
            ethogram.description = raw['description']
        if 'entries' in raw:
            events = [cls.Event(e)
                for e in raw['entries'] if 'event' in e]
            ethogram.events = dict(zip([e.name for e in events], events))
            interactions = [cls.Interaction(i)
                for i in raw['entries'] if 'interaction' in i]
            ethogram.interactions = dict(zip([i.name for i in interactions],
                interactions))
            codes = [cls.Code(c)
                for c in raw['entries'] if 'code' in c]
            ethogram.codes = dict(zip([c.code for c in codes], codes))
        return ethogram
    
    class Entry(FrozenDict):
        pass
    
    class Event(Entry):
        @property
        def name(self):
            return self._data['event']
        
        @property
        def type(self):
            return self._data['type']
        
        @property
        def values(self):
            return self._data.get('values', ())
        
        def __init__(self, data):
            if 'event' not in data or 'type' not in data:
                raise ValueError(str(data))
            super(type(self),self).__init__(data)
    
    class Interaction(Entry):
        _validTypes = ('moment', 'interval')
        
        @property
        def name(self):
            return self._data['interaction']
        
        @property
        def type(self):
            return self._data['type']
        
        @property
        def roles(self):
            return self._data['roles']
        
        def __init__(self, data):
            if 'interaction' not in data or 'type' not in data \
                    or 'roles' not in data:
                raise ValueError
            if not isinstance(data['interaction'], basestring):
                raise ValueError
            if data['type'] not in self._validTypes:
                raise ValueError
            data['roles'] = tuple(data['roles'])
            super(type(self),self).__init__(data)
    
    class Code(Entry):
        @property
        def code(self):
            return self._data['code']
        
        @property
        def argNames(self):
            return self._data.get('args', ())
        
        @property
        def prototype(self):
            return self._data['obs']
        
        def __init__(self, data):
            if 'code' not in data or 'obs' not in data:
                raise ValueError
            if not isinstance(data['code'], basestring):
                raise ValueError
            data['obs'] = ObservationPrototype(data['obs'])
            super(type(self),self).__init__(data)
        
        def make_obs(self, args):
            return self.prototype.make_obs(dict(zip(self.argNames, args)))

class ObservationPrototype(FrozenDict):
    def __init__(self, data):
        super(type(self),self).__init__(data)
        if 'event' in self._data:
            self.type = 'event'
        elif 'terminate' in self._data:
            self.type = 'terminate'
        elif 'interaction' in self._data:
            self.type = 'interaction'
        else:
            self.type = None
        
        self._freeVarPaths = {}
        self._locate_free_vars(self._data)
    
    def make_obs(self, args):
        newObs = copy.deepcopy(self._data)
        for key in set(args).intersection(set(self._freeVarPaths)):
            for path in self._freeVarPaths[key]:
                hierarchy_set(newObs, path, args[key])
        return newObs
    
    def _locate_free_vars(self, node, curPath=[]):
        if isinstance(node, basestring):
            if node.startswith('='):
                if node[1:] in self._freeVarPaths:
                    self._freeVarPaths[node[1:]].append(curPath)
                else:
                    self._freeVarPaths[node[1:]] = [curPath]
        elif isinstance(node, collections.Sequence):
            for i in range(len(node)):
                self._locate_free_vars(node[i], curPath + [i])
        elif isinstance(node, collections.Mapping):
            for key in node:
                self._locate_free_vars(node[key], curPath + [key])

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

def hierarchy_get(root, path):
    """
    Get an item in a "hierarchy" of sequences and mappings. path is a sequence
    of keys to locate the item. For example, the expression
        hierarchy_get(root, (a,b,c,d))
    is just
        root[a][b][c][d]
    This is just a convenience to make it easier to deal with situations when
    the "depth" of the hierarchy is known only from the number of keys. I 
    imagine there's probably a better, more Pythonic way to do this, but I don't
    know it yet.
    """
    item = root
    for key in path:
        item = item[key]
    return item

def hierarchy_set(root, path, value):
    """
    Set an item in a "hierarchy" of sequences and mappings. Works like
    hierarchy_get, but for setting.
        hierarchy_set(root, (a,b,c,d), val)
    is the same as
        root[a][b][c][d] = val
    """
    item = root
    for key in path[:-1]:
        item = item[key]
    item[path[-1]] = value

