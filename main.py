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
import time

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

#cursor.execute("""CREATE DATABASE IF NOT EXISTS Analystdb""")
cursor.execute("""USE focus973""")
#cursor.execute("""CREATE TABLE IF NOT EXISTS Stock(
#        StockId VARCHAR(255) PRIMARY KEY, Analysts TEXT) CHARACTER SET = utf8""")
#cursor.execute("""CREATE TABLE IF NOT EXISTS Industry(
#        IndustryId VARCHAR(255) PRIMARY KEY, Analysts TEXT) CHARACTER SET = utf8""")
cursor.execute("""TRUNCATE rank_stock""")
cursor.execute("""TRUNCATE rank_industry""")

df = pds.read_csv(args.file, dtype=str)


def load_analyst_index(cursor):
    sql = 'SELECT * FROM securities_company_staff'
    cursor.execute(sql)
    results = cursor.fetchall()
    analyst_name_to_id = dict()
    for row in results:
        if row[2] not in analyst_name_to_id:
            analyst_name_to_id[row[2]] = dict()
        analyst_name_to_id[row[2]][row[1]] = row[0]
    return analyst_name_to_id


def load_org_index(cursor):
    sql = 'SELECT * FROM securities_company'
    cursor.execute(sql)
    results = cursor.fetchall()
    org_name_to_id = dict()
    for row in results:
        org_name_to_id[row[1]] = row[0]
    return org_name_to_id

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

org_name_to_id = load_org_index(cursor)
analyst_name_to_id = load_analyst_index(cursor)
for idx, row in df.iterrows():
    analysts = row[ANALYST_NAME]
    org = row[ORG_NAME]

    if type(org) != str:
        continue
    if type(analysts) != str:
        continue

    if org not in org_name_to_id:
        continue
    org_id = org_name_to_id[org]
    if org_id not in analyst_name_to_id:
        continue

    analysts_idx = [add_vertex('analyst_%d' % analyst_name_to_id[org_id][item]) for item in analysts.split(',')
            if item in analyst_name_to_id[org_id]]
    org_idx = add_vertex('org_%d' % org_id)
    stock_idx =  add_vertex('stock_%s' % row[STOCK])
    industry_idx =  add_vertex('industry_%s' % row[INDUSTRY])

    edge_list.append((stock_idx, industry_idx))
    for analyst_idx in analysts_idx:
        edge_list.append((stock_idx, analyst_idx))
        edge_list.append((analyst_idx, org_idx))

inv_vmap = {v: k for k, v in vmap.items()}
print(len(vmap))
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
model = Word2Vec(sentences, size=64, window=3, workers=args.workers, min_count=1, negative=10)
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
        for index, analyst in enumerate(top_list):
            param.append((
                            k.split('_', 1)[1], # stock id
                            int(analyst), # appraiser id
                            index, # rank
                            int(time.time()) #timestamp
                            ))
cursor.executemany("INSERT INTO rank_stock VALUES(%s, %s, %s, %s)", param)


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

        for index, analyst in enumerate(top_list):
            param.append((
                            k.split('_', 1)[1], # industry id
                            int(analyst), # appraiser id
                            index, # rank
                            int(time.time()) #timestamp
                            ))
cursor.executemany("INSERT INTO rank_industry VALUES(%s, %s, %s, %s)", param)
cursor.close()
db.close()
