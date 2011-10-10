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
    """ This is the nasty bit of code to interact with the command-line
    interface of the CoreNLP tools.  Takes a string of the parser results
    and then returns a Python list of dictionaries, one for each parsed
    sentence.
    """
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
            tmp['words'] = [] 
            exp = re.compile('\[([^\]]+)\]')
            matches  = exp.findall(line)
            for s in matches:
                print s
                # split into attribute-value list 
                av = re.split("=| ", s) 
                # make [ignore,ignore,a,b,c,d] into [[a,b],[c,d]]
                # and save as attr-value dict, convert numbers into ints
                #tmp['words'].append((av[1], dict(zip(*[av[2:][x::2] for x in (0, 1)]))))
                # tried to convert digits to ints instead of strings, but
                # it seems the results of this can't be serialized into JSON?
                word = av[1]
                attributes = {}
                for a,v in zip(*[av[2:][x::2] for x in (0, 1)]):
                    if v.isdigit():
                        attributes[a] = int(v)
                    else:
                        attributes[a] = v
                tmp['words'].append((word, attributes))
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
            crexp = re.compile('\s(\d*)\s(\d*)\s\-\>\s(\d*)\s(\d*), that is')
            matches = crexp.findall(line)
            for src_i, src_pos, sink_i, sink_pos in matches:
                # TODO: src_i and sink_i correspond to the sentences.
                # this was built for single sentences, and thus ignores
                # the sentence number.  Should be fixed, but would require
                # restructuring the entire output.
                print "COREF MATCH", src_i, sink_i
                src = tmp['words'][int(src_pos)-1][0]
                sink = tmp['words'][int(sink_pos)-1][0]
                if tmp.has_key('coref'):
                    tmp['coref'].append((src, sink))
                else:
                    tmp['coref'] = [(src, sink)]
         
            print "CR", line
    if len(tmp.keys()) != 0:
        results.append(tmp)
    return results

class StanfordCoreNLP(object):
    """ 
    Command-line interaction with Stanford's CoreNLP java utilities.

    Can be run as a JSON-RPC server or imported as a module.
    """
    def __init__(self):	
        """
        Checks the location of the jar files.
        Spawns the server as a process.
        """

        jars = ["stanford-corenlp-2011-09-16.jar", 
                "stanford-corenlp-2011-09-14-models.jar",
                "joda-time.jar",
                "xom.jar"]
       
        # if CoreNLP libraries are in a different directory,
        # change the corenlp_path variable to point to them
        corenlp_path = ""
        java_path = "java"
        classname = "edu.stanford.nlp.pipeline.StanfordCoreNLP"
        # include the properties file, so you can change defaults
        # but any changes in output format will break parse_parser_results() 
        props = "-props default.properties" 

        # add and check classpaths
        jars = [corenlp_path + jar for jar in jars]
        for jar in jars:
            if not os.path.exists(jar):
                print "Error! Cannot locate %s" % jar
                sys.exit(1)
        
        # spawn the server
        self._server = pexpect.spawn("%s -Xmx1800m -cp %s %s %s" % (java_path, ':'.join(jars), classname, props))
        
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

    def _parse(self, text, verbose=True):
        """
        This is the core interaction with the parser. 

        It returns a Python data-structure, while the parse()
        function returns a JSON object
        """
        # clean up anything leftover
        while True:
            try:
                # the second argument is a forced delay (in seconds)
                # EVERY parse must incur.  
                # TODO make this as small as possible.
                ch = self._server.read_nonblocking (4000, 0.3)
            except pexpect.TIMEOUT:
                break

        self._server.sendline(text)
        # How much time should we give the parser to parse it?
        # the idea here is that you increase the timeout as a 
        # function of the text's length.
        
        # anything longer than 5 seconds requires that you also
        # increase timeout=5 in jsonrpc.py
        max_expected_time = min(5, 3 + len(text) / 20.0)
        if verbose: print "Timeout", max_expected_time
        end_time = time.time() + max_expected_time 
        incoming = ""
        while True: 
            # Time left, read more data
            try:
                ch = self._server.read_nonblocking (2000, 1)
                freshlen = len(ch)
                time.sleep (0.0001)
                incoming = incoming + ch
                if "\nNLP>" in incoming:
                    break
            except pexpect.TIMEOUT:
                print "Timeout" 
                if end_time - time.time() < 0:
                    return {'error': "timed out after %f seconds" % max_expected_time, 
                            'input': text,
                            'output': incoming}
                else:
                    continue
            except pexpect.EOF:
                break
        results = parse_parser_results(incoming)
        return results

    def _debug_parse(self, text, verbose=True):
        print "DEBUG PARSE -- "
        rf = open("test.out", 'r')
        incoming = ''.join(rf.readlines())
        rf.close()
        results = parse_parser_results(incoming)
        return results

    def parse(self, text, verbose=True):
        """ 
        This function takes a text string, sends it to the Stanford parser,
        reads in the result, parses the results and returns a list
        with one dictionary entry for each parsed sentence, in JSON format.
        """
        # convert to JSON and return
        if verbose: print "Request", text
        results = self._parse(text, verbose)
        if verbose: print "Results", results
        return dumps(results)

    def parse_imperative(self, text, verbose=True):
        """
        This is a hacky way to deal with imperative statements.

        Takes an imperative, adds a personal pronoun, parses it,
        and then removes it in the resulting parse.
        
        e.g. "open the door" gets parsed as "you open the door"
        """
        # find a pronoun that's not in the string already.
        used_pronoun = None
        pronouns = ["you","he", "she","i"]
        for p in pronouns:
            if text.startswith(p+" "):
                # it's already an imperative!
                used_pronoun = None
                break
            if p not in text:
                # found one not in there already
                used_pronoun = p
                break
        # if you can't find one, regress to original parse
        if not used_pronoun:
            return self.parse(text, verbose)
  
        # create text with pronoun and parse it
        new_text = used_pronoun+" "+text.lstrip()
        result = self._parse(new_text, verbose)
        
        if len(result) != 1:
            print "Non-imperative sentence?  Multiple sentences found."

        # remove the dummy pronoun
        used_pronoun_offset = len(used_pronoun)+1
        if result[0].has_key('text'):
            result[0]['text'] = text
            result[0]['tuples'] = filter(lambda x: not (x[1] == used_pronoun or x[2]
                    == used_pronoun), result[0]['tuples'])
            result[0]['words'] = result[0]['words'][1:]
            # account for offset
            ct = 0
            for word, av in result[0]['words']:
                for a,v in av.items():
                    if a.startswith("CharacterOffset"):
                        result[0]['words'][ct][1][a] = v-used_pronoun_offset
                ct += 1
            return dumps(result)
        else:
            # if there's a timeout error, just return it.
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
