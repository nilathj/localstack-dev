# localstack-dev
How to start using localstack for local aws development

[LocalStack](https://github.com/localstack/localstack) lets you to easily develop and more inportantly, contineously test aws services based application, all on your local pc without needing access to the AWS cloud infrastructure.  I wanted to make a set of notes that came in handy for me, when I started this journey, developing and testing applicaitons locally that use AWS services.

## Steps
### Install the latest python3 and aws cli using pip. 
https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html
Make sure you use python3 as the python 2.7 support will be deprecated soon and I found some strange python version errors when with aws tools when I was using the python 2.7 versions of the tools.

If you had previously installed the aws cli using the bundled installer, you can uninstal it using:
https://docs.aws.amazon.com/cli/latest/userguide/install-bundle.html#install-bundle-uninstall
Then you can reinstall the latest using pip.

### Install docker
https://docs.docker.com/install/

### Install awslocal
https://github.com/localstack/awscli-local
This is a handy tool that will let you use awslocal directly to hit the local instance rather than having to specify --endpoint local urls.

### Create a new directory for your project and start localstack using docker.  
You can define the AWS services that you want started when docker localstack starts up.  In this excersise, I'm going to build and Elasticsearch instance, with a lambda for searching.  The lambda requires the creation of an IAM role and I'm going to use the API geteway to connect to the lambda. 

```
docker run --name $docker_name -d \
    -e LAMBDA_EXECUTOR=docker \
    -e DOCKER_HOST=unix:///var/run/docker.sock \
    -e SERVICES=cloudformation,s3,sts,lambda,cloudwatch \
    -e DEBUG=1 \
    -p 443:443 \
    -p 4567-4596:4567-4596 \
    -p 8080:8080 \
    -v $PWD:$PWD \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /tmp/localstack:/tmp/localstack \
    localstack/localstack:latest
```

Start local lambda python 3.7 docker container.  This container will be used by localstack to run your python 3.7 lambda.
```
docker run -v "$PWD":/var/task lambci/lambda:python3.7
```

### Check docker logs to verify the two containers have started
```
docker ps
docker logs CONTAINER_ID (for localstack and lambci/lambda)
```

### Look at what infra has been created
http://localhost:8080/#/infra
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
awslocal lambda  invoke --function-name pexa_search_suggest --payload fileb://event_suggest.json outputfile.txt

### References
https://lobster1234.github.io/2017/04/05/working-with-localstack-command-line/

