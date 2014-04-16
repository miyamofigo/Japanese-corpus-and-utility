#!/usr/bin/python
# -*- coding: utf-8 -*-

# for Japanese I/O setting
import sys, codecs
reload(sys)
sys.setdefaultencoding('utf-8')
sys.stdout = codecs.getwriter('utf_8')(sys.stdout)
sys.stdin = codecs.getreader('utf_8')(sys.stdin)

import re, nltk
from nltk.corpus.reader import *
from nltk.corpus.reader.util import *
from nltk.corpus.util import *
from nltk.text import Text

from util import *

import MeCab
from nltk.tokenize.api import TokenizerI
class MeCabTokenizer(TokenizerI):
  def __init__(self):
    self.mecab = MeCab.Tagger('-Ochasen')
  def tokenize(self, text):
    tokens = []
    node = self.mecab.parseToNode(text.encode('utf-8'))
    node = node.next  
    while node.surface:
      tokens.append(tuple([node.surface, node.feature]))
      node = node.next
    return tokens

class JapaneseRegexpTokenizer(nltk.RegexpTokenizer):
  def tokenize(self, text, encoding='utf-8'):
    if not isinstance(text, unicode):
      text = unicode(text)
    tokens = nltk.RegexpTokenizer.tokenize(self, text) 
    return map(lambda x: x.encode(encoding), tokens)  

# CaboCha parser wrapper for Corpus
from nltk.parse.api import ParserI
import CaboCha
class CaboChaParser(ParserI):
  def __init__(self, parser=None):
    self._parser = CaboCha.Parser('--charset=UTF8')
  def parse(self, sent_str):
    tree_proxy = self._parser.parse(sent_str.encode('utf-8'))
    return CaboChaTree(tree_proxy)

class KNPParser(ParserI):
  def __init__(self, jumanpath=None, knppath=None):
    self.jumanpath = jumanpath
    self.knppath = knppath
  def parse(self, sentence):
    jumanpath, knppath = None, None
    if self.jumanpath:
      jumanpath = self.jumanpath
    if self.knppath:
      knppath = self.knppath  
    seq = pyknp(sentence, jumanpath, knppath)
    return KNPDependencyGraph.parse(KNPTree.parse(seq))

class JapaneseCorpusView(StreamBackedCorpusView):
  def __init__(self, corpus_file, encoding, parsed, tagged,
               group_by_sent, parsed_by_case, syntax_parser, 
               word_tokenizer, sent_tokenizer, case_parser): 
    self._parsed = parsed
    self._tagged = tagged
    self._group_by_sent = group_by_sent
    self._parsed_by_case = parsed_by_case
    self._syntax_parser = syntax_parser
    self._word_tokenizer = word_tokenizer
    self._sent_tokenizer = sent_tokenizer
    self._case_parser = case_parser
    StreamBackedCorpusView.__init__(self, corpus_file, encoding=encoding)
  def read_block(self, stream):
    block = []
    for sent_str in self._sent_tokenizer.tokenize(stream.read()):
      if self._parsed_by_case:
        dg = self._case_parser.parse(sent_str)
        block.append(dg)  
      elif self._parsed:
        tree = self._syntax_parser.parse(sent_str)
        block.append(tree)  
      else:
        sent = self._word_tokenizer.tokenize(sent_str)
        if not self._tagged:
          sent = [w for (w,t) in sent]
        if self._group_by_sent:
          block.append(sent)
        else:
          block.extend(sent)
    return block

jp_sent_tokenizer =\
     JapaneseRegexpTokenizer(u'[^　「」！？。]*[！？。]')

from nltk.corpus.reader.util import concat
from nltk.corpus.reader.api import CorpusReader
class JapaneseCorpusReader(CorpusReader):
  def __init__(self, root, fileids,
               syntax_parser=CaboChaParser(),
               word_tokenizer=MeCabTokenizer(),
               sent_tokenizer=jp_sent_tokenizer,
               case_parser=KNPParser(),
               encoding='utf-8'):
    CorpusReader.__init__(self, root, fileids, encoding)
    self._syntax_parser = syntax_parser
    self._word_tokenizer = word_tokenizer
    self._sent_tokenizer = sent_tokenizer
    self._case_parser = case_parser
  #
  # CorpusReader class has methods below:
  #   __repr__, readme?, fileids, open, abspath, abspaths, 
  #   encoding, _get_root 
  #
  # about details, see nltk/corpus/reader/api.py
  #
  def raw(self, fileids=None):
    if fileids is None: 
      fileids = self._fileids
    elif isinstance(fileids, basestring):
      fileids = [fileids]
    return concat([self.open(f).read() for f in fileids]) 
  def words(self, fileids=None):
    return concat([JapaneseCorpusView(fileid, enc,
                                      False, False, False, False,
                                      self._syntax_parser,
                                      self._word_tokenizer,
                                      self._sent_tokenizer,
                                      self._case_parser)
                   for (fileid, enc) in self.abspaths(fileids, True)])
  def sents(self, fileids=None):
    return concat([JapaneseCorpusView(fileid, enc,
                                      False, False, True, False,
                                      self._syntax_parser,
                                      self._word_tokenizer,
                                      self._sent_tokenizer,
                                      self._case_parser)
                   for (fileid, enc) in self.abspaths(fileids, True)])
  def tagged_words(self, fileids=None):
    return concat([JapaneseCorpusView(fileid, enc,
                                      False, True, False, False,
                                      self._syntax_parser,
                                      self._word_tokenizer,
                                      self._sent_tokenizer,
                                      self._case_parser)
                   for (fileid, enc) in self.abspaths(fileids, True)])
  def tagged_sents(self, fileids=None):
    return concat([JapaneseCorpusView(fileid, enc,
                                      False, True, True, False,
                                      self._syntax_parser,
                                      self._word_tokenizer,
                                      self._sent_tokenizer,
                                      self._case_parser)
                   for (fileid, enc) in self.abspaths(fileids, True)])
  def parsed_sents(self, fileids=None):
    return concat([JapaneseCorpusView(fileid, enc,
                                      True, False, False, False,
                                      self._syntax_parser,
                                      self._word_tokenizer,
                                      self._sent_tokenizer,
                                      self._case_parser)
                   for (fileid, enc) in self.abspaths(fileids, True)])
  def parsed_sents2(self, fileids=None):
    return concat([JapaneseCorpusView(fileid, enc,
                                      False, False, False, True,
                                      self._syntax_parser,
                                      self._word_tokenizer,
                                      self._sent_tokenizer,
                                      self._case_parser)
                   for (fileid, enc) in self.abspaths(fileids, True)])
  
if __name__ == '__main__':
  jpcorpus = JapaneseCorpusReader('./reviews', '2651755_0.txt')
  for dg in jpcorpus.parsed_sents2():
    dg.debug() 
  #KNPParser().parse("すもももももももものうち").debug()
