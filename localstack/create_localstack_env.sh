#!/bin/bash
# Purpose: Script to build and deploy search artefacts into localstack docker container

# keep track of the last executed command
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
# echo an error message before exiting
trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT

log::info() { printf "INFO: %s\n" "$1"; }
log::warn() { printf "WARN: %s\n" "$1"; }
log::error() { printf "ERROR: %s\n" "$1" >&2; }

root_dir=$(pwd)
REGION="ap-southeast-2"

exit_on_error() {
# exit when any command fails
    set -e
}

check_dependencies() {
    if [[ ! $(command -v docker) ]]
    then
        log::error "Cannot find docker, please install it."
        exit 1
    fi
    if [[ ! $(command -v jq) ]]
    then
        log::error "Cannot find jq, refer README.md to install it"
        exit 1
    fi
    if [[ ! $(command -v awslocal) ]]
    then
        log::error "Cannot find awslocal, refer README.md to install it"
        exit 1
    fi
    if [[ ! $(command -v aws) ]]
    then
        log::error "Cannot find aws, refer README.md to install it"
        exit 1
    fi
    if [[ ! $(command -v curl) ]]
    then
        log::error "Cannot find curl, please install it"
        exit 1
    fi
}

kill_docker() {
    docker kill localstack
    docker rm localstack
}

start_docker() {
    # localstack dashboard is at: http://localhost:8081/#/infra
    docker run --name localstack -d \
        -e LAMBDA_EXECUTOR=docker \
        -e DOCKER_HOST=unix:///var/run/docker.sock \
        -e SERVICES=apigateway,s3,lambda,es,iam,cloudwatch \
        -e DEFAULT_REGION=${REGION} \
        -e DEBUG=1 \
        -p 443:443 \
        -p 4567-4596:4567-4596 \
        -p 8081:8080 \
        -v $PWD:$PWD \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v /tmp/localstack:/tmp/localstack \
        localstack/localstack:latest

    sleep 20
}

create_es() {
    awslocal es create-elasticsearch-domain --domain-name workspace --region ${REGION}
    curl -sS -X PUT -H "Content-Type: application/json" -d @es/doc_mapping.json http://localhost:4571/workspace
    # The workspace json files are uploaded to ES by S3 triggering.  You can use this cmd to load them manually.
    # curl -sS -X POST -H "Content-Type: application/json" -d @../es/26000000_1400000000.json http://localhost:4571/workspace/doc/26000000_1400000000

    # Create a role for the lambda to use
    awslocal iam create-role --role-name basic_lambda_role --assume-role-policy-document file://iam/basic_lambda_role.json
}

# --------------------Search Suggest-------------------------
create_search_suggest_archive() {
    # Build suggest lambda
    cd search_lambda/suggest
    zip -FSr9 bin/search-suggest.zip * -x "bin/*" -x "test/*" -x "README.md" -x "event_suggest.json"

    # Create suggest lambda in localstack
    awslocal lambda create-function --function-name search_suggest --zip-file fileb://bin/search-suggest.zip --handler search_suggest.lambda_handler --runtime python3.7 --role basic_lambda_role --region ${REGION}

    # Verify search suggest lambda is available
    if ! awslocal lambda  invoke --function-name search_suggest --payload fileb://event_suggest.json bin/outputfile.txt | grep -q '200'; then
      echo "Unable to invoke search suggest lambda"
      exit 1
    fi
}

create_data_load_archive() {
    ROOT_DIR="${1}"
    LAMBDA_DIR="${2}"
    LAMBDA_FUNCTION_NAME="${3}"
    cd "${LAMBDA_DIR}/${LAMBDA_FUNCTION_NAME}"
    cp *.py bin/virtualenvs/ve-dataload/lib/python3.7/site-packages/
    cd bin/virtualenvs/ve-dataload/lib/python3.7/site-packages/
    zip -FSr9 search-${LAMBDA_FUNCTION_NAME}.zip * -x "urllib3-*" -x "requests-2*" -x "elasticsearch5*" -x "elasticsearch-6*" -x "setuptools*" -x "pip*" -x "bin*" -x "setuptools/*" -x "pkg_resources/*"
    log::info "Current working Directory - $(pwd)"

    # Create dataload lambda in localstack
    awslocal lambda create-function --function-name search_data_load --zip-file fileb://search-data_load.zip --handler data_load.lambda_handler --runtime python3.7 --role basic_lambda_role --region ${REGION}

    # Verify dataload lambda is available
    #if ! awslocal lambda  invoke --function-name search_data_load --payload fileb://event_suggest.json bin/outputfile.txt | grep -q '200'; then
    #  echo "Unable to invoke search suggest lambda"
    #  exit 1
    #fi
    cd "${ROOT_DIR}"
}

install_python_modules() {
  VENV_PATH="${1}"
  REQUIREMENTS_FILE="${2}"
  log::info "VENV_PATH and Requirements File - ${VENV_PATH} and ${REQUIREMENTS_FILE}"
  cd ${VENV_PATH}
  if [[ ! $(command -v virtualenv) ]]
  then
      log::warn "Cannot find virtualenv; installing virtualenv"
      python3.7 -m pip install virtualenv
  fi
  # virtualenv ${VENV_PATH}
  python3.7 -m venv ${VENV_PATH}
  source ${VENV_PATH}/bin/activate
  ${VENV_PATH}/bin/pip3.7 install -r "${REQUIREMENTS_FILE}"
  deactivate
  cd ${root_dir}
}

