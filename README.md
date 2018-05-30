# analyst

Assume we have [anaconda for python 3.6](https://www.anaconda.com/download)

```
conda install -c conda-forge python-igraph 
conda install -c anaconda mysql-connector-python 
conda install -c anaconda pandas 
conda install -c anaconda gensim 
```

## Usage

```
python main.py --file=FILE --host=MySqlAddress --user=MysqlUser --topK=10
```

The code will create two tables under database named Analystdb. The first table is for stock. The second is for industry.


