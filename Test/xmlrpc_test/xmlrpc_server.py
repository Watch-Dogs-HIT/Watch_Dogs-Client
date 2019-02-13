import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer


def get_power(n, m):
    return n ** m


def get_a_dict():
    return {'test': 'test'}


class A(object):

    @staticmethod
    def add(x, y):
        return x + y

    def add_1(self, x, y):
        return x + y

print A.add(2,3)
server = SimpleXMLRPCServer(("0.0.0.0", 8081))
print "start service get power on 0.0.0.0 8081..."
server.register_function(get_power, "get_power")
server.serve_forever()
