# localstack-dev
[LocalStack](https://github.com/localstack/localstack) lets you to easily develop and more importantly, contineously test AWS services based applications, all on your local docker without needing access to the AWS cloud infrastructure.  I wanted to make a set of notes that came in handy for me, as I didn't find much documentation to to setup and use localstack.

# Infrastructure setup using LocalStack
We will use LocalStack using the AWS command line to create the infrastructure needed for a search api.  
![LocalStack search architecture](/images/LocalStackSearch.png)

## Steps
### Install the latest python3 and aws cli using pip. 
https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html
Make sure you use python3 as the python 2.7 support will be deprecated soon and I found some strange python version errors when with aws tools when I was using the python 2.7 versions of the tools.

If you had previously installed the aws cli using the bundled installer, you can uninstal it using:
https://docs.aws.amazon.com/cli/latest/userguide/install-bundle.html#install-bundle-uninstall
Then you can reinstall the latest using pip.

## Prerequisite
Make sure these components are installed.

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

## Running the localstack setup script
To create our localstack environment:
```
./create_localstack_env.sh
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
NB. If your localstack ip address is different to 172.17.0.2, then you will need to change the ip address specified in the lambdas.


### Look at what infra has been created
http://localhost:8081/#/infra
This will open up your deployed resources console.  It will be empty.

### Create an Elasticsearch domain
Since we have defined that we will be using a "es" service in the docker-compose.yml above. We can now make use of it, by creating a domain called "workspace".

```
awslocal es create-elasticsearch-domain --domain-name workspace
```
You will see a json output with the created DomainStatus: {}.  In this json response,  you can use the Endpoint value to hit ES. "Endpoint": "http://localhost:4571".

If you refresh the web url. http://localhost:8080/#/infra
You will see the Elasticsearch workspace.

### Create a document json file called 26000001_1400000001
```json
{
   "propertys":[
      {
         "lotInUnregisteredPlan": "Lot number 2",
         "lvReportAddress": "222 Bourke St, Melbourne VIC 3000",
         "landIdentifier":"333/885",
         "id":124,
         "address":"223 Bourke St, Melbourne VIC 3000"
      },
      {
         "lotInUnregisteredPlan": "Lot number 1",
         "lvReportAddress": "111 Bourke St, Melbourne VIC 3000",
         "landIdentifier":"222/885",
         "id":123,
         "address":"112 Bourke St, Melbourne VIC 3000"
      }
   ],
   "participant":{
      "status":"ACTIVE",
      "role":"Role1",
      "id":1400000001,
      "reference":"MY Reference",
      "subscriberId":1111
   },
   "workspace":{
      "status":"IN_PREPARATION",
      "jurisdiction":"VIC",
      "number":"no-20001",
      "workgroups":[
         123,
         456,
         678
      ],
      "id":26000001
   },
   "parties":[
      {
         "id":111,
         "name":"Pary 1"
      },
      {
         "id":112,
         "name":"Party 2"
      }
   ]
}
```

### Upload the document into Elasticsearch domain for indexing
Upload a document with id 26000001_1400000001 into workspace domain under doc.
```
curl -v -X POST -H "Content-Type: application/json" -d @26000001_1400000001.json http://localhost:4571/workspace/doc/26000001_1400000001
```

### See the document is in the ES index.
You should see the newly added document.
```
http://localhost:4571/workspace/
```

## Lambda configuration
### Create a role 
Create a new role that the lambda can use.  Create a file basic_lambda_role.json
```
{
    "Version": "2019-04-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": { "AWS" : "*" },
        "Action": "sts:AssumeRole"
    }]
}
```
Load the lambda
```
awslocal iam create-role --role-name basic_lambda_role --assume-role-policy-document file://basic_lambda_role.json
```

### Create lambda
```
awslocal lambda create-function --function-name search_suggest --zip-file fileb://search-suggest.zip --handler search_suggest.lambda_handler --runtime python3.7 --role basic_lambda_role 
```

### Test lambda
```
awslocal lambda  invoke --function-name pexa_search_suggest --payload fileb://event_suggest.json outputfile.txt
```

## API Gateway
Createa an API gateway to trigger the lambda.
```
awslocal apigateway create-rest-api --name SearchOperations
```


### References
https://lobster1234.github.io/2017/04/05/working-with-localstack-command-line/

