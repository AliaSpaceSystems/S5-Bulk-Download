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

The script will search for products using some filters and download them from an authenticated GSS containing S5 products and save them in a selected folder.
The products can be filtered by PublicationDate, ContentDate, ProductType and ProcessingBaseline, setting the relative parameters. 
In order to work you can choose to put the needed parameters in a config file or pass them as script parameters or a mix of both ways. Keep in mind that script parameters have precedence over the same parameters set into the config file.

Empty config.env:
```bash
FOLDER_NAME=""
USERNAME=""
PASSWORD=""
SERVICE_URL="http(s)://<gss-domain>/odata/v2"
AUTH_URL="http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token"
CLIENT_ID="<auth-client-id>"
PRODUCT_TYPE=""
PUBLICATION_START_DATE=""
PUBLICATION_END_DATE=""
CONTENT_START_DATE=""
CONTENT_END_DATE=""
BASELINE=""
MODE=""
```

Relation between script parameters and config parameters and their function:
```bash
FOLDER_NAME                 -f --folder-name                : Path to the folder to store the downloaded products. Leave it empty to use default './downloads'
USERNAME                    -u --username                   : GSS authentication username
PASSWORD                    -p --password                   : GSS authentication password
SERVICE_URL                 -r -service-url                 : GSS url, written following the model 'http(s)//<gss-domain>/odata/v2'
AUTH_URL                    -a --auth-url                   : GSS Auth url, written following the model 'http(s)//<auth-domain>/auth/realms/<realm-name>/protocol/openid-connect/token'
CLIENT_ID                   -c --client-id                  : GSS Auth clientId
PRODUCT_TYPE                -t --product-type               : Choose between: ['SN5 L1B UVR','SN5 L1B SWR','SN5 L1B NIR','SN5 L1B IRR']
PUBLICATION_START_DATE      -s --publication-start-date     : Publication Start Date - Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.000Z
PUBLICATION_END_DATE        -e --publication-end-date       : Publication End Date - Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.000Z
CONTENT_START_DATE          -S --content-start-date         : Content Sensing Start Date - Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.000Z
CONTENT_END_DATE            -E --content-end-date           : Publication End Date - Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.000Z
BASELINE                    -b --baseline                   : Processing Baseline
MODE                        -m --mode                       : Choose between: ['normal', 'test']. Script run mode, defaults to 'normal'. Set to 'test' for a dry run, which let you check all parameters, without downloading products
                            -V --verbose                    : Print more info, as the output OData filter used.
                            -v --version                    : Print the script version
                            -h --help                       : Print the script help
```

All the filter parameters are not mandatory but a request to continue is asked to the user if no filters have been set, because a large number of products can be found.
Usually the user would put into the config file the parameters that do not need to be changed, as the SERVICE_URL, the AUTH_URL, the CLIENT_ID, the FOLDER_NAME and the credentials (USERNAME and PASSWORD). 
User can choose whether to put the PRODUCT_TYPE, the START_DATE and the END_DATE into the config file or to pass them as parameters, depending on how is convenient for user's case. As an example, if user needs to perform a lot of requests for the same productType, it can be convenient to put that into the config file parameter.

- Run:
```bash
./s5_bulk_download.py -h
```
to show the help.


- Run:
```bash
./s5_bulk_download.py -m test <...other-parameters>
```
to perform a dry run which will report how many products have been found with the given parameters, without downloading them.


- Example use:
```bash
./s5_bulk_download.py -s 2026-03-03 -e 2026-03-05T18:30:00.000Z -t "SN5 L1B IRR"
```
to download all products with ProductType == "SN5 L1B IRR" and with PublicationDate between 2026-03-03T00:00:00.000Z and 2026-03-05T18:30:00.000Z, and save them into the folder set inside the config file, or if not set, inside the default folder which is "./downloads"
In the last example the date is written in the two possible formats, with or without the time parameters.

- Example use:
```bash
./s5_bulk_download.py -S 2026-03-03 -E 2026-03-05T18:30:00.000Z -t "SN5 L1B IRR"
```
the same as before, but searching for ContentDate, instead of PublicationDate. (-S and -E instead of -s and -e).