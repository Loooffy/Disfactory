import os
import logging
from urllib.parse import urljoin
from uuid import uuid4

from django.conf import settings
import requests

import easymap
from .models import Factory, Image

LOGGER = logging.getLogger('django')


def _upload_image_to_imgur(image_buffer, client_id):
    tmp_path = os.path.join(settings.MEDIA_ROOT, f'{uuid4()}.jpg')
    with open(tmp_path, 'wb') as fw:
        fw.write(image_buffer)
    headers = {'Authorization': f'Client-ID {client_id}'}
    data = {'image': image_buffer}
    resp = requests.post(
        'https://api.imgur.com/3/upload',
        data=data,
        headers=headers,
    )
    try:
        resp_data = resp.json()
        if 'errors' in resp_data:
            credit_resp = requests.get(
                'https://api.imgur.com/3/credits',
                headers=headers,
            )
            LOGGER.error(f'Error upload to imgur. The credits remaining: {credit_resp.json()}')
            path = urljoin(urljoin(settings.DOMAIN, settings.MEDIA_URL), os.path.basename(tmp_path))
        else:
            path = resp_data['data']['link']
    except Exception as e:
        LOGGER.error(f'Error parsing imgur response data: {resp_data}')
        path = urljoin(urljoin(settings.DOMAIN, settings.MEDIA_URL), os.path.basename(tmp_path))
    return path


def update_landcode(factory_id):
    factory = Factory.objects.get(pk=factory_id)
    landinfo = easymap.get_land_number(factory.lng, factory.lat)
    landcode = landinfo.get('landno')
    sectname = landinfo.get('sectName')
    sectcode = landinfo.get('sectno')
    townname = landinfo.get('townname')
    towncode = landinfo.get('towncode')
    LOGGER.info(f"Factory {factory_id} retrieved land number {landcode}")
    Factory.objects.filter(pk=factory_id).update(
        landcode=landcode,
        sectcode=sectcode,
        sectname=sectname,
        towncode=towncode,
        townname=townname,
    )


def upload_image(image_path, client_id, image_id):
    LOGGER.info(f'Upload {image_id}: {image_path} with {client_id}')
    try:
        with open(image_path, 'rb') as f:
            image_buffer = f.read()
        path = _upload_image_to_imgur(image_buffer, client_id)
        try:
            Image.objects.filter(pk=image_id).update(image_path=path)
        except Exception as e:
            LOGGER.error(f"""
                Upload success and get imgur url {path},
                but other error happened when update image {image_id}
            """)
    except Exception as e:
        LOGGER.error(f"Upload {image_path} to Imgur with client ID {client_id} failed {e}")


    try:
        os.remove(image_path)
    except Exception as e:
        LOGGER.warning(f"""
            {image_id} upload and write to DB success,
            but other error happened when removing tempfile {image_path}.
        """)
