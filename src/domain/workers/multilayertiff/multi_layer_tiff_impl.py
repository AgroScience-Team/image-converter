import os
import tempfile

import rasterio
from minio import Minio
from pydantic import parse_obj_as

from ioc.anotations.beans.component import Component
from ioc.common_logger import log
from src.domain.models.multi_layer_tiff import MultiLayerTiff
from src.domain.workers.worker import Worker


@Component()
class MultiLayerTiffWorkerImpl(Worker):

    def __init__(self) -> None:
        self.minio_client = Minio(
            'localhost:9000',
            access_key='minioadmin',
            secret_key='minioadmin',
            secure=False
        )

        self.bucket_name = "agro-photos"
        self.output_folder = "converted"

    def key(self) -> str:
        return "MultiLayerTiff"

    def process(self, id: str, doc):
        # Преобразуем doc в объект MultiLayerTiff
        multi_layer_tiff: MultiLayerTiff = parse_obj_as(MultiLayerTiff, doc)

        # Путь к мультиканальному TIFF в S3
        path_multi_tif = f"new/{id}.{multi_layer_tiff.photoExtension}"

        # Обрабатываем TIFF файл
        self._process_tiff_file(id, path_multi_tif, multi_layer_tiff)

    def _process_tiff_file(self, id: str, path_multi_tif: str, multi_layer_tiff: MultiLayerTiff):
        """Основная функция для обработки TIFF файла."""
        extension: str = multi_layer_tiff.photoExtension
        try:
            log.info(f"Запуск обработки TIFF файла с id {id}.")

            # Создаем временный файл для хранения скачанного файла
            with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=False) as temp_tif_file:
                local_tif_path = temp_tif_file.name
                log.info(f"Скачиваем TIFF файл из Minio в {local_tif_path}")

                # Скачиваем TIFF файл из Minio
                self.minio_client.fget_object(self.bucket_name, path_multi_tif, local_tif_path)

                # Открываем TIFF файл
                with rasterio.open(local_tif_path) as multi_tif:
                    profile = multi_tif.profile
                    num_bands = multi_tif.count

                    # Обрабатываем только первые N каналов (где N — длина списка слоев)
                    num_layers = len(multi_layer_tiff.layers)
                    log.info(f"Найдено {num_bands} каналов, ожидается {num_layers}. Пропускаем лишние.")

                    for band_idx in range(1, min(num_bands, num_layers) + 1):
                        layer_name = multi_layer_tiff.layers[band_idx - 1]  # Имя слоя
                        self._process_tiff_layer(id, local_tif_path, band_idx, layer_name, profile, multi_layer_tiff.photoExtension)

            # Удаляем локальный мультиканальный TIFF файл после обработки
            if os.path.exists(local_tif_path):
                os.remove(local_tif_path)
                log.info(f"Локальный мультиканальный TIFF файл {local_tif_path} удален.")

        except Exception as e:
            log.error(f"Ошибка при обработке TIFF файла: {str(e)}")

    def _process_tiff_layer(self, id: str, local_tif_path: str, band_idx: int, layer: str, profile, extension: str):
        """Чтение и обработка одного канала изображения."""
        try:
            log.info(f"Начало обработки канала {layer} (канал {band_idx})")

            # Обновляем профиль для одного канала
            single_band_profile = profile.copy()
            single_band_profile.update(count=1)  # Указываем, что в новом файле только 1 канал

            # Формируем имя выходного файла
            file_name = f"{id}-{layer}.{extension}"

            # Создаем временный файл для записи одного канала
            with tempfile.NamedTemporaryFile(suffix=f"_{layer}.{extension}", delete=False) as temp_file:
                output_path = temp_file.name
                log.info(f"Начало записи во временный файл для канала {layer}")

                # Открываем исходный TIFF файл и создаем новый TIFF для каждого канала
                with rasterio.open(local_tif_path) as multi_tif, rasterio.open(output_path, 'w', **single_band_profile) as dst_band:
                    # Чтение и запись всего канала
                    band_data = multi_tif.read(band_idx)
                    dst_band.write(band_data, indexes=1)

                log.info(f"Файл для канала {layer} создан: {output_path}")

                # Загружаем файл в Minio
                self._upload_to_minio(output_path, file_name)

        except Exception as e:
            log.error(f"Ошибка при обработке канала {layer}: {str(e)}")

        finally:
            # Удаляем временный файл после загрузки в Minio
            if os.path.exists(output_path):
                os.remove(output_path)
                log.info(f"Временный файл {output_path} удален.")

    def _upload_to_minio(self, file_path, file_name):
        """Загрузка файла в Minio."""
        try:
            object_name = f"{self.output_folder}/{file_name}"
            self.minio_client.fput_object(
                self.bucket_name, object_name, file_path, content_type='image/tiff'
            )
            log.info(f"Файл {file_name} загружен в Minio.")
        except Exception as e:
            log.error(f"Ошибка при загрузке файла {file_name} в Minio: {str(e)}")
