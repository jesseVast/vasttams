'''
S3 data class
'''
import logging
import boto3
from os.path import exists
from os import makedirs
from re import sub
from urllib.parse import quote
from traceback import print_exc

S3_FETCH_MAX=1000
TMP_FOLDER="/tmp"

logger = logging.getLogger(__name__)

class VastS3:
    '''
    Returns a S3 session.
    s3session=S3(end_point_url,access_Key,secret_Key)
        Returns an S3 session Object

    Use the session.
    session=s3session.get_session()
    session.list_objects_v2(...)
    '''

    def __init__(self,end_point_url: str,access_key: str, secret_key: str) -> None:
        '''
        VastS3(end_point_url,access_Key,secret_Key)
        Returns an Vast S3 session.

        Example:
        # setup credentials
        s3_session = S3(end_point_url,access_Key,secret_Key)

        # get session
        s3_session.get_session()
        Returns a connection object to the S3 Bucket.
        '''
        
        logger.info("Endpoint: %s, Access_key= %s, Secret_key=XXXXXX",end_point_url,access_key)
        self._session = boto3.session.Session()
        self.url = end_point_url
        self._session = self._session.client(
                                service_name='s3',
                                aws_access_key_id=access_key,
                                aws_secret_access_key=secret_key,
                                endpoint_url=end_point_url)
        logger.info("Session Created")

    def get_session(self) -> None:
        '''
        get_session() -> object
        '''
        return self._session

    def _list_bucket(self,bucket_name,prefix) -> list:
        '''
        _list_bucket(bucket_name,prefix)
        Returns a list of object keys in the "bucket" starting with "prefix"
        '''
        logger.info("Get bucket (%s) list with prefix (%s)",bucket_name,prefix)
        s3_list=[]
        last_key=""
        while True:
            if last_key == "":
                response = self._session.list_objects_v2(Bucket = bucket_name,
                                                           Prefix = prefix)
                if 'Contents' in response:
                    s3_list = response['Contents']
                    last_key = s3_list[-1]['Key']
            else:
                response = self._session.list_objects_v2(Bucket = bucket_name,
                                                           Prefix=prefix,
                                                           StartAfter=last_key)
                if 'Contents' in response:
                    tmp_list = response['Contents'][1:]
                else:
                    break
                    
                if tmp_list[-1]['Key'] == last_key:
                    break
                else:
                    s3_list.extend(tmp_list[1:])
                    last_key = tmp_list[-1]['Key']
        logger.info("Fetched (%d) objects",len(s3_list))
        return s3_list     

    def list_bucket(self,bucket_name,prefix="",num_objects=1000) -> list:
        '''
        list_bucket(bucket_name,prefix,num_objects)
        Returns a list of object keys in the "bucket" starting with "prefix" and 
        "num_objects"
        if num_objects = -1, then the entire list is fetched.

        S3 list_object_v2 call has a limit of 1000 objects per fetch. This function could
        return a large number of objects so handle the output list with run time checks.
        '''
        logger.info("Get bucket (%s) list with prefix (%s) and num_objects (%d)",bucket_name,prefix,num_objects)
        s3_list=[]
        # Three cases.
        # 1. Number of objects requested is less than the max supported by s3 api (1000)
        # 2. Number of objects requested is greater than the max supported by s3 api (1000)
        # 3. Number of objects == -1, means all objects

        # Case 3.
        if num_objects == -1:
            logger.info("Fetching all objects in bucket")
            s3_list = self._list_bucket(bucket_name,prefix)
        
        # Case 1.
        elif num_objects < S3_FETCH_MAX:
            response = self._session.list_objects_v2(Bucket = bucket_name,
                                                      Prefix = prefix,
                                                      MaxKeys= num_objects)
            if 'Contents' in response:
                s3_list = response['Contents']
            else:
                logger.warning("Zero objects fetched.")
                return []
        elif num_objects > 0 :
            # Case 2
            # We need to track number of objects fetched. This helps optimize how much
            # we fetch.
            obj_remaining = num_objects
            # We also need to know the last key fetched so we can use it as a marker
            # for the next fetch.
            last_key=""
            while obj_remaining > 0:
                logger.info("Objects remaining: %s", obj_remaining)
                if not last_key:
                    # First time fetch with max objects supported.
                    response = self._session.list_objects_v2(Bucket = bucket_name,
                                                           Prefix = prefix)
                    if 'Contents' in response:
                        s3_list = response['Contents']
                        last_key = s3_list[-1]['Key']
                    else:
                        logger.warning("Zero objects fetched")
                        return []
                    logger.info("Fetched... %d objects so far.",len(s3_list))
                else:
                    # not the first fetch.
                    if obj_remaining > S3_FETCH_MAX:
                        response = self._session.list_objects_v2(Bucket = bucket_name,
                                                               Prefix=prefix,
                                                               StartAfter=last_key)
                    else:
                        # MaxKeys=obj_remaining+2
                        # We need 2 extra becuase we have to remove the head plus the tail.
                        response = self._session.list_objects_v2(Bucket = bucket_name,
                                                               Prefix=prefix,
                                                               StartAfter=last_key,
                                                                MaxKeys=obj_remaining+2)
                    if 'Contents' in response:
                        tmp_list = response['Contents'][1:]
                    else:
                        break
                        
                    if tmp_list[-1]['Key'] == last_key:
                        # We have all the objects.
                        break
                    else:
                        # more objects to come.
                        s3_list.extend(tmp_list[1:])
                        last_key = tmp_list[-1]['Key']
                        logger.info("Fetched... %d objects so far.",len(s3_list))
                obj_remaining = num_objects-len(s3_list)
                        
        logger.info("Fetched (%d) objects",len(s3_list))
        return s3_list
    
    def download_object(self,bucket_name: str, s3_object_key: str,dest_filepath: str):
        '''
        download_object(bucket_name,s3_object_key,dest_directory)
         Download the s3_object_key from the bucket_name and put it in the directory
         dest_dirtory.
         Returns the full path to the downloaded file.
        '''
        logger.info("Downloading %s from bucket %s to %s",s3_object_key,bucket_name,dest_filepath)
        # check is tmp dir exists
        # if not exists(dest_directory):
        #     logger.debug("Creating tmp directory.")
        #     makedirs(dest_directory,exist_ok=True)
        
        # create the file_name
        # file_name=sub('/','_',s3_object_key)
        # if use_file_name:
        #     dest_filename = f'{dest_directory}/{file_name}'

        try:
            self._session.download_file(bucket_name, quote(s3_object_key), str(dest_filepath))
        except Exception as e:
            logger.error("Could not download object (%s) from bucket(%s) as %s",s3_object_key,bucket_name,dest_filepath)
            logger.error(f"{print_exc(e)}")
            raise(e)
        logger.info("Downloaded file to %s",dest_filepath)
        return dest_filepath
    
    def obj_data_stream(self,bucket_name: str, s3_key: str) -> any:
        '''
        obj_data_stream(self,bucket_name: str, s3_key: str)
        Stream the s3_key in bucket bucket_name as a iostream
        '''
        logger.info("Streaming data from from bucket %s and key %s",bucket_name,s3_key)
        try:
            return self._session.get_object(Bucket=bucket_name, Key=quote(s3_key))['Body']
        except Exception as e:
            logger.error("Could not stream object (%s) from bucket(%s)",s3_key,bucket_name)
            logger.error(f"{print_exc(e)}")
            raise(e)

    def get_presigned_url(self,bucket_name: str, s3_object_key: str,expiration_time_s: int=3600) -> str:
            '''
            get_presigned_url(self,bucket_name: str, s3_object_key: str,expiration_time_s: int=3600) -> str:
            Get the s3 presigned url for the s3_object in the bucket. Only supports GET.
                bucket_name: The bucket name
                s3_object_key: The s3 object name(key) that needs to be converted to a pre signed URL
                expiration_time: How long is the signed URL valid in seconds [Default 3600 seconds = 1 Hour]
            '''

            # Generate presigned URL
            presigned_url = self._session.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': quote(s3_object_key)},
                ExpiresIn=expiration_time_s
            )
            logger.info(f"Presigned URL for {s3_object_key}: {presigned_url}")
            return presigned_url
    
    def get_tags(self,bucket_name: str, s3_object_key: str) -> dict:
        '''
        get_tags(self,bucket_name: str, s3_object_key: str) -> dict:
        Get S3 tags for the s3_object
            bucket_name: The bucket name
            s3_object: The s3 object whose tags we need.
        '''
        try:
            tags = self._session.get_object_tagging(Bucket=bucket_name,
                                               Key=quote(s3_object_key)) 
        except Exception as e:
            logger.error(f"Failed to get Tags for {s3_object_key} due to {e}")
            logger.error(f"{print_exc(e)}")
        tags = dict(list(map(lambda a: (a['Key'],a['Value']),tags['TagSet'])))
        logging.info(f"Tags for {s3_object_key}: {tags}")
        return tags

    def add_tags(self,bucket_name: str, s3_object_key: str, tags: dict) -> bool:
        '''
        add_tags(self,bucket_name: str, s3_object_key: str, tags: dict) -> bool
        Add S3 tags to a object
            bucket_name: The bucket name
            s3_object_key: The s3 object (key) whose tags we need.
            tags: dictionary of KV pairs to be added to the object
        '''
        # convert all values in tags to string
        safetags =  [ {'Key': k,'Value': str(v)} for k,v in tags.items()]
        logger.info(f'Tagging object {s3_object_key} in bucket {bucket_name} with tags {safetags}')
        # Add tags
        try:
            _ = self._session.put_object_tagging(Bucket = bucket_name,
                                                 Key = quote(s3_object_key),
                                                 Tagging = { 'TagSet': safetags}
            )
        except Exception as e:
            logger.error(f'Failed to add tags to {s3_object_key} in bucket {bucket_name}  to {e}')
            logger.error(f"{print_exc(e)}")
            return False
        logger.info(f'Success adding tags to object {s3_object_key} in bucket {bucket_name}')
        return True
    

    def put_object(self,bucket_name: str, key: str, data: bytes, tags: dict=None) -> bool:
        '''
        put_object(self,bucket_name: str, key: str, data: bytes, tags: dict=None) -> bool:
        Put an object into bucket
        '''
        logger.info(f"Putting object: {key} into bucket:{bucket_name} with tags: {tags}")
        try:
            if tags:
                result = self._session.put_object(Bucket=bucket_name,
                                                Key=key,
                                                Body=data,
                                                Tagging="&".join(list(map(lambda x: f"{x[0]}={x[1]}",tags.items())))
                                                )
            else:
                result = self._session.put_object(Bucket=bucket_name,
                                                Key=key,
                                                Body=data)
        except Exception as e:
            logger.error(f"Object: {key} put failed due to {print_exc(e)}")
        return True if result else False