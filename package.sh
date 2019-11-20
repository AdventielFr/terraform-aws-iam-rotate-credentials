#!/bin/sh

#----------------------------
# build and package lambda
#----------------------------

cd src/
rm -rf .serverless/
sls plugin install --name serverless-iam-roles-per-function
sls plugin install --name serverless-plugin-log-retention
sls plugin install --name serverless-python-requirements
sls plugin install --name serverless-python-requirements
sls plugin install --name serverless-pseudo-parameters
sls package --name lambda_function_payload
rm -rf my/dir || true
#rm ../lets-encrypt-renew-certificates.zip
#mv .serverless/lets-encrypt-renew-certificates.zip ../
#rm -rf .serverless/
