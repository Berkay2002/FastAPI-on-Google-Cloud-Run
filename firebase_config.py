import os
import json
import tempfile
from firebase_admin import credentials, initialize_app, storage
from firebase_admin.exceptions import FirebaseError
import logging

logger = logging.getLogger(__name__)

class FirebaseImageUploader:
    def __init__(self):
        self.app = None
        self.bucket = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            import firebase_admin
            if len(firebase_admin._apps) > 0:
                self.app = firebase_admin.get_app()
            else:
                # Try to get service account from environment variable
                service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
                bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET')
                
                if service_account_json and bucket_name:
                    # Parse the JSON from environment variable
                    service_account_info = json.loads(service_account_json)
                    
                    # Create credentials from the parsed JSON
                    cred = credentials.Certificate(service_account_info)
                    
                    # Initialize the app
                    self.app = initialize_app(cred, {
                        'storageBucket': bucket_name
                    })
                    
                    logger.info(f"Firebase initialized with bucket: {bucket_name}")
                else:
                    logger.warning("Firebase credentials not found in environment variables")
                    return
            
            # Get storage bucket
            self.bucket = storage.bucket()
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            self.app = None
            self.bucket = None
    
    def upload_image(self, image_data: bytes, filename: str, content_type: str = 'image/png') -> str | None:
        """
        Upload image data to Firebase Storage and return public URL
        
        Args:
            image_data: Raw image bytes
            filename: Name of the file (should include extension)
            content_type: MIME type of the image
        
        Returns:
            Public URL of the uploaded image, or None if upload failed
        """
        if not self.bucket:
            logger.error("Firebase bucket not initialized")
            return None
        
        try:
            # Create a unique path for the image (add timestamp to avoid conflicts)
            import time
            timestamp = int(time.time())
            blob_name = f"plots/{timestamp}_{filename}"
            
            # Create blob and upload
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(image_data, content_type=content_type)
            
            # Make the blob publicly accessible
            blob.make_public()
            
            # Return public URL
            public_url = blob.public_url
            logger.info(f"Successfully uploaded image to: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload image {filename}: {str(e)}")
            return None
    
    def is_configured(self) -> bool:
        """Check if Firebase is properly configured"""
        return self.bucket is not None

# Global instance
firebase_uploader = FirebaseImageUploader()
