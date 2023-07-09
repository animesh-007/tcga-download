import requests
import json
import re
from tqdm import tqdm
import threading
import pandas as pd
import os

files_endpt = "https://api.gdc.cancer.gov/files"

fields = [
    "file_name",
    "cases.disease_type",
    "cases.project.project_id"
]

fields = ",".join(fields)

files_endpt = "https://api.gdc.cancer.gov/files"
data_endpt = "https://api.gdc.cancer.gov/data"

# This set of filters is nested under an 'and' operator.
filters = {
    "op": "and",
    "content":[
        {
            "op": "in",
            "content":{
                "field": "cases.project.project_id",
                "value": ["TCGA-LUAD","TCGA-LUSC"]
            }
        },
        {
            "op": "in",
            "content":{
                "field": "files.data_format",
                "value": ["svs"]
            }
        },
        {
            "op": "in",
            "content":{
                "field": "files.experimental_strategy",
                "value": ["Diagnostic Slide"]
            }
        }
    ]
}

# Here a GET is used, so the filter parameters should be passed as a JSON string.
params = {
    "filters": json.dumps(filters),
    "fields": fields,
    "format": "JSON",
    "size": "2000"
}

response = requests.get(files_endpt, params=params)


def mthread(params, cases):
    response = requests.post(data_endpt, data=json.dumps(params), headers={"Content-Type": "application/json"})
    response_head_cd = response.headers["Content-Disposition"]
    file_name = re.findall("filename=(.+)", response_head_cd)[0]

    # Extract the class/project ID from the params
    project_id = cases

    # Create a directory for the class/project if it doesn't exist
    directory = os.path.join("./data", project_id)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Save the file in the respective directory
    file_path = os.path.join(directory, file_name)

    with open(file_path, "wb") as output_file:
        output_file.write(response.content)


t = []
i = 0
j = 0
batch_size = 4  # Number of threads to join in each batch
file_entries = json.loads(response.content.decode("utf-8"))["data"]["hits"]
df = pd.DataFrame(file_entries)
df1 = pd.concat([pd.DataFrame({'id': df.iloc[i]['id'], 'cases': df.iloc[i]['cases'][0]['project']['project_id']}, index=[0])
                for i in range(len(df))], ignore_index=True)

# This step populates the download list with the file_ids from the previous query
for i in tqdm(range(len(df1))):
    params = {"ids": df1.iloc[i]["id"]}
    t.append(threading.Thread(target=mthread, args=(params, df1.iloc[i]['cases'])))
    t[i].start()
    if i % batch_size == 0 and i > 0:
        for thread in t[j:i+1]:
            thread.join()
        j = i + 1
    i += 1

# Join any remaining threads
for thread in t[j:]:
    thread.join()
