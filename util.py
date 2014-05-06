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


import urllib2, time
def getTextsFromWebPages(url, urlopener, t_pattern, r_pattern=None,
											   encoding=None, interval=5):
	text_list = []
	file = urlopener.open(url)
	html = file.read()
	if encoding:
		charset = file.headers.getparam('charset')
		if charset != encoding:
			try:
				html = unicode(html, charset).encode(encoding)
			except:
				print "not encoded..........."
	file.close()
	matched_list = t_pattern.findall(html)
	if matched_list:
		text_list += [match[0] for match in matched_list]
	if r_pattern:
		nextPageUrlMatch = r_pattern.search(html)	
		if nextPageUrlMatch:
			if not interval >= 1:
				print "at least one second is required for interval..."
				return -1
			time.sleep(interval)
			nextPageUrl = nextPageUrlMatch.group(1)
			text_list += getTextsFromWebPages(nextPageUrl, urlopener, t_pattern, 
																			  r_pattern, encoding, interval)
	return text_list

def trimText(text, regexpObj=None):
	if regexpObj: 
		regexp = regexpObj
	else: 
		regexp = re.compile(r'<.*?>')
	text = regexp.sub('', text)	
	text = text.strip()
	return text

def genTextFile(text, path, fname_prefix, fnum):
	fname = path + fname_prefix + '_' + str(fnum) + '.txt'
	fd = open(fname, 'w')
	fd.write(text)
	fd.close() 

def scrape(url, t_pattern, uaInfo=None, r_pattern=None, trim=True, 
					 genfile=True, path=None, fname_prefix='dummy'):
	opener = urllib2.build_opener()
	if uaInfo:
		opener.addheaders = [('User-Agent', uaInfo)]
	text_list = getTextsFromWebPages(url, opener, t_pattern, 
																	 r_pattern, encoding='utf-8')
	if trim:
		regexp4t = re.compile(r'<.*?>')
		text_list = [trimText(text, regexp4t) for text in text_list]
	if genfile:
		if path:
			fpath = path
		else:
			fpath = './'
		for i, text in enumerate(text_list):
			genTextFile(text, fpath, fname_prefix, i)
		return fpath
	return text_list  

from nltk.tree import Tree			
import CaboCha
class CaboChaTree(Tree):
  def __init__(self, node_or_proxy, children=None, id=-1):
		if isinstance(node_or_proxy, CaboCha.Tree):
			trees = CaboChaTree.parse(node_or_proxy, True)
			Tree.__init__(self, 'S', trees) 			# 'S' stands for 'sentence'
		elif isinstance(node_or_proxy, CaboCha.Chunk):
			if children:
				Tree.__init__(self, 'C', children)	# 'C' stands for 'chunk' 
				if not id < 0:
					self.id = id
					self.link = node_or_proxy.link
				self.head = children[node_or_proxy.head_pos]
				self.func = children[node_or_proxy.func_pos]
			else:
				raise ValueError("expected children of this chunk..")
		else:
			if children: 
				Tree.__init__(node_or_proxy, children)
			else:
				raise ValueError("expected children for leaves..")
  @classmethod
  def parse(cls, proxy, istree=False):
		if not istree and isinstance(proxy, CaboCha.Tree):
			raise TypeError("expected CaboCha.Tree proxy..")  
		trees = []
		size = proxy.chunk_size()
		for i in range(size):
			chunk = proxy.chunk(i)  	
			children = []
			for j in range(chunk.token_size):
				token_pos = chunk.token_pos + j
				token = proxy.token(token_pos) 
				children.append(token.surface + '/' + token.feature)
			if i == size - 1:
				i = -1
			trees.append(CaboChaTree(chunk, children, i))
		return trees

from subprocess import Popen, PIPE 
def execWithPipe(command, pipe_in=None):
	return Popen(command, stdin=pipe_in, stdout=PIPE).stdout	

