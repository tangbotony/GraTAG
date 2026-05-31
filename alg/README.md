# Usage
## Prerequisites
- [ElasticSearch](https://www.elastic.co/downloads/elasticsearch)
- [MongoDB](https://www.mongodb.com)

## Create a conda environment
```bash
conda create -n news python=3.9
conda activate news
```

## Install dependencies
```bash
pip install -r requirements.txt
```

## Install the spacy model for Chinese
download link: [here](https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.8.0/zh_core_web_sm-3.8.0-py3-none-any.whl)

And then, run
```bash
pip install zh_core_web_sm-3.8.0-py3-none-any.whl
```
> [!NOTE]
> When you try to install the package `zh_core_web_sm`, the version of package `numpy` might be changed because of that. If so, you need to re-install the package `numpy` seperately, 
```bash
pip install numpy==1.26.2
```
> or you may encounter the following the error upon running the next step:
```bash
ValueError: numpy.dtype size changed, may indicate binary incompatibility. Expected 96 from C header, got 88 from PyObject
```

## Add some settings
- Add your own elasticsearch and milvus setting in line 103-111 of the file `include/config/common_config.py` and line 9-18 of the file `include/config/query_recommend_config.py`.
- Add your own NER setting in line 37-40 of the file `include/config/common_config.py`.
- Add your own mongodb connection strings in line 14 of the file `include/config/get_special_user_id.py`

## Start your first query
You can input your query in line 395 of the file `pipeline/functions.py`.
```python
query = """Give me some latest news about Iran-Israel conflict.""" # input your own query
```
After that, you can run the file `pipeline/functions.py` and wait for the result.

## Analyze your result
The answer to the query you entered will be printed on the console in the form of a JSON list, where each JSON object will contain the following fields.


|fields|explanation|remark|
|----|----|----|
|type|Type of currect JSON object, the optional values include the following categories: "state", "intention_query", "ref_page", "ref_answer", "text", "time_line", "text_end", "recommendation" ||
|data|The specific value of the current element，and its format will change with the value of the text field.||
|query|The query entered by the user||
|qa_series_id||Ignoreable|
|qa_pair_collection_id||Ignoreable|
|qa_pair_id||Ignoreable|

### Type "state" object
There will be only three JSON object of which the value of the text field is "state", and their values of the data field will be "search", "organized" and "complete", relatively. These three object symbolize the beginning of the search phase, the answer organization phase and the completion of the answer.

### Type "intention_query" object
There will be only one JSON object of which the value of the text field is "inetntion_query", and its values of the data field will be a list, of which each element is a query that will be entered to the search engine. The return of search engine for these queries will be used to organize the answer to the final query.

### Type "ref_page" object
There will be only one JSON object of which the value of the text field is "ref_page", and its values of the data field will be a nested dict object. Each key-value pair in the dict object represents an Internet source that can be used to refer to generate answers，where the key is the ID of the source, the value is detailed information of the source, including the title, url and main content of the webpage.

### Type "ref_answer" object
There will be only one JSON object of which the value of the text field is "ref_answer", and its values of the data field will be a list object, where each element is a JSON object, representing a citation summarized from above key-value pairs. Each citation will have a ID, a news_id corresponding to the id of each key-value pair above, and summarized content.

### Type "text" object
In most cases, the value of the data field of the element with the type field value of text represents a character in the final answer content (arranged in order using markdown syntax), but in a few cases it is an image placeholder (used to be replaced with an image). It should be noted that when the value of the data field is a left square bracket, and letters and numbers appear in the eight positions after it, and a right square bracket appears in the ninth position, these ten characters will be used together as a citation identifier, corresponding to an element id in ref_answer, to indicate that the previous answer content quotes the content in the corresponding ref_answer.

### Type "timeline" object
There will be only one JSON object which the value of the text field is "timeline". And its value of data field will be a nested dict object. The fields contained in the nested dict object are as follows: 
|field|explanation|
|---|---|
|is_multi_subject|Whether the timeline involves multiple topics or stages. When this field is true, the value of events will be a list containing multiple elements. Each element represents all event information under a topic/stage, and each topic/stage will have an independent title placed in the title field.|
|events|Information of all events collected through search engines|
|timeline_new_query|The query used to generate the timeline. In most cases, it is the same as the query entered by the user.|
|cot_split_questions|Chained thought queries entered into the search engine to generate the timeline|
|timeline_sort_events|List of events sorted from newest to oldest|


### Type "text_end" object
There will be only one JSON object which the value of the text field is "text_end". It should appear in the list after all objects whose type field value is text, and whose data field value is an empty string, indicating that the answer content has been output.

### Type "recommendation" object
There will be only one JSON object which the value of the text field is "recommendation". It should appear at the last position in the list, and its data field value is a list of strings, where each element represents a recommended follow-up question.
