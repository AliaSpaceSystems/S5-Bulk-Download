#!/usr/bin/env python3

import argparse
import os
import sys
import requests
import threading
import time
import json
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

products_list = []
progress_lock = threading.Lock()
downloaded_total = 0
total_size = 0

MAX_THREADS = 8

def get_version_from_readme(path="README.md"):
  with open(path, "r", encoding="utf-8") as f:
    content = f.read()

  match = re.search(r"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)", content)
  return match.group(1) if match else None
  
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

def validate_date(value):
  pattern1 = r"^\d{4}-\d{2}-\d{2}$"
  pattern2 = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"

  if re.match(pattern1, value) or re.match(pattern2, value):
    return value

  raise argparse.ArgumentTypeError("Invalid date format")
  
def fetch_products(service_url, token, filter):
  try:
    if filter['verbose']:
      print(f"Fetching products with filter: {filter}")
    url = f"{service_url}/Products"
    if filter['publication_start_date'] or filter['publication_end_date'] or filter['content_start_date'] or filter['content_end_date'] or filter['product_type'] or filter['baseline']:
      url += "?$expand=Attributes&$filter="
    else:
      ans = input("No filters selected. Are you sure to continue? [y/N]: ").strip().lower()
      if ans != "y" and ans != "yes" and ans != "Y":
        print("Stop")
        exit()
    isFirstAttr = True
    
    # PublicationDate
    if filter['publication_start_date'] != "":
      if not isFirstAttr:
        url += " and "
      if "T" in filter['publication_start_date']:
        url += f"(PublicationDate ge {filter['publication_start_date']})"
      else:
        url += f"(PublicationDate ge {filter['publication_start_date']}T00:00:00.000Z)"
      isFirstAttr = False
    if filter['publication_end_date'] != "":
      if not isFirstAttr:
        url += " and "
      if "T" in filter['publication_end_date']:
        url += f"(PublicationDate ge {filter['publication_end_date']})"
      else:
        url += f"(PublicationDate le {filter['publication_end_date']}T23:59:59.999Z)"
      isFirstAttr = False
      
    # ContentDate
    if filter['content_start_date'] != "":
      if not isFirstAttr:
        url += " and "
      if "T" in filter['content_start_date']:
        url += f"(ContentDate/Start ge {filter['content_start_date']})"
      else:
        url += f"(ContentDate/Start ge {filter['content_start_date']}T00:00:00.000Z)"
      isFirstAttr = False
    if filter['content_end_date'] != "":
      if not isFirstAttr:
        url += " and "
      if "T" in filter['content_end_date']:
        url += f"(ContentDate/End ge {filter['content_end_date']})"
      else:
        url += f"(ContentDate/End le {filter['content_end_date']}T23:59:59.999Z)"
      isFirstAttr = False
      
    # ProductType
    if filter['product_type'] != "":
      if not isFirstAttr:
        url += " and "
      url += f"(Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{filter['product_type']}'))"
      isFirstAttr = False
      
    # ProcessingBaseline
    if filter['baseline'] != "":
      if not isFirstAttr:
        url += " and "
      url += f"(Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'processingBaseline' and att/OData.CSC.StringAttribute/Value eq '{filter['baseline']}'))"
      isFirstAttr = False
    
    if filter['verbose']:
      print(f"Searching for products using url: {url}")
    
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
    
    
def md5_file(path):
  hash_md5 = hashlib.md5()
  with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(8192), b""):
      hash_md5.update(chunk)
  return hash_md5.hexdigest()

