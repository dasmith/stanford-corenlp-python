# Python interface to Stanford Core NLP tools

This a Python wrapper for Stanford University's NLP group's Java-based [CoreNLP tools](http://nlp.stanford.edu/software/corenlp.shtml).  It can either be imported as a module or run as an JSON-RPC server. Because it uses many large trained models (requiring 3GB RAM and usually a few minutes loading time), most applications will probably want to run it as a server.

There's not much to this script.

It requires `pexpect`.

This uses [jsonrpc](http://www.simple-is-better.org/rpc/) and [python-progressbar](http://code.google.com/p/python-progressbar/), which are included in this repository.


## Download and Usage 

You should have [downloaded](http://nlp.stanford.edu/software/corenlp.shtml#Download) and unpacked the tgz file containing Stanford's Core-NLP package.  Then copy all of the python files from this repository into the `stanford-corenlp-2010-11-12` folder.

Then, to launch a server:

    python server.py

Optionally, specify a host or port:

    python server.py -H 0.0.0.0 -p 3456

To run a public JSON-RPC server on port 3456.

See `client.py` for example of how to connect with a client.

<!--
## Adding WordNet

Download WordNet-3.0 Prolog:  http://wordnetcode.princeton.edu/3.0/WNprolog-3.0.tar.gz
-->

## Questions 

I have only tested this on **Core NLP tools version 1.0.2** released 2010-11-12.

If you think there may be a problem with this wrapper, first ensure you can run the Java program:

    java -cp stanford-corenlp-2010-11-12.jar:stanford-corenlp-models-2010-11-06.jar:xom-1.2.6.jar:xom.jar:jgraph.jar:jgrapht.jar -Xmx3g edu.stanford.nlp.pipeline.StanfordCoreNLP -props default.properties
