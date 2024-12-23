from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient
import configparser
import hashlib
import json
import os

config = configparser.ConfigParser()
config.read('config.ini')

stroage_connection_string = config['AzureStorage']['STORAGE_CONNECTION_STRING']
blob_service_client = BlobServiceClient.from_connection_string(stroage_connection_string)

CONTAINER_NAME = "chathistory"

def create_container(container_name):
    blob_service_client.create_container(container_name)

def delete_container(container_name):
    blob_service_client.delete_container(container_name)

def get_blob_data( blob_name, container_name = CONTAINER_NAME):
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        data = blob_client.download_blob().readall().decode("utf-8")
        data_list = json.loads(data)
        return data_list
        
    except Exception as e:
        container_client.upload_blob(name= blob_name, data="[]")
        return []

# download blob data and store as the file name with "chat_history.json" on loacl
def download_blob(blob_name, container_name = CONTAINER_NAME):
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    data = blob_client.download_blob().readall()
    with open("chat_history.json", "wb") as file:
        file.write(data)
    

def upload_blob( blob_name, data, container_name = CONTAINER_NAME):
    container_client = blob_service_client.get_container_client(container_name)
    container_client.upload_blob(name= blob_name, data=data, overwrite=True)

def delete_blob(blob_name, container_name = CONTAINER_NAME):
    container_client = blob_service_client.get_container_client(container_name)
    container_client.delete_blob(blob_name)

def list_blobs(container_name = CONTAINER_NAME):
    container_client = blob_service_client.get_container_client(container_name)
    return [blob.name for blob in container_client.list_blobs()]

def hash_username(username):
    return hashlib.sha256(username.encode()).hexdigest()


# def get_blob_data():
    
#     container_name = 'storagecommoncontainer'
#     blob_name = 'sample3.txt'

#     # set client to access azure storage container
#     blob_service_client = BlobServiceClient(account_url= account_url, credential= credentials)

#     # get the container client 
#     container_client = blob_service_client.get_container_client(container=container_name)

#     # download blob data 
#     blob_client = container_client.get_blob_client(blob= blob_name)

#     data = blob_client.download_blob().readall().decode("utf-8")

#     print(data)

# def list_blob():
#     container_name = 'storagecommoncontainer'

#     # set client to access azure storage container
#     blob_service_client = BlobServiceClient(account_url= account_url, credential= credentials)

#     # get the container client 
#     container_client = blob_service_client.get_container_client(container=container_name)

#     for blob in container_client.list_blobs():
#         print(blob.name)


# def get_multi_blob_data():
#     container_name = 'storagecommoncontainer'

#     # set client to access azure storage container
#     blob_service_client = BlobServiceClient(account_url= account_url, credential= credentials)

#     # get the container client 
#     container_client = blob_service_client.get_container_client(container=container_name)

#     for blob in container_client.list_blobs():
#         blob_client = container_client.get_blob_client(blob= blob.name)
#         data = blob_client.download_blob().readall()
#         print(data.decode("utf-8"))

# def upload_blob():
#     local_dir = "input"
#     container_name = 'storagecommoncontainer'

#     # set client to access azure storage container
#     blob_service_client = BlobServiceClient(account_url= account_url, credential= credentials)

#     # get the container client 
#     container_client = blob_service_client.get_container_client(container=container_name)

#     # read all files from directory
#     filenames = os.listdir(local_dir)
    
#     for filename in filenames :
#         # get full file path
#         full_file_path = os.path.join(local_dir, filename) 

#         # read files and upload data to blob storage container 
#         with open(full_file_path, "r") as fl :
#             data = fl.read()
#             container_client.upload_blob(name= filename, data=data)

# # main
if __name__ == "__main__":
    # list all blobs in container
    print(list_blobs())
#     #get_blob_data()
#     #list_blob()
#     #get_multi_blob_data()
#     # upload_blob()
#     username = 'testuser1'
#     hashed_username = hash_username(username)
#     blob_name = hashed_username + '.json'

#     # get data from azure storage
#     get_data = get_blob_data(blob_name)
#     print(get_data)
    
#     # blob_service_client.create_container(containr_name)
#     # data = get_blob_client(containr_name, 'testblob').download_blob().readall().decode("utf-8")
#     # print(data)
#     pass