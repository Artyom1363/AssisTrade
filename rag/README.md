# RAG


To run RAG follow those steps:

Download requirements
```
pip install -r requirements.txt
```

Create directories for :
- downloading images
- index data for chroma db
- persist dir for chroma db 
```
mkdir -p metamask_data/images
mkdir index
mkdir chroma_persist
```

Added your current dir to PYTHONPATH
```
export PYTHONPATH=`pwd`
```

Download acutal docs from metamask
```
python3 src/parsing/scrap_metamask.py
```

Create index for chroma db
```
python3 welding_index/welding_index.py --data-dir metamask_data --output-dir index
```

Create environment
```
touch .env
```
Place here your GIGACHAT_API_KEY

Launch main app
```
python3 main.py --vector-data-dir index --persist-dir chroma_persist  --data-dir metamask_data
```

