import os
from minio import Minio
from minio.error import S3Error
from datetime import timedelta
from dotenv import load_dotenv, find_dotenv
import os

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path, override=True)

class MinioManager:
    """Wrapper for MinIO S3 operations."""
    def __init__(self):
        self.endpoint = os.getenv("MINIO_URL", "minio.nextai.asia")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minio-admin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "aLongPassword123")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "eko.ecommercetest")
        self.secure = str(os.getenv("MINIO_SECURE", "true")).lower() == "true"
        
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Ensure bucket exists upon initialization
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Created MinIO bucket: {self.bucket_name}")
        except S3Error as err:
            print(f"MinIO Bucket Error: {err}")

    def upload_file(self, object_name: str, file_path: str, content_type: str = "image/png"):
        """Uploads a local file to the MinIO bucket."""
        try:
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type
            )
            return object_name
        except S3Error as err:
            print(f"MinIO Upload Error: {err}")
            raise err

    def get_presigned_url(self, object_name: str, expires_in_hours: int = 24) -> str:
        """Generates a secure temporary URL for frontend image rendering."""
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(hours=expires_in_hours)
            )
            return url
        except S3Error as err:
            print(f"MinIO Presigned URL Error: {err}")
            return ""

# Singleton Instance
minio_db = MinioManager()
