from google.cloud import storage, secretmanager
import paramiko
import os
import logging
from io import StringIO

GCP_PROJECT = os.environ['GCP_PROJECT']
SFTP_HOST = os.environ['SFTP_HOST']
SECRET_NAME = os.environ['SECRET_NAME']
USERNAME = os.environ['USERNAME']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(event, context):
    bucket = event['bucket']
    file_name = event['name']
    if is_valid_operation(context):
        storage_client = storage.Client(GCP_PROJECT)
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(file_name)
        sftp_dropper = SFTPDropper()
        sftp_dropper.write_file(blob, file_name)
        sftp_dropper.close_connection()
    else:
        logger.error("Not a valid event")

def is_valid_operation(context):
    return context.event_type == 'google.storage.object.finalize'

class SFTPDropper:
  def __init__(self):
    logging.getLogger("paramiko").setLevel(logging.INFO)
    try:
      self.ssh_client = paramiko.SSHClient()
      ssh_key = paramiko.RSAKey.from_private_key(StringIO(self.retrieve_ssh_key()))
      self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      self.ssh_client.connect(SFTP_HOST, username=USERNAME, pkey=ssh_key)
    except Exception as e:
      logger.error(e)
  
  def retrieve_ssh_key(self):
    try:
      secrets = secretmanager.SecretManagerServiceClient()
      return secrets.access_secret_version("projects/"+GCP_PROJECT+"/secrets/"+SECRET_NAME+"/versions/latest").payload.data.decode("utf-8")
    except Exception as e:
      logger.error(e)

  def write_file(self, file_object, destination_filename):
    try:
      sftp_client = self.ssh_client.open_sftp()
      with sftp_client.file(destination_filename, 'w') as target:
        file_object.download_to_file(target)
      sftp_client.close()
      logger.info(f'Wrote {file_object} to {SFTP_HOST} at {destination_filename}')
    except Exception as e:
      logger.error(e)
      self.ssh_client.close()
  
  def close_connection(self):
    self.ssh_client.close()
