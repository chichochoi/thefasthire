import os
from google.cloud import storage
from fastapi import UploadFile
import uuid
from datetime import datetime, timedelta


class GCSService:
    def __init__(self):
        self.client = storage.Client()
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        self.bucket = self.client.bucket(self.bucket_name)
    
    async def upload_file(self, file: UploadFile, folder: str = "resumes") -> tuple[str, str]:
        """
        파일을 GCS에 업로드하고 (파일경로, signed URL)을 반환
        """
        # 고유한 파일명 생성
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        blob_name = f"{folder}/{unique_filename}"
        
        # GCS에 업로드
        blob = self.bucket.blob(blob_name)
        
        # 파일 내용 읽기
        file_content = await file.read()
        
        # 업로드
        blob.upload_from_string(
            file_content,
            content_type=file.content_type
        )
        
        # 24시간 동안 유효한 signed URL 생성
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.utcnow() + timedelta(hours=24),
            method="GET",
        )
        
        return blob_name, signed_url
    
    def get_file_content(self, file_path: str) -> bytes:
        """GCS에서 파일 내용을 바이트로 가져오기"""
        blob = self.bucket.blob(file_path)
        return blob.download_as_bytes()
