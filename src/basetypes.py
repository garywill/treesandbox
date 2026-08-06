from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


class EnhancedFalse:
    def __init__(self, dictObj, keyName):
        self.dictObj = dictObj
        self.keyName = keyName
    def _error(self):
        raise_exit(f"Program tries to stringlize or compare a non-defined member '{self.keyName}' of a dict-like obj: {str(self.dictObj)[:200]} ...")
    def __str__(self):
        self._error()
    def __repr__(self):
        self._error()
    def __bool__(self):
        return False
    def __eq__(self, other):
        return False
    def __ne__(self, other):
        return True
    def __lt__(self, other):
        self._error()
    def __le__(self, other):
        self._error()
    def __gt__(self, other):
        self._error()
    def __ge__(self, other):
        self._error()
    __hash__ = None


class EnhancedDictTempl(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict) and not isinstance(value, type(self)):
                self[key] = type(self)(value)
            elif isinstance(value, list):
                self[key] = self._convert_list(value)
    def _convert_list(self, lst):
        new_list = []
        for item in lst:
            if isinstance(item, dict) and not isinstance(item, type(self)):
                new_list.append(type(self)(item))
            elif isinstance(item, list):
                new_list.append(self._convert_list(item))
            else: new_list.append(item)
        return new_list
    def __setattr__(self, name, value):
        self[name] = value
    def __delattr__(self, name):
        try: del self[name]
        except KeyError: pass
    def __setitem__(self, key, value):
        processed_value = value
        if isinstance(value, dict) and not isinstance(value, type(self)):
            processed_value = type(self)(value)
        elif isinstance(value, list):
             processed_value = self._convert_list(value)
        super().__setitem__(key, processed_value)
class Dict(EnhancedDictTempl):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        try: return self[name]
        except :
            raise
class DictFALSE(EnhancedDictTempl):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
        try: return self[name]
        except KeyError:
            return EnhancedFalse(self, name)
    def __getitem__(self, key):
        try: return super().__getitem__(key)
        except KeyError:
            return EnhancedFalse(self, key)
class DictNone(EnhancedDictTempl):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        try: return self[name]
        except :
            return None
    def __getitem__(self, key):
        try: return super().__getitem__(key)
        except KeyError:
            return None
D = Dict  # Raises an error when trying to access a non-existent key.
d = DictFALSE  # Returns EnhancedFalse when trying to access a non-existent key.
dn = DictNone  # Returns None when trying to access a non-existent key.

