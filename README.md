# Python interface to Stanford Core NLP tools

This a Python wrapper for Stanford NLP group's Java-based [CoreNLP tools](http://nlp.stanford.edu/software/corenlp.shtml).  It can either be imported as a module or run as a server. Because it uses many large trained models (3GB Ram), this is probably best run as a server.

This uses [SimpleJSONRPCServer](http://www.freenet.org.nz/dojo/pyjson/) and [python-progressbar](http://code.google.com/p/python-progressbar/)

    java -cp stanford-corenlp-2010-11-12.jar:stanford-corenlp-models-2010-11-06.jar:xom-1.2.6.jar:xom.jar:jgraph.jar:jgrapht.jar -Xmx3g edu.stanford.nlp.pipeline.StanfordCoreNLP 

