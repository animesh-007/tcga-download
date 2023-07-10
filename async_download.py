import asyncio
import aiohttp
import json
import re
from tqdm import tqdm
import os

files_endpt = "https://api.gdc.cancer.gov/files"
data_endpt = "https://api.gdc.cancer.gov/data"

async def download_file(session, file_entry, semaphore, counter):
    params = {"ids": file_entry["id"]}
    async with semaphore:
        try:
            async with session.post(data_endpt, data=json.dumps(params), headers={"Content-Type": "application/json"}) as response:
                # response_head_cd = response.headers["Content-Disposition"]
                # file_name = re.findall("filename=(.+)", response_head_cd)[0]

                file_size = int(response.headers.get("Content-Length", 0))

                # Extract the class/project ID from the params
                project_id = file_entry['cases'][0]['project']['project_id']

                file_name = file_entry["file_name"]

                # Create a directory for the class/project if it doesn't exist
                directory = os.path.join("./data", project_id)
                os.makedirs(directory, exist_ok=True)

                # Save the file in the respective directory
                file_path = os.path.join(directory, file_name)

                # print("=")
                with open(file_path, "wb") as output_file:
                    progress_bar = tqdm(total=file_size, unit="B", unit_scale=True, desc=f"==> Downloading {file_name}")
                    async for data in response.content.iter_any():
                        output_file.write(data)
                        progress_bar.update(len(data))
                    progress_bar.close()
                    counter.update(1)

        except aiohttp.client_exceptions.ServerDisconnectedError:
            print(f"Server disconnected for file {file_entry['id']}")

async def process_files(filters, max_concurrent_downloads):
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

    async with aiohttp.ClientSession() as session:
        async with session.get(files_endpt, params=params) as response:
            file_entries = json.loads(await response.text())["data"]["hits"]

        semaphore = asyncio.Semaphore(max_concurrent_downloads)
        counter = tqdm(total=len(file_entries), desc="Files downloaded")

        tasks = []
        for file_entry in file_entries:
            task = asyncio.ensure_future(download_file(session, file_entry, semaphore, counter))
            tasks.append(task)

        await asyncio.gather(*tasks)

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

    max_concurrent_downloads = 16  # Set the maximum number of concurrent downloads

    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_files(filters, max_concurrent_downloads))