create_rest_api() {
    REST_API_ID=$(awslocal apigateway create-rest-api --name search --region ${REGION} | jq -r '.id')
    echo ${REST_API_ID}
}

# --------------------Setup API Gateway-------------------------
create_api_gateway_suggest_config() {
    # passed in REST_API_ID
    PARENT_ID=$(awslocal apigateway get-resources --rest-api-id $1 --region ${REGION} | jq -r '.items | .[0].id')

    # --------------------Search suggest lambda config--------------
    # Create resource - suggest
    RESOURCE_ID=$(awslocal apigateway create-resource --rest-api-id $1 --path-part suggest --parent-id ${PARENT_ID} --region ${REGION} | jq -r '.id')

    # Create GET method on resouce
    RESOURCE_METHOD=$(awslocal apigateway put-method --rest-api-id $1 --resource-id ${RESOURCE_ID} --http-method GET --authorization-type NONE --region ${REGION} | jq -r '.httpMethod')

    # Set lambda function as the destination for the GET method:
    API_GATEWAY=$(awslocal apigateway put-integration --rest-api-id $1 --resource-id ${RESOURCE_ID} \
    --region ${REGION} \
    --http-method GET --type AWS_PROXY --integration-http-method POST \
    --uri arn:aws:apigateway:${REGION}:lambda:path/functions/arn:aws:lambda:${REGION}:000000000000:function:search_suggest \
    --passthrough-behavior WHEN_NO_MATCH \
    --endpoint-url=http://localhost:4567)

    # Set response of api to JSON
    API_RESPONSE_STATUS=$(awslocal apigateway put-method-response --rest-api-id $1 \
    --region ${REGION} \
    --resource-id ${RESOURCE_ID} --http-method GET \
    --status-code 200 --response-models application/json=Empty | jq -r '.statusCode')
    if [[ "${API_RESPONSE_STATUS}" != "200" ]]
    then
        log::error "FATAL: Unable to set response type of suggest api gateway: ${API_RESPONSE_STATUS}"
        exit 1
    fi

    # Set response of lambda fn to JSON
    LAMBDA_RESPONSE_STATUS=$(awslocal apigateway put-integration-response --rest-api-id $1 \
    --region ${REGION} \
    --resource-id ${RESOURCE_ID} --http-method GET \
    --status-code 200 --response-templates application/json="" | jq -r '.statusCode')
    if [[ "${LAMBDA_RESPONSE_STATUS}" != "200" ]]
    then
        log::error "FATAL: Unable to set response type of suggest lambda: ${LAMBDA_RESPONSE_STATUS}"
        exit 1
    fi

    echo ${PARENT_ID}
}

deploy_test_api_gateway() {
    #$REST_API_ID is passed in
    # Deploy the api gateway:
    API_GATEWAY_ID_QUERY=$(awslocal apigateway create-deployment --rest-api-id $1 --stage-name test --region ${REGION} | jq -r '.id')

    # Test suggest api gateway endpoint.
    API_GATEWAY_SUGGEST_URL="http://localhost:4567/restapis/$1/test/_user_request_/suggest?q=high&workGroups=1086&subscriberId=4281"
    API_GATEWAY_SUGGEST_RESP=$(curl -sS ${API_GATEWAY_SUGGEST_URL})
    log::info "API_GATEWAY_SUGGEST_URL: ${API_GATEWAY_SUGGEST_URL}"
    #log::info "API_GATEWAY_SUGGEST_RESP: ${API_GATEWAY_SUGGEST_RESP}"
}

function create_data_load_s3() {
    awslocal s3api create-bucket --bucket localstack-search --region ${REGION}
    awslocal s3api put-bucket-notification-configuration --bucket localstack-search --region ${REGION} --notification-configuration file://s3/obj_created_trigger.json
    awslocal s3 cp es/workspaces-10000-10002.txt s3://localstack-search/
}

function error() {
    JOB="$0"              # job name
    LASTLINE="$1"         # line of error occurrence
    LASTERR="$2"          # error code
    log::error "ERROR in ${JOB} : line ${LASTLINE} with exit code ${LASTERR}"
    exit 1
}
trap 'error ${LINENO} ${?}' ERR

#Main
check_dependencies
kill_docker
install_python_modules "${root_dir}/search_lambda/data_load/bin/virtualenvs/ve-dataload" "${root_dir}/search_lambda/data_load/requirements/requirements.in"
exit_on_error
start_docker
create_es
create_search_suggest_archive
create_data_load_archive "${root_dir}" "${root_dir}/search_lambda" "data_load"
REST_API_ID=$(create_rest_api)
PARENT_ID=$(create_api_gateway_suggest_config "$REST_API_ID")
deploy_test_api_gateway "$REST_API_ID"
create_data_load_s3