def verify_md5(path, expected_md5):
  calc_md5 = md5_file(path)
  # with open("output_md5.txt", "a", encoding="utf-8") as f:
  #   f.write(f"Calc md5: {calc_md5}\n")
  #   f.write(f"Prod md5: {expected_md5.lower()}\n")
  return calc_md5.lower() == expected_md5.lower()
  
    
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
    temp_md5 = product['Checksum'][0]['Value']
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
          
    if not verify_md5(f.name, temp_md5):
      msg = f"Error: Checksum is not valid for product: {product['Name']}"
      finished_messages.append(msg)
      return msg
      
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

  version = get_version_from_readme()
  
  parser.add_argument("-v", "--version", action="version", version=f"S5-Bulk-Download script v{version}", help="Display script version")
  parser.add_argument("-V", "--verbose", action="store_true", help="Enable verbose output")
  parser.add_argument("-t", "--product-type", choices=['SN5 L1B UVR','SN5 L1B SWR','SN5 L1B NIR','SN5 L1B IRR'], help="Choose between: ['SN5 L1B UVR','SN5 L1B SWR','SN5 L1B NIR','SN5 L1B IRR']\nor leave it empty to search for all product types")
  parser.add_argument("-s", "--publication-start-date", type=validate_date, help="Publication Start Date\nFormat: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.000Z", metavar="DATE")
  parser.add_argument("-e", "--publication-end-date", type=validate_date, help="Publication End Date\nFormat: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.000Z", metavar="DATE")
  parser.add_argument("-S", "--content-start-date", type=validate_date, help="Sensing (Content) Start Date\nFormat: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.000Z", metavar="DATE")
  parser.add_argument("-E", "--content-end-date", type=validate_date, help="Sensing (Content) End Date\nFormat: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.000Z", metavar="DATE")
  parser.add_argument("-b", "--baseline", help="Processing Baseline")
  parser.add_argument("-u", "--username", help="GSS authentication username")
  parser.add_argument("-p", "--password", help="GSS authentication password")
  parser.add_argument("-f", "--folder-name", help="Path to the folder to store the downloaded products\nLeave it empty to use default './downloads'")
  parser.add_argument("-r", "--service-url", help="GSS url\nFormat: http(s)//<gss-domain>/odata/v2")
  parser.add_argument("-a", "--auth-url", help="GSS Auth url\nFormat: http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token")
  parser.add_argument("-c", "--client-id", help="GSS Auth clientId")
  parser.add_argument("-m", "--mode", choices=['normal', 'test'], help="Script run mode, defaults to 'normal'\nSet to 'test' for a dry run, which let you check all parameters, without downloading products")

  args = parser.parse_args()    
  config = load_config()

  folder = get_param(args.folder_name, config.get("FOLDER_NAME"), "folder-name", default="./downloads")
  username = get_param(args.username, config.get("USERNAME"), "username")
  password = get_param(args.password, config.get("PASSWORD"), "password")
  service_url = get_param(args.service_url, config.get("SERVICE_URL"), "service-url")
  auth_url = get_param(args.auth_url, config.get("AUTH_URL"), "auth-url")
  client_id = get_param(args.client_id, config.get("CLIENT_ID"), "client-id")
  product_type = get_param(args.product_type, config.get("PRODUCT_TYPE"), "product-type", False)
  publication_start_date = get_param(args.publication_start_date, config.get("PUBLICATION_START_DATE"), "publication-start-date", False)
  publication_end_date = get_param(args.publication_end_date, config.get("PUBLICATION_END_DATE"), "publication-end-date", False)
  content_start_date = get_param(args.content_start_date, config.get("CONTENT_START_DATE"), "content-start-date", False)
  content_end_date = get_param(args.content_end_date, config.get("CONTENT_END_DATE"), "content-end-date", False)
  baseline = get_param(args.baseline, config.get("BASELINE"), "baseline", False)
  mode = get_param(args.mode, config.get("MODE"), "mode", default="normal")
  verbose = args.verbose
  
  os.makedirs(folder, exist_ok=True)

  token = get_token(auth_url, username, password, client_id)
  filter = {
    "product_type": product_type,
    "publication_start_date": publication_start_date,
    "publication_end_date": publication_end_date,
    "content_start_date": content_start_date,
    "content_end_date": content_end_date,
    "baseline": baseline,
    "verbose": verbose
  }
  products = fetch_products(
    service_url,
    token,
    filter
  )

  print(f"Products found: {len(products)}")
  
  global products_list
  products_list = [
    {"Id": item["Id"], "Name": item["Name"], "Size": item["ContentLength"], "Checksum": item['Checksum'], "Percent": 0}
    for item in products
    if "Id" in item and "Name" in item and "Checksum" in item
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