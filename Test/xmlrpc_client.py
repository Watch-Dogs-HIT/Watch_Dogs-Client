import xmlrpclib

server_power = xmlrpclib.ServerProxy("http://localhost:8081/")
print server_power.get_a_dict()
print "3**2 = %d" %(server_power.get_power(3,2))
print "2**5 = %d" %(server_power.get_power(2,5))
