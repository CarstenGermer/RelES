#!/usr/bin/env python
# coding: utf-8

"""An example and test data for categories."""

from __future__ import absolute_import, print_function, unicode_literals

import httplib
from urlparse import urljoin
import sys

from flask import json
from requests import Session


RELES_URL = 'http://localhost:8080'


if __name__ == '__main__':
    # Have a clean ES to start with
    # Start the RelES server to create the indices and have the API up and running
    # ./manage.py categories import data/categories.csv
    # ./manage.py customers create mycustomer
    # ./manage.py permissions grant mycustomer customer=read reles=read media=read
    # ./manage.py permissions grant mycustomer customer=write reles=write media=write
    # ./manage.py users create (your email) mycustomer
    # Open http://127.0.0.1:8080/login with a browser and save the resulting token_file
    # Start this code with the token file as parameter
    # $ python models_post.py <token_file>

    jwt = open(sys.argv[1])
    client = Session()
    client.headers['Authorization'] = 'Bearer %s' % jwt.read()

    # upload two pictures to RELES

    with open('examples/modelcheck/files/filterallthethings.jpeg', 'rb') as f:
        data = f.read()

    response = client.post(
        'http://localhost:8080/cdn/files/',
        files={'file': ('filterallthethings.jpeg', data, 'image/jpeg')},
        allow_redirects=False
    )
    if response.status_code != 201:
        print('Failed to upload picture:', response.content, response.status_code)
        sys.exit()
    else:
        object_data = json.loads(response.content)
        pic01path = object_data['path'].lstrip('/')
        print ('Successfully uploaded picture', pic01path)

    with open('examples/modelcheck/files/Heroesjourney.svg.png', 'rb') as f:
        data = f.read()

    response = client.post(
        'http://localhost:8080/cdn/files/',
        files={'file': ('Heroesjourney.svg.png', data, 'image/png')},
        allow_redirects=False
    )
    if response.status_code != 201:
        print('Failed to upload picture:', response.content, response.status_code)
        sys.exit()
    else:
        object_data = json.loads(response.content)
        pic02path = object_data['path'].lstrip('/')
        print ('Successfully uploaded picture', pic02path)

    # create documents in /media/pictures to use as article pic later
    pictures_url = urljoin(RELES_URL, '/media/pictures/')

    # Create picture1
    response = client.post(pictures_url, json={
        "title": "filterallthethings",
        "credit": "memebase 2010",
        "production_date": "2010-08-22",
        "picture": {
            "title": "iiznotteautofill?",
            "sys_filename": pic01path,
            "file_format": "JPG"
        }
    })
    if response.status_code == httplib.CREATED:
        print('Successfully created picture 1:', response.content)
        object_data = json.loads(response.content)
        pic01id = object_data['_id']
    else:
        print ('Failed to create picture 1:', response.content, response.status_code)
        sys.exit()

    # Create picture2
    response = client.post(pictures_url, json={
        "title": "heroesjourney",
        "credit": "storybase 1998",
        "production_date": "1998-08-22",
        "picture": {
            "title": "iiznotteautofill?",
            "sys_filename": pic02path,
            "file_format": "PNG"
        }
    })
    if response.status_code == httplib.CREATED:
        print('Successfully created picture 2:', response.content)
        object_data = json.loads(response.content)
        pic02id = object_data['_id']
    else:
        print('Failed to create picture 2:', response.content, response.status_code)
        sys.exit()

    # Create two /reles/venues
    # includes snippets: reles, entityname, adress, contact

    venues_url = urljoin(RELES_URL, '/reles/venues/')

    # Create venue 1

    response = client.post(venues_url, json={
        # "reles" : {} will be autofilled
        "entityname": {
            "officialname": "Chez Burger",
            "alternate_names_de": [
                "Großbürger"
            ],
            "alternate_names_en": [
                "Masses for the Masses"
            ]
        },
        "address": {
            "postal_address": "Rathausmarkt 1, 20095 Hamburg",
            "geo_point": "53.5497212,9.992299299999999"
        },
        "contact": {
            "phones": [
                {
                    "description": "Zentrale",
                    "number": "+49 40 428312064"
                }
            ],
            "webpages": [
                {
                    "description": "General Information",
                    "URL": "http://hamburg.de/"
                }
            ]
        }
    })

    if response.status_code == httplib.CREATED:
        print('Successfully created venue 1:', response.content)
        object_data = json.loads(response.content)
        venue01id = object_data['_id']
    else:
        print('Failed to create venue 1:', response.content, response.status_code)
        sys.exit()

    # Create venue 2

    response = client.post(venues_url, json={
        # "reles" : {} will be autofilled
        "entityname": {
            "officialname": "Joy",
            "alternate_names_de": [
                "Uhlenkniep"
            ],
            "alternate_names_en": [
                "z Joyz"
            ]
        },
        "address": {
            "postal_address": "Winterhuder Weg 69, 22085 Hamburg",
            "geo_point": "53.5774741,10.0182598"
        },
        "contact": {
            "phones": [
                {
                    "description": "Tresen",
                    "number": "+49 40 2279278"
                }
            ],
            "webpages": [
                {
                    "description": "Homepage",
                    "URL": "http://joy-hamburg.net/"
                }
            ]
        }
    })

    if response.status_code == httplib.CREATED:
        print('Successfully created venue 2:', response.content)
        object_data = json.loads(response.content)
        venue02id = object_data['_id']
    else:
        print('Failed to create venue 2:', response.content, response.status_code)
        sys.exit()

    # create two customer/restaurants
    ferests_url = urljoin(RELES_URL, '/customer/restaurants/')

    # Create customer restaurant 1

    response = client.post(ferests_url, json={
        # "reles" is autofilled
        "parent_venue": venue01id,
        "local_cuisine_categories": [
            "NAM",
            "DEU"
        ],
        "maincourse": {
            "from": 7.60,
            "currency": "EUR"
        },
        "customer_rating": [
            {
                "rating": 4,
                "year": "2016"
            }
        ],
        "accepted_currencies": [
            "EUR",
            "USD"
        ],
        "accepted_paycards": [
            "EC",
            "Visa"
        ]

    })

    if response.status_code == httplib.CREATED:
        print('Successfully created restaurant 1:', response.content)
        object_data = json.loads(response.content)
        restaurant01id = object_data['_id']
    else:
        print('Failed to create restaurant 1:', response.content, response.status_code)
        sys.exit()

    # Create customer restaurant 2

    response = client.post(ferests_url, json={
        # "reles" is autofilled
        "parent_venue": venue02id,
        "local_cuisine_categories": [
            "NORDIC",
            "DEU-SACHS"
        ],
        "maincourse": {
            "from": 16,
            "currency": "EUR"
        },
        "customer_rating": [
            {
                "rating": 5,
                "year": "2016"
            }
        ],
        "accepted_currencies": [
            "EUR",
            "DKK"
        ],
        "accepted_paycards": [
            "EC",
            "Visa",
            "Amex"
        ]

    })

    if response.status_code == httplib.CREATED:
        print('Successfully created restaurant 2:', response.content)
        object_data = json.loads(response.content)
        restaurant02id = object_data['_id']
    else:
        print('Failed to create restaurent 2:', response.content, response.status_code)
        sys.exit()

    # create two customer/articles
    fearticles_url = urljoin(RELES_URL, '/customer/articles/')

    # create customer article 1

    response = client.post(fearticles_url, json={
        # "reles" is autofilled
        "parent_venue": venue02id,
        "pictures": [
            pic01id
        ],
        "print_de": {
            "headline": "Futter, Darts und Kicker!",
            "subheadline": "Alles, nur heute, nur hier.",
            "teaser": "Im Joyz zieht der Duft von Gulaschsuppe und Pizza Hot Dog über den Kickertisch.",
            "text": "dolor something something *mumble*",
            "tags": "for, comma, seperated, whatever"
        }
    })

    if response.status_code == httplib.CREATED:
        print('Successfully created article 1:', response.content)
        object_data = json.loads(response.content)
        article01id = object_data['_id']
    else:
        print('Failed to create article 1:', response.content, response.status_code)
        sys.exit()

    # create customer article 2

    response = client.post(fearticles_url, json={
        # "reles" is autofilled
        "parent_venue": venue01id,
        "pictures": [
            pic02id
        ],
        "print_de": {
            "headline": "Steaks und Fisch. immer frisch",
            "subheadline": "Der älteste Kalauer der Welt, nur hier.",
            "teaser": "Fischsuppe von Feinbiss und zum Nachtisch ein Steak.",
            "text": "dolor something somthing *mumble*",
            "tags": "for, comma, seperated, whatever"
        }
    })

    if response.status_code == httplib.CREATED:
        print('Successfully created article 2:', response.content)
        object_data = json.loads(response.content)
        article02id = object_data['_id']
    else:
        print('Failed to create article 2:', response.content, response.status_code)
        sys.exit()
