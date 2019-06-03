# Using LocalStack for development
[LocalStack](https://github.com/localstack/localstack) lets you to easily develop and more importantly, contineously test AWS services based applications, all on your local docker without needing access to the AWS cloud infrastructure.  I wanted to make a set of notes that came in handy for me, as I didn't find much documentation to to setup and use localstack.

# Infrastructure setup using LocalStack
We will use LocalStack using the AWS command line to create the infrastructure needed for a search api.  
![LocalStack search architecture](/images/LocalStackSearch.png)
We will create an elasticsearch instance, with documents indexed when a lambda is triggered to S3 insert.  The search lamdba is exposed to the user via the API gateway.  This lambda will query elasticsearch to retrieve matching documents.

---

## Prerequisites
Make sure these components are installed.

### Install the latest python3 and aws cli using pip. 
https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html
Make sure you use python3 as the python 2.7 support will be deprecated soon and I found some strange python version errors when with aws tools when I was using the python 2.7 versions of the tools.

If you had previously installed the aws cli using the bundled installer, you can uninstal it using:
https://docs.aws.amazon.com/cli/latest/userguide/install-bundle.html#install-bundle-uninstall
Then you can reinstall the latest using pip.

### Install docker
[Docker for mac](https://docs.docker.com/docker-for-mac/install/)

### Install aws cli using pip3
[aws cli](https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html)
Make sure you install aws cli using pip3 instructions from the middle of the page in the above link.
aws needs to be in you path.

### Install awslocal
[awslocal](https://github.com/localstack/awscli-local)
This is a handy tool that will let you use awslocal directly to hit the local instance rather than having to specify --endpoint local urls.

### Install jq JSON parse used in the run script 
[jq](https://stedolan.github.io/jq/) - command-line JSON processor
```
brew install jq
```

---


## Running the localstack setup script
To create our localstack environment:
```
./create_localstack_env.sh
```
After the scripts runs successfully, it will print out the API Gateway end point url to use, to hit the search-lambda.
**NB.** The restapi id is **dynamic**, so everytime you create a new localstack environment, this id will change.
```
INFO: API_GATEWAY_SUGGEST_URL: http://localhost:4567/restapis/2790A-Z89004/test/_user_request_/suggest?q=high&workGroups=1086&subscriberId=4281
```

### Check docker logs to verify image localstack/localstack:latest has started
```
docker ps
docker logs CONTAINER_ID (to see the logs of localstack)
```

### Verify internal IP address of localstack.
I had a lot of issues with inter docker container communications inside localstack.  I was expecting that when I used localhost from a lambda running in one docker container, that I would have been able to connect to elastic search running on another container, all inside localstack. This turned out not to be the case.  Refer: https://github.com/localstack/localstack/issues/1277

What I had to do was ssh into localstack, and use ifconfig to get the localstacks ip address:
```
docker exec -it localstack /bin/bash
ifconfig
```
**NB.** If your localstack ip address is different to 172.17.0.2, then you will need to change the ip address specified in the lambdas.


### Look at what infra has been created
http://localhost:8081/#/infra
This will open up your deployed resources console.  It should have 2 lambda functions (search-suggest and data-load), elasticsearch instance, S3.  It will not show the API gateway even though its configured to call the search-suggest lambda. 

---

## Query search-suggest lambda via the API Gateway
```
curl -X GET \
  'http://localhost:4567/restapis/2790A-Z89004/test/_user_request_/suggest?q=collins&workGroups=1086&subscriberId=4281' 
```

## Query ElasticSearch directly
To list all documents in ElasticSearch
```
curl -X GET \
  http://localhost:4571/_search \
```

## List documents in S3
```
awslocal s3 ls s3://localstack-search/
```

## Upload a document into S3
This will trigger the data load lambda on upload, which will index the document contents into ElasticSearch.
```
awslocal s3 cp es/workspaces-1000-2000.json s3://localstack-search/
```

---

### References
https://lobster1234.github.io/2017/04/05/working-with-localstack-command-line/

