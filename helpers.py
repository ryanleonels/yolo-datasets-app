import math
import requests
import certifi

from flask import redirect, render_template, request
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from config import *

client = MongoClient(mongodb_uri, server_api=ServerApi('1'), tlsCAFile=certifi.where())

def get_datasets():
    """Gets summary entries for uploaded datasets"""

    datasets = client['yolo_datasets']['datasets'].aggregate([
        {
            '$sort': {
                'upload_time': -1
            }
        },
    ])

    return datasets

def get_dataset_info(dataset_id):
    """Gets summary entry for a dataset"""

    datasets = client['yolo_datasets']['datasets'].aggregate([
        {
            '$sort': {
                'upload_time': -1
            }
        },
    ])

    for dataset in datasets:
        if str(dataset['_id']) == dataset_id:
            return dataset

    return {}

def convert_size(size_bytes):
    """https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python"""
    if size_bytes == 0:
        return "0.0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

def build_datasets_info(datasets, classes, images):
    """Combines counts of classes and images to datasets info"""

    datasets_info = []

    class_data = {}
    for class1 in classes:
        class_data[class1['_id']] = class1['count']

    image_data = {}
    for image1 in images:
        image_data[image1['_id']] = image1['count']

    for dataset in datasets:
        dataset1 = dataset
        dataset1['id'] = str(dataset['_id'])
        if dataset1['id'] in class_data:
            dataset1['classes_count'] = class_data[dataset1['id']]
        else:    
            dataset1['classes_count'] = 0
        if dataset1['id'] in image_data:
            dataset1['images_count'] = image_data[dataset1['id']]
        else:    
            dataset1['images_count'] = 0
        dataset1['dataset_size'] = convert_size(dataset1['size'])
        datasets_info.append(dataset1)

    return datasets_info

def get_classes(dataset_id):
    """Gets list of classes for a dataset"""

    classes = client['yolo_datasets']['dataset_classes'].aggregate([
        {
            '$match': {
                'dataset_id': dataset_id
            }
        }, {
            '$sort': {
                'class_id': 1
            }
        },
    ])

    return classes

def get_class_names(dataset_id):
    """Gets list of classes for a dataset"""

    classes = get_classes(dataset_id)

    class_names = {}
    for class1 in classes:
        class_names[class1['class_id']] = class1['class_name']

    return class_names

def get_label_counts(dataset_id, image_set):
    """Gets counts of labels for a dataset"""

    labels = client['yolo_datasets']['dataset_labels'].aggregate([
        {
            '$match': {
                'dataset_id': dataset_id,
                'image_set': image_set
            }
        }, {
            '$group': {
                "_id": "$class_id",
                "count": {'$sum': 1}
            }
        }, {
            '$sort': {
                'class_id': 1
            }
        },
    ])

    return labels

def build_classes_counts(classes, labels):
    """Combines list of classes and counts of labels for a specific dataset and image set"""

    classes_counts = []

    label_data = {}
    for label1 in labels:
        label_data[label1['_id']] = label1['count']

    for class1 in classes:
        class_count = class1
        if class_count['class_id'] in label_data:
            class_count['count'] = label_data[class_count['class_id']]
        else:    
            class_count['count'] = 0
        classes_counts.append(class_count)

    return classes_counts

def get_class_counts():
    """Gets counts of classes for all datasets"""

    class_counts = client['yolo_datasets']['dataset_classes'].aggregate([
        {
            '$group': {
                "_id": "$dataset_id",
                "count": {'$sum': 1}
            }
        }
    ])

    return class_counts

def get_image_counts():
    """Gets counts of images for all datasets"""

    image_counts = client['yolo_datasets']['dataset_images'].aggregate([
        {
            '$group': {
                "_id": "$dataset_id",
                "count": {'$sum': 1}
            }
        }
    ])

    return image_counts

def get_images(dataset_id, image_set):
    """Gets list of images for a dataset"""

    images = client['yolo_datasets']['dataset_images'].aggregate([
        {
            '$match': {
                'dataset_id': dataset_id,
                'image_set': image_set
            }
        }, {
            '$sort': {
                'image_name': 1
            }
        },
    ])

    return images

def get_labels(dataset_id, image_set):
    """Gets list of image labels for a dataset"""

    image_labels = client['yolo_datasets']['dataset_labels'].aggregate([
        {
            '$match': {
                'dataset_id': dataset_id,
                'image_set': image_set
            }
        }, {
            '$sort': {
                'image_name': 1,
                'class_id': 1
            }
        },
    ])

    return image_labels

def build_images_with_labels(images, image_labels, class_id, class_names):
    """Build list of images with labels for a dataset"""

    images_with_labels = []

    image_data = {}
    for image1 in images:
        image_data[image1['image_name']] = image1
        image_data[image1['image_name']]['labels'] = set()
        image_data[image1['image_name']]['label_names'] = ""
        image_data[image1['image_name']]['label_data'] = []

    for label in image_labels:
        image_name = label['image_name']
        if label['class_id'] not in image_data[image_name]['labels']:
            if image_data[label['image_name']]['label_names'] != "":
                image_data[label['image_name']]['label_names'] += ", "
            image_data[label['image_name']]['label_names'] += class_names[label['class_id']]
            image_data[image_name]['labels'].add(label['class_id'])
        image_data[label['image_name']]['label_data'].append((label['class_id'], label['label_data']))

    for image in image_data:
        if class_id == "" or class_id in image_data[image]['labels']:
            images_with_labels.append(image_data[image])
    
    return images_with_labels
