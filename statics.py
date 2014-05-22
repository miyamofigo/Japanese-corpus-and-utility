#! /usr/local/bin/python2.7
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
from nltk.probability import *

from util import *
from numpy import array
from scipy.stats import chi2_contingency

def test_independency(feature, condition, cfdist,
                      test_func=chi2_contingency):
  if not isinstance(cfdist, ConditionalFreqDist):
    raise TypeError("ConditionalFreqDist is expected for cfdist2 "
                    "argument.")
  try:
    feat_cond = cfdist[condition][feature] 
    feat_not_cond = sum(map(lambda x: x[feature], cfdist.values()))\
                    - feat_cond
    not_feat_cond = cfdist[condition].N() - feat_cond
    not_feat_not_cond = cfdist.N() - feat_cond\
                        - feat_not_cond -not_feat_cond
    table = array([[feat_cond, feat_not_cond],
                   [not_feat_cond, not_feat_not_cond]])
  except IndexError:
    # ignore a feature which appears only on a specific condition
    return False
  x2, p, dof, expected = test_func(table)
  if p < 0.05:
    return True
  else:
    return False
