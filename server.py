"""
This is a Python interface to Stanford Core NLP tools.

It can be imported as a module or run as a server.

Dustin Smith, 2011
"""
import pexpect
from wsgiref import simple_server
from webob import Request, Response
from webob import exc
import optparse
from wsgiref import simple_server
from simplejson import loads, dumps
import traceback
import sys
import os

from progressbar import *

"""
if not os.path.exists()
"""

class StanfordCoreNLPServer(object):
    """
    Serve the given object via json-rpc (http://json-rpc.org/)
    """
    def __init__(self):	
        print "Initializing Server"
        jars = ["stanford-corenlp-2010-11-12.jar", "stanford-corenlp-models-2010-11-06.jar",
        "jgraph.jar", "jgrapht.jar", "xom.jar"]
        classname = "edu.stanford.nlp.pipeline.StanfordCoreNLP"
        javapath = "java"

        for jar in jars:
            if not os.path.exists(jar):
                print "Error! Cannot locate %s" % jar
                sys.exit(1)

        self._server = pexpect.spawn("%s -Xmx3g -cp %s %s" % (javapath, ':'.join(jars), classname))

        widgets = ['Starting Server: ', Fraction(), ' ', Bar(marker=RotatingMarker()), ' ', ETA(300)]
        pbar = ProgressBar(widgets=widgets, maxval=5, force_update=True).start()
        self._server.expect("done.")
        pbar.update(1)
        self._server.expect("done.")
        pbar.update(2)
        self._server.expect("done.")
        pbar.update(3)
        self._server.expect("Entering interactive shell.")
        pbar.finish()
        print self._server.before
        
    
    def __call__(self, environ, start_response):
        req = Request(environ)
        try:
            resp = self.process(req)
        except ValueError, e:
            resp = exc.HTTPBadRequest(str(e))
        except exc.HTTPException, e:
            resp = e
        return resp(environ, start_response)

    def parse(self, str):
	print "Input", str
	print p.stdout.readline()
 	out, err = self._server.communicate(str)
	print "Result"
	print "\t OUT:", out
	print "\t ERR:", err
	print p.stdout.readline()
	return out


	
    def process(self, req):
        if not req.method == 'POST':
            raise exc.HTTPMethodNotAllowed( "Only POST allowed", allowed='POST').exception
        try:
            json = loads(req.body)
        except ValueError, e:
            raise ValueError('Bad JSON: %s' % e)
        try:
            method = json['method']
            params = json['params']
            id = json['id']
        except KeyError, e:
            raise ValueError( "JSON body missing parameter: %s" % e)
        if method in ["process",'__init__']:
            raise exc.HTTPForbidden( "Bad method name %s" % method).exception
        if not isinstance(params, list):
            raise ValueError( "Bad params %r: must be a list" % params)
        try:
            method = getattr(self, method)
        except AttributeError:
            raise ValueError( "No such method %s" % method)
        try:
            result = method(*params)
        except:
            text = traceback.format_exc()
            exc_value = sys.exc_info()[1]
            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=str(exc_value),
                error=text)
            return Response(
                status=500,
                content_type='application/json',
                body=dumps(dict(result=None,
                                error=error_value,
                                id=id)))
        return Response(
            content_type='application/json',
            body=dumps(dict(result=result,
                            error=None,
                            id=id)))



if __name__ == '__main__':
    parser = optparse.OptionParser(
        usage="%prog [OPTIONS] MODULE:EXPRESSION")
    parser.add_option(
        '-p', '--port', default='8080',
        help='Port to serve on (default 8080)')
    parser.add_option(
        '-H', '--host', default='127.0.0.1',
        help='Host to serve on (default localhost; 0.0.0.0 to make public)')
    options, args = parser.parse_args()
    parser.print_help()
    app = StanfordCoreNLPServer()
    server = simple_server.make_server( options.host, int(options.port), app)
    print 'Serving on http://%s:%s' % (options.host, options.port)
    server.serve_forever()




