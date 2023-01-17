import json
import requests
import cv2
import numpy as np
import urllib.parse
from enum import Enum
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt6.QtCore import QUrl


class RequestType(Enum):
    PRINT = 0  # Just care about result
    RANDOM_POTENTIAL = 1  # Return hashs


class HydrusAPI:
    def __init__(self, URL, KEY):

        self.CLIENT_URL = URL
        self.API_KEY = KEY
        self.headers = {"Hydrus-Client-API-Access-Key": self.API_KEY}
        self.nam = QNetworkAccessManager()

    def get_url(self, url, callback):
        url = QUrl(self.CLIENT_URL + url)
        request = QNetworkRequest(url)
        request.setRawHeader(
            b"Hydrus-Client-API-Access-Key", bytes(self.API_KEY, "utf-8")
        )
        reply = self.nam.get(request)
        reply.finished.connect(lambda: callback(reply))

        # return requests.get(self.CLIENT_URL + url, headers=self.headers)

    def post_url(self, url, body, callback):
        url = QUrl(self.CLIENT_URL + url)
        request = QNetworkRequest(url)
        request.setRawHeader(
            b"Hydrus-Client-API-Access-Key", bytes(self.API_KEY, "utf-8")
        )
        reply = self.nam.post(request, body)
        reply.finished.connect(lambda: callback(reply))
        # return requests.post(
        #    self.CLIENT_URL + url, headers=self.headers, json=body
        # )

    def get_file(self, hash):
        return self.get_url("/get_files/file?hash=" + hash)

    def get_random_potentials(self):
        # Art
        # 6c6f63616c2066696c6573
        hydrus_images = []
        tags = [
            # "system:num file relationships > 5 potential duplicates",
            "system:file service is currently in art",
        ]
        encoded = urllib.parse.quote(json.dumps(tags))
        print(encoded)
        res = self.get_url(
            "/manage_file_relationships/get_random_potentials?"
            + "tags_1="
            + encoded
            + "&search_type=1"
        )
        print(res.text)
        images = res.json()["random_potential_duplicate_hashes"]
        for img in images:
            content = self.get_file(img)
            hydrus_images.append(HydrusImage(img, content.content))

        return hydrus_images

    def set_best(self, best_hash, other_hashes):
        self.set_relationship(4, best_hash, other_hashes, True, False, True)

    def set_alts(self, hashes):
        self.set_relationship_all(3, hashes, True, False, False)

    def set_false(self, hashes):
        self.set_relationship_all(1, hashes, True, False, False)

    def set_relationship(
        self, relation, best_hash, other_hashes, merge, delete_a, delete_b
    ):
        pair_rows = []
        for worse in other_hashes:
            pair_rows.append(
                [relation, best_hash, worse, merge, delete_a, delete_b]
            )

        json_object = {"pair_rows": pair_rows}

        res = self.post_url(
            "/manage_file_relationships/set_file_relationships", json_object
        )
        print(json_object)
        print(res.status_code, res.text)

    def set_relationship_all(
        self, relation, other_hashes, merge, delete_a, delete_b
    ):
        pair_rows = []
        for one in other_hashes:
            for two in other_hashes:
                pair_rows.append(
                    [relation, one, two, merge, delete_a, delete_b]
                )

        json_object = {"pair_rows": pair_rows}

        res = self.post_url(
            "/manage_file_relationships/set_file_relationships", json_object
        )
        print(json_object)
        print(res.status_code, res.text)

    def delete_all(self, hashes):
        res = self.post_url("/add_files/delete_files", {"hashes": hashes})
        print(res.status_code, res.text)


class HydrusImage:
    def __init__(self, hash, data):
        self.hash = hash
        self.data = data
        self.size = sizeof_fmt(len(data))

        nparr1 = np.frombuffer(self.data, np.uint8)
        self.img = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
        self.height = self.img.shape[0]
        self.width = self.img.shape[1]


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
