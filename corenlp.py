#!/usr/bin/env python
"""
This is a Python interface to Stanford Core NLP tools.
It can be imported as a module or run as a server.

For more details:
    https://github.com/dasmith/stanford-corenlp-python

By Dustin Smith, 2011
"""
from simplejson import loads, dumps
import optparse
import sys
import os
import time
import re

import pexpect

import jsonrpc
from progressbar import *


def remove_id(word):
    """Removes the numeric suffix from the parsed recognized words: e.g. 'word-2' > 'word' """
    return word.count("-") == 0 and word or word[0:word.rindex("-")]

def parse_parser_results(text):
    state = 0
    tmp = {}
    results = []
    for line in text.split("\n"):
        if line.startswith("Sentence #"):
            state = 1
            if len(tmp.keys()) != 0:
                results.append(tmp)
                tmp = {}
        elif state == 1:
            tmp['text'] = line.strip()
            state = 2
        elif state == 2:
            if not line.startswith("[Text="):
                print line
                raise Exception("Parse error. Could not find [Text=")
            tmp['words'] = {} 
            exp = re.compile('\[([a-zA-Z0-9=. ]+)\]')
            matches  = exp.findall(line)
            for s in matches:
                # split into attribute-value list 
                av = re.split("=| ", s) 
                # make [ignore,ignore,a,b,c,d] into [[a,b],[c,d]]
                # and save as attr-value dict, convert numbers into ints
                tmp['words'][av[1]] = dict(zip(*[av[2:][x::2] for x in (0, 1)]))
                # the results of this can't be serialized into JSON?
                # av = zip(*[av[2:][x::2] for x in (0, 1)]) 
                # tmp['words'][av[1]] = dict(map(lambda x: (x[0], x[1].isdigit() and int(x[1]) or x[1]), av))
            state = 3
        elif state == 3:
            # skip over parse tree
            if not (line.startswith(" ") or line.startswith("(ROOT")):
                state = 4
                tmp['tuples'] = [] 
        if state == 4:
            # dependency parse
            line = line.rstrip()
            if not line.startswith(" ") and line.endswith(")"):
                split_entry = re.split("\(|, ", line[:-1]) 
                if len(split_entry) == 3:
                    rel, left, right = map(lambda x: remove_id(x), split_entry)
                    tmp['tuples'].append(tuple([rel,left,right]))
            elif "Coreference links" in line:
                state = 5
        elif state == 5:
            # coreference links.  Not yet implemented
            print "CR", line
    if len(tmp.keys()) != 0:
        results.append(tmp)
    return results

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
        # include the properties file, so you can change defaults
        # but any changes in output format will break parse_parser_results() 
        props = "-props default.properties" 

        for jar in jars:
            if not os.path.exists(jar):
                print "Error! Cannot locate %s" % jar
                sys.exit(1)
        
        # spawn the server
        self._server = pexpect.spawn("%s -Xmx3g -cp %s %s %s" % (javapath, ':'.join(jars), classname, props))
        
        print "Starting the Stanford Core NLP parser."
        self.state = "plays hard to get, smiles from time to time"
        # show progress bar while loading the models
        widgets = ['Loading Models: ', Fraction(), ' ',
                Bar(marker=RotatingMarker()), ' ', self.state ]
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
        print "NLP tools loaded."
        #print self._server.before

    def _parse(self, text):
        """
        This is the core interaction with the parser. 

        It returns a Python data-structure, while the parse()
        function returns a json object
        """
        self._server.sendline(text)
        # How much time should we give the parser to parse it?
        # the idea here is that you increase the timeout as a 
        # function of the text's length.
        
        # anything longer than 5 seconds requires that you also
        # increase timeout=5 in jsonrpc.py
        max_expected_time = min(6, 3 + len(text) / 20.0)
        print "Timeout", max_expected_time
        end_time = time.time() + max_expected_time 
        incoming = ""
        while True: 
            # Time left, read more data
            ch = self._server.read_nonblocking (2000, max_expected_time)
            freshlen = len(ch)
            time.sleep (0.0001)
            incoming = incoming + ch
            if "\nNLP>" in incoming:
                break
            if end_time - time.time() < 0:
                return {'error': "timed out after %f seconds" % max_expected_time, 
                        'input': text,
                        'output': incoming}
        results = parse_parser_results(incoming)
        return results

    def parse(self, text):
        """ 
        This function takes a text string, sends it to the Stanford parser,
        reads in the result, parses the results and returns a list
        with one dictionary entry for each parsed sentence, in JSON format.
        """
        # convert to JSON and return
        print "Request", text
        results = self._parse(text)
        print "Results", results
        return dumps(results)

    def parse_imperative(self, text):
        """
        This is kind of hacky way to deal with imperative statements.

        Takes an imperative string, adds a personal pronoun to the parse,
        and then removes it in the resulting parse.
        
        e.g. "open the door" gets parsed as "you open the door"

        """
        used_pronoun = None
        pronouns = ["you","he", "she","i"]
        for p in pronouns:
            if p not in text:
                used_pronoun = p
                break

        if not used_pronoun:
            return self.parse(text)
    
        text = used_pronoun+" "+text.lstrip()
        first_word = ""
        if len(text.split()) > 1:
            first_word = text.split()[1]
        result = self._parse(text)
        if result[0].has_key('text'):
            result[0]['text'] = text
            result[0]['tuples'] = filter(lambda x: not (x[1] == used_pronoun or x[2]
                    == used_pronoun), result[0]['tuples'])
            del result[0]['words'][used_pronoun] 
            return dumps(result)
        else:
            return dumps(result)

if __name__ == '__main__':
    parser = optparse.OptionParser(usage="%prog [OPTIONS]")
    parser.add_option(
        '-p', '--port', default='8080',
        help='Port to serve on (default 8080)')
    parser.add_option(
        '-H', '--host', default='127.0.0.1',
        help='Host to serve on (default localhost; 0.0.0.0 to make public)')
    options, args = parser.parse_args()
    server = jsonrpc.Server(jsonrpc.JsonRpc20(), 
                            jsonrpc.TransportTcpIp(addr=(options.host, int(options.port))))
    nlp = StanfordCoreNLP()
    server.register_function(nlp.parse)
    server.register_function(nlp.parse_imperative)
    print 'Serving on http://%s:%s' % (options.host, options.port)
    server.serve()
