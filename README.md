# yolo-datasets-app
App prototype for importing and displaying YOLO datasets

## YOLO Datasets Hub

### Description:
This is a basic full-stack web application built with Python, Flask, and MongoDB Atlas along with HTML (with the help of Bootstrap) and CSS as markup languages. This app allows you to import YOLO datasets into the platform, list the uploaded datasets and drill down to display the images with labels for the specific datasets. To use this application code you will need to upload the dataset to your own free Atlas database and input your Atlas connection string in the main.py and helpers.py files. 

### Dependencies
- The web program is written in Python 3 with the Flask framework.
- Python library dependencies: Flask, requests, Python re, Python date, pymongo (+ gunicorn and Werkzeug for Google Cloud Run)
- HTML and CSS are used as markup languages for the basic frontend.

### Deployment

You will need to have a MongoDB Atlas and Google Cloud Storage account set up for the deployment

#### Development server (local machine):
- Create a virtual environment for your code with: ```python3 -m venv .venv; ./.venv/bin/activate; pip3 install -r requirements.txt; python3 main.py```

#### Staging server (Google Cloud Run)
- Create a Google Cloud project according to https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service and install the Google Cloud CLI
- Run ```gcloud run deploy --source .``` to deploy the service

### Approach and Trade-Off
- The application is divided into three core use cases: list all uploaded datasets, upload a dataset, list images with labels for specific datasets
- The application is designed to run on Google Cloud Run + Google Cloud Storage using MongoDB Atlas, these are done in order to make the app more scalable
  - Database connection URI is separated in config.py file that does not get checked into source control (ideally this should be stored in GCP Secret Manager in production environment)
- Data model is divided into several collections in yolo_datasets database:
  - datasets: List of datasets and their summaries (Columns: `_id, task, name, description, upload_time, size`)
  - dataset_classes: List of object classes available for labelling in the dataset (Columns: `_id, dataset_id, class_id, class_name`)
  - dataset_images: List of images in the uploaded dataset (Columns: `dataset_id, image_set, image_name, image_url`)
  - dataset_labels: All labeling data in the uploaded dataset (Columns: `dataset_id, image_set, image_name, class_id, label_data`)
- The front-end is limited to basic Bootstrap/CSS to minimize development complexity (as it is out of scope) 
  - Image list does not include image processing to highlight the objects yet (although the labels for each image are listed)
  - Currently image_url refers to static URL of uploaded image assets (ideally it should be dynamic to allow CDN use)
- There is no user authentication and session data as users and auth is out of scope
- Currently dataset extraction and processing is done during upload time in the same application
  - Ideally (as the dataset can be huge) the extraction processing should be done separately using Google Cloud PubSub, once the dataset zip file has been uploaded