def commandSequence(sequence, pipe_in=None):
	try:
		head, rest = sequence.split('|', 1)
		cmd = head.split()
		fdin = execWithPipe(cmd, pipe_in)
		fdout = commandSequence(rest, fdin)
	except ValueError:
		cmd = sequence.split()
		fdout = execWithPipe(cmd, pipe_in)
	return fdout

# caution: it returns file descriptor not string
def pyknp(sentence, jumanpath=None, knppath=None):
	cmdseq = "echo %s | " % sentence.encode('utf-8')
	if jumanpath:
		cmdseq += jumanpath
	cmdseq += "juman | "
	if knppath:
		cmdseq += knppath
	cmdseq += "knp -tab"
	return commandSequence(cmdseq)	

class KNPTree(Tree):
	def __init__(self, node, children, parent_node=None,
							 rel=None, attrs=None, head=None):
		self.parent_node = parent_node
		self.rel = rel
		self.attrs = attrs
		self.head = head	
		Tree.__init__(self, node, children)  
	@classmethod
	def parse(cls, stream_or_lst,
						regex_deps=re.compile(r'([\-0-9]*)([ADIP])'),
						regex_attrs=re.compile(r'<(.*?)>'),
						regex_phrase_head=re.compile(u'文節主辞')):
		result = []
		flag = True
		if isinstance(stream_or_lst, file):
			lst = [line for line in stream_or_lst]	
		elif isinstance(stream_or_lst, list):
			lst = stream_or_lst
		else:
			raise TypeError("expected file or list.")
		while lst:
			if lst[0][0] == '#':
				lst = lst[1:]
			elif lst[0][0] == '*':
				if flag:
					flag = False 
				m = regex_deps.search(lst[0])	
				parent_node = m.group(1)
				rel = m.group(2)
				m_lst = regex_attrs.findall(lst[0])
				attrs = m_lst
				children = KNPTree.parse(lst[1:], regex_deps, regex_attrs,
																 regex_phrase_head)		
				result.append(KNPTree('C', children, parent_node, 
															rel, attrs))	
				lst = lst[1:]
			elif lst[0][0] == '+':
				if not flag:
					lst = lst[1:]
					continue
				m = regex_deps.search(lst[0])	
				parent_node = m.group(1)
				rel = m.group(2)
				m_lst = regex_attrs.findall(lst[0])
				attrs = m_lst
				children = []
				head = None
				i = 1 
				while lst[i][0] not in ['*', '+', 'E']:
					children.append(lst[i].strip())
					if regex_phrase_head.search(unicode(lst[i])):
						head = i - 1 
					i += 1
				result.append(KNPTree('P', children, parent_node, 
															rel, attrs, head))
				lst = lst[1:]
				if lst[0][0] == '*':
					break 
			else:
				if lst[0][:3] == 'EOS':
					break
				else:
					lst = lst[1:]
					if flag and lst[0][0] == '*':
						break
		return result		

class KNPDependencyGraph(object):
	def __init__(self, nodelst=None):
		if nodelst:
			self.nodelist = nodelst
		else:
			self.nodelist = []
		self.root = None
		self.stream = None
	@classmethod
	def parse(cls, trees):
		nodelst = []
		for i, tree in enumerate(trees):
			phrase = ''.join(map(lambda x: x.split()[0], tree.leaves()))
			node = {
								'tree'		: tree,
								'phrase'	: phrase, # use 'phrase' as chunk content
								'deps'		: [],
								'rel'			:	tree.rel, 
								'address'	: i 
						 }
			nodelst.append(node)
		dg = KNPDependencyGraph(nodelst)
		root = dg.build()
		dg.root = root
		return dg
	# build a dependency graph from a nodelist only instance
	def build(self):
		lst = self.nodelist
		while len(lst) > 1:
			parents = [] 
			childs = []
			parents_index = set([int(node['tree'].parent_node)
													 for node in lst]) 
			for node in lst:
				if node['address'] in parents_index:
					parents.append(node)
				else:
					childs.append(node)
			for c_node in childs:
				i = int(c_node['tree'].parent_node)
				self.nodelist[i]['deps'].append(c_node['address'])  
			lst = parents	
		root = lst[0]
		root['rel'] = 'TOP'
		return root	
	def debug(self, curr=None, depth=0):
		if not curr:
			if not self.root:
				for node in self.nodelist:
					print node['phrase']
			else:
				print self.root['rel'], self.root['phrase']
				deps = self.root['deps']
				if deps:
					for address in deps: 
						self.debug(self.nodelist[address])
		else:
			depth += 1
			print '\t' * depth, curr['rel'], curr['phrase']
			deps = curr['deps']
			if deps:
				for address in deps:
					self.debug(self.nodelist[address], depth)	

