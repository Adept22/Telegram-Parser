import re

from processors.ApiProcessor import ApiProcessor

class Entity(object):
    _attrs = []
    _type = ''
    
    def __init__(self, _dict):
        if type(_dict) == dict:
            raise Exception('Unexpected entity dictionary')
            
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
    
    def from_api(self, _class: 'Entity', entity, nullable=False):
        if isinstance(entity, dict):
            api_entity = ApiProcessor().get(_class.api_path, entity)
            
            entity = _class(api_entity)
            
        if (nullable == False and entity == None) or not isinstance(entity, _class):
            raise TypeError(f'Unexpected entity type {type(entity).__name__}. Expects dictionary{", NoneType" if nullable == True else ""} or {type(_class).__name__}.')
        
        return entity