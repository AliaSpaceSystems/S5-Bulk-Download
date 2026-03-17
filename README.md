# S5 Bulk Download

Download products from the S5 GSS corresponding to a given Product Type and included in a Publication Time window.


## Version: 

Version: 1.0.1


## Install

- Clone this repository anywhere in your machine:
```bash
git clone https://github.com/AliaSpaceSystems/S5-Bulk-Download.git
cd S5-Bulk-Download
```

- Give s5_bulk_download.py execution permission with: 
```bash
chmod a+x s5_bulk_download.py
```

- Windows:
The 'requests' library is needed for this app to run. If missing, you can install it with:
```bash
py -m pip install requests
```

## Usage

The script will download products, filtered by 'ProductType' and a 'PublicationDate' window, from an authenticated GSS containing S5 products and save them in a selected folder.
In order to work you can choose to put the needed parameters in a config file, pass them as script parameters, or a mix of both ways. Keep in mind that script parameters have precedence over the config file.

Empty config.env:
```bash
FOLDER_NAME=""
USERNAME=""
PASSWORD=""
SERVICE_URL="http(s)://<gss-domain>/odata/v2"
AUTH_URL="http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token"
CLIENT_ID="<auth-client-id>"
PRODUCT_TYPE=""
START_DATE=""
END_DATE=""
BASELINE=""
MODE=""
```

Relation between script parameters and config parameters and their function:
```bash
FOLDER_NAME     -f --folder-name    : Path to the folder to store the downloaded products. Leave it empty to use default './downloads'
USERNAME        -u --username       : GSS authentication username
PASSWORD        -p --password       : GSS authentication password
SERVICE_URL     -r -service-url     : GSS url, written following the model 'http(s)//<gss-domain>/odata/v2'
AUTH_URL        -a --auth-url       : GSS Auth url, written following the model 'http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token'
CLIENT_ID       -c --client-id      : GSS Auth clientId
PRODUCT_TYPE    -t --product-type   : Choose between: ['SN5 L1B UVR','SN5 L1B SWR','SN5 L1B NIR','SN5 L1B IRR'], or leave it empty to search for all product types
START_DATE      -s --start-date     : Publication Start Date
END_DATE        -e --end-date       : Publication End Date
BASELINE        -b --baseline       : Processing Baseline
MODE            -m --mode           : Leave it empty for normal behavior. Set to 'test' for a dry run, which let you check all parameters, without downloading products
```

Usually you would put into the config file the parameters that do not need to be changed, as the SERVICE_URL, the AUTH_URL, the CLIENT_ID, the FOLDER_NAME and the credentials (USERNAME and PASSWORD).

You can choose whether to put the PRODUCT_TYPE, the START_DATE and the END_DATE into the config file or to pass them as parameters, depending on how is convenient for your case.

- Run:
```bash
./s5_bulk_download.py -h
```
to show the help.

- Run:
```bash
./s5_bulk_download.py -m test <other-parameters>
```

to perform a dry run which will report how many products have been found with the given parameters, without downloading them.

- Example use:
```bash
./s5_bulk_download.py -s 2026-03-03 -e 2026-03-05 -t "SN5 L1B IRR"
```

to download all products with ProductType == "SN5 L1B IRR" and with PublicationDate between 2026-03-03 and 2026-03-05, and save them into the folder set inside the config file, or if not set, inside the default folder which is "./downloads"