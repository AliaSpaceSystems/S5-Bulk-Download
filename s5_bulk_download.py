import argparse
import os
import sys
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

#test:
import json

products = []
progress_lock = threading.Lock()
downloaded_total = 0
total_size = 0

MAX_THREADS = 8

def load_config(path="config.env"):
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


def get_param(cli_value, config_value, name, required=True):
    val = cli_value if cli_value else config_value
    if required and not val:
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


def fetch_products(service_url, token, product_type, start_date, end_date):
    try:
        if product_type != "":
          url = f"{service_url}/Products?$expand=Attributes&$filter=(PublicationDate ge {start_date}T00:00:00.000Z) and (PublicationDate le {end_date}T23:59:59.999Z) and (Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{product_type}'))"
        else:
          url = f"{service_url}/Products?$expand=Attributes&$filter=(PublicationDate ge {start_date}T00:00:00.000Z) and (PublicationDate le {end_date}T23:59:59.999Z)"
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        
        data = r.json()       
        products = data.get("value", [])
        #test:
        with open("output.json", "w", encoding="utf-8") as f:
          json.dump(products, f, indent=2, ensure_ascii=False)
    
        return products

    except Exception as e:
        print("Error fetching products:", e)
        sys.exit(1)

def print_progress():
    global downloaded_total, total_size, products
    bar_len = 40
    lines_printed = 0
    
    # Single products:
    for p in products:
        percent = p.get('Percent', 0)
        filled = int(bar_len * percent)
        bar = "#" * filled + "-" * (bar_len - filled)
        sys.stdout.write(f"Product {p['Id']}: [{bar}] {percent*100:5.1f}%\n")
        lines_printed += 1
    
    # Total:
    percent = downloaded_total / total_size
    filled = int(bar_len * percent)
    bar = "#" * filled + "-" * (bar_len - filled)
    sys.stdout.write(f"Total progress: [{bar}] {percent*100:5.1f}%\n")
    lines_printed += 1
    
    sys.stdout.write(f"\033[{lines_printed}F")
    sys.stdout.flush()
    
    
def download_product(service_url, product, token, folder, total_size):
    global downloaded_total

    url = f"{service_url}/Products({product['Id']})/$value"
    filename = os.path.join(folder, product['Name'])
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(url, headers=headers, stream=True)
    r.raise_for_status()
    downloaded = 0

    with open(filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if not chunk:
                continue

            f.write(chunk)
            downloaded += len(chunk)
            product['Percent'] = downloaded / product['Size'] * 100 if product['Size'] else 0

            with progress_lock:
                downloaded_total += len(chunk)
                print_progress()

    return f"Downloaded {filename}"

def main():

    parser = argparse.ArgumentParser(
      description="Download products from the S5 GSS corresponding to a given Product Type and included in a Publication Time window",
      formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("-t", "--product-type", help="Choose between: ['SN5 L1B UVR','SN5 L1B SWR','SN5 L1B NIR','SN5 L1B IRR']\nor leave it empty to search for all product types")
    parser.add_argument("-s", "--start-date", help="Publication Start Date", metavar="YYYY-MM-DD")
    parser.add_argument("-e", "--end-date", help="Publication End Date", metavar="YYYY-MM-DD")
    parser.add_argument("-u", "--username", help="GSS authentication username")
    parser.add_argument("-p", "--password", help="GSS authentication password")
    parser.add_argument("-f", "--folder-name", help="Path to the folder to store the downloaded products.\nLeave it empty to use default './downloads'", default="./downloads")
    parser.add_argument("-r", "--service-url", help="GSS url", metavar="http(s)//<gss-domain>/odata/v2")
    parser.add_argument("-a", "--auth-url", help="GSS Auth url", metavar="http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token")
    parser.add_argument("-c", "--client-id", help="GSS Auth clientId")
    parser.add_argument("-m", "--mode", help="Leave it empty for normal behavior.\nSet to 'test' for a dry run, which let you check all parameters, without downloading products")

    args = parser.parse_args()
    config = load_config()

    folder = get_param(args.folder_name, config.get("FOLDER_NAME"), "folder-name")
    username = get_param(args.username, config.get("USERNAME"), "username")
    password = get_param(args.password, config.get("PASSWORD"), "password")
    service_url = get_param(args.service_url, config.get("SERVICE_URL"), "service-url")
    auth_url = get_param(args.auth_url, config.get("AUTH_URL"), "auth-url")
    client_id = get_param(args.client_id, config.get("CLIENT_ID"), "client-id")
    product_type = get_param(args.product_type, config.get("PRODUCT_TYPE"), "product-type", False)
    start_date = get_param(args.start_date, config.get("START_DATE"), "start-date")
    end_date = get_param(args.end_date, config.get("END_DATE"), "end-date")
    mode = get_param(args.mode, config.get("MODE"), "mode", False)

    os.makedirs(folder, exist_ok=True)

    token = get_token(auth_url, username, password, client_id)

    global products
    products = fetch_products(
        service_url,
        token,
        product_type,
        start_date,
        end_date
    )

    print(f"Products found: {len(products)}")
    
    products_list = [
      {"Id": item["Id"], "Name": item["Name"], "Size": item["ContentLength"], "Percent": 0}
      for item in products
      if "Id" in item and "Name" in item
    ]
     
    #debug:
    print(products_list)
    
    if mode == "test":
      print("This script was run in 'test' mode, so no download will be performed.")
    else:
      global total_size
      total_size = sum(
          p['Size']
          for p in products_list
      )
      print(f"total_size: {total_size}")
      print()
      with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
          futures = [
              executor.submit(download_product, service_url, product, token, folder, total_size)
              for product in products_list
          ]
          for future in as_completed(futures):
              print(future.result())
      print()


if __name__ == "__main__":
    main()