from google.cloud import storage, secretmanager
import paramiko
import os
import logging
from io import StringIO

GCP_PROJECT = os.environ['GCP_PROJECT']
SFTP_HOST = os.environ['SFTP_HOST']
SECRET_NAME = os.environ['SECRET_NAME']
USERNAME = os.environ['USERNAME']
BASE_DIRECTORY = os.environ['BASE_DIR']
AUTH_MODE = os.environ['AUTH_MODE']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main(event, context):
    bucket = event['bucket']
    file_name = event['name']
    if is_valid_operation(context):
        storage_client = storage.Client(GCP_PROJECT)
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(file_name)
        try:
            sftp_dropper = SFTPDropper()
            sftp_dropper.write_file(blob, destination_filename(file_name))
            sftp_dropper.close_connection()
        except Exception as e:
            logger.error(e)
            raise
    else:
        logger.error("Not a valid event")


def is_valid_operation(context):
    return context.event_type == 'google.storage.object.finalize'


def destination_filename(file_name):
    base_directory = BASE_DIRECTORY.lstrip('/').rstrip('/')
    if base_directory == '':
        return file_name
    else:
        return base_directory + '/' + file_name


class SFTPDropper:

    def __init__(self):
        logging.getLogger("paramiko").setLevel(logging.INFO)
        try:
            self.ssh_client = paramiko.SSHClient()
            self.open_connection()
            self.sftp_client = self.ssh_client.open_sftp()
        except Exception as e:
            self.close_connection()
            raise (e)

    def open_connection(self):
        try:
            if AUTH_MODE == 'SSH':
                logger.info('Using SSH authentication for connection')
                ssh_key = paramiko.RSAKey.from_private_key(
                    StringIO(self.retrieve_sftp_secret()))
                self.ssh_client.set_missing_host_key_policy(
                    paramiko.AutoAddPolicy())
                self.ssh_client.connect(SFTP_HOST,
                                        username=USERNAME,
                                        pkey=ssh_key)
            elif AUTH_MODE == 'PASSWORD':
                logger.info(
                    'Using Username/Password authentication for connection')
                self.ssh_client.set_missing_host_key_policy(
                    paramiko.AutoAddPolicy())
                self.ssh_client.connect(SFTP_HOST,
                                        username=USERNAME,
                                        password=self.retrieve_sftp_secret())
            else:
                logger.error("Must set auth mode SSH or PASSWORD")
        except Exception as e:
            logger.error("Failed to open connection")
            raise (e)

    def retrieve_sftp_secret(self):
        try:
            secrets = secretmanager.SecretManagerServiceClient()
            return secrets.access_secret_version(
                "projects/" + GCP_PROJECT + "/secrets/" + SECRET_NAME +
                "/versions/latest").payload.data.decode("utf-8")
        except Exception as e:
            raise (e)

    def write_file(self, file_object, destination_filename):
        try:
            self.mkdir_p(os.path.dirname(destination_filename))
            with self.sftp_client.file(destination_filename, 'w') as target:
                file_object.download_to_file(target)
            logger.info(
                f'Wrote {file_object} to {SFTP_HOST} at {destination_filename}')
        except Exception as e:
            logger.error(f'Error writing to {destination_filename}')
            self.ssh_client.close()
            raise (e)

    def mkdir_p(self, remote_directory):
        current_dir = './'
        for dir_element in remote_directory.split('/'):
            logger.info(dir_element)
            if dir_element:
                current_dir += dir_element + '/'
                try:
                    logger.info(f'Creating {current_dir}')
                    self.sftp_client.mkdir(current_dir)
                except:
                    pass

    def close_connection(self):
        self.ssh_client.close()
