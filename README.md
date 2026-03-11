*** S5 Bulk Download ***

usage: s5_bulk_download.py [-h] [-t PRODUCT_TYPE] [-s YYYY-MM-DD] [-e YYYY-MM-DD] [-u USERNAME] [-p PASSWORD] [-f FOLDER_NAME] [-r http(s)//<gss-domain>/odata/v2]
                           [-a http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token] [-c CLIENT_ID] [-m MODE]

Download products from the S5 GSS corresponding to a given Product Type and included in a Publication Time window

options:
  -h, --help            show this help message and exit
  -t PRODUCT_TYPE, --product-type PRODUCT_TYPE
                        Choose between: ['SN5 L1B UVR','SN5 L1B SWR','SN5 L1B NIR','SN5 L1B IRR']
                        or leave it empty to search for all product types
  -s YYYY-MM-DD, --start-date YYYY-MM-DD
                        Publication Start Date
  -e YYYY-MM-DD, --end-date YYYY-MM-DD
                        Publication End Date
  -u USERNAME, --username USERNAME
                        GSS authentication username
  -p PASSWORD, --password PASSWORD
                        GSS authentication password
  -f FOLDER_NAME, --folder-name FOLDER_NAME
                        Path to the folder to store the downloaded products.
                        Leave it empty to use default './downloads'
  -r http(s)//<gss-domain>/odata/v2, --service-url http(s)//<gss-domain>/odata/v2
                        GSS url
  -a http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token, --auth-url http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token
                        GSS Auth url
  -c CLIENT_ID, --client-id CLIENT_ID
                        GSS Auth clientId
  -m MODE, --mode MODE  Leave it empty for normal behavior.
                        Set to 'test' for a dry run, which let you check all parameters, without downloading products