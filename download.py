import requests
import json
import re

files_endpt = "https://api.gdc.cancer.gov/files"

fields = [
    "file_name",
    # "cases.submitter_id",
    # "cases.samples.sample_type",
    "cases.disease_type",
    # "cases.
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

response = requests.get(files_endpt, params = params)


# This step populates the download list with the file_ids from the previous query
for file_entry in json.loads(response.content.decode("utf-8"))["data"]["hits"]:

    params = {"ids": file_entry["id"]}

    response = requests.post(data_endpt, data = json.dumps(params), headers = {"Content-Type": "application/json"})

    response_head_cd = response.headers["Content-Disposition"]

    file_name = re.findall("filename=(.+)", response_head_cd)[0]

    with open(file_name, "wb") as output_file:
        output_file.write(response.content)