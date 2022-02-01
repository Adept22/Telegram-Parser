import re

from processors.ApiProcessor import ApiProcessor

class Entity(object):
    _attrs = []
    _type = ''
    
    def __init__(self, _dict):
        if not 'id' in _dict or _dict['id'] is None:
            raise Exception('Unexpected entity id')
        
        self.dict = _dict
    
    def from_dict(self):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in self.dict:
            setattr(self, pattern.sub('_', key).lower(), self.dict[key])
        
        return self
    
    def save(self):        
        dict = {}
        
        for key in self.__dict__:
            if not key in self._attrs:
                components = key.split('_')
                
                dict[components[0] + ''.join(x.title() for x in components[1:])] = self.__dict__[key]
                
        ApiProcessor().set(self._type, dict)