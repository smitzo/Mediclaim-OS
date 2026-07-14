from io import BytesIO
from app.services.documents import S3Documents, object_key
from app.core.config import settings


def test_private_s3_contract_without_network(monkeypatch):
    monkeypatch.setattr(settings, "s3_bucket", "synthetic-private-bucket")
    class Client:
        def put_object(self, **kwargs):
            assert kwargs["ServerSideEncryption"] == "AES256"
            assert kwargs["Bucket"] == "synthetic-private-bucket"
            assert kwargs["ChecksumSHA256"]
            self.body = kwargs["Body"]
        def get_object(self, **kwargs): return {"Body": BytesIO(self.body)}
        def delete_object(self, **kwargs): self.body = None
    client = Client()
    objects = S3Documents(client)
    key = object_key("tenant-synthetic", "a"*32)
    objects.put(key, b"%PDF-synthetic")
    assert objects.get(key) == b"%PDF-synthetic"
    objects.delete(key)
    assert client.body is None
