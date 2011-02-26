from webob import Request
from wsgiproxy.exactproxy import proxy_exact_request
from simplejson import loads, dumps

proxy = proxy_exact_request        

json = dict(method='parse', id=None, params=['this is a sentence'])
req = Request.blank("http://localhost:8080")
req.method = 'POST'
req.content_type = 'application/json'
req.body = dumps(json)
resp = req.get_response(proxy)
json = loads(resp.body)
print json

