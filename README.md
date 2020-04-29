# GCS to SFTP File Dropper
This Cloud Function will listen to a GCS bucket, then sync any newly written files to an SFTP server of your choice.

## Usage
1. Create a Service Account that contains the following permissions:
* Secret Manager Secret Accessor
* Storage Admin

2. Load your SSH key or SFTP password to [Secrets Manager](https://cloud.google.com/secret-manager/docs) and note the name used (in the example below, `sftp-secret`)
```bash
echo -n "my super secret data" | gcloud secrets create sftp-secret \
    --replication-policy=automatic \
    --data-file=-
```

3. Create a file called `.env.yml` in this directory that contains the following, replacing `SECRET_NAME` with the name of the secret you created in Step 2 and filling in the appropriate username and SFTP host.
```yml
SECRET_NAME: sftp-secret
USERNAME: my-username
SFTP_HOST: hostname
BASE_DIR: '' # Custom base directory for files in SFTP
```

4. (Optional) Create a [VPC Connector](https://cloud.google.com/vpc/docs/configure-serverless-vpc-access). If you need access to an SFTP server that uses private IP address or is on-premise, you can create a VPC Connector for this function.
* Use the [console](https://cloud.google.com/vpc/docs/configure-serverless-vpc-access#creating_a_connector) to configure or
* Run the following:
```
gcloud compute networks vpc-access connectors create [CONNECTOR_NAME] \
--network [VPC_NETWORK] \
--region [REGION] \
--range [IP_RANGE]
```

5. Set variables for the GCS bucket you'll sync files to, and for the username created in Step 1.
```
export BUCKET_NAME=<bucket name, do not include gs://>
export SERVICE_ACCOUNT=<service account created above>
```

6. Deploy the GCS function.
```bash
gcloud functions deploy sftp-dropper \
  --source=./src/ \
  --env-vars-file .env.yml \
  --entry-point main \
  --runtime python37 \
  --memory 2048MB \
  --timeout 540s \
  --trigger-resource "${BUCKET_NAME}" \
  --trigger-event google.storage.object.finalize \
  --service-account "${SERVICE_ACCOUNT}" \ 
  --vpc-connector=[projects/${PROJECT}/locations/${LOCATION}/connectors/${CONNECTOR}]
```

## Testing
You can test by dropping a file into your bucket, or by triggering a test in the console using the following trigger event:
```json
{"bucket":"bucket","name":"filename.txt"}
```
