#!/usr/bin/env python3

import argparse
import os
import sys
import requests
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

products_list = []
progress_lock = threading.Lock()
downloaded_total = 0
total_size = 0

MAX_THREADS = 8

def load_config(path=None):
    if path is None:
        path = "config-dev.env" if os.getenv("ENV") == "DEV" else "config.env"
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, path)
    config = {}
    if not os.path.exists(path):
        return config

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if (value.startswith('"') or value.startswith("'")) and (value.endswith('"') or value.endswith("'")):
                value = value[1:-1]
            config[key.strip()] = value
    return config


def get_param(cli_value, config_value, name, required=True, default=None):
    val = cli_value if cli_value else config_value
    if required and not val:
        if default:
            return default
        print(f"Missing parameter: {name}")
        sys.exit(1)
    return val


def get_token(auth_url, username, password, clientId):
    try:
        payload = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": clientId
        }

        r = requests.post(auth_url, data=payload)
        r.raise_for_status()
        return r.json()["access_token"]

    except Exception as e:
        print("Auth error:", e)
        sys.exit(1)


def fetch_products(service_url, token, product_type, start_date, end_date, baseline):
    try:
        url = f"{service_url}/Products?$expand=Attributes&$filter=(PublicationDate ge {start_date}T00:00:00.000Z) and (PublicationDate le {end_date}T23:59:59.999Z)"
        if product_type != "":
          url += f" and (Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{product_type}'))"
        if baseline != "":
          url += f" and (Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'processingBaseline' and att/OData.CSC.StringAttribute/Value eq '{baseline}'))"

        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        
        data = r.json()       
        products = data.get("value", [])
        
        # debug - write products to a json file:
        #with open("output.json", "w", encoding="utf-8") as f:
        #  json.dump(products, f, indent=2, ensure_ascii=False)
    
        return products

    except Exception as e:
        print("Error fetching products:", e)
        sys.exit(1)

def print_progress():
    global downloaded_total, total_size, products_list

    bar_len = 40
    lines = [f"Downloading products:"]

    # products
    for p in products_list:
        percent = p.get("Percent", 0)
        filled = int(bar_len * percent)
        bar = "#" * filled + "-" * (bar_len - filled)
        lines.append(f"- {p['Name']}: [{bar}] {percent*100:5.1f}%")

    # total
    percent_total = downloaded_total / total_size if total_size else 0
    filled = int(bar_len * percent_total)
    bar_total = "#" * filled + "-" * (bar_len - filled)
    lines.append(f"")
    lines.append(f"Total progress: [{bar_total}] {percent_total*100:5.1f}%")

    with progress_lock:
        sys.stdout.write(f"\033[{len(lines)}F")
        for line in lines:
            sys.stdout.write("\033[K")  # clear line
            sys.stdout.write(line + "\n")
        sys.stdout.flush()
    
    
def download_product(service_url, product, token, folder, finished_messages):
    global downloaded_total

    url = f"{service_url}/Products({product['Id']})/$value"
    filename = os.path.join(folder, product['Name'])
    headers = {"Authorization": f"Bearer {token}"}

    try:
        r = requests.get(url, headers=headers, stream=True)
        r.raise_for_status()
        downloaded = 0
        chunk_count = 0
        
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                chunk_count += 1

                with progress_lock:
                    product['Percent'] = downloaded / product['Size']
                    downloaded_total += len(chunk)
                    
                if chunk_count % 10 == 0:
                    print_progress()
            
        product['Percent'] = 1
        print_progress()
        
        # File was correctly downloaded
        msg = f"SUCCESS: Downloaded {filename}"
        finished_messages.append(msg)
        return msg
    except Exception as e:
        with progress_lock:
            product['Percent'] = downloaded / product['Size'] if downloaded else 0
            print_progress()

        msg = f"FAILED: {filename} - {e}"
        finished_messages.append(msg)
        return msg
      

def human_readable_size(size_bytes):
    for unit in ['B','KB','MB','GB','TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"
  
def progress_thread_fn():
    while any(p['Percent'] < 1 for p in products_list):
        print_progress()
        time.sleep(0.2)
    print_progress()
    
  
def main():
    parser = argparse.ArgumentParser(
      description="Download products from the S5 GSS corresponding to a given Product Type and included in a Publication Time window",
      formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("-t", "--product-type", help="Choose between: ['SN5 L1B UVR','SN5 L1B SWR','SN5 L1B NIR','SN5 L1B IRR']\nor leave it empty to search for all product types")
    parser.add_argument("-s", "--start-date", help="Publication Start Date", metavar="YYYY-MM-DD")
    parser.add_argument("-e", "--end-date", help="Publication End Date", metavar="YYYY-MM-DD")
    parser.add_argument("-b", "--baseline", help="Processing Baseline")
    parser.add_argument("-u", "--username", help="GSS authentication username")
    parser.add_argument("-p", "--password", help="GSS authentication password")
    parser.add_argument("-f", "--folder-name", help="Path to the folder to store the downloaded products.\nLeave it empty to use default './downloads'")
    parser.add_argument("-r", "--service-url", help="GSS url", metavar="http(s)//<gss-domain>/odata/v2")
    parser.add_argument("-a", "--auth-url", help="GSS Auth url", metavar="http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token")
    parser.add_argument("-c", "--client-id", help="GSS Auth clientId")
    parser.add_argument("-m", "--mode", help="Leave it empty for normal behavior.\nSet to 'test' for a dry run, which let you check all parameters, without downloading products")

    args = parser.parse_args()
    config = load_config()

    folder = get_param(args.folder_name, config.get("FOLDER_NAME"), "folder-name", default="./downloads")
    username = get_param(args.username, config.get("USERNAME"), "username")
    password = get_param(args.password, config.get("PASSWORD"), "password")
    service_url = get_param(args.service_url, config.get("SERVICE_URL"), "service-url")
    auth_url = get_param(args.auth_url, config.get("AUTH_URL"), "auth-url")
    client_id = get_param(args.client_id, config.get("CLIENT_ID"), "client-id")
    product_type = get_param(args.product_type, config.get("PRODUCT_TYPE"), "product-type", False)
    start_date = get_param(args.start_date, config.get("START_DATE"), "start-date")
    end_date = get_param(args.end_date, config.get("END_DATE"), "end-date")
    baseline = get_param(args.baseline, config.get("BASELINE"), "baseline", False)
    mode = get_param(args.mode, config.get("MODE"), "mode", False)
    
    os.makedirs(folder, exist_ok=True)

    token = get_token(auth_url, username, password, client_id)

    products = fetch_products(
        service_url,
        token,
        product_type,
        start_date,
        end_date,
        baseline
    )

    print(f"Products found: {len(products)}")
    
    global products_list
    products_list = [
      {"Id": item["Id"], "Name": item["Name"], "Size": item["ContentLength"], "Percent": 0}
      for item in products
      if "Id" in item and "Name" in item
    ]
    
    if mode == "test":
      print("This script was run in 'test' mode, so no download will be performed.")
    else:
      global total_size
      total_size = sum(
          p['Size']
          for p in products_list
      )
      print(f"total_size: {total_size} - {human_readable_size(total_size)}")
      for _ in range(len(products_list) + 4):
          print()
          
      finished_messages = []
      with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:          
          futures = [executor.submit(download_product, service_url, p, token, folder, finished_messages) for p in products_list]
          t = threading.Thread(target=progress_thread_fn)
          t.start()
          for future in futures:
              future.result()
          t.join()
          
      print()
      for msg in finished_messages:
        print(msg)


if __name__ == "__main__":
    main()