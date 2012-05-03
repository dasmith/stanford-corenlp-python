#!/usr/bin/env python
#
# corenlp  - Python interface to Stanford Core NLP tools
# Copyright (c) 2012 Dustin Smith
#   https://github.com/dasmith/stanford-corenlp-python
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

try:
    import json
except ImportError:
    import simplejson as json
    
import optparse
import sys
import os
import time
import re
import logging

try:
    from unidecode import unidecode
except ImportError:
    logging.info("unidecode library not installed")
    def unidecode(text):
        return text

from progressbar import *
import jsonrpc

import pexpect


def remove_id(word):
    """Removes the numeric suffix from the parsed recognized words: e.g. 'word-2' > 'word' """
    return word.count("-") == 0 and word or word[0:word.rindex("-")]

def parse_bracketed(s):
  '''Parse word features [abc=... def = ...]
  Also manages to parse out features that have XML within them
  '''
  word = None
  attrs = {}
  temp = {}
  # Substitute XML tags, to replace them later
  for i, tag in enumerate(re.findall(r"(<[^<>]+>.*<\/[^<>]+>)", s)):
    temp["^^^%d^^^" % i] = tag
    s = s.replace(tag, "^^^%d^^^" % i)
  # Load key-value pairs, substituting as necessary
  for attr, val in re.findall(r"([^=\s]*)=([^=\s]*)", s):
    if val in temp:
      val = temp[val]
    if attr == 'Text':
      word = val
    else:
      attrs[attr] = val
  return (word, attrs)

def parse_parser_results(text):
    """ This is the nasty bit of code to interact with the command-line
    interface of the CoreNLP tools.  Takes a string of the parser results
    and then returns a Python list of dictionaries, one for each parsed
    sentence.
    """
    state = 0
    tmp = {}
    coref_set = []
    results = { "sentences": [] }
    text = unidecode(text) # Force output conversion to ASCII to avoid RPC error
    for line in text.split("\n"):
        if line.startswith("Sentence #"):
            state = 1
            if len(tmp.keys()) != 0:
                results["sentences"].append(tmp) # Put results in "sentences" key so "corefs" can exist outside
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
                tmp['words'].append(parse_bracketed(s))
            state = 3
            tmp['parsetree'] = []
        elif state == 3:
            # Output parse tree as well (useful especially if you want to pull this into NLTK)
            if not (line.startswith(" ") or line.startswith("(ROOT")):
                state = 4
                tmp['parsetree'] = " ".join(tmp['parsetree'])
                tmp['tuples'] = []
            else:
              tmp['parsetree'].append(line.strip())
        if state == 4:
            # dependency parse
            line = line.rstrip()
            if not line.startswith(" ") and line.endswith(")"):
                split_entry = re.split("\(|, ", line[:-1]) 
                if len(split_entry) == 3:
                    rel, left, right = map(lambda x: remove_id(x), split_entry)
                    tmp['tuples'].append(tuple([rel,left,right]))
            elif "Coreference set" in line:
                state = 5
                coref_set = []
        elif state == 5:
          if "Coreference set" in line: # Create new coreference set if needed
            if len(coref_set) > 0:
              if results.has_key('coref'):
                results['coref'].append(coref_set)
              else:
                results['coref'] = [coref_set]
            coref_set = []
          else:
            # Updated for new coreference format
            crexp = re.compile(r"\((\d*),(\d)*,\[(\d*),(\d*)\)\) -> \((\d*),(\d)*,\[(\d*),(\d*)\)\), that is: \"(.*)\" -> \"(.*)\"")
            matches = crexp.findall(line)
            for src_i, src_pos, src_l, src_r, sink_i, sink_pos, sink_l, sink_r, src_word, sink_word in matches:
                src_i, src_pos, src_l, src_r = int(src_i)-1, int(src_pos)-1, int(src_l)-1, int(src_r)-1
                sink_i, sink_pos, sink_l, sink_r = int(sink_i)-1, int(sink_pos)-1, int(sink_l)-1, int(sink_r)-1
                print "COREF MATCH", src_i, sink_i                
                coref_set.append(((src_word, src_i, src_pos, src_l, src_r), (sink_word, sink_i, sink_pos, sink_l, sink_r)))
            print "CR", line
    if len(tmp.keys()) != 0:
        results["sentences"].append(tmp)
    if len(coref_set) > 0: # Add final coreference set if needed
      if results.has_key('coref'):
        results['coref'].append(coref_set)
      else:
        results['coref'] = [coref_set]      
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
        jars = ["stanford-corenlp-2012-04-09.jar", 
                "stanford-corenlp-2012-04-09-models.jar",
                "joda-time.jar",
                "xom.jar"]
       
        # if CoreNLP libraries are in a different directory,
        # change the corenlp_path variable to point to them
        corenlp_path = "stanford-corenlp-2012-04-09/"
        
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
        return json.dumps(results)


if __name__ == '__main__':
    """
    This block is executed when the file is run directly as a script, not when it
    is imported. 
    
    The code below starts an JSONRPC server
    """
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
    print 'Serving on http://%s:%s' % (options.host, options.port)
    server.serve()
