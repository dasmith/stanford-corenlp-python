import jsonrpc
try:
    import json
except ImportError:
    import simplejson as json

server = jsonrpc.ServerProxy(jsonrpc.JsonRpc20(),
        jsonrpc.TransportTcpIp(addr=("127.0.0.1", 8080)))

# call a remote-procedure 
result = json.loads(server.parse("hello world"))
print "Result", result

# now handles imperatives
result = json.loads(server.parse("stop smoking"))
print "Result", result

result = json.loads(server.parse("eat dinner"))
print "Result", result

import pprint
result = json.loads(server.parse("Hello world!  It is so beautiful."))
pprint.pprint(result)

# example using nltk
from nltk.tree import *
tree = Tree.parse(result['sentences'][0]['parsetree'])
print tree
print tree.leaves()
