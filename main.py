import sys
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QGridLayout,
    QListView,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QWidget,
    QPushButton,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
)
from PyQt6.QtGui import QColor, QIcon, QImage, QPixmap, QPalette
from PyQt6.QtCore import QSize, Qt, pyqtSignal
import cv2 as cv2
import numpy as np
from hydrus import HydrusAPI, HydrusImage
import json

CLIENT_URL = "http://localhost:45869"
API_KEY = sys.argv[1]


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.hydrus = HydrusAPI(CLIENT_URL, API_KEY)

        print(self.hydrus.get_url("/verify_access_key").text)
        print(self.hydrus.get_url("/get_services").text)

        # TODOs:
        # 1. image sorting + hydrus relationship setting
        #   -> ie show best first and bulk do multiple images
        # 2. image comparison
        #   -> subtraction
        #   -> idk otherstuff
        # 3. Image viewer tools. Zoom, swap
        # Some sort of image preview
        #
        # Option to set image as comparioson thingy
        #   -> turns all images into subtractions

        # 2 checkbox to turn images to subtractions

        # Why only getting a few images rather than a lot

        self.showMaximized()
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # --- Control Panel
        self.controls = QVBoxLayout()
        control_widget = QWidget()
        control_widget.setLayout(self.controls)
        self.layout.addWidget(control_widget, 50)

        reload = QPushButton("Reload")
        reload.clicked.connect(self.reset)
        self.controls.addWidget(reload)

        best = QPushButton("Set selected as best and delete others")
        best.clicked.connect(self.set_best)
        self.controls.addWidget(best)

        alts = QPushButton("Set all as alts")
        alts.clicked.connect(self.set_alts)
        self.controls.addWidget(alts)

        false = QPushButton("Set all as false")
        false.clicked.connect(self.set_false)
        self.controls.addWidget(false)

        delete = QPushButton("Delete all")
        delete.clicked.connect(self.set_delete)
        self.controls.addWidget(delete)

        self.preview = QLabel()
        self.controls.addWidget(self.preview)

        # --- Control Panel

        # --- Image Viewer
        self.scroll = QImageDisplayer()

        # self.scroll.currentItemChanged.connect(self.previewItem)
        self.scroll.itemSelectionChanged.connect(self.previewItem)
        self.layout.addWidget(self.scroll, 50)
        # --- Image Viewer

        self.reset()

    def previewItem(self):
        item = self.scroll.get_current_item()
        if item is None:
            return
        pixmap = QPixmap()
        pixmap.loadFromData(item.data)
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
        )

    def reset(self):
        self.scroll.clear()
        self.load_images()
        self.preview.clear()

    def set_best(self):
        # grab selected
        # get rest of images
        best, other = self.scroll.get_hashes_selected()
        if best is None:
            return
        self.hydrus.set_best(best, other)
        self.reset()

    def set_alts(self):
        # grab selected
        # get rest of images
        hashes = self.scroll.get_all_hashes()
        self.hydrus.set_alts(hashes)
        self.reset()

    def set_false(self):
        # grab selected
        # get rest of images
        hashes = self.scroll.get_all_hashes()
        self.hydrus.set_false(hashes)
        self.reset()

    def set_delete(self):
        # grab selected
        # get rest of images
        hashes = self.scroll.get_all_hashes()
        self.hydrus.delete_all(hashes)
        self.reset()

    def load_images(self):
        images = self.hydrus.get_random_potentials()
        images.sort(key=lambda x: len(x.data), reverse=True)
        multiplier, grey, aspect = subtract_image(images[0], images[1])
        if multiplier:

            mult_label = QLabel(
                "Contrast Multiplier (higher means less different): "
                + str(multiplier)
            )
            images.append(HydrusImage("", cv2.imencode(".png", grey)[1]))

        for i, img in enumerate(images):
            self.scroll.addImage(img)


class QImageDisplayer(QListWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setIconSize(QSize(700, 700))
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setDragDropMode(QListView.DragDropMode.NoDragDrop)

    def addImage(self, hydrusImage: HydrusImage):
        item = QListWidgetItem()
        item.setText(
            "{} {}x{}".format(
                hydrusImage.size, hydrusImage.width, hydrusImage.height
            )
        )
        icon = QIcon()
        image = QPixmap()
        image.loadFromData(hydrusImage.data)
        icon.addPixmap(image)
        item.setIcon(icon)
        item.setData(Qt.ItemDataRole.UserRole, hydrusImage)
        self.addItem(item)

    def get_current_item(self):
        items = self.selectedItems()
        if len(items) == 1:
            item = items[0]
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def get_all_hashes(self):
        return [
            self.item(i).data(Qt.ItemDataRole.UserRole).hash
            for i in range(self.count())
            if self.item(i).data(Qt.ItemDataRole.UserRole).hash != ""
        ]

    def get_hashes_selected(self):
        items = self.selectedItems()
        if len(items) == 1:
            selected = items[0].data(Qt.ItemDataRole.UserRole).hash
            if selected == "":
                return None, None
            hashes = [
                self.item(i).data(Qt.ItemDataRole.UserRole).hash
                for i in range(self.count())
                if self.item(i).data(Qt.ItemDataRole.UserRole).hash != selected
                and self.item(i).data(Qt.ItemDataRole.UserRole).hash != ""
            ]
            return selected, hashes
        return None, None


def subtract_image(im1: HydrusImage, im2: HydrusImage):
    img1 = im1.img
    img2 = im2.img

    # Compare image sizes

    aspect = None
    if img1.size != img2.size:
        print("Images resolution do not match")
        print("Attepmting resize")
        aspect = (im1.width / im1.height, im2.width / im2.height)
        print(
            "aspect ratio {} vs {}".format(
                im1.width / im1.height, im2.width / im2.height
            )
        )
        # im1 should be larger
        img2 = cv2.resize(
            img2, (im1.width, im1.height), interpolation=cv2.INTER_NEAREST
        )
        # need to resize the image
    diff = cv2.subtract(img1, img2)
    grey = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, max_val, _, _ = cv2.minMaxLoc(grey)
    multiplier = 255.0 / max_val
    grey = grey * multiplier
    print("Contrast boosted by: " + str(multiplier))
    # cv2.imshow("test", grey)
    # enhance contrast
    return multiplier, grey, aspect


if __name__ == "__main__":
    app = QApplication([])
    main = Main()
    sys.exit(app.exec())
