import sys
import os
import json
import requests
import tempfile
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QComboBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from zipfile import ZipFile
import shutil


class MHInstaller(QWidget):
    # URL к update.json
    UPDATE_JSON_URL = "https://github.com/goosedev72-projects/MH-FreeInstaller/raw/refs/heads/main/update.json"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MH Installer")
        self.setMinimumWidth(400)

        # Иконка приложения
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Переменные
        self.update_data = None
        self.gd_folder = ""
        self.geode_path = ""

        # Создание интерфейса
        self.create_ui()

        # Загрузка начальных данных
        self.load_update_data()

    def create_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        title_label = QLabel("Select MH version to install")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Выбор версий
        versions_layout = QHBoxLayout()

        self.gd_combo = QComboBox()
        self.gd_combo.currentTextChanged.connect(self.update_mh_versions)
        versions_layout.addWidget(QLabel("GD Version:"))
        versions_layout.addWidget(self.gd_combo)

        self.mh_combo = QComboBox()
        versions_layout.addWidget(QLabel("MH Version:"))
        versions_layout.addWidget(self.mh_combo)

        layout.addLayout(versions_layout)

        # Кнопка обновления MH List
        self.update_list_btn = QPushButton(
            "Update MH List", clicked=self.reload_update_data
        )
        layout.addWidget(self.update_list_btn)

        # Выбор папки GD
        folder_layout = QHBoxLayout()

        self.folder_label = QLabel("Select GD Folder:")
        folder_layout.addWidget(self.folder_label)

        self.select_folder_btn = QPushButton("...", clicked=self.select_gd_folder)
        folder_layout.addWidget(self.select_folder_btn)

        layout.addLayout(folder_layout)

        # Кнопка установки
        self.install_btn = QPushButton("Install", clicked=self.install_mh)
        layout.addWidget(self.install_btn)

        self.setLayout(layout)

    def load_update_data(self):
        try:
            response = requests.get(self.UPDATE_JSON_URL)
            response.raise_for_status()
            self.update_data = response.json()

            # Обновить комбобоксы
            self.update_gd_versions_ui()

            # Сообщение об успехе
            QMessageBox.information(
                self, "Update Success", "MH list updated successfully!"
            )

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(
                self,
                "Network Error",
                f"Failed to load update data from GitHub: {str(e)}",
            )
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", "Failed to parse update.json")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load update data: {str(e)}")

    def reload_update_data(self):
        reply = QMessageBox.question(
            self,
            "Confirm Update",
            "Are you sure you want to update the MH list from GitHub?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.load_update_data()

    def update_gd_versions_ui(self):
        # Очистить комбобоксы
        self.gd_combo.clear()
        self.mh_combo.clear()

        if self.update_data and "gd_versions" in self.update_data:
            gd_versions = list(self.update_data["gd_versions"].keys())
            self.gd_combo.addItems(gd_versions)

            # Установить первую версию по умолчанию
            if gd_versions:
                self.update_mh_versions(gd_versions[0])

    def update_mh_versions(self, gd_version):
        self.mh_combo.clear()

        if not self.update_data or not gd_version:
            return

        gd_data = self.update_data["gd_versions"].get(gd_version)
        if not gd_data:
            return

        # Получить доступные MH версии с указанием варианта
        mh_versions = []
        for mh_data in gd_data.get("mh_versions", []):
            version = mh_data["version"]
            variant = mh_data["variant"]
            mh_version_label = f"{version} ({variant.capitalize()})"
            mh_versions.append(
                (mh_version_label, version, variant)
            )  # (отображение, версия, вариант)

        # Сортировка версий (по версии, по убыванию)
        mh_versions.sort(key=lambda x: x[1], reverse=True)

        # Добавляем в комбобокс
        for label, _, _ in mh_versions:
            self.mh_combo.addItem(label)

    def select_gd_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select GD Folder")
        if folder:
            self.gd_folder = folder
            self.folder_label.setText(f"Selected GD folder: {folder}")

            # Проверить папку на наличие необходимых файлов
            if not self.check_gd_folder():
                QMessageBox.warning(
                    self,
                    "Invalid Folder",
                    "Selected folder doesn't contain required GD files",
                )

    def check_gd_folder(self):
        if not self.update_data or not self.gd_combo.currentText():
            return False

        gd_version = self.gd_combo.currentText()
        gd_data = self.update_data["gd_versions"].get(gd_version)
        if not gd_data:
            return False

        required_files = gd_data.get("required_files", [])

        # Проверить наличие всех требуемых файлов
        for file in required_files:
            if not os.path.exists(os.path.join(self.gd_folder, file)):
                return False

        # Проверить наличие папки geode/mods для Geode версии MH
        self.geode_path = os.path.join(self.gd_folder, "geode", "mods")
        if not os.path.exists(self.geode_path):
            try:
                os.makedirs(self.geode_path)
            except Exception as e:
                QMessageBox.warning(
                    self, "Error", f"Failed to create geode/mods folder: {str(e)}"
                )
                return False

        return True

    def install_mh(self):
        if not self.gd_folder:
            QMessageBox.warning(self, "Error", "Please select GD folder first")
            return

        if not self.check_gd_folder():
            QMessageBox.warning(self, "Error", "GD folder is invalid")
            return

        gd_version = self.gd_combo.currentText()
        mh_combo_text = self.mh_combo.currentText()

        if not gd_version or not mh_combo_text:
            QMessageBox.warning(self, "Error", "Please select both GD and MH versions")
            return

        # Извлечение версии и варианта
        try:
            version_part, variant_part = mh_combo_text.split(" (")
            variant = variant_part.rstrip(")").lower()
            mh_version = version_part.strip()
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid MH version format in combobox")
            return

        # Найти данные для выбранной версии MH
        gd_data = self.update_data["gd_versions"].get(gd_version)
        if not gd_data:
            QMessageBox.critical(self, "Error", "GD version data not found")
            return

        mh_data = None
        for data in gd_data.get("mh_versions", []):
            if data["version"] == mh_version and data["variant"] == variant:
                mh_data = data
                break

        if not mh_data:
            QMessageBox.critical(self, "Error", "MH version data not found")
            return

        # Скачать и установить MH
        try:
            self.download_and_install(mh_data)
            QMessageBox.information(self, "Success", "MH installed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to install MH: {str(e)}")

    def download_and_install(self, mh_data):
        base_url = self.update_data.get(
            "base_url",
            "https://github.com/goosedev72-projects/MH-FreeInstaller/raw/refs/heads/main/",
        )
        variant = mh_data["variant"]
        mh_version = mh_data["version"]

        # Генерация URL
        if mh_data["variant"] == "geode":
            download_url = (
                f"{base_url}/megahack/geode/{mh_version}/absolllute.megahack.geode"
            )
        else:
            download_url = f"{base_url}/megahack/default/{mh_version}/lib.zip"

        file_name = os.path.basename(download_url)

        # Скачивание
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, file_name)
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            # Установка
            if mh_data["variant"] == "geode":
                shutil.copy(file_path, os.path.join(self.geode_path, file_name))
            else:
                with ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(self.gd_folder)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    installer = MHInstaller()
    installer.show()
    sys.exit(app.exec())
