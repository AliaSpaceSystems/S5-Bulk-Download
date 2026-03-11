# S5 Bulk Download

Download products from the S5 GSS corresponding to a given Product Type and included in a Publication Time window.


## Version: 

Version: 1.0.0


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
MODE=""
```

Usually you would put into the config file the parameters that do not need to be changed, as the SERVICE_URL, the AUTH_URL, the CLIENT_ID, the FOLDER_NAME and the credentials (USERNAME and PASSWORD). 
You can choose whether to put the PRODUCT_TYPE, the START_DATE and the END_DATE into the config file or to pass them as parameters, depending on how is convenient for your case.

