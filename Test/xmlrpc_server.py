import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer


def get_power(n, m):
    return n ** m


def get_a_dict():
    return {'test': 'test'}


server = SimpleXMLRPCServer(("0.0.0.0", 8081))
print "start service get power on 0.0.0.0 8081..."
server.register_function(get_power, "get_power")
server.serve_forever()