# translation to logic expression from dependency graph
# in the simplest way. 
def simple_translation(graph, node=None, depth=0, limit=0,
											 var_count=0, func_count=0):
	if not isinstance(graph, KNPDependencyGraph):
		raise TypeError("expected KNPDependencyGraph instance for "
										"the first argument")
	if depth == 0:
		if node:
			curr = node
		else:
			curr = graph.root
		fname = curr['phrase']
		var = chr(ord('a')+var_count)
		if curr['deps'] and limit:
			depth += 1
			for child_expr in simple_translation(graph, curr, depth, limit):
				yield child_expr
		else:
			yield '\\' + var + '. ' + func_style(fname, var)
	else:
		flag = False
		if limit != depth:
			flag = True 
		pararell_nodes = [graph.nodelist[i] for i in node['deps']
											if graph.nodelist[i]['rel'] == 'P']
		if node['rel'] == 'P' and not node['deps']:
			yield node['phrase']
		for i, expr in enumerate(node2lambda(graph, node, flag, var_count)):
			if type(expr) == str:
				yield expr
			elif expr is None:
				continue
			else:
				fsymbol = chr(ord('A')+func_count)
				var = chr(ord('a')+var_count)
				expr[-1] = (fsymbol, expr[-1][1])
				func_lst = [func_style(*name) for name in expr]  		
				prefix = '\\' + fsymbol + ' ' + var + '. '
				parent_expr = prefix + bracket(' & '.join(func_lst))
				curr = graph.nodelist[node['deps'][i]]
				depth += 1
				var_count += 1
				func_count += 1
				for arg_expr in simple_translation(graph, curr, depth, limit,
																					 var_count, func_count):
					expr = parent_expr + bracket(arg_expr)
					yield expr	
		if pararell_nodes:
			depth -= 1 
			limit -= 1
			for pnode in pararell_nodes:
				for expr in simple_translation(graph, pnode, depth, limit,
																			 var_count, func_count):
					yield expr

def func_style(fname, arg):
	return fname + '(' + arg + ')'
	
def bracket(expr):
	return '(' + expr + ')'
				
def node2lambda(dg, node, rflag=False, count=0):
	var = chr(ord('a')+count)
	prefix = '\\'
	prefix += var + '. '
	parent = node['phrase']  
	for index in node['deps']:
		child = dg.nodelist[index]
		if child['rel'] == 'P':
			yield None
			continue
		name_arg_lst = map(lambda x: (x, var), (parent, child['phrase']))
		if rflag and child['deps']:
			yield name_arg_lst
			continue 
		func_lst = [func_style(*name) for name in name_arg_lst]
		expr = prefix + bracket(' & '.join(func_lst))
		yield expr

def getdepth(graph, current=None):
	if not current:
		current = graph.root
	depth, additional = 0, 0
	for index in current['deps']:
		depth += 1
		deepest = 0
		current = graph.nodelist[index]
		additional = getdepth(graph, current)
		if additional > deepest:
			deepest = additional
	depth += additional
	return depth 

def collectTranslations(graph, limit=-1):
	d = getdepth(graph)
	lst = []
	for i in range(d):
		if i == limit:
			break
		for expr in simple_translation(graph, limit=i):
			lst.append(expr)
	return set(lst)	

def word_features(words, features={}):
	return features.update({word:True for word in words 
													if word not in features})

