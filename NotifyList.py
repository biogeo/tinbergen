
import collections;

class NotifyList(list):
    def __setitem__(self, key, value):
        print "Setting %s to %s" % (key, value);
        list.__setitem__(self, key, value);

class TBEventDef(dict):
    def __init__(self, data, notifier=None):
        dict.__init__(self, data);
        self.notifier = notifier;
