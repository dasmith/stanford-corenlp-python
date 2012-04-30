# Python interface to Stanford Core NLP tools v1.2.0

This is a Python wrapper for Stanford University's NLP group's Java-based [CoreNLP tools](http://nlp.stanford.edu/software/corenlp.shtml).  It can either be imported as a module or run as an JSON-RPC server. Because it uses many large trained models (requiring 3GB RAM on 64-bit machines and usually a few minutes loading time), most applications will probably want to run it as a server.

It requires [pexpect](http://www.noah.org/wiki/pexpect).  The repository includes and uses code from [jsonrpc](http://www.simple-is-better.org/rpc/) and [python-progressbar](http://code.google.com/p/python-progressbar/).

There's not much to this script.  I decided to create it after having problems using other Python wrappers to Stanford's dependency parser. 
First the JPypes approach used in [stanford-parser-python](http://projects.csail.mit.edu/spatial/Stanford_Parser) had trouble initializing a JVM on two separate computers.  Next, I discovered I could not use a 
[Jython solution](http://blog.gnucom.cc/2010/using-the-stanford-parser-with-jython/) because the Python modules I needed did not work in Jython.

It runs the Stanford CoreNLP jar in a separate process, communicates with the java process using its command-line interface, and makes assumptions about the output of the parser in order to parse it into a Python dict object and transfer it using JSON.  The parser will break if the output changes significantly, but it has been tested on **Core NLP tools version 1.3.1** released 2012-04-09.

## Download and Usage 

You should have [downloaded](http://nlp.stanford.edu/software/corenlp.shtml#Download) and unpacked the tgz file containing Stanford's CoreNLP package.  By default, `corenlp.py` looks for the Stanford Core NLP folder as a subdirectory of where the script is being run.

In other words: 

    sudo pip install pexpect unidecode   # unidecode is optional
	git clone git://github.com/dasmith/stanford-corenlp-python.git
	cd stanford-corenlp-python.git
    wget http://nlp.stanford.edu/software/stanford-corenlp-2012-04-09.tgz
    tar xvfz stanford-corenlp-2012-04-09.tgz

Then, to launch a server:

    python corenlp.py

Optionally, you can specify a host or port:

    python corenlp.py -H 0.0.0.0 -p 3456

That will run a public JSON-RPC server on port 3456.

Assuming you are running on port 8080, the code in `client.py` shows an example parse: 

    import jsonrpc
    from simplejson import loads
    server = jsonrpc.ServerProxy(jsonrpc.JsonRpc20(),
            jsonrpc.TransportTcpIp(addr=("127.0.0.1", 8080)))

    result = loads(server.parse("hello world"))
    print "Result", result

That returns a list containing a dictionary for each sentence, with keys `text`, `tuples` of the dependencies, and `words`:

		{u'sentences': [{u'parsetree': u'(ROOT (NP (JJ hello) (NN world)))', 
						 u'text': u'hello world', 
						 u'tuples': [[u'amod', u'world', u'hello'], 
						             [u'root', u'ROOT', u'world']], 
						 u'words': [[u'hello', {u'NamedEntityTag': u'O', 
						                        u'CharacterOffsetEnd': u'5', 
						                        u'CharacterOffsetBegin': u'0', 
						                        u'PartOfSpeech': u'UH', 
						                        u'Lemma': u'hello'}], 
						            [u'world', {u'NamedEntityTag': u'O', 
						                        u'CharacterOffsetEnd': u'11', 
						                        u'CharacterOffsetBegin': u'6', 
						                        u'PartOfSpeech': u'NN', 
						                        u'Lemma': u'world'}]]}]}
    
To use it in a regular script or to edit/debug it (because errors via RPC are opaque), load the module instead:

    from corenlp import *
    corenlp = StanfordCoreNLP()  # wait a few minutes...
    corenlp.parse("Parse an imperative sentence, damnit!")

### Parsing Imperative Sentences

I added a function called `parse_imperative` that introduces a dummy pronoun to overcome the problems that dependency parsers have with **imperative sentences**, dealing with only one at a time. 

    corenlp.parse("stop smoking")
    >> [{"text": "stop smoking", "tuples": [["nn", "smoking", "stop"]], "words": [["stop", {"NamedEntityTag": "O", "CharacterOffsetEnd": 4, "Lemma": "stop", "PartOfSpeech": "NN", "CharacterOffsetBegin": 0}], ["smoking", {"NamedEntityTag": "O", "CharacterOffsetEnd": 12, "Lemma": "smoking", "PartOfSpeech": "NN", "CharacterOffsetBegin": 5}]]}]

    corenlp.parse_imperative("stop smoking")
    >> [{"text": "stop smoking", "tuples": [["xcomp", "stop", "smoking"]], "words": [["stop", {"NamedEntityTag": "O", "CharacterOffsetEnd": 8, "Lemma": "stop", "PartOfSpeech": "VBP", "CharacterOffsetBegin": 4}], ["smoking", {"NamedEntityTag": "O", "CharacterOffsetEnd": 16, "Lemma": "smoke", "PartOfSpeech": "VBG", "CharacterOffsetBegin": 9}]]}]

Only with the dummy pronoun does the parser correctly identify the first word, *stop*, to be a verb.

**Coreferences** are returned in the `coref` key, only when they are found as a list of references, e.g. `{'coref': [['he','John']]}`.

<!--
## Adding WordNet

Note: wordnet doesn't seem to be supported using this approach.  Looks like you'll need Java.

Download WordNet-3.0 Prolog:  http://wordnetcode.princeton.edu/3.0/WNprolog-3.0.tar.gz
tar xvfz WNprolog-3.0.tar.gz 

-->

## Questions 

**Stanford CoreNLP tools require a large amount of free memory**.  Java 5+ uses about 50% more RAM on 64-bit machines than 32-bit machines.  32-bit machine users can lower the memory requirements by changing `-Xmx3g` to `-Xmx2g` or even less.
If pexpect timesout while loading models, check to make sure you have enough memory and can run the server alone without your kernel killing the java process:

    java -cp stanford-corenlp-2011-09-16.jar:stanford-corenlp-2011-09-14-models.jar:xom.jar:joda-time.jar -Xmx3g edu.stanford.nlp.pipeline.StanfordCoreNLP -props default.properties

You can reach me, Dustin Smith, by sending a message on GitHub or through email (contact information is available [on my webpage](http://web.media.mit.edu/~dustin)).

# Contributors


