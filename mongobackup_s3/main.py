import io
import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from typing import Any

import boto3
from botocore.exceptions import EndpointConnectionError, NoCredentialsError


def load_env_vars() -> dict[str, Any]:
    """Загружает переменные окружения из файла .env"""
    return {
        "mongo_url": os.getenv("MONGO__URL"),
        "mongo_db_name": os.getenv("MONGO__DB_NAME"),
        "s3_endpoint_url": os.getenv("S3_STORAGE__ENDPOINT_URL"),
        "s3_access_key": os.getenv("S3_STORAGE__ACCESS_KEY_ID"),
        "s3_secret_key": os.getenv("S3_STORAGE__SECRET_KEY"),
        "s3_bucket_name": os.getenv("S3_STORAGE__BUCKET_NAME"),
    }


def backup_mongodb_to_memory(uri: str, db_name: str) -> bytes:
    """Делает бэкап базы данных MongoDB и сохраняет его в памяти"""
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    backup_dir = f"/tmp/{db_name}_backup_{timestamp}"

    try:
        args = ["mongodump", "--uri", uri, "--db", db_name, "--out", backup_dir]
        print(args)
        subprocess.run(args, check=True)
        print(f"Бэкап базы данных {db_name} завершен. Путь: {backup_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении mongodump: {e}")
        raise

    backup_io = io.BytesIO()

    with tarfile.open(fileobj=backup_io, mode="w:gz") as tar:
        tar.add(backup_dir, arcname=os.path.basename(backup_dir))

    backup_io.seek(0)

    # Удаляем временную директорию после архивирования
    shutil.rmtree(backup_dir)

    return backup_io.getvalue()


def upload_to_s3(
    file_data: bytes, bucket: str, object_name: str, endpoint_url: str, access_key: str, secret_key: str
) -> bool:
    """Загружает архив в указанный S3 бакет"""
    s3_client = boto3.client(
        "s3", endpoint_url=endpoint_url, aws_access_key_id=access_key, aws_secret_access_key=secret_key
    )

    try:
        s3_client.put_object(Bucket=bucket, Key=object_name, Body=file_data)
        print(f"Файл успешно загружен в {bucket}/{object_name}")
        return True
    except NoCredentialsError:
        print("Учетные данные не найдены")
        return False
    except EndpointConnectionError:
        print("Не удается подключиться к endpoint URL")
        return False


def main() -> None:
    env_vars = load_env_vars()
    mongo_uri = env_vars["mongo_url"]
    db_name = env_vars["mongo_db_name"]
    endpoint_url = env_vars["s3_endpoint_url"]
    access_key = env_vars["s3_access_key"]
    secret_key = env_vars["s3_secret_key"]
    bucket_name = env_vars["s3_bucket_name"]
    s3_object_name = f'backup/{db_name}_backup_{datetime.utcnow().strftime("%Y_%m_%d_%H_%M_%S")}.tar.gz'

    try:
        backup_data = backup_mongodb_to_memory(mongo_uri, db_name)
        uploaded = upload_to_s3(backup_data, bucket_name, s3_object_name, endpoint_url, access_key, secret_key)
        if uploaded:
            print("Загрузка завершена успешно")
        else:
            print("Загрузка завершилась с ошибкой")

        if datetime.utcnow().weekday() == 0 and datetime.utcnow().hour < 1:
            # Еженедельный бэкап по понедельникам
            weekly_s3_object_name = f'weekly_backup/{db_name}_backup_{datetime.utcnow().strftime("%Y_%m_%d_%H_%M_%S")}.tar.gz'
            uploaded = upload_to_s3(backup_data, bucket_name, weekly_s3_object_name, endpoint_url, access_key, secret_key)
            if uploaded:
                print("Загрузка завершена успешно")
            else:
                print("Загрузка завершилась с ошибкой")

        if datetime.utcnow().day == 1 and datetime.utcnow().hour < 1:
            # Ежемесячный бэкап 1 числа
            monthly_s3_object_name = f'monthly_backup/{db_name}_backup_{datetime.utcnow().strftime("%Y_%m_%d_%H_%M_%S")}.tar.gz'
            uploaded = upload_to_s3(backup_data, bucket_name, monthly_s3_object_name, endpoint_url, access_key, secret_key)
            if uploaded:
                print("Загрузка завершена успешно")
            else:
                print("Загрузка завершилась с ошибкой")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        raise


# Пример использования
if __name__ == "__main__":
    main()
