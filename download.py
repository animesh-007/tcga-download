import requests
import json
import re
from multiprocessing import Pool
import os
from tqdm import tqdm


files_endpt = "https://api.gdc.cancer.gov/files"
data_endpt = "https://api.gdc.cancer.gov/data"

def download_file(file_entry):
    params = {"ids": file_entry["id"]}

    # Extract the class/project ID from the params
    project_id = file_entry['cases'][0]['project']['project_id']

    file_name = file_entry["file_name"]

    # Create a directory for the class/project if it doesn't exist
    directory = os.path.join("./data", project_id)
    os.makedirs(directory, exist_ok=True)
    
    response = requests.post(data_endpt, data=json.dumps(params), headers={"Content-Type": "application/json"})

    # Save the file in the respective directory
    file_path = os.path.join(directory, file_name)

    print(f"==> Downloading {file_name}")
    with open(file_path, "wb") as output_file:
        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024
        progress_bar = tqdm(total=total_size, unit="B", unit_scale=True)
        for data in response.iter_content(block_size):
            output_file.write(data)
            progress_bar.update(len(data))
        progress_bar.close()

def process_files(filters):
    fields = [
        "file_name",
        "cases.disease_type",
        "cases.project.project_id"
    ]
    fields = ",".join(fields)

    params = {
        "filters": json.dumps(filters),
        "fields": fields,
        "format": "JSON",
        "size": "2000"
    }

    response = requests.get(files_endpt, params=params)

    file_entries = json.loads(response.content.decode("utf-8"))["data"]["hits"]

    with Pool(processes=8) as pool:
        pool.map(download_file, file_entries)

if __name__ == "__main__":
    filters = {
        "op": "and",
        "content": [
            {
                "op": "in",
                "content": {
                    "field": "cases.project.project_id",
                    "value": ["TCGA-LUAD", "TCGA-LUSC"]
                }
            },
            {
                "op": "in",
                "content": {
                    "field": "files.data_format",
                    "value": ["svs"]
                }
            },
            {
                "op": "in",
                "content": {
                    "field": "files.experimental_strategy",
                    "value": ["Diagnostic Slide"]
                }
            }
        ]
    }

    process_files(filters)
