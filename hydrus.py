import json
import requests
import cv2
import numpy as np
import urllib.parse
from enum import Enum
from PyQt6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkRequest,
    QNetworkReply,
)
from PyQt6.QtCore import QByteArray, QUrl, QJsonDocument
from typing import List, Callable


class HydrusImage:
    hash: str
    data: str
    size: str
    width: int
    height: int

    def __init__(self, hash, data):
        self.hash = hash
        self.data = data
        self.size = sizeof_fmt(len(data))

        nparr1 = np.frombuffer(self.data, np.uint8)
        self.img = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
        self.height = self.img.shape[0]
        self.width = self.img.shape[1]


class RequestType(Enum):
    PRINT = 0  # Just care about result
    RANDOM_POTENTIAL = 1  # Return hashs


class RandomPotentials:
    images: List[HydrusImage]
    total: int
    callback: Callable[[List[HydrusImage]], None]

    def __init__(
        self, total: int, callback: Callable[[List[HydrusImage]], None]
    ):
        self.total = total
        self.images = []
        self.callback = callback

    def done_callback(self, hash: str, data: QByteArray):
        img = HydrusImage(hash, data)

        self.images.append(img)
        if len(self.images) == self.total:
            self.callback(self.images)


class HydrusAPI:
    nam: QNetworkAccessManager

    def __init__(self, URL, KEY):

        self.CLIENT_URL = URL
        self.API_KEY = KEY
        self.headers = {"Hydrus-Client-API-Access-Key": self.API_KEY}
        self.nam = QNetworkAccessManager()

    def get_url(self, url: str, callback: Callable[[QByteArray], None]):
        url = QUrl(self.CLIENT_URL + url)
        print("2. get url", url)
        request = QNetworkRequest(url)
        request.setRawHeader(
            b"Hydrus-Client-API-Access-Key", bytes(self.API_KEY, "utf-8")
        )
        reply = self.nam.get(request)
        reply.finished.connect(lambda: callback(reply.readAll()))

    def post_url(
        self,
        url: str,
        body,
        callback: Callable[[List[HydrusImage]], None],
    ):
        url = QUrl(self.CLIENT_URL + url)
        request = QNetworkRequest(url)
        request.setRawHeader(
            b"Hydrus-Client-API-Access-Key", bytes(self.API_KEY, "utf-8")
        )
        # QByteArray data("{\"key1\":\"value1\",\"key2\":\"value2\"}");
        reply = self.nam.post(request, body)
        reply.finished.connect(lambda: callback(reply))
        # return requests.post(
        #    self.CLIENT_URL + url, headers=self.headers, json=body
        # )

    def get_file(self, hash, callback):
        return self.get_url("/get_files/file?hash=" + hash, callback)

    def get_random_potentials(
        self, callback: Callable[[List[HydrusImage]], None]
    ):
        # Art
        # 6c6f63616c2066696c6573
        tags = [
            # "system:num file relationships > 5 potential duplicates",
            "system:file service is currently in art",
        ]
        encoded = urllib.parse.quote(json.dumps(tags))
        print("1. getting random potetials")
        self.get_url(
            "/manage_file_relationships/get_random_potentials?"
            + "tags_1="
            + encoded
            + "&search_type=1",
            lambda data: self.__get_random_potentials_images_callback(
                data, callback
            ),
        )

    def __get_random_potentials_images_callback(
        self, data: QByteArray, callback: Callable[[List[HydrusImage]], None]
    ):
        print("3. private", data)
        res = json.loads(bytes(data))
        images = res["random_potential_duplicate_hashes"]
        rp = RandomPotentials(len(images), callback)
        for img in images:
            self.get_file(img, lambda data: rp.done_callback(img, data))

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


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
