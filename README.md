# Python interface to Stanford Core NLP tools

This a Python wrapper for Stanford University's NLP group's Java-based [CoreNLP tools](http://nlp.stanford.edu/software/corenlp.shtml).  It can either be imported as a module or run as an JSON-RPC server. Because it uses many large trained models (requiring 3GB RAM and usually a few minutes loading time), most applications will probably want to run it as a server.

It requires [pexpect](http://www.noah.org/wiki/pexpect).  Included dependencies are [jsonrpc](http://www.simple-is-better.org/rpc/) and [python-progressbar](http://code.google.com/p/python-progressbar/).

There's not much to this script.  I decided to create it after having trouble initializing a JVM using JPypes on two different machines. 

It runs the Stanford CoreNLP jar in a separate process, communicates with the java process using its command-line interface, and makes assumptions about the output of the parser in order to parse it into a Python dict object and transfer it using JSON.  The parser will break if the output changes significantly. I have only tested this on **Core NLP tools version 1.0.2** released 2010-11-12.

## Download and Usage 

You should have [downloaded](http://nlp.stanford.edu/software/corenlp.shtml#Download) and unpacked the tgz file containing Stanford's CoreNLP package.  Then copy all of the python files from this repository into the `stanford-corenlp-2010-11-12` folder.

In other words: 

    sudo pip install pexpect
    wget http://nlp.stanford.edu/software/stanford-corenlp-v1.0.2.tgz
    tar xvfz stanford-corenlp-v1.0.2.tgz
    cd stanford-corenlp-2010-11-12
    git clone git://github.com/dasmith/stanford-corenlp-python.git
    mv stanford-corenlp-python/* .

Then, to launch a server:

    python server.py

Optionally, you can specify a host or port:

    python server.py -H 0.0.0.0 -p 3456

That will run a public JSON-RPC server on port 3456.

Assuming you are running on port 8080, the code in `client.py` shows an example parse: 

    import jsonrpc
    server = jsonrpc.ServerProxy(jsonrpc.JsonRpc20(),
            jsonrpc.TransportTcpIp(addr=("127.0.0.1", 8080)))

    result = server.parse("hello world")
    print "Result", result


Produces a list with a parsed dictionary for each sentence:

    Result [{"text": "hello world", 
            "tuples": [("amod", "world", "hello")], 
            "words": {"world": {"NamedEntityTag": "O", 
                                "CharacterOffsetEnd": "11", 
                                "Lemma": "world", 
                                "PartOfSpeech": "NN", 
                                "CharacterOffsetBegin": "6"}, 
                      "hello": {"NamedEntityTag": "O", 
                                "CharacterOffsetEnd": "5", 
                                "Lemma": "hello", 
                                "PartOfSpeech": "JJ", 
                                "CharacterOffsetBegin": 0}}}]


To use it in a regular script or to edit/debug, load the module instead:

    from server import *
    corenlp = StanfordCoreNLP() 
    corenlp.parse("Parse an imperative sentence, damnit!")

<!--
## Adding WordNet

Download WordNet-3.0 Prolog:  http://wordnetcode.princeton.edu/3.0/WNprolog-3.0.tar.gz
-->

## Questions 

If you think there may be a problem with this wrapper, first ensure you can run the Java program:

    java -cp stanford-corenlp-2010-11-12.jar:stanford-corenlp-models-2010-11-06.jar:xom-1.2.6.jar:xom.jar:jgraph.jar:jgrapht.jar -Xmx3g edu.stanford.nlp.pipeline.StanfordCoreNLP -props default.properties
