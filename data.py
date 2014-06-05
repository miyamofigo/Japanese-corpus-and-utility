#!/usr/bin/python
# -*- coding: utf-8 -*-

# for Japanese I/O setting
import sys, codecs
sys.stdout = codecs.getwriter('utf_8')(sys.stdout)
sys.stdin = codecs.getreader('utf_8')(sys.stdin)
reload(sys)
sys.setdefaultencoding('utf-8')

import re, nltk
from nltk.corpus.reader import *
from nltk.corpus.reader.util import *
from nltk.corpus.util import *
from nltk.text import Text

import sqlite3
class Connection(object):
  _db = sqlite3
  def __init__(self, fname, timeout=5, 
               detect_types=0, isolation_level='None'):
    self.fname = fname
    self.detect_types = detect_types
    self.isolation_level = isolation_level
    self._conn = self._db.connect(fname, timeout, detect_types,
                                  isolation_level)
    self._cur_lst = []
    self._row = False
  def __del__(self):
    self.close()
  def reconnect(self):
    self.close()
    self._conn = self._db.connect(fname, timeout, detect_types,
                                  isolation_level)
  def close(self):
    if self.isolation_level != 'None':
      self.commit()
    for cur in self._cur_lst:
      cur.close()
    self._conn.close()
  def commit(self):
    if self.isolation_level != 'None':
      self._conn.commit()
  def rollback(self):
    if self.isolation_level != 'None':
      self._conn.rollback()
  def cursor(self):
    return Cursor(self) 
  def new_cursor(self):
    return self._cursor() 
  def _cursor(self):
    return self._conn.cursor()
  @property
  def row(self):
    pass
  @row.getter
  def row(self):
    return self._row 
  @row.setter
  def row(self, value):
    if isinstance(value, bool) and self._row != value:
      self._row = value 
      if self._row:
        self._conn.row_factory = sqlite3.Row
      else:
        self._conn.row_factory = None
      self.refresh_all_curs()
  def refresh_all_curs(self):
    if self.isolation_level != 'None':
      self.commit()
    for cur in self._cur_lst:
      cur.refresh()
  def add_cur(self, cur):
    if not isinstance(cur, Cursor):
      raise TypeError("a Cursor object is expected.")
    self._cur_lst.append(cur)
  def remove_cur(self, cur):
    try:
      self._cur_lst.remove(cur) 
    except IndexError:
      pass

class Cursor(object):
  def __init__(self, conn):
    self.conn = conn
    self._cur = conn.new_cursor()
    self.conn.add_cur(self)
    self._sql = None
  @property
  def rowcount(self):
    return self._cur.rowcount
  def callproc(self):
    raise NotImplementedError("sqlite3 does not provide callpc function")
  def close(self):
    self.conn.remove_cur(self)
    self._cur.close()
  def execute(self, sql, *args, **kwargs):
    self._sql = sql.replace('%s', '?')
    return self._cur.execute(self._sql, *args, **kwargs)
  def executemany(self, sql, sequence):
    self._sql = sql.replace('%s', '?')
    return self._cur.executemany(self._sql, sequence)
  def fetchone(self):
    return self._cur.fetchone() 
  def fetchmany(self, *args, **kwargs):
    return self._cur.fetchmany(*args, **kwargs) 
  def fetchall(self):
    return self._cur.fetchall() 
  def nextset(self):
    raise NotImplementedError("sqlite3 does not provide nextset function")
  def setinputsizes(self):
    raise NotImplementedError("sqlite3 does not provide setinputsizes"
                              " function")
  def setoutputsize(self):
    raise NotImplementedError("sqlite3 does not provide setoutputsize"
                              " function")
  def refresh(self):
    self._cur.close()
    self._cur = self.conn.new_cursor()

if __name__ == "__main__":
  conn = Connection(":memory:", isolation_level = 'EXCLUSIVE')
  cur = conn.cursor()
  print conn.row
  cur.execute("create table one(id integer);")
  cur.executemany("insert into one values(?);", [(1,), (2,), (3,)])
  print cur.rowcount
  cur.execute("select * from one;")
  tup = cur.fetchone()
  assert isinstance(tup, tuple), "a tuple is expected." 
  print tup
  lst = cur.fetchall()
  for t in lst:
    print t
  conn.row = True
  cur.execute("select * from one;")
  row = cur.fetchone()
  assert isinstance(row, sqlite3.Row), "a row is expected."
  print row
  for key in row.keys():
    print key
  conn.commit()
