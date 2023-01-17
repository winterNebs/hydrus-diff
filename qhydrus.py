from PyQt6.QtCore import QObject, QThread, pyqtSignal

from hydrus import HydrusAPI, HydrusImage

from typing import List


class RandomPotentialThread(QThread):
    images = pyqtSignal(list)

    def __init__(self, hydrus: HydrusAPI, parent=None):
        super().__init__(parent)
        self.hydrus = hydrus

    def run(self):
        print("getting potential images")
        images = self.hydrus.get_random_potentials()
        print("done getting potential images")
        self.images.emit(images)
        self.deleteLater()


class RandomImageBuffer(QObject):
    # use a queue XD

    __buffer = []
    BUFFER_SIZE = 10
    no_more = pyqtSignal()
    images_ready = pyqtSignal()
    feed_me = pyqtSignal(list)
    __emit_time = False
    __threads = []

    def __init__(self, hydrus: HydrusAPI, parent=None):
        super().__init__(parent)
        self.hydrus = hydrus
        for _ in range(self.BUFFER_SIZE):
            self.__get_images()

    def __get_images(self):
        thread = RandomPotentialThread(self.hydrus)
        thread.images.connect(self.__get_images_callback)
        thread.start()
        self.__threads.append(thread)

    def __get_images_callback(self, images: List[HydrusImage]):
        self.__buffer.append(images)
        if self.__emit_time:
            print(self.__buffer)
            self.feed_me.emit(self.__buffer.pop(0))
            self.__emit_time = False

    def get_images(self):
        print("buffer", len(self.__buffer))
        if len(self.__buffer) > 0:
            self.feed_me.emit(self.__buffer.pop(0))
            self.__emit_time = False
        else:
            self.__emit_time = True

        print("to loop", self.BUFFER_SIZE - len(self.__buffer))
        for _ in range(self.BUFFER_SIZE - len(self.__buffer)):
            self.__get_images()
