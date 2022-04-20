import multiprocessing
import os, socket
import services

def init():
    global parser
    
    if "PARSER_ID" in os.environ:
        parser = services.ApiService().get('telegram/parser', {'id': os.environ['PARSER_ID']})
        
        # if parser["host"]["localIp"] != socket.gethostbyname(socket.gethostname()):
        #     raise Exception("Can't start parser. Parser host local ip doesn't equal with current host local ip.")
        
        services.ApiService().set('telegram/parser', {'id': parser['id'], 'status': 'running'})
    else:
        raise Exception("Can't start parser. Environment variable 'PARSER_ID' not set.")
