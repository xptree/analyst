#!/usr/bin/env python
# encoding: utf-8
# File Name: main.py
# Author: Jiezhong Qiu
# Create Time: 2018/05/25 14:28
# TODO:

import pandas as pds
import igraph
import random
import itertools
from gensim.models import Word2Vec
import mysql.connector as conn
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--host', type=str, default='localhost', help="mysql address")
parser.add_argument('--user', type=str, default='root', help="mysql user")
parser.add_argument('--password', type=str, default='yuik', help="mysql password")
parser.add_argument('--file', type=str, default='./data_name_20180521.csv', help="data file")
parser.add_argument('--walk-length', type=int, default=80, help="length of random walk")
parser.add_argument('--num-walk', type=int, default=10, help="number of walks")
parser.add_argument('--topk', type=int, default=10, help="topk analysts to show")
parser.add_argument('--workers', type=int, default=1, help="number of workers for training")
args = parser.parse_args()

db=conn.connect(host=args.host, user=args.user, password=args.password, charset='utf8', autocommit=True)
cursor=db.cursor()
cursor.execute("""CREATE DATABASE IF NOT EXISTS Analystdb""")
cursor.execute("""USE Analystdb""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Stock(
        StockId VARCHAR(255) PRIMARY KEY, Analysts TEXT) CHARACTER SET = utf8""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Industry(
        IndustryId VARCHAR(255) PRIMARY KEY, Analysts TEXT) CHARACTER SET = utf8""")
cursor.execute("""TRUNCATE Stock""")
cursor.execute("""TRUNCATE Industry""")

df = pds.read_csv("./data_name_20180521.csv", dtype=str)
df.drop("Unnamed: 39", axis=1, inplace=True)

vmap = dict()
edge_list = list()

ANALYST_NAME = u'股评师名称'
ORG_NAME = u'股评机构名称'
STOCK = u'股票代码'
INDUSTRY = u'行业代码'

def random_walk(g, start):
    current = start
    stop = False
    while not stop:
        stop = yield current
        current = random.choice(g.neighbors(current))

def add_vertex(s):
    if s not in vmap:
        idx = len(vmap)
        vmap[s] = idx
        return idx
    return vmap[s]

for idx, row in df.iterrows():
    analysts = row[ANALYST_NAME]
    if analysts == u'研究部':
        row[ANALYST_NAME] = row[ORG_NAME] + '_' + row[ANALYST_NAME]
        analysts = row[ANALYST_NAME]
    if type(analysts) != str:
        row[ANALYST_NAME] = row[ORG_NAME] + '_' + u'研究部'
        analysts = row[ANALYST_NAME]

    analysts_idx = [add_vertex('analyst_%s' % item) for item in analysts.split(',')]
    org_idx = add_vertex('org_%s' % row[ORG_NAME])
    stock_idx =  add_vertex('stock_%s' % row[STOCK])
    industry_idx =  add_vertex('industry_%s' % row[INDUSTRY])

    edge_list.append((stock_idx, industry_idx))
    edge_list.append((stock_idx, org_idx))
    for analyst_idx in analysts_idx:
        edge_list.append((org_idx, analyst_idx))

inv_vmap = {v: k for k, v in vmap.items()}
graph = igraph.Graph(len(vmap))
graph.add_edges(edge_list)
graph.to_undirected()

# random walk
print("generate random walk sequence")
sentences = []
for u in range(len(vmap)):
    for j in range(args.num_walk):
        sentence = list(itertools.islice(random_walk(graph, u), args.walk_length))
        sentence = [inv_vmap[x] for x in sentence]
        sentences.append(sentence)

print("training")
model = Word2Vec(sentences, size=64, window=5, workers=args.workers, min_count=1, negative=10)
#model.save("a.wv")
#model.wv.save_word2vec_format("a.txt")

# write to mysql

param = list()
for k in vmap:
    if k.startswith('stock_'):
        most_similar = model.most_similar(positive=[k,], topn=len(vmap))
        top_list = list()
        for item in most_similar:
            if item[0].startswith('analyst_'):
                top_list.append(item[0].split('_', 1)[1])
                if len(top_list) == args.topk:
                    break
                    break
        param.append((k.split('_', 1)[1], ",".join(top_list)))
cursor.executemany("INSERT INTO Stock VALUES(%s, %s)", param)

param = list()
for k in vmap:
    if k.startswith('industry_'):
        most_similar = model.most_similar(positive=[k,], topn=len(vmap))
        top_list = list()
        for item in most_similar:
            if item[0].startswith('analyst_'):
                top_list.append(item[0].split('_', 1)[1])
                if len(top_list) == args.topk:
                    break
        param.append((k.split('_', 1)[1], ",".join(top_list)))
cursor.executemany("INSERT INTO Industry VALUES(%s, %s)", param)
cursor.close()
db.close()
