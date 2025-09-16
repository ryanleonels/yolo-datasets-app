import math
import requests
import certifi
import zipfile
import yaml
import json

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
    print(image_data)

    for image in image_data:
        print(class_id)
        print(image_data[image]['labels'])
        if class_id == "" or int(class_id) in image_data[image]['labels']:
            images_with_labels.append(image_data[image])
    
    return images_with_labels

def parse_yaml_file(yaml_filename):
    try:
        f = open(filename, 'r')
        data = yaml.load(f, Loader=yaml.SafeLoader)
        f.close()
    except FileNotFoundError:
        print("YAML file not found")
        return {}
    except yaml.scanner.ScannerError:
        print("Invalid YAML file format")
        return {}
    
    return data

def upload_image(image_url):
    return image_url

def process_zip_file(filename, dataset_id, task = "detect"):
    try:
        with zipfile.ZipFile(filename) as archive:
            if task == "classify": # classify zip = no YAML file, sort images into classes based on directory structure
                yaml_data = {}
                class_names = []
                (train_images, val_images, test_images) = ({}, {}, {})
                for file in archive.namelist():
                    if file[-1] != '/' and file.count('/') >= 2:
                        (image_set, class1, image_name) = file.split('/', 2)
                        if image_set in ['train', 'val', 'test']:
                            if class1 not in class_names:
                                class_names.append(class1)
                            if image_set == 'train':
                                if class1 not in train_images:
                                    train_images[class1] = []
                                train_images[class1].append(image_name) 
                            if image_set == 'val':
                                if class1 not in val_images:
                                    val_images[class1] = []
                                val_images[class1].append(image_name)
                            if image_set == 'test':
                                if class1 not in test_images:
                                    test_images[class1] = []
                                test_images[class1].append(image_name)
                class_names.sort()
                classes = {}
                for i in range(0, len(class_names)):
                    classes[i] = class_names[i]
                class_ids = {}
                for i in classes:
                    class_ids[classes[i]] = i
                images = []
                labels = []
                for class1 in train_images:
                    for image in train_images[class1]:
                        images.append(('train', image, 'train' + '/' + class1 + '/' + image))
                        class_id = class_ids[class1]
                        labels.append(('train', image, class_id, ''))
                for class1 in val_images:
                    for image in val_images[class1]:
                        images.append(('val', image, 'val' + '/' + class1 + '/' + image))
                        class_id = class_ids[class1]
                        labels.append(('val', image, class_id, ''))
                for class1 in test_images:
                    for image in test_images[class1]:
                        images.append(('test', image, 'test' + '/' + class1 + '/' + image))
                        class_id = class_ids[class1]
                        labels.append(('test', image, class_id, ''))
                #print(classes)
                #print(images)
                #print(labels)
            else:
                # list all files
                #archive.printdir()
                # try to find YAML file and main path
                yaml_file = ""
                for file in archive.namelist():
                    #print(file)
                    if file[-5:] == ".yaml":
                        file_info = archive.getinfo(file)
                        if file_info.is_dir() is False:
                            if yaml_file != "":
                                print("Error - Multiple YAML files detected")
                                return False
                            yaml_file = file
                if yaml_file == "":
                    print("Error - No YAML file detected")
                    return False
                print(yaml_file)
                yaml_path = '/'.join(yaml_file.split('/')[:-1])
                if yaml_path != "":
                    yaml_path += "/"
                print(yaml_path)
                # read YAML file to extract paths and class names
                yaml_data = {}
                try:
                    f = archive.open(yaml_file, 'r')
                    data = yaml.load(f, Loader=yaml.SafeLoader)
                    print(data)
                    f.close()
                except FileNotFoundError:
                    print("Error - YAML file cannot be found")
                    return False
                except yaml.scanner.ScannerError:
                    print("Error - Invalid YAML file format")
                    return False
                # get images and labels
                (train_images, val_images, test_images) = ([], [], [])
                (train_labels, val_labels, test_labels) = ({}, {}, {})
                for key in data:
                    print(key, data[key])
                (train_path, val_path, test_path) = (None, None, None)
                if 'train' in data and data['train'] != None:
                    train_path = yaml_path + data['train'] + '/'
                if 'val' in data and data['val'] != None:
                    val_path = yaml_path + data['val'] + '/'
                if 'test' in data and data['test'] != None:
                    test_path = yaml_path + data['test'] + '/'
                for file in archive.namelist():
                    if train_path != None and file.startswith(train_path) and file != train_path:
                        file_info = archive.getinfo(file)
                        if file_info.is_dir() is False:
                            train_images.append(file[len(train_path):])
                    if val_path != None and file.startswith(val_path) and file != val_path:
                        file_info = archive.getinfo(file)
                        if file_info.is_dir() is False:
                            val_images.append(file[len(train_path):])
                    if test_path != None and file.startswith(test_path) and file != test_path:
                        file_info = archive.getinfo(file)
                        if file_info.is_dir() is False:
                            test_images.append(file[len(train_path):])
                classes = {}
                if 'names' in data and data['names'] != None:
                    classes = data['names']
                images = []
                labels = []
                (train_label_path, val_label_path, test_label_path) = ('', '', '')
                if 'train' in data and data['train'] != None:
                    train_label_path = yaml_path + data['train'].replace('images/', 'labels/') + '/'
                if 'val' in data and data['val'] != None:
                    val_label_path = yaml_path + data['val'].replace('images/', 'labels/') + '/'
                if 'test' in data and data['test'] != None:
                    test_label_path = yaml_path + data['test'].replace('images/', 'labels/') + '/'
                for image in train_images:
                    images.append(('train', image, train_path + image))
                    label_filename = '.'.join(image.split('.')[:-1]) + '.txt'
                    if label_filename == '.txt':
                        label_filename = image + '.txt'
                    label_file = train_label_path + label_filename
                    if label_file in archive.namelist():
                        f = archive.open(label_file, 'r')
                        label_data = f.read()
                        f.close()

                        label_lines = label_data.decode().split('\n')
                        for label_line in label_lines:
                            line = label_line.strip()
                            if line != '':
                                class_id = line.split(' ')[0]
                                if class_id.isnumeric():
                                    class_id = int(class_id)
                                labels.append(('train', image, class_id, line))
                for image in val_images:
                    images.append(('val', image, val_path + image))
                    label_filename = '.'.join(image.split('.')[:-1]) + '.txt'
                    if label_filename == '.txt':
                        label_filename = image + '.txt'
                    label_file = val_label_path + label_filename
                    if label_file in archive.namelist():
                        f = archive.open(label_file, 'r')
                        label_data = f.read()
                        f.close()
                        label_lines = label_data.decode().split('\n')
                        for label_line in label_lines:
                            line = label_line.strip()
                            if line != '':
                                class_id = line.split(' ')[0]
                                if class_id.isnumeric():
                                    class_id = int(class_id)
                                labels.append(('val', image, class_id, line))
                for image in test_images:
                    images.append(('test', image, test_path + image))
                    label_filename = '.'.join(image.split('.')[:-1]) + '.txt'
                    if label_filename == '.txt':
                        label_filename = image + '.txt'
                    label_file = test_label_path + label_filename
                    if label_file in archive.namelist():
                        f = archive.open(label_file, 'r')
                        label_data = f.read()
                        f.close()
                        label_lines = label_data.decode().split('\n')
                        for label_line in label_lines:
                            line = label_line.strip()
                            if line != '':
                                class_id = line.split(' ')[0]
                                if class_id.isnumeric():
                                    class_id = int(class_id)
                                labels.append(('test', image, class_id, line))
                #print(classes)
                #print(images)
                #print(labels)
    except zipfile.BadZipFile as error:
        print(error)
        return False

    # write YAML extra data into MongoDB
    yaml_extra_data = {}
    for field in ['train', 'val', 'test', 'kpt_shape', 'flip_idx', 'download']:
        if field in yaml_data:
            yaml_extra_data[field] = yaml_data[field]
    filter_yaml = {'_id': dataset_id}
    yaml_value = { "$set": {'yaml_extra_data': json.JSONEncoder().encode(yaml_extra_data)} }
    client['yolo_datasets']['datasets'].update_one(filter_yaml, yaml_value)

    # write classes, images, labels data into MongoDB
    classes_table = client['yolo_datasets']['dataset_classes']
    images_table = client['yolo_datasets']['dataset_images']
    labels_table = client['yolo_datasets']['dataset_labels']
    for class1 in classes:
        class_data = {'dataset_id': dataset_id, 'class_id': int(class1), 'class_name': classes[class1]}
        client['yolo_datasets']['dataset_classes'].insert_one(class_data)
    for image in images:
        uploaded_image_url = upload_image(image[2])
        image_data = {'dataset_id': dataset_id, 'image_set': image[0], 'image_name': image[1], 'image_url': image[2]}
        client['yolo_datasets']['dataset_images'].insert_one(image_data)
    for label in labels:
        label_data = {'dataset_id': dataset_id, 'image_set': label[0], 'image_name': label[1], 'class_id': label[2], 'label_data': label[3]}
        client['yolo_datasets']['dataset_labels'].insert_one(label_data)

    return True
