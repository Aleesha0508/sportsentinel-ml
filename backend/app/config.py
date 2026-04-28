from google.cloud import firestore
from google.cloud import storage

PROJECT_ID = "sportssentinel"


def get_firestore_client():
    return firestore.Client(project=PROJECT_ID)


def get_storage_client():
    return storage.Client(project=PROJECT_ID)