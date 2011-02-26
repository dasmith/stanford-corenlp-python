"""
This is a Python interface to Stanford Core NLP tools.

It can be imported as a module or run as a server.

Works with the 2010-11-22 release.

Dustin Smith, 2011
"""
import pexpect
from simplejson import loads, dumps
import optparse
import sys
import os

import jsonrpc

from progressbar import *

class StanfordCoreNLP(object):
    
    def __init__(self):	
        """
        Checks the location of the jar files.
        Spawns the server as a process.
        """

        jars = ["stanford-corenlp-2010-11-12.jar", 
                "stanford-corenlp-models-2010-11-06.jar",
                "jgraph.jar",
                "jgrapht.jar",
                "xom.jar"]

        classname = "edu.stanford.nlp.pipeline.StanfordCoreNLP"
        javapath = "java"

        for jar in jars:
            if not os.path.exists(jar):
                print "Error! Cannot locate %s" % jar
                sys.exit(1)
        
        # spawn the server
        self._server = pexpect.spawn("%s -Xmx3g -cp %s %s" % (javapath, ':'.join(jars), classname))

        # show progress bar while loading the models
        widgets = ['Starting Server: ', Fraction(), ' ', Bar(marker=RotatingMarker()), ' ', ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=5, force_update=True).start()
        self._server.expect("done.", timeout=20) # Load pos tagger model (~5sec)
        pbar.update(1)
        self._server.expect("done.", timeout=200) # Load NER-all classifier (~33sec)
        pbar.update(2)
        self._server.expect("done.", timeout=600) # Load NER-muc classifier (~60sec)
        pbar.update(3)
        self._server.expect("done.", timeout=600) # Load CoNLL classifier (~50sec)
        pbar.update(4)
        self._server.expect("done.", timeout=200) # Loading PCFG (~3sec)
        pbar.update(5)
        self._server.expect("Entering interactive shell.")
        pbar.finish()
        print self._server.before
    
    def parse(self, text):
        self._server.sendline(text)
        return self._server.readlines()


if __name__ == '__main__':
    parser = optparse.OptionParser(usage="%prog [OPTIONS]")
    parser.add_option(
        '-p', '--port', default='8080',
        help='Port to serve on (default 8080)')
    parser.add_option(
        '-H', '--host', default='127.0.0.1',
        help='Host to serve on (default localhost; 0.0.0.0 to make public)')
    options, args = parser.parse_args()
    parser.print_help()
    server = jsonrpc.Server(jsonrpc.JsonRrpc20(), 
                            jsonrpc.TransportTcpIp(addr=(options.host, int(options.port))),
                            logfunc=jsonrpc.log_file("stanford_server.log"))
    corenlp = StanfordCoreNLP() 
    server.register_function(corenlp.parse)
    #server.register_instance(StanfordCoreNLP())
    print 'Serving on http://%s:%s' % (options.host, options.port)
    server.serve()




