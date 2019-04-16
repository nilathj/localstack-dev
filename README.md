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

### Install docker and docker-compose
https://docs.docker.com/compose/install/

### Install awslocal
https://github.com/localstack/awscli-local
This is a handy tool that will let you use awslocal directly to hit the local instance rather than having to specify --endpoint local urls.

### Create a new directory for your project and a docker-compose.yml file in it.  
This yml file defines your infrastructure services that you want to build locally.  In this excersise, I'm going to build and Elasticsearch instance.

```json
version: "2.1"

services:
  localstack:
    image: localstack/localstack:latest
    environment:
      - "SERVICES=${LOCALSTACK_SERVICES:-es,s3,lambda}"
      - "DEFAULT_REGION=${AWS_REGION:-us-east-1}"
      - "HOSTNAME=${LOCALSTACK_HOSTNAME:-localhost}"
      - "HOSTNAME_EXTERNAL=${LOCALSTACK_HOSTNAME_EXTERNAL:-localhost}"
      - "USE_SSL=false"
    volumes:
      - ./templates:/opt/bootstrap/templates
    ports:
      - "4567-4582:4567-4582"
      - "8080:8080"
```

### Start docker compose
From inside your project directory that you created:
```
docker-compose up
```

It should start up successfully and be ready:
```
...
localstack_1  | Waiting for all LocalStack services to be ready
localstack_1  | Waiting for all LocalStack services to be ready
localstack_1  | Ready.
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
      "id":123,
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
      "id":20001
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

### References
https://lobster1234.github.io/2017/04/05/working-with-localstack-command-line/