def phrase_features(trees, regex=None, n=0, features={}):
# CaboChaTree instance is expected for trees argument
	if not regex:
		regex = re.compile(u'[。！？、]')
	def fill(phrase, features=features):
		try: 
			if features[phrase]:
				pass
		except KeyError:
			features[phrase] = True
	# this function connect words and trim them -> returns a phrase
	def prepare(leaves, regex=regex):
		# get rid of pos information
		words = map(lambda x: x.split('/')[0], leaves)
		phrase = ''.join(words)
		phrase = regex.sub(u'', unicode(phrase)).encode('utf-8')
		return phrase	
	for sent_tree in trees:
		if n > 1:
			chunk_tups = nltk.ngrams(sent_tree, n) 
			for tup in chunk_tups:
				leaves_lst = map(lambda x: x.leaves(), tup) 
				phrases = tuple(map(prepare, leaves_lst))   
				fill(phrases)
		else:
			for chunk in sent_tree:
				phrase = prepare(chunk.leaves())
				fill(phrase)
	return features

# get features from cabocha-tree dependency.
def cabo_deps_features(cabo_trees, regex=None, n=2, features={}):
	sample = cabo_trees[0]
	if not isinstance(sample, CaboChaTree) or not sample.node == 'S': 
		raise TypeError("a parsed sentence list by CaboChaTree "
										"is expected for cabo_tree argument.")
	if n < 2:
		raise ValueError("a number which equals to larger than 2 "
										 "is expected for n argument")
	if not regex:
		regex = re.compile(u'[。！？、]')
	lst = []	
	for cabo_tree in cabo_trees:
		for chunk in cabo_tree:
			count = n
			chunks = []
			curr = chunk
			while count:
				chunks.append(curr)
				try:
					curr = cabo_tree[curr.link]
				except AttributeError:
					if count > 1:
						chunks = []
						break
				count -= 1
			if chunks:
				lst.append(tuple(chunks))
	for chunk_tup in lst:
		tagged_words_lst = map(lambda x: x.leaves(), chunk_tup)
		words_lst = [map(lambda x: x.split('/')[0], tagged_words) 
								 for tagged_words in tagged_words_lst]   
		phrase_lst = [''.join(words) for words in words_lst] 
		phrases = tuple(map(
			lambda x: regex.sub(u'', unicode(x)).encode('utf_8'),
			phrase_lst))
		try:
			if features[phrases]:
				pass
		except KeyError:
			features[phrases] = True
	return features 

if __name__ == '__main__':
	#url = "http://my.cosme.net/open_entry_reviewlist/list/user_id/"
	#user_id = 2651755
	#url += str(user_id)
	#UserAgent =\
	#	"scraping with python2. you can contact me via miyamofigo@gmail.com"
	#opener = urllib2.build_opener()
	#opener.addheaders = [('User-Agent', UserAgent)]
	#t_pattern = re.compile(r'<p class="read".*?>((.|\n)*?)</p>')
	#r_pattern = re.compile(r'<a class=\'pageNext\' href=\'(http.*)\'.*?>')
	#review_list = getTextsFromWebPages(url, opener, t_pattern, 
	#																	r_pattern, encoding='utf-8')
	#review_list = getTextsFromWebPages(
	#	url, opener, t_pattern, encoding='utf-8')
	#for review in review_list:
	#	print trimText(review)
	#			
 	#scrape(url, t_pattern, UserAgent, r_pattern, 
	#			 path='./reviews/', fname_prefix=str(user_id))
	#cabocha = CaboCha.Parser('--charset=UTF8')
	#sent = u'太郎はこの本を持っていた女性に渡した。'.encode('utf-8')
	#tree = cabocha.parse(sent)
	#ctree = CaboChaTree(tree)
	#print ctree	
	#seq = pyknp(u"太郎はこの本とミカンを持っていた女性に渡した。")
	#trees = KNPTree.parse(seq)
	#for tree in trees:
	#	print tree
	dg = KNPDependencyGraph.parse(trees)
	#dg.debug()
	#exprset = collectTranslations(dg)
	#for expr in exprset:
	#	print expr
