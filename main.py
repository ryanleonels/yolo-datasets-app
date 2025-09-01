import os
import re
import datetime
import certifi

from flask import Flask, render_template, request
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from config import *
from helpers import *

app = Flask(__name__)

client = MongoClient(mongodb_uri, server_api=ServerApi('1'), tlsCAFile=certifi.where())

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client['yolo_datasets']
datasets_table = db['datasets']

@app.route("/", methods=["GET"])
def datasets():

    # Get list of datasets
    datasets = get_datasets()
    classes = get_class_counts()
    images = get_image_counts()
    datasets_info = build_datasets_info(datasets, classes, images)

    return render_template("datasets.html", datasets_info=datasets_info)

@app.route("/images.html", methods=["GET"])
def images():

    dataset_id = request.args.get('id')

    if dataset_id is not None:
        dataset_info = get_dataset_info(dataset_id)

        image_set = request.args.get('set')
        if image_set is None:
            image_set = "train"

        class_id = request.args.get('class')
        if class_id is None:
            class_id = ""

        classes = get_classes(dataset_id)
        labels = get_label_counts(dataset_id, image_set)
        classes_counts = build_classes_counts(classes, labels)

        images = get_images(dataset_id, image_set)
        image_labels = get_labels(dataset_id, image_set)
        class_names = get_class_names(dataset_id)
        images_with_labels = build_images_with_labels(images, image_labels, class_id, class_names)
        return render_template("images.html", dataset_info=dataset_info, image_set=image_set, class_id=class_id, classes_counts=classes_counts, images_with_labels=images_with_labels)

    return datasets()

@app.route("/upload.html", methods=["GET", "POST"])
def upload():

    # For GET request: Display form for user to upload dataset
    if request.method == "GET":
        return render_template("upload.html")
   
    # For POST request: Get data of dataset from form and add to MongoDB
    # also unzip + parse the contents and add them to the relevant collections
    # Create empty Python dictionary to hold details of the dataset
    dataset_upload = {}

    # Get dataset information from user form submission
    task = request.form.get("task")
    name = request.form.get("name")
    description = request.form.get("description")

    # Get date that user submitted the form
    # Attribution: Found this way to convert time of form submission here: https://www.programiz.com/python-programming/datetime/current-datetime
    upload_time = datetime.datetime.now(datetime.UTC)
    upload_time = upload_time.strftime("%Y-%m-%d %H:%M:%S.%f")

    # upload file
    request.files['file'].save('/tmp/file')
    file_length = os.stat('/tmp/file').st_size

    # Compile upload details into Python dictionary
    dataset_upload["task"] = task
    dataset_upload["name"] = name
    dataset_upload["description"] = description
    dataset_upload["upload_time"] = upload_time
    dataset_upload["size"] = file_length
    
    # Add dataset to MongoDB Atlas database
    dataset_entry = datasets_table.insert_one(dataset_upload)
    dataset_id = str(dataset_entry.inserted_id)

    # Return confirmation message after dataset submission 
    return render_template("imported.html")

if __name__ == "__main__":
    app.run(port=8000)
