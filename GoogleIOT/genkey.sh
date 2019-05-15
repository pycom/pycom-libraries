# Google Cloud IoT Core
if [[ $# -eq 0 ]] ; then
    echo "Usage: $0 device_id"
    exit 0
fi

DB_DIR='db'
DEVICE_ID=$1

if [ ! -f $DB_DIR/$DEVICE_ID-priv.pem ]; then
  openssl genrsa -out $DB_DIR/$DEVICE_ID-priv.pem 2048
fi

if [ ! -f $DB_DIR/$DEVICE_ID-pub.pem ]; then
  openssl rsa -in $DB_DIR/$DEVICE_ID-priv.pem -pubout -out $DB_DIR/$DEVICE_ID-pub.pem
fi

if [ ! -f flash/cert/$DEVICE_ID-pk8.key ]; then
  openssl pkcs8 -topk8 -nocrypt -in $DB_DIR/$DEVICE_ID-priv.pem -out flash/cert/$DEVICE_ID-pk8.key
fi

if [ ! -f flash/cert/google_roots.pem ]; then
  wget "https://pki.google.com/roots.pem" -O flash/cert/google_roots.pem
fi

echo "Please add this public key to Google Cloud IoT Core Registry"
cat $DB_DIR/$DEVICE_ID-pub.pem
