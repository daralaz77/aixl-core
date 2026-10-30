#!/bin/sh
# Throw-away certificates for the TLS / mTLS check (valid 2 days). Python 3.13+ verifies STRICTLY: a CA must carry keyUsage (a first version without it made every HTTP case fail with
# "CA cert does not include key usage extension", while gRPC's more lenient library accepted it). Usage: make_certs.sh <dir> [lan-ip]
set -e; D="$1"; LAN="$2"; mkdir -p "$D"; cd "$D"
openssl genrsa -out ca.key 2048 2>/dev/null
openssl req -x509 -new -key ca.key -sha256 -days 2 -subj "/CN=aixl-otel-test-ca" -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" -addext "subjectKeyIdentifier=hash" -out ca.pem 2>/dev/null
SAN="DNS:localhost,IP:127.0.0.1"; [ -n "$LAN" ] && SAN="$SAN,IP:$LAN"
printf "subjectAltName=%s\nextendedKeyUsage=serverAuth\nkeyUsage=critical,digitalSignature,keyEncipherment\nauthorityKeyIdentifier=keyid\nbasicConstraints=CA:FALSE\n" "$SAN" > server.ext
printf "extendedKeyUsage=clientAuth\nkeyUsage=critical,digitalSignature\nauthorityKeyIdentifier=keyid\nbasicConstraints=CA:FALSE\n" > client.ext
for n in server client; do openssl genrsa -out $n.key 2048 2>/dev/null; openssl req -new -key $n.key -subj "/CN=$n" -out $n.csr 2>/dev/null
  openssl x509 -req -in $n.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out $n.pem -days 2 -sha256 -extfile $n.ext 2>/dev/null; done
echo "$LAN" > lan_ip.txt; openssl verify -CAfile ca.pem server.pem client.pem
